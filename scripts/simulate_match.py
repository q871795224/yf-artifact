#!/usr/bin/env python3
"""Small complete-match experiments with original cards, items and defended structures."""

import argparse
from collections import Counter
from dataclasses import dataclass, field
from itertools import product
import json
from pathlib import Path

from simulate_heroes import Game, Unit, SOURCE, PROJECT, RANGED, ARROWS, distance, sample_rosters, roster_name, dump, viewer

CARDS = {c['card_id']: c for c in SOURCE['cards']}
POOL = json.loads((PROJECT / 'docs/design/first-card-pool.json').read_text())
ITEMS = [c['card_id'] for c in POOL['items']]
GEAR = [c['card_id'] for c in POOL['items'] if c['category'] == 'equipment']
BY_COLOR = {color: [c['card_id'] for c in POOL['ordinary_cards'] if color in c['colors']] for color in ('red', 'blue', 'green', 'black')}
ATTACK_GEAR = {3002: 2, 10215: 4, 10238: 8}
HEALTH_GEAR = {10213: 8, 10236: 16}
ARMOR_GEAR = {3001: 1}
OUT = PROJECT / 'docs/design/simulations/match-batch-01'


@dataclass
class BattleUnit(Unit):
    card_id: int = 1006
    permanent_attack: int = 0
    temporary_attack: int = 0
    temporary_armor: int = 0
    equipment: dict = field(default_factory=dict)

    @property
    def name(self):
        return CARDS[self.card_id]['card_name']['schinese']

    @property
    def max_hp(self):
        return CARDS[self.card_id]['hit_points'] + sum(HEALTH_GEAR.get(i, 0) for i in self.equipment.values())

    @property
    def armor(self):
        return CARDS[self.card_id].get('armor', 0) + self.temporary_armor + sum(ARMOR_GEAR.get(i, 0) for i in self.equipment.values())


@dataclass
class Fort:
    team: int
    hp: int = 40
    stage: str = 'tower'
    active_from: int = 1
    target_uid: str | None = None
    position: tuple | None = None

    @property
    def uid(self):
        return 'AB'[self.team] + 'F'

    @property
    def row(self):
        return self.position[0] if self.position else (6.5 if self.team == 0 else .5)

    @property
    def max_hp(self):
        return 40 if self.stage == 'tower' else 80


class Match(Game):
    ordinary_by_color = BY_COLOR
    item_ids = ITEMS
    gear_ids = GEAR

    def __init__(self, a, b, seed=11, tower_attack=5, protection=False, trace=False, columns=6, fort_cells=False):
        self.forts = [Fort(team, position=((7 if team == 0 else 0), columns//2) if fort_cells else None) for team in (0, 1)]
        self.tower_attack = tower_attack
        self.protection = protection
        self.finished = False
        self.winner = None
        self.end_reason = None
        self.deck = [[], []]
        self.hand = [[], []]
        self.item_deck = [[], []]
        self.item_hand = [[], []]  # (ID, already paid by Golden Ticket)
        self.improvements = [[], []]
        self.created = 0
        super().__init__(a, b, seed, probes=False, trace=trace, targeting='aggro', columns=columns)
        self.promote_units()
        for team, roster in enumerate(self.rosters):
            # Fixed 18-card experiment deck: each hero contributes two copies
            # of its color's three ordinary cards; these are not signature cards.
            for h in roster:
                color = CARDS[h]['colors'][0]
                self.deck[team].extend(self.ordinary_by_color[color] * 2)
            self.rng(f'ordinary-deck:{team}').shuffle(self.deck[team])
            self.item_deck[team] = list(self.item_ids)
            self.rng(f'item-deck:{team}').shuffle(self.item_deck[team])
            self.draw(team, 5)
            self.draw_item(team)

    def promote_units(self):
        self.units = [u if isinstance(u, BattleUnit) else BattleUnit(**vars(u), card_id=u.hero or 1006) for u in self.units]

    def attack(self, unit, pos=None):
        if not isinstance(unit, BattleUnit):
            return super().attack(unit, pos)
        pos = unit.pos if pos is None else pos
        wolf = 2 * sum(u.hero == 10014 and u is not unit and distance(u.pos, pos) == 1 for u in self.field(unit.team))
        return CARDS[unit.card_id].get('attack', 0) + unit.permanent_attack + unit.temporary_attack + unit.bonus + sum(ATTACK_GEAR.get(i, 0) for i in unit.equipment.values()) + wolf

    def draw(self, team, n):
        for _ in range(min(n, len(self.deck[team]))):
            card = self.deck[team].pop()
            self.hand[team].append(card)
            self.record(f"{'AB'[team]}抽牌：{CARDS[card]['card_name']['schinese']}")

    def draw_item(self, team):
        if self.item_deck[team]:
            card = self.item_deck[team].pop()
            self.item_hand[team].append((card, False))
            self.record(f"{'AB'[team]}收到物品：{CARDS[card]['card_name']['schinese']}")

    def start_round(self):
        for u in self.units:
            u.temporary_attack = u.temporary_armor = 0
        super().start_round()
        self.promote_units()
        for team in (0, 1):
            if self.round > 1:
                self.draw(team, 2)
            if self.round % 3 == 0:
                self.draw_item(team)
            for u in self.field(team):
                u.permanent_attack += len(self.improvements[team])

    def protecting_heroes(self, team, observer=None, override=None):
        if not self.protection:
            return []
        result = []
        for h in self.field(1-team):
            if not h.hero or h.stunned:
                continue
            hp = override[1] if override and h is override[0] else h.pos
            victim = Game.target(self, h, pos=hp, override=override)
            if victim and victim.hero and victim.team == team and (observer is None or distance(observer, hp) <= 1):
                result.append(h)
        return result

    def target(self, unit, pos=None, override=None):
        pos = unit.pos if pos is None else pos
        if not unit.hero:
            attackers = self.protecting_heroes(unit.team, observer=pos, override=override)
            def hp(h):
                return override[1] if override and h is override[0] else h.pos
            legal = [h for h in attackers if (pos[0] == hp(h)[0] or pos[1] == hp(h)[1]) and 0 < distance(pos, hp(h)) <= unit.reach]
            if legal:
                return next((h for h in legal if h.uid == unit.target_uid), min(legal, key=lambda h: (distance(pos, hp(h)), h.uid)))
        return Game.target(self, unit, pos, override)

    def fort_power(self, fort):
        return self.tower_attack * (2 if fort.stage == 'base' else 1)

    def blocked_positions(self):
        return {f.position for f in self.forts if f.position is not None}

    def fort_distance(self, fort, pos):
        return distance(pos, fort.position) if fort.position else abs(pos[0]-fort.row)

    def fort_target(self, fort, override=None):
        if fort.hp <= 0 or self.round < fort.active_from or self.fort_power(fort) == 0:
            return None
        def position(u):
            return override[1] if override and u is override[0] else u.pos
        candidates = [u for u in self.field(1-fort.team) if self.fort_distance(fort, position(u)) <= 2]
        protected = [h for h in self.protecting_heroes(fort.team, override=override) if h in candidates]
        pool = protected or candidates
        return next((u for u in pool if u.uid == fort.target_uid), min(pool, key=lambda u: (self.fort_distance(fort, position(u)), u.uid)) if pool else None)

    def refresh_targets(self):
        previous = {u.uid:u.target_uid for u in self.field()}
        super().refresh_targets()
        for u in self.field():
            if self.protection and not u.hero and previous.get(u.uid) is not None and previous[u.uid] != u.target_uid:
                if any(h.uid == u.target_uid for h in self.protecting_heroes(u.team,observer=u.pos)):
                    self.stats[u.team]['creep_protection_switches'] += 1
                    self.record(f'{u.uid}保护友方英雄，转火 {u.target_uid}')
        for f in self.forts:
            target = self.fort_target(f)
            uid = target.uid if target else None
            if f.target_uid != uid:
                if f.target_uid is not None and target in self.protecting_heroes(f.team):
                    self.stats[f.team]['fort_protection_switches'] += 1
                self.record(f"{f.uid}建筑索敌：{f.target_uid or '无'} → {uid or '无'}")
                f.target_uid = uid

    def building_target(self, unit, pos=None):
        pos = unit.pos if pos is None else pos
        f = self.forts[1-unit.team]
        aligned = f.position is None or pos[0] == f.position[0] or pos[1] == f.position[1]
        return f if self.round >= f.active_from and f.hp > 0 and aligned and self.fort_distance(f, pos) <= unit.reach else None

    def position_score(self, unit, pos):
        score = super().position_score(unit, pos)
        fort = self.forts[1-unit.team]
        score -= .75 * max(0, self.fort_distance(fort, pos)-unit.reach)
        if self.target(unit, pos) is None and self.building_target(unit, pos):
            score += self.attack(unit, pos) * (1.4 if fort.stage == 'base' else 1.1)
        if self.fort_target(fort, override=(unit, pos)) is unit:
            incoming = max(0, self.fort_power(fort)-unit.armor)
            score -= .6*incoming + (7 if incoming >= unit.hp else 0)
        if pos[0] == (0 if unit.team == 0 else 7):
            score -= 10  # Enemy fountain: fixed 10 ordinary area damage.
        return score

    def spawn_positions(self, team):
        occupied = {u.pos for u in self.field()} | self.blocked_positions()
        heroes = [u for u in self.field(team) if u.hero]
        fountain = 7 if team == 0 else 0
        return [(r,c) for r in range(8) for c in range(self.columns) if (r,c) not in occupied
                and (r == fountain or any(distance((r,c),h.pos) <= 1 for h in heroes))]

    def spawn_score(self, team, pos):
        forward = 7-pos[0] if team == 0 else pos[0]
        neighbors = sum(distance(pos,u.pos) == 1 for u in self.field(1-team))
        return forward*.4 + min(neighbors,2)*.6

    def summon(self, team, card_id, count=1, first=None):
        for index in range(count):
            places = self.spawn_positions(team)
            if not places or len(self.field(team)) >= 24:
                self.stats[team]['summons_blocked'] += count-index
                break
            pos = first if index == 0 and first in places else max(places,key=lambda p:(self.spawn_score(team,p),p))
            self.created += 1
            u = BattleUnit(f"{'AB'[team]}S{self.created}", team, None, CARDS[card_id]['hit_points'], pos, card_id=card_id)
            self.units.append(u)
            self.stats[team]['summons'] += 1
            self.record(f"{u.uid}召唤 {u.name} 于 {pos}，死亡赏金 1")

    def incoming_damage(self, unit):
        amount = sum(self.primary_damage(e,unit) for e in self.field(1-unit.team) if not e.stunned and self.target(e) is unit)
        fort = self.forts[1-unit.team]
        if self.fort_target(fort) is unit:
            amount += max(0,self.fort_power(fort)-unit.armor)
        if unit.pos[0] == (0 if unit.team==0 else 7):
            amount += max(0,10-unit.armor)
        return amount

    def equipment_value(self, item, hero):
        old = hero.equipment.get(CARDS[item]['sub_type'])
        return ((ATTACK_GEAR.get(item,0)-ATTACK_GEAR.get(old,0))*1.2
                +(ARMOR_GEAR.get(item,0)-ARMOR_GEAR.get(old,0))*2
                +(HEALTH_GEAR.get(item,0)-HEALTH_GEAR.get(old,0))*.35)

    def actions(self, team):
        actions = super().actions(team)
        friends, enemies = self.field(team), self.field(1-team)
        heroes = [u for u in friends if u.hero]
        colors = {color for h in heroes for color in CARDS[h.hero]['colors']}
        seen = set()
        for index, card_id in enumerate(self.hand[team]):
            c = CARDS[card_id]
            if card_id in seen or c['mana_cost'] > self.mana[team] or not colors.intersection(c['colors']):
                continue
            seen.add(card_id)
            candidates = []
            if c['card_type'] == 'Creep' or card_id == 10355:
                places = self.spawn_positions(team)
                if places and len(friends) < 24:
                    p = max(places,key=lambda p:(self.spawn_score(team,p),p))
                    value = 4 + (2 if card_id == 10355 else 0) + self.spawn_score(team,p)
                    candidates.append((value,f'{p[0]},{p[1]}'))
            elif card_id == 10352:
                f = self.forts[1-team]
                if self.round >= f.active_from:
                    candidates.append((5 + (8 if f.hp <= 6 and f.stage == 'base' else 0),'fort'))
            elif card_id == 10402:
                value = sum(min(u.hp,max(0,2-u.armor))*(1.3 if u.hero else 1) for u in enemies)
                if value: candidates.append((value,'all'))
            elif card_id in (10313,10297,10368):
                for u in friends:
                    if card_id == 10313 and (not u.hero or 'red' not in CARDS[u.hero]['colors']):continue
                    if card_id == 10297 and not u.hero:continue
                    fighting = not u.stunned and (self.target(u) is not None or self.building_target(u) is not None)
                    if card_id == 10313 and u.stunned:continue
                    if card_id == 10297:
                        incoming = self.incoming_damage(u)
                        value = min(3,incoming)*1.5
                    else:
                        value = (4 if card_id == 10313 else 2)*(1 if fighting else .3)
                    if value > 0:candidates.append((value,u.uid))
            elif card_id == 10169:
                candidates.append((2 + len(friends)*.8,'self'))
            elif card_id == 10270:
                for u in enemies:
                    amount = max(0,2-u.armor)
                    if amount:candidates.append((min(amount,u.hp)+((7 if u.hero else 2)if u.hp<=amount else 0),u.uid))
            elif card_id == 10322:
                need = sum(0 if paid else CARDS[i]['gold_cost'] for i,paid in self.item_hand[team])+15
                if 0 < self.gold[team] < need:candidates.append((min(self.gold[team],15)*.6,'self'))
            if candidates:
                value,target = max(candidates,key=lambda x:(x[0],x[1]))
                actions.append((value,'card',str(index),target))
        for index,(item,paid) in enumerate(self.item_hand[team]):
            price = 0 if paid else CARDS[item]['gold_cost']
            if price > self.gold[team]:continue
            if item in self.gear_ids:
                for h in heroes:
                    gain = self.equipment_value(item, h)
                    if gain > 0:actions.append((gain,'item',str(index),h.uid))
            elif item in (3003,3004):
                for u in friends:
                    heal = min(u.max_hp-u.hp,6 if item == 3003 else u.max_hp)
                    if heal:actions.append((heal*.8,'item',str(index),u.uid))
            elif item == 3005 and self.deck[team]:
                actions.append((3,'item',str(index),'draw'))
            elif item == 10211 and self.improvements[1-team]:
                actions.append((5,'item',str(index),'improvement'))
            elif item == 10216:
                actions.append((5,'item',str(index),'ticket'))
            elif item == 3006:
                occupied = {u.pos for u in self.field()} | self.blocked_positions()
                free = any((7 if team == 0 else 0,c) not in occupied for c in range(self.columns))
                if free:
                    for h in heroes:
                        incoming = self.incoming_damage(h)
                        if incoming >= h.hp and incoming > 0:actions.append((7,'item',str(index),h.uid))
        return actions

    def damage_fort(self, team, amount):
        f = self.forts[team]
        if self.round < f.active_from:return
        effective = min(max(0,f.hp),amount)
        f.hp -= amount
        self.stats[1-team]['building_damage'] += effective
        self.record(f"{f.uid} {'塔' if f.stage == 'tower' else '基地'}受到 {amount} 伤害，剩余 {max(0,f.hp)}")
        if f.hp <= 0 and f.stage == 'tower':
            f.stage, f.hp, f.active_from, f.target_uid = 'base',80,self.round+1,None
            self.stats[1-team]['towers_destroyed'] += 1
            self.record(f"{f.uid}塔被摧毁；基地在相同位置出现，下轮可受伤和攻击；无过量伤害转移")

    def check_victory(self):
        dead = [f.team for f in self.forts if f.stage == 'base' and f.hp <= 0]
        if dead:
            self.finished = True
            self.winner = 1-dead[0] if len(dead)==1 else None
            self.end_reason = 'base-destroyed' if len(dead)==1 else 'simultaneous'

    def cleanup(self):
        before = list(self.gold)
        super().cleanup()
        for team in (0,1):
            self.stats[team]['bounty_income'] += self.gold[team]-before[team]

    def take_action(self, action, team):
        value,kind,index,target_id = action
        if kind not in ('card','item'):
            super().take_action(action,team)
            return
        self.stats[team]['actions'] += 1
        units = {u.uid:u for u in self.field()}
        target = units.get(target_id)
        if kind == 'card':
            card_id = self.hand[team][int(index)];card = CARDS[card_id]
            assert self.mana[team] >= card['mana_cost']
            assert any(h.hero and set(CARDS[h.hero]['colors']).intersection(card['colors']) for h in self.field(team))
            self.hand[team].pop(int(index))
            self.mana[team] -= card['mana_cost']
            self.stats[team]['cards_played'] += 1
            self.stats[team][f'card_used_{card_id}'] += 1
            if card['card_type']=='Creep' or card_id == 10355:
                pos = tuple(map(int,target_id.split(',')))
                self.summon(team,1006 if card_id==10355 else card_id,3 if card_id==10355 else 1,first=pos)
            elif card_id == 10352:self.damage_fort(1-team,6)
            elif card_id == 10402:
                for u in self.field(1-team):u.hp -= max(0,2-u.armor)
            elif card_id == 10313:target.temporary_attack += 4
            elif card_id == 10297:target.temporary_armor += 3
            elif card_id == 10368:target.permanent_attack += 2
            elif card_id == 10169:self.improvements[team].append(card_id)
            elif card_id == 10270:target.hp -= max(0,2-target.armor)
            elif card_id == 10322:
                self.stats[team]['payday_income'] += self.gold[team]
                self.gold[team] *= 2
            self.record(f"{'AB'[team]}出牌 {card['card_name']['schinese']} → {target_id}，消耗 {card['mana_cost']} 法力；评分 {value:.2f}")
            heroes = [h for h in self.field(team) if h.hero]
            if card['card_type']=='Spell':
                self.stats[team]['spells'] += 1
                if not self.first_spell[team] and any(h.hero==10064 for h in heroes):
                    before = self.mana[team];self.mana[team]=min(min(self.round,10),before+2)
                    self.stats[team]['mana_refunded'] += self.mana[team]-before
                self.first_spell[team] = True
                if 'blue' in card['colors']:
                    for z in [h for h in heroes if h.hero==10065]:
                        for enemy in self.field(1-team):
                            if distance(z.pos,enemy.pos)==1:
                                enemy.hp -= 1;self.stats[team]['zeus_damage'] += 1
        else:
            item,paid = self.item_hand[team][int(index)];price = 0 if paid else CARDS[item]['gold_cost']
            assert self.gold[team] >= price
            self.item_hand[team].pop(int(index))
            self.gold[team] -= price
            self.stats[team]['gold_spent'] += price
            self.stats[team]['items_played'] += 1
            self.stats[team][f'item_used_{item}'] += 1
            if item in self.gear_ids:
                old_max = target.max_hp
                target.equipment[CARDS[item]['sub_type']] = item
                target.hp = min(target.max_hp,target.hp+max(0,target.max_hp-old_max))
                self.stats[team]['equipment_equipped'] += 1
            elif item in (3003,3004):target.hp=min(target.max_hp,target.hp+(6 if item==3003 else target.max_hp))
            elif item==3005:self.draw(team,1)
            elif item==10211:self.improvements[1-team].pop(0)
            elif item==10216:
                choice=self.rng(f'ticket:{team}').choice(self.gear_ids)
                self.item_hand[team].append((choice,True))
            elif item==3006:
                occupied={u.pos for u in self.field()} | self.blocked_positions();row=7 if team==0 else 0
                target.pos=next((row,c)for c in range(self.columns)if(row,c)not in occupied)
                target.target_uid=None  # Retreat does not refresh its first-move bonus.
            self.record(f"{'AB'[team]}使用 {CARDS[item]['card_name']['schinese']} → {target_id}，消耗 {price} 金币；评分 {value:.2f}")
        self.cleanup();self.check_victory();self.refresh_targets()

    def action_phase(self):
        side,passes,count=(self.round-1)%2,0,0
        while passes<2 and not self.finished:
            choices=self.actions(side)
            if choices:
                self.take_action(max(choices,key=lambda a:(round(a[0],8),a[1],a[2],a[3])),side)
                self.check();self.frame('行动');passes=0;count+=1
                assert count<=96,'Unbounded match action phase'
            else:passes+=1
            side=1-side

    def combat(self):
        self.refresh_targets();units=self.field();damage=Counter();building_damage=Counter()
        regen={u.uid:self.regeneration(u)for u in units}
        for u in units:
            if u.stunned:continue
            group='hero'if u.hero else'creep'
            self.stats[u.team]['attack_opportunities']+=1
            self.stats[u.team][group+'_attack_opportunities']+=1
            target=self.target(u)
            fort=self.building_target(u)if target is None else None
            if target is None and fort is None:
                self.stats[u.team]['out_of_range']+=1
                self.stats[u.team][group+'_out_of_range']+=1
                continue
            self.stats[u.team]['attacks']+=1;self.stats[u.team][group+'_attacks']+=1
            if fort:
                building_damage[fort.team]+=self.attack(u)
                self.stats[u.team]['building_attacks']+=1
                self.record(f"{u.uid}普攻建筑 {fort.uid}：{self.attack(u)}")
                continue
            amount=self.primary_damage(u,target);damage[target.uid]+=amount
            self.record(f"{u.uid}普攻 {target.uid}：{amount}")
            if target.hero==10069:damage[u.uid]+=max(0,2-u.armor)
            if u.hero==10054:
                dr,dc=self.attack_direction(u,target)
                sides=((target.pos[0]+dc,target.pos[1]-dr),(target.pos[0]-dc,target.pos[1]+dr))
                for extra in units:
                    if extra.team!=u.team and extra.pos in sides:damage[extra.uid]+=max(0,self.attack(u)//2-extra.armor)
        for f in self.forts:
            t=self.fort_target(f)
            if t:
                dealt=max(0,self.fort_power(f)-t.armor);damage[t.uid]+=dealt
                self.stats[f.team]['fort_shots']+=1
                self.record(f"{f.uid}建筑攻击 {t.uid}：{dealt}")
            fountain_row=7 if f.team==0 else 0
            for enemy in units:
                if enemy.team!=f.team and enemy.pos[0]==fountain_row:
                    damage[enemy.uid]+=max(0,10-enemy.armor)
                    self.stats[f.team]['fountain_hits']+=1
        for u in units:
            u.hp-=damage[u.uid]
            recovered=min(regen[u.uid],u.max_hp-u.hp)
            u.hp+=recovered;self.stats[u.team]['regenerated']+=recovered
        self.cleanup()
        for team,amount in building_damage.items():self.damage_fort(team,amount)
        self.check_victory()
        for u in self.field():
            if u.card_id==10111:u.permanent_attack+=2
        self.refresh_targets();self.check()

    def frame(self, phase):
        if not self.trace:return
        super().frame(phase)
        frame=self.frames[-1]
        index={u.uid:u for u in self.field()}
        for entry in frame['units']:
            u=index[entry['id']]
            if entry['target']is None:
                fort=self.building_target(u)
                if fort:
                    entry['target']=fort.uid;entry['arrow']='↑'if fort.row<u.pos[0]else'↓'
            entry['equipment']=[CARDS[i]['card_name']['schinese']for i in u.equipment.values()]
        frame['structures']=[{'team':f.team,'id':f.uid,'stage':f.stage,'hp':max(0,f.hp),'max_hp':f.max_hp,
                              'attack':self.fort_power(f),'ready':self.round>=f.active_from,'target':f.target_uid}for f in self.forts]
        frame['players']=[{'hand':[CARDS[i]['card_name']['schinese']for i in self.hand[t]],
                           'items':[CARDS[i]['card_name']['schinese']+('（已付费）'if paid else'')for i,paid in self.item_hand[t]],
                           'deck':len(self.deck[t]),'improvements':len(self.improvements[t])}for t in(0,1)]

    def run(self, rounds=24):
        for turn in range(1,rounds+1):
            self.round=turn;self.start_round();self.auto_move();self.reveal();self.check();self.frame('移动后／攻击意图公开')
            self.action_phase()
            if not self.finished:self.combat();self.frame('交战后')
            if self.finished:break
        return {'seed':self.seed,'mode':'ordinary-cards','targeting':'aggro','tower_attack':self.tower_attack,'protection':self.protection,
                'rounds':self.round,'max_rounds':rounds,'outcome':('AB'[self.winner]if self.winner is not None else self.end_reason or'timeout'),
                'rosters':[list(r)for r in self.rosters],'gold':self.gold,'stats':[dict(s)for s in self.stats],
                'survivors':[len(self.field(t))for t in(0,1)],
                'forts':[{'stage':f.stage,'hp':max(0,f.hp),'active_from':f.active_from}for f in self.forts],
                **({'frames':self.frames}if self.trace else{})}


def match_pairs():
    rosters=sample_rosters()
    indices={(a,b)for a in range(4)for b in range(4)}
    for a,b in [(4+i,10+i)for i in range(6)]+[(16+i,i)for i in range(4)]:
        indices.update(((a,b),(b,a)))
    return rosters,sorted(indices)


def report(out, results):
    summary=[]
    for power,protect in product((0,4,5,6),(False,True)):
        rs=[r for r in results if r['tower_attack']==power and r['protection']==protect]
        stats=sum((Counter(s)for r in rs for s in r['stats']),Counter());n=len(rs)
        summary.append({'tower_attack':power,'base_attack':2*power,'protection':protect,'games':n,
                        'finished':sum(r['outcome']!='timeout'for r in rs),'timeouts':sum(r['outcome']=='timeout'for r in rs),
                        'mean_rounds':sum(r['rounds']for r in rs)/n,
                        'mean_finished_rounds':(sum(r['rounds']for r in rs if r['outcome']!='timeout')/max(1,sum(r['outcome']!='timeout'for r in rs))),
                        'hero_deaths_per_team':stats['hero_deaths']/(2*n),'gold_spent_per_team':stats['gold_spent']/(2*n),
                        'cards_played_per_team':stats['cards_played']/(2*n),'items_played_per_team':stats['items_played']/(2*n),
                        'equipment_per_team':stats['equipment_equipped']/(2*n),'building_damage_per_team':stats['building_damage']/(2*n),
                        'creep_protection_switches':stats['creep_protection_switches'],'fort_protection_switches':stats['fort_protection_switches'],
                        'bounty_income_per_team':stats['bounty_income']/(2*n),'payday_income_per_team':stats['payday_income']/(2*n),
                        'towers_destroyed':stats['towers_destroyed']})
    dump(out/'comparison.json',summary)
    lines=['# 完整对局实验 01','',f"对照方法与测试假设见 [README](README.md)。每种场景 108 局，八种共 864 局，上限 {results[0]['max_rounds']} 轮；超时不判赢家。",'','| 塔／基地攻击 | 保护仇恨 | 完成／总局数 | 已完成局平均轮数 | 超时 | 每队英雄阵亡 | 每队金币消费 | 每队出牌 | 每队用物品 |','| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s in summary:
        lines.append(f"| {s['tower_attack']}／{s['base_attack']} | {'开'if s['protection']else'关'} | {s['finished']}／{s['games']} | {s['mean_finished_rounds']:.2f} | {s['timeouts']} | {s['hero_deaths_per_team']:.2f} | {s['gold_spent_per_team']:.2f} | {s['cards_played_per_team']:.2f} | {s['items_played_per_team']:.2f} |")
    lines+=['','保护转火只计已有非空目标切换到攻击友方英雄的敌方英雄；普通目标失效后的新锁定仍可能计入，不能将次数当作严格的因果贡献。','','| 塔攻击 | 保护 | 小兵保护转火 | 建筑保护转火 | 每队赏金收入 | 每队发薪日增金 |','| --- | --- | ---: | ---: | ---: | ---: |']
    for s in summary:
        lines.append(f"| {s['tower_attack']} | {s['protection']} | {s['creep_protection_switches']} | {s['fort_protection_switches']} | {s['bounty_income_per_team']:.2f} | {s['payday_income_per_team']:.2f} |")
    totals=sum((Counter(s)for r in results for s in r['stats']),Counter())
    lines+=['','## 卡牌与物品使用覆盖','','| ID | 名称 | 实际使用次数 |','| --- | --- | ---: |']
    for entry in POOL['ordinary_cards']+POOL['items']:
        i=entry['card_id'];prefix='item'if i in ITEMS else'card'
        lines.append(f"| {i} | {CARDS[i]['card_name']['schinese']} | {totals[f'{prefix}_used_{i}']} |")
    lines+=['','所有阵容及逐局结果见 [results.json](results.json)，汇总见 [comparison.json](comparison.json)。[回放](replays.html)提供成对场景，显示建筑血量、手牌、金币和攻击意图。','']
    (out/'summary.md').write_text('\n'.join(lines))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--rounds',type=int,default=24)
    args=parser.parse_args()
    if args.rounds<1:parser.error('rounds must be positive')
    args.out.mkdir(parents=True,exist_ok=True)
    rosters,pairs=match_pairs();results=[]
    for power,protect in product((0,4,5,6),(False,True)):
        for a,b in pairs:
            for seed in(11,12,13):results.append(Match(rosters[a],rosters[b],seed,power,protect).run(args.rounds))
        print(f'Completed tower {power}, protection {protect}: {len(results)} games',flush=True)
    dump(args.out/'results.json',results);report(args.out,results)
    # Use one identical seed/lineup in all eight scenes, then a mixed lineup.
    replays=[Match(rosters[0],rosters[2],11,p,g,trace=True).run(args.rounds)for p,g in product((0,4,5,6),(False,True))]
    replays.append(Match(rosters[7],rosters[18],12,5,True,trace=True).run(args.rounds))
    dump(args.out/'replays.json',replays);viewer(args.out,replays)
    print(f'Saved {len(results)} matches and {len(replays)} replays to {args.out}')


if __name__=='__main__':main()
