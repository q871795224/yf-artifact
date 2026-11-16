#!/usr/bin/env python3
"""Read-only item-economy diagnostics; assert replay equality before saving observations."""

import argparse
from collections import Counter
import json
from pathlib import Path

from simulate_expanded_match import ExpandedMatch, CARDS, PROJECT, dump

OUT = PROJECT / 'docs/design/simulations/item-economy-01'
SOURCE = PROJECT / 'docs/design/simulations/match-batch-02/results.json'


class EconomyMatch(ExpandedMatch):
    def __init__(self, *args, **kwargs):
        self.received_items = [[], []]
        self.economy = []
        super().__init__(*args, **kwargs)

    def draw_item(self, team):
        before = len(self.item_deck[team])
        super().draw_item(team)
        if len(self.item_deck[team]) < before:
            self.received_items[team].append(self.item_hand[team][-1][0])

    def item_reason(self, team, item, paid):
        """Reasons refer to this AI's willingness, not all actions allowed by the game."""
        friends = self.field(team)
        heroes = [u for u in friends if u.hero]
        if not paid and CARDS[item]['gold_cost'] > self.gold[team]:
            return 'unaffordable'
        if item in self.gear_ids:
            if not heroes:
                return 'no_hero_in_field'
            if max(self.equipment_value(item, h) for h in heroes) <= 0:
                return 'no_upgrade_by_ai'
        elif item in (3003, 3004):
            if not any(u.hp < u.max_hp for u in friends):
                return 'no_wounded_friend'
        elif item == 3005:
            if not self.deck[team]:
                return 'ordinary_deck_empty'
        elif item == 10211:
            if not self.improvements[1-team]:
                return 'no_enemy_improvement'
        elif item == 3006:
            occupied = {u.pos for u in self.field()}
            row = 7 if team == 0 else 0
            if not any((row, c) not in occupied for c in range(6)):
                return 'fountain_full'
            if not heroes:
                return 'no_hero_in_field'
            if not any(self.incoming_damage(h) >= h.hp for h in heroes):
                return 'no_lethal_retreat_by_ai'
        elif item != 10216:
            raise ValueError(f'Unclassified item {item}')
        return 'usable_by_ai'

    def economy_snapshot(self, team):
        cards = [{'id': item, 'paid': paid, 'reason': self.item_reason(team, item, paid)}
                 for item, paid in self.item_hand[team]]
        if not cards:
            reason = 'empty_item_hand'
        elif any(c['reason'] == 'usable_by_ai' for c in cards):
            reason = 'usable_item_unspent'
        elif all(c['reason'] == 'unaffordable' for c in cards):
            reason = 'unaffordable_only'
        elif all(c['reason'] in ('unaffordable', 'no_hero_in_field') for c in cards):
            reason = 'no_hero_for_affordable_items'
        else:
            affordable = [c for c in cards if c['reason'] != 'unaffordable']
            equipment = sum(c['id'] in self.gear_ids for c in affordable)
            reason = ('equipment_not_wanted' if equipment == len(affordable) else
                      'consumables_not_wanted' if equipment == 0 else 'mixed_not_wanted')
        received_value = sum(CARDS[i]['gold_cost'] for i in self.received_items[team])
        unpaid_hand = sum(CARDS[c['id']]['gold_cost'] for c in cards if not c['paid'])
        spent = self.stats[team]['gold_spent']
        income = self.stats[team]['bounty_income'] + self.stats[team]['payday_income']
        assert received_value == spent + unpaid_hand
        assert income-spent == self.gold[team]
        heroes = [u for u in self.units if u.hero and u.team == team]
        return {'round': self.round, 'team': team, 'gold': self.gold[team], 'income': income,
                'spent': spent, 'drawn_items': len(self.received_items[team]),
                'drawn_item_value': received_value,
                'minimum_gold_if_all_drawn_items_bought': max(0, income-received_value),
                'drawn_equipment': sum(i in self.gear_ids for i in self.received_items[team]),
                'occupied_slots': sum(len(h.equipment) for h in heroes),
                'heroes_with_weapon': sum('Weapon' in h.equipment for h in heroes),
                'heroes_in_field': len(self.field(team)) - sum(not u.hero for u in self.field(team)),
                'reason': reason, 'items': cards}

    def action_phase(self):
        super().action_phase()
        if not self.finished:
            self.economy.extend(self.economy_snapshot(t) for t in (0, 1))


def summarize(games):
    output = []
    for policy in ('greedy', 'push'):
        group = [g for g in games if g['policy'] == policy]
        rows = [s for g in group for s in g['snapshots']]
        high = [s for s in rows if s['gold'] >= 15]
        output.append({'policy': policy, 'games': len(group), 'team_round_snapshots': len(rows),
                       'at_least_15_gold': len(high),
                       'high_gold_reasons': dict(Counter(s['reason'] for s in high)),
                       'high_gold_item_reasons': dict(Counter(c['reason'] for s in high for c in s['items'])),
                       'same_round': {str(turn): {
                           'samples': len(selected),
                           **{key: sum(s[key] for s in selected)/len(selected) for key in
                              ('gold', 'income', 'spent', 'drawn_items', 'drawn_item_value',
                               'minimum_gold_if_all_drawn_items_bought', 'drawn_equipment',
                               'occupied_slots', 'heroes_with_weapon')},
                           'reasons': dict(Counter(s['reason'] for s in selected))}
                           for turn in (6, 9, 12) if (selected := [s for s in rows if s['round'] == turn])}})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    original = json.loads(args.source.read_text())
    observations = []
    for policy in ('greedy', 'push'):
        group = [r for r in original if r['pool'] == 'expanded' and r['policy'] == policy]
        for old in group:
            g = EconomyMatch(*old['rosters'], old['seed'], old['tower_attack'], old['protection'],
                             pool=old['pool'], policy=policy)
            assert g.run(old['max_rounds']) == old, 'Diagnostics changed original gameplay'
            assert not any(s['reason'] == 'usable_item_unspent' for s in g.economy), 'Classifier disagrees with actual AI'
            observations.append({'rosters': old['rosters'], 'seed': old['seed'],
                                 'policy': policy, 'outcome': old['outcome'], 'snapshots': g.economy})
        print(f'{policy}: {len(group)} games exactly reproduced', flush=True)
    summary = summarize(observations)
    dump(args.out/'observations.json', observations)
    dump(args.out/'comparison.json', summary)
    for s in summary:
        print(s['policy'], 'high-gold rounds', s['at_least_15_gold'], s['high_gold_reasons'], flush=True)
        print('round 12', s['same_round'].get('12'), flush=True)


if __name__ == '__main__':
    main()
