#!/usr/bin/env python3
"""Reproducible eight-round hero combat experiments, not a full game or balance solver."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations, product
import json
from pathlib import Path
import random

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT / "docs/design/simulations/hero-batch-02"
COLORS = ("red", "blue", "green", "black")
COLOR_NAMES = dict(zip(COLORS, ("红", "蓝", "绿", "黑")))
POOLS = ((10020, 10069, 10054), (10065, 10064, 10033), (10017, 10014, 10036), (10023, 10047, 10060))
IDS = tuple(h for pool in POOLS for h in pool)
HERO_COLOR = {h: COLORS[i] for i, pool in enumerate(POOLS) for h in pool}
RANGED = {10065, 10064, 10017, 10036, 10060}
CARDINAL = ((-1, 0), (1, 0), (0, -1), (0, 1))
EIGHT = tuple((r, c) for r in (-1, 0, 1) for c in (-1, 0, 1) if r or c)
ARROWS = dict(zip(CARDINAL, ("↑", "↓", "←", "→")))
SOURCE = json.loads((PROJECT / "references/artifact-classic/cards.json").read_text())
PANELS = {c["card_id"]: c for c in SOURCE["cards"] if c["card_id"] in IDS}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def distance(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def valid(pos):
    return 0 <= pos[0] < 8 and 0 <= pos[1] < 6


def roster_kind(roster):
    counts = Counter(HERO_COLOR[h] for h in roster)
    return {1: "pure", 2: "dual", 3: "triple"}[len(counts)]


def sample_rosters():
    """20 rosters: 4 pure, 12 directed dual-color, 4 triple-color; each hero occurs 5 times."""
    sample = [tuple(sorted(pool)) for pool in POOLS]
    for major in range(4):
        others = [i for i in range(4) if i != major]
        for minor in others:
            omit = others.index(minor)
            minority_index = [i for i in range(4) if i != minor].index(major)
            sample.append(tuple(sorted([h for i, h in enumerate(POOLS[major]) if i != omit] + [POOLS[minor][minority_index]])))
    for absent in range(4):
        sample.append(tuple(sorted(POOLS[color][[i for i in range(4) if i != color].index(absent)] for color in range(4) if color != absent)))
    assert len(set(sample)) == 20
    assert set(Counter(h for roster in sample for h in roster).values()) == {5}
    return sample


def roster_name(roster):
    return "／".join(PANELS[h]["card_name"]["schinese"] for h in roster)


@dataclass
class Unit:
    uid: str
    team: int
    hero: int | None
    hp: int
    pos: tuple | None
    cd: int = 0
    next_cd: int = 4
    due: int = 0
    first_move: bool = True
    moved: bool = False
    stunned: bool = False
    bonus: int = 0
    arrow: tuple = (-1, 0)
    target_uid: str | None = None

    @property
    def name(self):
        return PANELS[self.hero]["card_name"]["schinese"] if self.hero else "近战兵"

    @property
    def max_hp(self):
        return PANELS[self.hero]["hit_points"] if self.hero else 4

    @property
    def armor(self):
        return PANELS[self.hero].get("armor", 0) if self.hero else 0

    @property
    def reach(self):
        return 2 if self.hero in RANGED else 1


class Game:
    def __init__(self, roster_a, roster_b, seed=11, probes=False, trace=False, targeting="aggro"):
        if targeting not in ("arrows", "aggro"):
            raise ValueError(f"Unknown targeting rule: {targeting}")
        self.targeting = targeting
        self.seed = seed
        self.probes = probes
        self.trace = trace
        self.rosters = (tuple(roster_a), tuple(roster_b))
        self.units = []
        self.round = 0
        self.gold = [0, 0]
        self.stats = [Counter(), Counter()]
        self.mana = [1, 1]
        self.spells = [set(), set()]
        self.first_spell = [False, False]
        self.frames = []
        self.events = []
        columns = self.rng("opening").sample(range(6), 4)
        for team, roster in enumerate(self.rosters):
            ordered = sorted(roster)
            offset = seed % 3
            ordered = ordered[offset:] + ordered[:offset]
            for slot, hero in enumerate(ordered):
                pos = ((4 if team == 0 else 3), columns[slot]) if slot < 2 else None
                self.units.append(Unit(f"{'AB'[team]}H{slot+1}", team, hero, PANELS[hero]["hit_points"], pos, due=2 if slot == 2 else 0))
            for slot in range(2):
                self.units.append(Unit(f"{'AB'[team]}C1{slot}", team, None, 4, (4 if team == 0 else 3, columns[slot+2])))
        self.check()

    def rng(self, label):
        # Separate environment events from policy evaluation; no Python hash().
        return random.Random(f"hero-v1:{self.seed}:{self.round}:{label}")

    def field(self, team=None):
        return [u for u in self.units if u.pos is not None and (team is None or u.team == team)]

    def record(self, text):
        if self.trace:
            self.events.append(text)

    def frame(self, phase):
        if self.trace:
            units = []
            for u in self.field():
                target = self.target(u)
                arrow = ARROWS[u.arrow] if self.targeting == "arrows" else (ARROWS[self.attack_direction(u, target)] if target else "·")
                units.append({"id": u.uid, "team": u.team, "hero": u.hero, "name": u.name, "r": u.pos[0], "c": u.pos[1], "hp": u.hp,
                              "max_hp": u.max_hp, "attack": self.attack(u), "armor": u.armor, "cd": u.cd, "stunned": u.stunned,
                              "arrow": arrow, "target": target.uid if target else None})
            self.frames.append({"round": self.round, "phase": phase, "gold": list(self.gold), "mana": list(self.mana), "events": self.events[:], "units": units})
            self.events.clear()

    def check(self):
        field = self.field()
        assert len({u.pos for u in field}) == len(field), "Overlapping units"
        assert all(valid(u.pos) and 0 < u.hp <= u.max_hp for u in field), "Invalid position or HP"
        assert all(len(self.field(t)) <= 24 for t in (0, 1)), "Team unit cap exceeded"

    def attack(self, unit, pos=None):
        pos = unit.pos if pos is None else pos
        base = PANELS[unit.hero]["attack"] if unit.hero else 2
        return base + unit.bonus + 2 * sum(u.hero == 10014 and u is not unit and distance(u.pos, pos) == 1 for u in self.field(unit.team))

    def regeneration(self, unit):
        return 2 * sum(u.hero == 10036 and distance(u.pos, unit.pos) <= 1 for u in self.field(unit.team))

    def target(self, unit, pos=None, override=None):
        pos = unit.pos if pos is None else pos
        if self.targeting == "aggro":
            candidates = []
            for foe in self.field(1-unit.team):
                foe_pos = override[1] if override and foe is override[0] else foe.pos
                if (pos[0] == foe_pos[0] or pos[1] == foe_pos[1]) and 0 < distance(pos, foe_pos) <= unit.reach:
                    candidates.append((distance(pos, foe_pos), foe.uid, foe))
            for _, uid, foe in candidates:
                if uid == unit.target_uid:
                    return foe
            return min(candidates, key=lambda entry: entry[:2])[2] if candidates else None
        occupied = {override[1] if override and u is override[0] else u.pos: u for u in self.field()}
        for step in range(1, unit.reach + 1):
            square = (pos[0] + step * unit.arrow[0], pos[1] + step * unit.arrow[1])
            enemy = occupied.get(square)
            if enemy and enemy.team != unit.team:
                return enemy
        return None  # Friends do not obstruct ranged unit attacks in this experiment.

    @staticmethod
    def attack_direction(unit, target):
        dr, dc = target.pos[0]-unit.pos[0], target.pos[1]-unit.pos[1]
        return ((dr > 0)-(dr < 0), (dc > 0)-(dc < 0))

    def refresh_targets(self):
        if self.targeting != "aggro":
            return
        # Commit only actual states. AI's hypothetical target()/position_score()
        # calls must never change locks or affect later candidate evaluations.
        for unit in self.field():
            target = self.target(unit)
            uid = target.uid if target else None
            if uid != unit.target_uid:
                self.stats[unit.team]["target_changes"] += 1
                self.record(f"{unit.uid}索敌：{unit.target_uid or '无'} → {uid or '无'}")
                unit.target_uid = uid

    def primary_damage(self, unit, target, pos=None):
        extra = 4 if unit.hero == 10047 and target.hero else 0
        return max(0, self.attack(unit, pos) + extra - target.armor)

    def cleanup(self):
        for unit in list(self.field()):
            if unit.hp > 0:
                continue
            bounty = 5 if unit.hero else 1
            self.gold[1-unit.team] += bounty
            self.stats[unit.team]["hero_deaths" if unit.hero else "creep_deaths"] += 1
            self.stats[1-unit.team]["hero_kills" if unit.hero else "creep_kills"] += 1
            self.record(f"{unit.uid} {unit.name}阵亡；对方 +{bounty} 金" + (f"，第 {self.round+2} 轮可返场" if unit.hero else ""))
            unit.pos = None
            unit.target_uid = None
            unit.due = self.round + 2 if unit.hero else 0
            if not unit.hero:
                self.units.remove(unit)

    def spawn_hero(self, unit):
        occupied = {u.pos: u for u in self.field()}
        row = 7 if unit.team == 0 else 0
        candidates = [(row, c) for c in self.rng("hero-birth").sample(range(6), 6)]
        free = next((p for p in candidates if p not in occupied), None)
        replaceable = [occupied[p] for p in candidates if p in occupied and occupied[p].team == unit.team and not occupied[p].hero]
        if free is None:
            if not replaceable:
                self.stats[unit.team]["hero_spawn_wait"] += 1
                self.record(f"{unit.uid}返场受阻：泉水无可用格，延至下轮重试")
                return
            victim = min(replaceable, key=lambda u: (u.hp, u.uid))
            free = victim.pos
            victim.hp = 0
            self.cleanup()
        if len(self.field(unit.team)) >= 24:
            creeps = [u for u in self.field(unit.team) if not u.hero]
            if not creeps:
                return
            min(creeps, key=lambda u: (u.hp, u.uid)).hp = 0
            self.cleanup()
        unit.pos, unit.hp = free, unit.max_hp
        unit.first_move, unit.due = True, 0
        self.record(f"{unit.uid} {unit.name}在泉水登场 {free}，技能剩余 CD {unit.cd}")

    def start_round(self):
        for u in self.units:
            u.cd = max(0, u.cd - 1)
            u.stunned, u.moved, u.bonus = False, False, 0
        if self.round > 1:
            for unit in list(self.units):
                if unit.hero and unit.pos is None and unit.due <= self.round:
                    self.spawn_hero(unit)
            preferred = self.rng("creep-birth").sample(range(6), 6)
            for team in (0, 1):
                for slot in range(2):
                    occupied = {u.pos for u in self.field()}
                    row = 7 if team == 0 else 0
                    pos = next(((row, c) for c in preferred if (row, c) not in occupied), None)
                    if pos is None or len(self.field(team)) >= 24:
                        self.stats[team]["creep_spawn_blocked"] += 1
                        continue
                    unit = Unit(f"{'AB'[team]}C{self.round}{slot}", team, None, 4, pos)
                    self.units.append(unit)
                    self.record(f"{unit.uid}近战兵出生 {pos}")
        self.mana = [min(self.round, 10)] * 2
        self.spells = [{"damage", "heal"} if self.probes else set() for _ in (0, 1)]
        self.first_spell = [False, False]

    def auto_move(self):
        fresh = {u.uid for u in self.field() if not u.hero and u.first_move}
        if self.round == 1:
            for u in self.field():
                u.first_move = False
            return
        for wave in (0, 1):
            occupied = {u.pos: u for u in self.field()}
            intents = {}
            for team in (0, 1):
                forward = -1 if team == 0 else 1
                creeps = sorted((u for u in self.field(team) if not u.hero and (wave == 0 or u.uid in fresh)), key=lambda u: (u.pos[0] if team == 0 else -u.pos[0], u.pos[1]))
                for unit in creeps:
                    if any(distance(unit.pos, foe.pos) == 1 and (unit.pos[0] == foe.pos[0] or unit.pos[1] == foe.pos[1]) for foe in self.field(1-team)):
                        continue
                    choices = [(unit.pos[0]+forward, unit.pos[1])]
                    sides = [-1, 1]
                    self.rng(f"sidestep:{wave}:{unit.uid}").shuffle(sides)
                    choices += [(unit.pos[0]+forward, unit.pos[1]+c) for c in sides]
                    for pos in choices:
                        blocker = occupied.get(pos)
                        vacates = blocker and blocker.team == team and blocker.uid in intents
                        if valid(pos) and (blocker is None or vacates):
                            intents[unit.uid] = pos
                            break
            groups = defaultdict(list)
            for uid, pos in intents.items():
                groups[pos].append(uid)
            winners = {}
            for pos, contenders in sorted(groups.items()):
                winner = self.rng(f"conflict:{wave}:{pos}").choice(sorted(contenders))
                winners[winner] = pos
                if len(contenders) > 1:
                    self.record(f"争格 {pos}：{','.join(contenders)}，公开随机结果 {winner}")
            while True:
                blocked = [uid for uid, pos in winners.items() if occupied.get(pos) and occupied[pos].uid not in winners]
                if not blocked:
                    break
                for uid in blocked:
                    del winners[uid]
            for u in self.field():
                if u.uid in winners:
                    self.record(f"{u.uid}自动移动 {u.pos} → {winners[u.uid]}")
                    u.pos = winners[u.uid]
        for u in self.field():
            if not u.hero:
                u.first_move = False

    def reveal(self):
        for u in self.field():
            if self.targeting == "arrows":
                u.arrow = self.rng("arrow:" + u.uid).choice(CARDINAL)
                if self.round == 1 and not u.hero:
                    u.arrow = (-1 if u.team == 0 else 1, 0)
            if u.hero == 10023:
                u.bonus = 4 if self.rng("bounty:" + u.uid).random() < .5 else 0
                self.record(f"{u.uid}赏金被动：本轮额外攻击 {u.bonus}")
        self.refresh_targets()

    def reachable(self, unit):
        occupied = {u.pos for u in self.field()}
        visited, frontier = {unit.pos}, {unit.pos}
        for _ in range(2 if unit.first_move else 1):
            new = set()
            for r, c in frontier:
                for dr, dc in EIGHT:
                    p = (r+dr, c+dc)
                    if valid(p) and p not in occupied and p not in visited:
                        new.add(p)
            visited.update(new)
            frontier = new
        return sorted(visited - {unit.pos})

    def position_score(self, unit, pos):
        target = self.target(unit, pos)
        score = 0.
        if target:
            amount = self.primary_damage(unit, target, pos)
            score += amount * (1.25 if target.hero else .75)
            if amount >= target.hp:
                score += 4 if target.hero else 1.5
        incoming = sum(self.primary_damage(foe, unit) for foe in self.field(1-unit.team) if not foe.stunned and self.target(foe, override=(unit, pos)) is unit)
        score -= .6 * incoming
        if incoming >= unit.hp:
            score -= 7
        friends = [u for u in self.field(unit.team) if u is not unit and distance(u.pos, pos) == 1]
        if unit.hero == 10014:
            score += 1.2 * len(friends)
        if unit.hero == 10036:
            score += sum(min(2, u.max_hp-u.hp) for u in friends)
        enemies = self.field(1-unit.team)
        if enemies:
            score -= .35 * min(distance(pos, foe.pos) for foe in enemies)
            if unit.hero in (10017, 10033, 10060) and unit.cd == 0:
                score += 1.3 * sum(distance(pos, foe.pos) <= 2 for foe in enemies)
        return score

    def actions(self, team):
        actions = []
        enemies = self.field(1-team)
        for u in self.field(team):
            if not u.hero or u.stunned:
                continue
            if u.cd == 0:
                if u.hero in (10017, 10060):
                    for foe in enemies:
                        if distance(u.pos, foe.pos) > 2:
                            continue
                        if u.hero == 10017 and not foe.hero and len(self.field(team)) < 24:
                            value = 4 + self.attack(foe) + foe.hp*.3
                            actions.append((value, "chen", u.uid, foe.uid))
                        elif u.hero == 10060:
                            value = min(8, foe.hp) + ((9 if foe.hero else 2) if foe.hp <= 8 else 0)
                            actions.append((value, "lion", u.uid, foe.uid))
                if u.hero == 10033:
                    for dr, dc in EIGHT:
                        targets = [v for v in enemies if not v.stunned and v.pos in ((u.pos[0]+dr, u.pos[1]+dc), (u.pos[0]+2*dr, u.pos[1]+2*dc))]
                        if targets:
                            value = sum(1 + (self.attack(v) if self.target(v) else 0) + (2 if v.hero and v.cd == 0 else 0) for v in targets)
                            actions.append((value, "stun", u.uid, f"{dr},{dc}"))
            if not u.moved:
                before = self.position_score(u, u.pos)
                for pos in self.reachable(u):
                    value = self.position_score(u, pos) - before
                    if value > .05:
                        actions.append((value, "move", u.uid, f"{pos[0]},{pos[1]}"))
        # Controlled test hands, not production cards: one damage and one heal each round.
        if self.probes and self.mana[team] and any(u.hero for u in self.field(team)):
            if "damage" in self.spells[team]:
                for foe in enemies:
                    amount = max(0, 2-foe.armor)
                    value = min(amount, foe.hp)*1.2 + ((7 if foe.hero else 2) if 0 < foe.hp <= amount else 0)
                    if value > 0:
                        actions.append((value, "damage", "spell", foe.uid))
            if "heal" in self.spells[team]:
                for ally in self.field(team):
                    amount = min(2, ally.max_hp-ally.hp)
                    if amount:
                        actions.append((amount*1.2, "heal", "spell", ally.uid))
        return actions

    def take_action(self, action, team):
        value, kind, actor_id, target_id = action
        index = {u.uid: u for u in self.field()}
        actor = index.get(actor_id)
        target = index.get(target_id)
        self.stats[team]["actions"] += 1
        if kind == "move":
            pos = tuple(map(int, target_id.split(',')))
            self.record(f"{'AB'[team]}行动：{actor.uid} {actor.name}移动 {actor.pos} → {pos}；位置评分提升 {value:.2f}")
            actor.pos, actor.moved, actor.first_move = pos, True, False
            self.stats[team]["hero_moves"] += 1
        elif kind in ("chen", "lion", "stun"):
            assert actor.cd == 0 and not actor.stunned
            actor.cd = actor.next_cd if kind == "lion" else 4
            if kind == "lion":
                actor.next_cd = max(1, actor.next_cd-1)
                target.hp -= 8
                self.stats[team]["lion_casts"] += 1
                self.record(f"{'AB'[team]}行动：{actor.uid}死亡之指 → {target.uid}，8 透甲伤害；本次冷却 {actor.cd}，后续 {actor.next_cd}；评分 {value:.2f}")
            elif kind == "chen":
                target.team = team
                self.stats[team]["conversions"] += 1
                self.record(f"{'AB'[team]}行动：{actor.uid}劝化 {target.uid}，保留位置、生命和箭头；评分 {value:.2f}")
            else:
                dr, dc = map(int, target_id.split(','))
                targets = [u for u in self.field(1-team) if u.pos in ((actor.pos[0]+dr, actor.pos[1]+dc), (actor.pos[0]+2*dr, actor.pos[1]+2*dc))]
                for u in targets:
                    u.stunned = True
                self.stats[team]["stuns"] += len(targets)
                self.record(f"{'AB'[team]}行动：{actor.uid}沟壑方向 ({dr},{dc})，眩晕 {','.join(u.uid for u in targets)}；评分 {value:.2f}")
            self.cleanup()
        else:
            self.spells[team].remove(kind)
            self.mana[team] -= 1
            if kind == "damage":
                target.hp -= max(0, 2-target.armor)
            else:
                target.hp = min(target.max_hp, target.hp+2)
            self.stats[team]["spells"] += 1
            self.record(f"{'AB'[team]}行动：测试法术 {kind} → {target.uid}；评分 {value:.2f}")
            heroes = [u for u in self.field(team) if u.hero]
            if not self.first_spell[team] and any(u.hero == 10064 for u in heroes):
                before = self.mana[team]
                self.mana[team] = min(min(self.round, 10), before+2)
                self.stats[team]["mana_refunded"] += self.mana[team]-before
                self.record(f"冰女触发：当前法力 {before} → {self.mana[team]}")
            self.first_spell[team] = True
            # Choose the blue variant when blue is available; all colors have identical probes.
            for zeus in [u for u in heroes if u.hero == 10065]:
                for foe in self.field(1-team):
                    if distance(zeus.pos, foe.pos) == 1:
                        foe.hp -= 1
                        self.stats[team]["zeus_damage"] += 1
                        self.record(f"宙斯静电场 → {foe.uid}，1 透甲伤害")
            self.cleanup()

        self.refresh_targets()

    def action_phase(self):
        side, passes, count = (self.round-1) % 2, 0, 0
        while passes < 2:
            choices = self.actions(side)
            if choices:
                # Same deterministic greedy policy on both sides; future random events are unknown.
                best = max(choices, key=lambda a: (round(a[0], 8), a[1], a[2], a[3]))
                self.take_action(best, side)
                self.check()
                self.frame("行动")
                passes = 0
                count += 1
                assert count <= 24, "Unbounded action phase"
            else:
                self.record(f"{'AB'[side]}让过：没有正收益的合法行动")
                passes += 1
            side = 1-side

    def combat(self):
        self.refresh_targets()
        field = self.field()
        damage = Counter()
        regeneration = {u.uid: self.regeneration(u) for u in field}
        for unit in field:
            if unit.stunned:
                continue
            target = self.target(unit)
            group = "hero" if unit.hero else "creep"
            self.stats[unit.team]["attack_opportunities"] += 1
            self.stats[unit.team][f"{group}_attack_opportunities"] += 1
            if target is None:
                in_reach = any((unit.pos[0] == foe.pos[0] or unit.pos[1] == foe.pos[1])
                               and 0 < distance(unit.pos, foe.pos) <= unit.reach for foe in field if foe.team != unit.team)
                reason = "arrow_misses" if in_reach else "out_of_range"
                assert self.targeting != "aggro" or not in_reach, "Aggro missed a legal enemy"
                self.stats[unit.team][reason] += 1
                self.stats[unit.team][f"{group}_{reason}"] += 1
                continue
            self.stats[unit.team]["attacks"] += 1
            self.stats[unit.team][f"{group}_attacks"] += 1
            amount = self.primary_damage(unit, target)
            damage[target.uid] += amount
            self.record(f"{unit.uid} {unit.name} → {target.uid} {target.name}：普攻 {amount}")
            if target.hero == 10069:
                reflected = max(0, 2-unit.armor)
                damage[unit.uid] += reflected
                self.record(f"{target.uid}反伤 → {unit.uid}：{reflected}")
            if unit.hero == 10054:
                dr, dc = self.attack_direction(unit, target)
                sides = ((target.pos[0]+dc, target.pos[1]-dr), (target.pos[0]-dc, target.pos[1]+dr))
                for extra in field:
                    if extra.team != unit.team and extra.pos in sides:
                        splash = max(0, self.attack(unit)//2-extra.armor)
                        damage[extra.uid] += splash
                        self.record(f"{unit.uid}溅射 → {extra.uid}：{splash}")
        for unit in field:
            unit.hp -= damage[unit.uid]
            if regeneration[unit.uid]:
                recovered = min(regeneration[unit.uid], unit.max_hp-unit.hp)
                unit.hp += recovered
                self.stats[unit.team]["regenerated"] += recovered
                self.record(f"{unit.uid}恢复 {recovered}，伤害与恢复结算后生命 {unit.hp}")
        self.cleanup()
        self.refresh_targets()
        self.check()

    def run(self, rounds=8):
        for turn in range(1, rounds+1):
            self.round = turn
            self.start_round()
            self.auto_move()
            self.reveal()
            self.check()
            self.frame("移动后／攻击意图公开")
            self.action_phase()
            self.combat()
            self.frame("交战后")
        result = {"seed": self.seed, "mode": "probes" if self.probes else "heroes-only", "targeting": self.targeting, "rounds": rounds,
                  "rosters": [list(r) for r in self.rosters], "gold": self.gold, "stats": [dict(s) for s in self.stats],
                  "survivors": [len(self.field(t)) for t in (0, 1)],
                  "hero_hp_fraction": [round(sum(u.hp/u.max_hp for u in self.field(t) if u.hero), 3) for t in (0, 1)]}
        if self.trace:
            result["frames"] = self.frames
        return result


def make_report(out, rosters, results):
    rounds = results[0]["rounds"]
    targetings = list(dict.fromkeys(r["targeting"] for r in results))
    comparison = []
    for targeting, mode in product(targetings, ("heroes-only", "probes")):
        games = [r for r in results if r["targeting"] == targeting and r["mode"] == mode]
        total = sum((Counter(s) for r in games for s in r["stats"]), Counter())
        breakdown = {}
        for group in ("hero", "creep"):
            n = total[f"{group}_attack_opportunities"]
            breakdown[group] = {"opportunities": n, **{key: total[f"{group}_{key}"]/n for key in ("attacks", "arrow_misses", "out_of_range")}}
        observations = 2*len(games)
        comparison.append({"targeting": targeting, "mode": mode, "games": len(games), "units": breakdown,
                           "hero_deaths_per_team": total['hero_deaths']/observations,
                           "creep_deaths_per_team": total['creep_deaths']/observations,
                           "survivors_per_team": sum(sum(r['survivors']) for r in games)/observations,
                           "hero_moves_per_team": total['hero_moves']/observations})
    dump(out / "comparison.json", comparison)
    lines = ["# 英雄批量推演：索敌实验", "", f"这是 {rounds} 轮战场实验，不包含推塔胜负；不能据此给颜色排强弱。规则、策略和测试假设见 [说明](README.md)。", "",
             "## 覆盖", "", f"本批共 {len(results)} 局；20 个阵容两两有序配对，含镜像；每对 3 个环境种子，分别运行无牌与测试法术两种模式；索敌机制：{', '.join(targetings)}。", "",
             "- 全部合法三英雄阵容：220（纯色 4，双色 108，三色 108）。", "- 本批抽取 20：纯色 4、双色 12、三色 4；每位英雄恰好出现 5 次。", "- 同一阵容轮换第三位英雄的入场选择；种子 11、12、13 覆盖三种延后入场选择。", "", "## 抽样阵容", "", "| 编号 | 类型 | 英雄 |", "| --- | --- | --- |"]
    for i, roster in enumerate(rosters):
        lines.append(f"| {i:02} | {roster_kind(roster)} | {roster_name(roster)} |")
    lines += ["", "## 机制对照", "", "每个单位在每轮交战开始时存活且未眩晕，算一次机会；以下是该类单位的加权比例。", "",
              "| 法术模式 | 索敌 | 单位 | 实际普攻 | 有敌但未选到 | 四向射程内无敌 |", "| --- | --- | --- | ---: | ---: | ---: |"]
    for entry in comparison:
        for group, label in (("hero", "英雄"), ("creep", "小兵")):
            rates = entry['units'][group]
            lines.append(f"| {entry['mode']} | {entry['targeting']} | {label} | {rates['attacks']:.1%} | {rates['arrow_misses']:.1%} | {rates['out_of_range']:.1%} |")
    lines += ["", "下表为每队、每次八轮参赛的平均值，不是胜率。", "", "| 法术模式 | 索敌 | 英雄阵亡 | 小兵阵亡 | 末轮场上单位 | 英雄移动次数 |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for entry in comparison:
        lines.append(f"| {entry['mode']} | {entry['targeting']} | {entry['hero_deaths_per_team']:.2f} | {entry['creep_deaths_per_team']:.2f} | {entry['survivors_per_team']:.2f} | {entry['hero_moves_per_team']:.2f} |")
    for targeting, mode in product(targetings, ("heroes-only", "probes")):
        games = [r for r in results if r["mode"] == mode and r["targeting"] == targeting]
        totals = [Counter() for _ in rosters]
        counts = Counter()
        for result in games:
            for side, roster in enumerate(result["rosters"]):
                index = rosters.index(tuple(roster))
                counts[index] += 1
                totals[index].update(result["stats"][side])
                totals[index]["gold"] += result["gold"][side]
                totals[index]["survivors"] += result["survivors"][side]
        lines += ["", f"## 索敌：{targeting}；法术模式：{mode}", "", "每个阵容有 120 次参赛观测（含双方位置和镜像双方），不是独立玩家对局胜率。以下均为每次参赛的平均值。", "",
                  "| 阵容 | 己方英雄阵亡 | 敌方英雄阵亡 | 获得金币 | 末轮场上单位 | 施法次数 | 有目标的普攻占比 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for i, total in enumerate(totals):
            n = counts[i]
            rate = total['attacks']/max(1, total['attack_opportunities'])
            lines.append(f"| {i:02} | {total['hero_deaths']/n:.2f} | {total['hero_kills']/n:.2f} | {total['gold']/n:.2f} | {total['survivors']/n:.2f} | {total['spells']/n:.2f} | {rate:.1%} |")
        all_stats = sum(totals, Counter())
        lines += ["", "事件总计：" + "；".join(f"{key}={all_stats[key]}" for key in ("conversions", "lion_casts", "stuns", "hero_moves", "mana_refunded", "zeus_damage", "regenerated", "creep_spawn_blocked", "hero_spawn_wait")) + "。"]
        total = all_stats['attack_opportunities']
        lines += ["", f"非眩晕单位的交战机会：{total} 次；实际普攻 {all_stats['attacks']/total:.1%}，射程内有敌人但箭头落空 {all_stats['arrow_misses']/total:.1%}，四向射程内均无敌人 {all_stats['out_of_range']/total:.1%}。后者包含增援赶路，不能全部归因为随机箭头。"]
        lines += ["", "按单位类型拆分。分母为交战开始时存活且未眩晕的单位，每轮每个单位计一次；普攻选到目标即计一次，即使被护甲减到零伤害。技能、反伤和溅射不另计普攻次数。", "",
                  "| 类型 | 单位×轮次 | 实际普攻 | 射程有敌但箭头落空 | 四向射程内无敌人 |", "| --- | ---: | ---: | ---: | ---: |"]
        for group, label in (("hero", "英雄"), ("creep", "小兵")):
            n = all_stats[f"{group}_attack_opportunities"]
            lines.append(f"| {label} | {n} | {all_stats[f'{group}_attacks']/n:.1%} | {all_stats[f'{group}_arrow_misses']/n:.1%} | {all_stats[f'{group}_out_of_range']/n:.1%} |")
    lines += ["", "## 观看与重跑", "", "打开 [replays.html](replays.html) 对照查看样本；每一步包含棋盘、攻击方向、目标 ID、生命、CD 和行动理由。完整批量指标见 [results.json](results.json)，汇总见 [comparison.json](comparison.json)，全部 220 个阵容见 [rosters.json](rosters.json)。", "",
              "```sh", "python3 scripts/simulate_heroes.py --targeting compare", "python3 scripts/simulate_heroes.py --a 10020,10054,10069 --b 10033,10064,10065 --seed 11 --probes --targeting aggro", "```", ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def viewer(out, replays):
    # Standalone local visualization: embedded data, no service, network or external assets.
    data = json.dumps(replays, ensure_ascii=False).replace("<", "\\u003c")
    template = (Path(__file__).with_name("hero_replay.html")).read_text(encoding="utf-8")
    (out / "replays.html").write_text(template.replace("/* REPLAY_DATA */[]", data), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--a", help="Three official hero IDs, comma separated")
    parser.add_argument("--b", help="Three official hero IDs, comma separated")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--probes", action="store_true", help="Single replay: enable identical test-spell hands")
    parser.add_argument("--targeting", choices=("aggro", "arrows", "compare"), default="aggro", help="Target retention, legacy random arrows, or paired batch comparison")
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("rounds must be positive")
    if args.a or args.b:
        if args.targeting == "compare":
            parser.error("Use aggro or arrows for a single replay")
        if not (args.a and args.b):
            parser.error("--a and --b are required together")
        rosters = [tuple(sorted(map(int, v.split(',')))) for v in (args.a, args.b)]
        if any(len(r) != 3 or len(set(r)) != 3 or not set(r) <= set(IDS) for r in rosters):
            parser.error("Each roster must contain three distinct supported heroes")
        if args.out == DEFAULT_OUT:
            args.out = DEFAULT_OUT / "single"
        args.out.mkdir(parents=True, exist_ok=True)
        replay = Game(*rosters, args.seed, args.probes, trace=True, targeting=args.targeting).run(args.rounds)
        dump(args.out / "single-replay.json", replay)
        viewer(args.out, [replay])
        print(f"Replay written to {args.out / 'replays.html'}")
        return
    args.out.mkdir(parents=True, exist_ok=True)
    all_rosters = [tuple(sorted(r)) for r in combinations(IDS, 3)]
    dump(args.out / "rosters.json", [{"heroes": list(r), "name": roster_name(r), "kind": roster_kind(r)} for r in all_rosters])
    sample = sample_rosters()
    results = []
    targetings = ("arrows", "aggro") if args.targeting == "compare" else (args.targeting,)
    for targeting in targetings:
        for probes in (False, True):
            for a, b in product(sample, repeat=2):
                for seed in (11, 12, 13):
                    results.append(Game(a, b, seed, probes, targeting=targeting).run(args.rounds))
            print(f"Completed {targeting} / {'probes' if probes else 'heroes-only'}: {len(results)} total games", flush=True)
    dump(args.out / "results.json", results)
    cases = [(sample[0], sample[1], False), (sample[0], sample[2], False), (sample[0], sample[3], False),
             (sample[1], sample[2], True), (sample[7], sample[18], True)]
    replays = [Game(a, b, 11, p, trace=True, targeting=targeting).run(args.rounds) for a, b, p in cases for targeting in targetings]
    dump(args.out / "replays.json", replays)
    viewer(args.out, replays)
    make_report(args.out, sample, results)
    print(f"Saved {len(results)} games, {len(replays)} replays to {args.out}")


if __name__ == "__main__":
    main()
