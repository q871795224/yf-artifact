#!/usr/bin/env python3
"""Factorial comparison of expanded original cards and a forward-looking movement policy."""

import argparse
from collections import Counter
from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path

from simulate_heroes import EIGHT, valid, distance, PROJECT, dump, viewer
from simulate_match import (Match, BattleUnit, CARDS, POOL,
                            ATTACK_GEAR, ARMOR_GEAR, HEALTH_GEAR, match_pairs)

EXPANDED_POOL = json.loads((PROJECT / 'docs/design/expanded-card-pool.json').read_text())
EXTRA_ATTACK = {10212: 2, 10223: 2, 10252: 2, 10256: 2}
OUT = PROJECT / 'docs/design/simulations/match-batch-02'


@dataclass
class ExpandedUnit(BattleUnit):
    permanent_health: int = 0
    permanent_armor: int = 0
    permanent_cleave: int = 0
    permanent_retaliate: int = 0
    permanent_siege: int = 0
    temporary_cleave: int = 0
    pike_growth: int = 0

    @property
    def max_hp(self):
        return super().max_hp + self.permanent_health + (4 if 3000 in self.equipment.values() else 0)

    @property
    def armor(self):
        return super().armor + self.permanent_armor + (2 if 10214 in self.equipment.values() else 0)


class ExpandedMatch(Match):
    def __init__(self, *args, pool='expanded', policy='push', **kwargs):
        if pool not in ('first', 'expanded') or policy not in ('greedy', 'push'):
            raise ValueError('Unknown pool or policy')
        self.pool_name, self.policy = pool, policy
        self.pool = POOL if pool == 'first' else EXPANDED_POOL
        self.ordinary_by_color = {c: [x['card_id'] for x in self.pool['ordinary_cards'] if c in x['colors']]
                                  for c in ('red', 'blue', 'green', 'black')}
        self.item_ids = [x['card_id'] for x in self.pool['items']]
        self.gear_ids = [x['card_id'] for x in self.pool['items'] if x['category'] == 'equipment']
        self.timeline = []
        super().__init__(*args, **kwargs)

    def promote_units(self):
        self.units = [u if isinstance(u, ExpandedUnit) else ExpandedUnit(**vars(u), **({} if isinstance(u, BattleUnit) else {'card_id': u.hero or 1006}))
                      for u in self.units]

    def summon(self, *args, **kwargs):
        super().summon(*args, **kwargs)
        self.promote_units()

    def start_round(self):
        for u in self.units:
            u.temporary_cleave = 0
        super().start_round()

    def attack(self, unit, pos=None):
        amount = super().attack(unit, pos)
        if isinstance(unit, ExpandedUnit):
            amount += sum(EXTRA_ATTACK.get(i, 0) for i in unit.equipment.values())
            if 10252 in unit.equipment.values():
                amount += unit.pike_growth
            if unit.card_id == 10085:
                amount -= 2 * sum(u is not unit for u in self.field(unit.team))
        return max(0, amount)

    def primary_damage(self, unit, target, pos=None):
        if 10256 in getattr(unit, 'equipment', {}).values():
            return self.attack(unit, pos) + (4 if unit.hero == 10047 and target.hero else 0)
        return super().primary_damage(unit, target, pos)

    def cleave(self, unit):
        return unit.permanent_cleave + unit.temporary_cleave + (2 if 10212 in unit.equipment.values() else 0)

    def siege(self, unit):
        return unit.permanent_siege + (5 if 10223 in unit.equipment.values() else 0) + {10102: 6, 10085: 5}.get(unit.card_id, 0)

    def equipment_value(self, item, hero):
        old = hero.equipment.get(CARDS[item]['sub_type'])
        def value(i):
            result = (ATTACK_GEAR.get(i, 0)+EXTRA_ATTACK.get(i, 0))*1.2
            result += (ARMOR_GEAR.get(i, 0)+(2 if i == 10214 else 0))*2
            result += (HEALTH_GEAR.get(i, 0)+(4 if i == 3000 else 0))*.35
            result += {10212: 2, 10223: 4, 10252: 2, 10256: 3}.get(i, 0)
            if i == old == 10252:
                result += hero.pike_growth*1.2
            return result
        gain = value(item)-value(old)
        if self.policy == 'push' and gain > 0:
            # Give offensive equipment to heroes able to use it, without overlooking rear heroes.
            attack_item = item in ATTACK_GEAR or item in EXTRA_ATTACK
            if attack_item:
                fort = self.forts[1-hero.team]
                gain *= 1 + .4/(1+max(0, abs(hero.pos[0]-fort.row)-hero.reach))
                if self.target(hero) or self.building_target(hero):
                    gain *= 1.15
        return gain

    def position_score(self, unit, pos):
        if self.policy == 'greedy':
            return super().position_score(unit, pos)
        target = self.target(unit, pos)
        fort = self.building_target(unit, pos)
        enemy_fort = self.forts[1-unit.team]
        score = -1.1*max(0, abs(pos[0]-enemy_fort.row)-unit.reach)
        if target:
            amount = self.primary_damage(unit, target, pos)
            score += min(amount, target.hp)*(1.25 if target.hero else .75)
            if amount >= target.hp:
                score += 5 if target.hero else 1.5
            dr, dc = pos[0]-target.pos[0], pos[1]-target.pos[1]
            sides = ((target.pos[0]+(dc>0)-(dc<0), target.pos[1]-(dr>0)+(dr<0)),
                     (target.pos[0]-(dc>0)+(dc<0), target.pos[1]+(dr>0)-(dr<0)))
            splash = self.cleave(unit) + (self.attack(unit, pos)//2 if unit.hero == 10054 else 0)
            score += .7*sum(min(e.hp, max(0, splash-e.armor)) for e in self.field(1-unit.team) if e.pos in sides)
        if fort:
            amount = self.siege(unit) if target else self.attack(unit, pos)
            score += min(amount, fort.hp)*1.8
            if amount >= fort.hp and amount > 0:
                score += 100 if fort.stage == 'base' else 10
        incoming = sum(self.primary_damage(e, unit) for e in self.field(1-unit.team)
                       if not e.stunned and self.target(e, override=(unit, pos)) is unit)
        if self.fort_target(enemy_fort, override=(unit, pos)) is unit:
            incoming += max(0, self.fort_power(enemy_fort)-unit.armor)
        if pos[0] == (0 if unit.team == 0 else 7):
            incoming += max(0, 10-unit.armor)
        score -= .6*min(incoming, unit.hp) + (7 if incoming >= unit.hp else 0)
        neighbors = [u for u in self.field(unit.team) if u is not unit and distance(pos, u.pos) == 1]
        if unit.hero == 10014:
            score += 1.2*len(neighbors)
        if unit.hero == 10036:
            score += sum(min(2, u.max_hp-u.hp) for u in neighbors)
        if unit.hero in (10017, 10033, 10060) and unit.cd == 0:
            score += 1.3*sum(distance(pos, e.pos) <= 2 for e in self.field(1-unit.team))
        return score

    def movement_actions(self, team):
        occupied = {u.pos for u in self.field()} | self.blocked_positions()
        result = []
        for h in self.field(team):
            if not h.hero or h.stunned or h.moved:
                continue
            before = self.position_score(h, h.pos)
            for pos in self.reachable(h):
                now = self.position_score(h, pos)
                future = [pos] + [(pos[0]+dr, pos[1]+dc) for dr, dc in EIGHT
                                  if valid((pos[0]+dr, pos[1]+dc), self.columns) and
                                  ((pos[0]+dr, pos[1]+dc) not in occupied or (pos[0]+dr, pos[1]+dc) == h.pos)]
                # One future step with a frozen board; not a full turn/opponent search.
                potential = max(self.position_score(h, p) for p in future)
                value = max(now-before, .25*now+.75*potential-before-.5)
                if value > .05:
                    result.append((value, 'move', h.uid, f'{pos[0]},{pos[1]}'))
        return result

    def actions(self, team):
        actions = super().actions(team)
        if self.policy == 'push':
            actions = [a for a in actions if a[1] != 'move'] + self.movement_actions(team)
        friends, enemies = self.field(team), self.field(1-team)
        heroes = [h for h in friends if h.hero]
        colors = {c for h in heroes for c in CARDS[h.hero]['colors']}
        for index, cid in enumerate(self.hand[team]):
            c = CARDS[cid]
            if c['mana_cost'] > self.mana[team] or not colors.intersection(c['colors']):
                continue
            value, target = 0, 'all'
            if cid == 10344:
                for h in heroes:
                    victim = self.target(h)
                    if h.stunned or not victim:
                        continue
                    dr, dc = self.attack_direction(h, victim)
                    sides = ((victim.pos[0]+dc, victim.pos[1]-dr), (victim.pos[0]-dc, victim.pos[1]+dr))
                    value += sum(min(e.hp, max(0, 4-e.armor)) for e in enemies if e.pos in sides)
            elif cid == 10425:
                value = 5*len(heroes)
            elif cid == 10307:
                value = min(2, len(self.deck[team]))*3
                target = 'draw'
            elif cid == 10412:
                value = sum(min(e.hp, max(0, 4-e.armor))*(1.3 if e.hero else 1) for e in enemies)
            elif cid == 10353:
                fort = self.forts[1-team]
                if self.round >= fort.active_from:
                    value = min(20, fort.hp)*1.1
                    target = 'fort'
            elif cid == 10311:
                value = 2*sum(not u.hero for u in friends)
            elif cid in (10410, 10354):
                targets = [e for e in enemies if cid == 10354 or not e.hero]
                if targets:
                    def worth(e):
                        amount = e.hp if cid == 10410 else max(0, 4-e.armor)
                        return min(amount, e.hp) + ((7 if e.hero else 2) if amount >= e.hp else 0)
                    if self.policy == 'push':
                        # Keep every legal target until the building-opening bonus is applied.
                        actions.extend((worth(e), 'card', str(index), e.uid) for e in targets if worth(e) > 0)
                        continue
                    victim = max(targets, key=lambda e: (worth(e), e.uid))
                    value, target = worth(victim), victim.uid
            if value > 0:
                actions.append((value, 'card', str(index), target))
        if self.policy == 'push':
            revised = []
            for value, kind, index, target in actions:
                if kind == 'card':
                    cid = self.hand[team][int(index)]
                    fort = self.forts[1-team]
                    if cid in (10352, 10353) and fort.stage == 'base' and fort.hp <= (6 if cid == 10352 else 20):
                        value += 1000  # Take an immediate legal win before a speculative move.
                    if CARDS[cid]['card_type'] == 'Creep':
                        pos = tuple(map(int, target.split(',')))
                        future_unit = ExpandedUnit('preview', team, None, CARDS[cid]['hit_points'], pos, card_id=cid)
                        value += self.attack(future_unit)*.5 + future_unit.hp*.15 + self.siege(future_unit)*.5
                    # Clearing an actual blocker can free several normal attacks on the fort.
                    amount = {10270: 2, 10354: 4, 10402: 2, 10412: 4}.get(cid)
                    killed = [e for e in enemies if (target == 'all' or e.uid == target) and
                              ((cid == 10410 and not e.hero) or (amount and max(0, amount-e.armor) >= e.hp))]
                    killed_ids = {e.uid for e in killed}
                    value += sum(5 if e.hero else 1 for e in killed)
                    if killed_ids:
                        for friend in friends:
                            victim = self.target(friend)
                            if friend.stunned or not victim or victim.uid not in killed_ids or not self.building_target(friend):
                                continue
                            remaining = [e for e in enemies if e.uid not in killed_ids and
                                         (friend.pos[0] == e.pos[0] or friend.pos[1] == e.pos[1]) and
                                         distance(friend.pos, e.pos) <= friend.reach]
                            if not remaining:
                                value += self.attack(friend)*.8
                revised.append((value, kind, index, target))
            actions = revised
        return actions

    def take_action(self, action, team):
        value, kind, index, target_id = action
        cid = self.hand[team][int(index)] if kind == 'card' else None
        added = {10344, 10425, 10307, 10412, 10353, 10311, 10410, 10354}
        if cid not in added:
            item = self.item_hand[team][int(index)][0] if kind == 'item' else None
            actor = next((u for u in self.field() if u.uid == target_id), None)
            super().take_action(action, team)
            if item == 10252:
                actor.pike_growth = 0
            if item == 10256:
                actor.stunned = False  # Stun is the only opposing debuff in this experiment.
                self.refresh_targets()
            return
        card = CARDS[cid]
        assert self.mana[team] >= card['mana_cost']
        assert any(h.hero and set(CARDS[h.hero]['colors']).intersection(card['colors']) for h in self.field(team))
        if cid in (10410, 10354):
            victim = next((e for e in self.field(1-team) if e.uid == target_id), None)
            assert victim is not None and (cid != 10410 or not victim.hero)
        if cid == 10353:
            assert self.round >= self.forts[1-team].active_from
        self.hand[team].pop(int(index))
        self.mana[team] -= card['mana_cost']
        self.stats[team]['actions'] += 1
        self.stats[team]['cards_played'] += 1
        self.stats[team][f'card_used_{cid}'] += 1
        friends = self.field(team)
        if cid == 10344:
            for h in friends:
                if h.hero:
                    h.temporary_cleave += 4
        elif cid == 10425:
            for h in friends:
                if h.hero:
                    h.permanent_attack += 4
                    h.permanent_armor += 4
                    h.permanent_health += 4
                    h.hp += 4
                    h.permanent_cleave += 4
                    h.permanent_retaliate += 4
                    h.permanent_siege += 4
        elif cid == 10307:
            self.draw(team, 2)
        elif cid == 10412:
            for e in self.field(1-team):
                e.hp -= max(0, 4-e.armor)
        elif cid == 10353:
            self.damage_fort(1-team, 20)
        elif cid == 10311:
            for u in friends:
                if not u.hero:
                    u.permanent_attack += 2
                    u.permanent_armor += 1
        else:
            if cid == 10410:
                victim.hp = 0
            else:
                victim.hp -= max(0, 4-victim.armor)
        self.record(f"{'AB'[team]}出牌 {card['card_name']['schinese']} → {target_id}，消耗 {card['mana_cost']} 法力；评分 {value:.2f}")
        heroes = [h for h in friends if h.hero]
        self.stats[team]['spells'] += 1
        if not self.first_spell[team] and any(h.hero == 10064 for h in heroes):
            before = self.mana[team]
            self.mana[team] = min(min(self.round, 10), before+2)
            self.stats[team]['mana_refunded'] += self.mana[team]-before
        self.first_spell[team] = True
        if 'blue' in card['colors']:
            for z in [h for h in heroes if h.hero == 10065]:
                for e in self.field(1-team):
                    if distance(z.pos, e.pos) == 1:
                        e.hp -= 1
                        self.stats[team]['zeus_damage'] += 1
        self.cleanup(); self.check_victory(); self.refresh_targets()

    def on_battle_damage(self, attacker, target, amount):
        """Extension point for item effects, after an individual battle-damage contribution."""

    def combat(self):
        self.refresh_targets()
        units = self.field()
        damage, building_damage = Counter(), Counter()
        regen = {u.uid: self.regeneration(u) for u in units}
        for u in units:
            if u.stunned:
                continue
            group = 'hero' if u.hero else 'creep'
            self.stats[u.team]['attack_opportunities'] += 1
            self.stats[u.team][group+'_attack_opportunities'] += 1
            target, fort = self.target(u), self.building_target(u)
            if not target and not fort:
                self.stats[u.team]['out_of_range'] += 1
                self.stats[u.team][group+'_out_of_range'] += 1
                continue
            self.stats[u.team]['attacks'] += 1
            self.stats[u.team][group+'_attacks'] += 1
            if not target:
                building_damage[fort.team] += self.attack(u)
                self.stats[u.team]['building_attacks'] += 1
                self.record(f'{u.uid}普攻建筑 {fort.uid}：{self.attack(u)}')
                continue
            amount = self.primary_damage(u, target)
            damage[target.uid] += amount
            self.on_battle_damage(u, target, amount)
            self.record(f'{u.uid}普攻 {target.uid}：{amount}')
            retaliate = (2 if target.hero == 10069 else 0)+target.permanent_retaliate
            damage[u.uid] += max(0, retaliate-u.armor)
            splash = self.cleave(u)+(self.attack(u)//2 if u.hero == 10054 else 0)
            dr, dc = self.attack_direction(u, target)
            sides = ((target.pos[0]+dc, target.pos[1]-dr), (target.pos[0]-dc, target.pos[1]+dr))
            if splash:
                for e in units:
                    if e.team != u.team and e.pos in sides:
                        extra = max(0, splash-e.armor)
                        damage[e.uid] += extra
                        self.on_battle_damage(u, e, extra)
            if fort and self.siege(u):
                building_damage[fort.team] += self.siege(u)
                self.stats[u.team]['siege_damage'] += self.siege(u)
                self.record(f'{u.uid}攻城 {fort.uid}：{self.siege(u)}')
        for fort in self.forts:
            victim = self.fort_target(fort)
            if victim:
                amount = max(0, self.fort_power(fort)-victim.armor)
                damage[victim.uid] += amount
                self.stats[fort.team]['fort_shots'] += 1
                self.record(f'{fort.uid}建筑攻击 {victim.uid}：{amount}')
            for e in units:
                if e.team != fort.team and e.pos[0] == (7 if fort.team == 0 else 0):
                    damage[e.uid] += max(0, 10-e.armor)
                    self.stats[fort.team]['fountain_hits'] += 1
        for u in units:
            u.hp -= damage[u.uid]
            healed = min(regen[u.uid], u.max_hp-u.hp)
            u.hp += healed
            self.stats[u.team]['regenerated'] += healed
        self.cleanup()
        for team, amount in building_damage.items():
            self.damage_fort(team, amount)
        self.check_victory()
        for u in self.field():
            if u.card_id == 10111:
                u.permanent_attack += 2
            if 10252 in u.equipment.values():
                u.pike_growth += 1
                self.stats[u.team]['pike_growth'] += 1
        self.refresh_targets(); self.check()

    def frame(self, phase):
        super().frame(phase)
        if self.trace:
            for entry in self.frames[-1]['units']:
                u = next(u for u in self.field() if u.uid == entry['id'])
                entry.update(cleave=self.cleave(u), siege=self.siege(u), pike_growth=u.pike_growth,
                             pierce=10256 in u.equipment.values())
        if phase == '交战后':
            self.timeline.append({'round': self.round, 'gold': list(self.gold),
                                  'spent': [s['gold_spent'] for s in self.stats],
                                  'deck': [len(d) for d in self.deck], 'hand': [len(h) for h in self.hand],
                                  'equipment': [s['equipment_equipped'] for s in self.stats],
                                  'building_damage': [s['building_damage'] for s in self.stats]})

    def run(self, rounds=24):
        result = super().run(rounds)
        result.update(pool=self.pool_name, policy=self.policy, timeline=self.timeline)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--rounds', type=int, default=24)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('rounds must be positive')
    args.out.mkdir(parents=True, exist_ok=True)
    rosters, pairs = match_pairs()
    results, summary = [], []
    for pool, policy in product(('first', 'expanded'), ('greedy', 'push')):
        group = [ExpandedMatch(rosters[a], rosters[b], seed, 4, True, pool=pool, policy=policy).run(args.rounds)
                 for a, b in pairs for seed in (11, 12, 13)]
        results.extend(group)
        stats = sum((Counter(s) for r in group for s in r['stats']), Counter())
        n = len(group)
        finished = [r for r in group if r['outcome'] != 'timeout']
        summary.append({'pool': pool, 'policy': policy, 'games': n, 'finished': len(finished),
                        'timeouts': n-len(finished), 'mean_finished_rounds': sum(r['rounds'] for r in finished)/max(1, len(finished)),
                        'gold_remaining_per_team': sum(sum(r['gold']) for r in group)/(2*n),
                        **{k+'_per_team': stats[k]/(2*n) for k in ('gold_spent', 'cards_played', 'equipment_equipped', 'building_damage', 'siege_damage')},
                        'round_snapshots': {str(turn): {
                            key: sum(sum(t[key]) for r in group for t in r['timeline'] if t['round'] == turn)/(2*sum(any(t['round']==turn for t in r['timeline']) for r in group))
                            for key in ('gold', 'spent', 'deck', 'hand', 'equipment', 'building_damage')}
                            for turn in (6, 9, 12) if any(r['rounds'] >= turn for r in group)}})
        print(f'{pool}/{policy}: {len(finished)}/{n} finished', flush=True)
    dump(args.out/'results.json', results); dump(args.out/'comparison.json', summary)
    replays = [ExpandedMatch(rosters[0], rosters[1], 11, 4, True, trace=True, pool=p, policy=a).run(args.rounds)
               for p, a in product(('first', 'expanded'), ('greedy', 'push'))]
    dump(args.out/'replays.json', replays); viewer(args.out, replays)
    lines = ['# 牌池与 AI 对照实验 02', '', '固定塔 4／基地 8，保护开启。方法和适配细则见 [README](README.md)。', '',
             f'| 牌池 | AI | {args.rounds} 轮内结束／总局数 | 超时 | 已结束局平均轮数 | 每队剩余金币 | 每队花金 | 每队出牌 |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s in summary:
        lines.append(f"| {s['pool']} | {s['policy']} | {s['finished']}／{s['games']} | {s['timeouts']} | {s['mean_finished_rounds']:.2f} | {s['gold_remaining_per_team']:.2f} | {s['gold_spent_per_team']:.2f} | {s['cards_played_per_team']:.2f} |")
    lines += ['', '上述轮数只统计已结束局，不是全部对局的平均完成时间。期末金币受对局长度影响，需同时看 [comparison.json](comparison.json) 的同轮快照。', '',
              '[逐局结果](results.json) · [四个成对回放](replays.html)', '']
    (args.out/'summary.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
