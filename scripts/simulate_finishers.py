#!/usr/bin/env python3
"""Ablate mana finishers and two original 25-gold offensive items at fixed deck sizes."""

import argparse
from collections import Counter
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from simulate_heroes import PROJECT, dump, viewer
from simulate_match import CARDS, BattleUnit, match_pairs
from simulate_expanded_match import ExpandedMatch, ExpandedUnit

OUT = PROJECT / 'docs/design/simulations/finisher-batch-01'
GOLD_REPLACEMENTS = {10238: 10263, 10236: 10260}
MANA_REPLACEMENTS = {10425: 10313, 10353: 10352, 10102: 10111, 10108: 10111, 10085: 10128}


@dataclass
class FinisherUnit(ExpandedUnit):
    horn_cd: int = 0
    blade_cd: int = 0

    @property
    def max_hp(self):
        return super().max_hp + (4 if 10260 in self.equipment.values() else 0)


class FinisherMatch(ExpandedMatch):
    def __init__(self, *args, mana_finishers=True, gold_finishers=True, **kwargs):
        self.mana_finishers, self.gold_finishers = mana_finishers, gold_finishers
        self.pending_condemns = set()
        self.terminal_purchases = []
        super().__init__(*args, pool='expanded', policy='greedy', **kwargs)
        if not mana_finishers:
            self.hand = [[MANA_REPLACEMENTS.get(i, i) for i in cards] for cards in self.hand]
            self.deck = [[MANA_REPLACEMENTS.get(i, i) for i in cards] for cards in self.deck]
            self.ordinary_by_color = {c: [MANA_REPLACEMENTS.get(i, i) for i in ids]
                                      for c, ids in self.ordinary_by_color.items()}
        if gold_finishers:
            self.item_deck = [[GOLD_REPLACEMENTS.get(i, i) for i in cards] for cards in self.item_deck]
            self.item_ids = [GOLD_REPLACEMENTS.get(i, i) for i in self.item_ids]
            self.gear_ids = [GOLD_REPLACEMENTS.get(i, i) for i in self.gear_ids]

    def promote_units(self):
        self.units = [u if isinstance(u, FinisherUnit) else FinisherUnit(**vars(u), **({} if isinstance(u, BattleUnit) else {'card_id': u.hero or 1006}))
                      for u in self.units]

    def draw(self, team, n):
        if not self.mana_finishers:
            self.deck[team] = [MANA_REPLACEMENTS.get(i, i) for i in self.deck[team]]
        super().draw(team, n)

    def draw_item(self, team):
        before = len(self.item_deck[team])
        if self.gold_finishers and self.item_deck[team]:
            self.item_deck[team][-1] = GOLD_REPLACEMENTS.get(self.item_deck[team][-1], self.item_deck[team][-1])
        super().draw_item(team)
        if self.gold_finishers and len(self.item_deck[team]) < before:
            item, paid = self.item_hand[team][-1]
            item = GOLD_REPLACEMENTS.get(item, item)
            self.item_hand[team][-1] = (item, paid)
            if item in GOLD_REPLACEMENTS.values():
                self.stats[team][f'finisher_drawn_{item}'] += 1

    def start_round(self):
        for u in self.units:
            u.horn_cd = max(0, u.horn_cd-1)
            u.blade_cd = max(0, u.blade_cd-1)
        super().start_round()

    def attack(self, unit, pos=None):
        return super().attack(unit, pos) + (8 if 10263 in getattr(unit, 'equipment', {}).values() else 0)

    def siege(self, unit):
        return super().siege(unit) + (4 if 10263 in unit.equipment.values() else 0)

    def equipment_value(self, item, hero):
        old = hero.equipment.get(CARDS[item]['sub_type'])
        extra = {10263: 8*1.2+4*.8+12, 10260: 4*.35+12}
        return super().equipment_value(item, hero) + extra.get(item, 0)-extra.get(old, 0)

    def incoming_damage(self, unit):
        amount = super().incoming_damage(unit)
        if any(not e.stunned and 10263 in e.equipment.values() and self.target(e) is unit and
               self.primary_damage(e, unit) > 0 for e in self.field(1-unit.team)):
            amount = max(amount, unit.hp)
        return amount

    def position_score(self, unit, pos):
        score = super().position_score(unit, pos)
        target = self.target(unit, pos)
        if target and 10263 in unit.equipment.values():
            amount = self.primary_damage(unit, target, pos)
            if 0 < amount < target.hp:
                score += min(20, target.hp-amount)+5
        if any(not e.stunned and 10263 in e.equipment.values() and
               self.target(e, override=(unit, pos)) is unit and self.primary_damage(e, unit) > 0
               for e in self.field(1-unit.team)):
            score -= 7
        return score

    def actions(self, team):
        actions = super().actions(team)
        for h in self.field(team):
            if not h.hero or h.stunned:
                continue
            if 10260 in h.equipment.values() and h.horn_cd == 0:
                positions = self.spawn_positions(team)
                if positions and len(self.field(team)) < 24:
                    pos = max(positions, key=lambda p: (self.spawn_score(team, p), p))
                    actions.append((12+self.spawn_score(team, pos), 'horn', h.uid, f'{pos[0]},{pos[1]}'))
            if 10263 in h.equipment.values() and h.blade_cd == 0:
                target = self.target(h)
                count = len(self.improvements[1-team]) + (len(target.equipment) if target else 0)
                if count:
                    actions.append((5*count, 'blade', h.uid, target.uid if target else 'improvements'))
        return actions

    def take_action(self, action, team):
        value, kind, actor_id, target_id = action
        if kind not in ('horn', 'blade'):
            item, paid = self.item_hand[team][int(actor_id)] if kind == 'item' else (None, None)
            before = self.gold[team]
            super().take_action(action, team)
            if item in GOLD_REPLACEMENTS.values():
                h = next(u for u in self.field(team) if u.uid == target_id)
                if item == 10260:
                    h.horn_cd = 0
                else:
                    h.blade_cd = 0
                self.stats[team]['finisher_equipped_free' if paid else 'finisher_equipped_paid'] += 1
                self.terminal_purchases.append({'round': self.round, 'team': team, 'item': item,
                                                'hero': h.uid, 'paid_by_ticket': paid,
                                                'gold_before': before, 'gold_after': self.gold[team]})
            return
        h = next(u for u in self.field(team) if u.uid == actor_id)
        assert h.hero and not h.stunned
        if kind == 'horn':
            assert 10260 in h.equipment.values() and h.horn_cd == 0
            pos = tuple(map(int, target_id.split(',')))
            assert pos in self.spawn_positions(team) and len(self.field(team)) < 24
            self.summon(team, 10102, first=pos)
            h.horn_cd = 2
            self.stats[team]['horn_casts'] += 1
            self.record(f'{h.uid}使用领袖号角，召唤雷肤兽群于 {pos}，CD 2，不消耗法力或金币')
        else:
            assert 10263 in h.equipment.values() and h.blade_cd == 0
            target = self.target(h)
            assert target_id == (target.uid if target else 'improvements')
            assert self.improvements[1-team] or (target and target.equipment)
            self.stats[team]['blade_improvements_removed'] += len(self.improvements[1-team])
            self.improvements[1-team].clear()
            if target:
                self.stats[team]['blade_items_removed'] += len(target.equipment)
                target.equipment.clear()
                target.hp = min(target.hp, target.max_hp)
            h.blade_cd = 1
            self.stats[team]['blade_casts'] += 1
            self.record(f'{h.uid}使用封神之刃，摧毁敌方强化与当前普攻目标装备，CD 1')
        self.stats[team]['actions'] += 1
        self.cleanup(); self.refresh_targets(); self.check()

    def on_battle_damage(self, attacker, target, amount):
        if 10263 in attacker.equipment.values() and amount > 0 and target.uid not in self.pending_condemns:
            self.pending_condemns.add(target.uid)
            self.stats[attacker.team]['blade_condemns'] += 1
            self.record(f'{attacker.uid}封神之刃：{target.uid}受到战斗伤害，标记惩处')

    def cleanup(self):
        for u in self.field():
            if u.uid in self.pending_condemns:
                u.hp = 0
        self.pending_condemns.clear()
        super().cleanup()

    def frame(self, phase):
        super().frame(phase)
        if self.trace:
            for entry in self.frames[-1]['units']:
                u = next(u for u in self.field() if u.uid == entry['id'])
                entry['item_cooldowns'] = {CARDS[i]['card_name']['schinese']: cd for i, cd in
                                           ((10260, u.horn_cd), (10263, u.blade_cd)) if i in u.equipment.values()}

    def run(self, rounds=24):
        result = super().run(rounds)
        result.update(mana_finishers=self.mana_finishers, gold_finishers=self.gold_finishers,
                      terminal_purchases=self.terminal_purchases)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--seeds', type=int, nargs='+', default=list(range(11, 23)))
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds):
        parser.error('seeds must be unique')
    args.out.mkdir(parents=True, exist_ok=True)
    rosters, pairs = match_pairs()
    results, extended, comparisons = [], [], []
    for mana, gold in product((False, True), repeat=2):
        group = [FinisherMatch(rosters[a], rosters[b], seed, 4, True, mana_finishers=mana, gold_finishers=gold).run()
                 for a, b in pairs for seed in args.seeds]
        results.extend(group)
        later = []
        for r in group:
            if r['outcome'] == 'timeout':
                later.append(FinisherMatch(*r['rosters'], r['seed'], 4, True,
                                           mana_finishers=mana, gold_finishers=gold).run(48))
        extended.extend(later)
        stats = sum((Counter(s) for r in group for s in r['stats']), Counter())
        n = len(group); done = [r for r in group if r['outcome'] != 'timeout']
        comparisons.append({'mana_finishers': mana, 'gold_finishers': gold, 'games': n,
                            'finished_24': len(done), 'finished_48': len(done)+sum(r['outcome'] != 'timeout' for r in later),
                            'mean_completed_rounds_24': sum(r['rounds'] for r in done)/max(1,len(done)),
                            'gold_remaining_per_team': sum(sum(r['gold']) for r in group)/(2*n),
                            **{k+'_per_team': stats[k]/(2*n) for k in ('gold_spent', 'building_damage', 'hero_deaths',
                                                                      'finisher_equipped_paid', 'finisher_equipped_free',
                                                                      'horn_casts', 'blade_condemns', 'blade_casts')},
                            'natural_finisher_draws': sum(stats[f'finisher_drawn_{i}'] for i in GOLD_REPLACEMENTS.values())})
        print(f'mana {mana}, gold {gold}: {len(done)}/{n} at 24; {comparisons[-1]["finished_48"]}/{n} at 48', flush=True)
        dump(args.out/'results.json', results); dump(args.out/'extended-timeouts.json', extended)
        dump(args.out/'comparison.json', comparisons)
    replays = [FinisherMatch(rosters[0], rosters[1], 11, 4, True, trace=True,
                             mana_finishers=m, gold_finishers=g).run() for m, g in product((False, True), repeat=2)]
    candidates = [r for r in results if r['gold_finishers'] and r['terminal_purchases']]
    if candidates:
        r = max(candidates, key=lambda r: sum(s.get('horn_casts',0)+s.get('blade_condemns',0) for s in r['stats']))
        replays.append(FinisherMatch(*r['rosters'], r['seed'], 4, True, trace=True,
                                    mana_finishers=r['mana_finishers'], gold_finishers=True).run())
    dump(args.out/'replays.json', replays); viewer(args.out, replays)
    lines = ['# 双经济终端对照', '', '方法与适配见 [README](README.md)。每组使用相同阵容与种子，牌库长度与供给节奏不变。', '',
             '| 法力终端 | 金币终端 | 24 轮内结束 | 48 轮内结束 | 已结束局平均轮数（24 截止） | 每队剩金 | 每队消费 | 每队直接买终端 |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s in comparisons:
        lines.append(f"| {'开' if s['mana_finishers'] else '关'} | {'开' if s['gold_finishers'] else '关'} | {s['finished_24']}／{s['games']} | {s['finished_48']}／{s['games']} | {s['mean_completed_rounds_24']:.2f} | {s['gold_remaining_per_team']:.2f} | {s['gold_spent_per_team']:.2f} | {s['finisher_equipped_paid_per_team']:.2f} |")
    lines += ['', '平均完成轮数只包含已结束对局；续跑属于相同对局，不是新的独立样本。', '',
              '[逐局结果](results.json) · [24 轮超时的 48 轮续测](extended-timeouts.json) · [回放](replays.html)', '']
    (args.out/'summary.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
