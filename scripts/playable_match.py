"""Human-turn adapter around the existing Classic-based simulation engine.

The engine still owns damage, resources, movement, spawning and victory. This
module enumerates human legal choices (independent of AI scores), steps the
alternating action phase, and serializes the information visible to the player.
"""

from copy import deepcopy
import hashlib
import re

from simulate_finishers import FinisherMatch
from simulate_match import CARDS
from simulate_heroes import EIGHT, ARROWS, distance, valid


PLAYER_ROSTER = (10020, 10033, 10014)
ENEMY_ROSTER = (10069, 10064, 10047)
SKILLS = {"stun": "沟壑", "chen": "神圣劝化", "lion": "死亡之指",
          "horn": "领袖号角", "blade": "封神之刃"}
SUPPORTED_CARDS = {10352, 10353, 10402, 10412, 10313, 10297, 10368, 10169,
                   10270, 10322, 10344, 10425, 10307, 10311, 10410, 10354, 10355}


class InvalidAction(ValueError):
    pass


class StaleAction(InvalidAction):
    pass


def legal_actions(game, team=0):
    """All legal player actions, including moves/replacements with a poor AI score."""
    result = []
    friends, foes = game.field(team), game.field(1-team)
    heroes = [u for u in friends if u.hero]
    colors = {c for h in heroes for c in CARDS[h.hero]['colors']}

    def add(kind, actor, target):
        result.append((0, kind, str(actor), str(target)))

    for hero in heroes:
        if hero.stunned:
            continue
        if not hero.moved:
            for r, c in game.reachable(hero):
                add('move', hero.uid, f'{r},{c}')
        if hero.cd == 0:
            if hero.hero == 10033:
                for dr, dc in EIGHT:
                    if any(valid((hero.pos[0]+dr*n, hero.pos[1]+dc*n)) for n in (1, 2)):
                        add('stun', hero.uid, f'{dr},{dc}')
            elif hero.hero in (10017, 10060):
                for foe in foes:
                    if distance(hero.pos, foe.pos) <= 2:
                        if hero.hero == 10060:
                            add('lion', hero.uid, foe.uid)
                        elif not foe.hero and len(friends) < 24:
                            add('chen', hero.uid, foe.uid)
        if 10260 in hero.equipment.values() and hero.horn_cd == 0 and len(friends) < 24:
            for r, c in game.spawn_positions(team):
                add('horn', hero.uid, f'{r},{c}')
        if 10263 in hero.equipment.values() and hero.blade_cd == 0:
            victim = game.target(hero)
            if game.improvements[1-team] or (victim and victim.equipment):
                add('blade', hero.uid, victim.uid if victim else 'improvements')

    for index, card_id in enumerate(game.hand[team]):
        card = CARDS[card_id]
        if card['mana_cost'] > game.mana[team] or not colors.intersection(card['colors']):
            continue
        targets = []
        if card['card_type'] == 'Creep' or card_id == 10355:
            if len(friends) < 24:
                targets = [f'{r},{c}' for r, c in game.spawn_positions(team)]
        elif card_id in (10352, 10353):
            if game.round >= game.forts[1-team].active_from:
                targets = ['fort']
        elif card_id in (10402, 10412, 10344, 10425, 10311):
            targets = ['all']
        elif card_id in (10169, 10322):
            targets = ['self']
        elif card_id == 10307:
            targets = ['draw']
        elif card_id in (10313, 10297, 10368):
            targets = [u.uid for u in friends if
                       (card_id != 10297 or u.hero) and
                       (card_id != 10313 or (u.hero and 'red' in CARDS[u.hero]['colors']))]
        elif card_id in (10270, 10354, 10410):
            targets = [u.uid for u in foes if card_id != 10410 or not u.hero]
        elif card_id not in SUPPORTED_CARDS:
            raise ValueError(f'Unsupported playable card: {card_id}')
        for target in targets:
            add('card', index, target)

    for index, (item, paid) in enumerate(game.item_hand[team]):
        if (0 if paid else CARDS[item]['gold_cost']) > game.gold[team]:
            continue
        targets = []
        if item in game.gear_ids:
            targets = [h.uid for h in heroes]
        elif item in (3003, 3004):
            targets = [u.uid for u in friends]
        elif item == 3005:
            targets = ['draw']
        elif item == 10211 and game.improvements[1-team]:
            targets = ['improvement']
        elif item == 10216:
            targets = ['ticket']
        elif item == 3006:
            occupied = {u.pos for u in game.field()}
            if any((7 if team == 0 else 0, c) not in occupied for c in range(6)):
                targets = [h.uid for h in heroes]
        for target in targets:
            add('item', index, target)
    return result


def action_view(game, action, version):
    _, kind, actor, target = action
    key = f'{version}:{kind}:{actor}:{target}'
    view = {'id': hashlib.sha256(key.encode()).hexdigest()[:20],
            'kind': kind, 'actor': actor, 'target': target}
    if kind in ('card', 'item'):
        index = int(actor)
        card_id = game.hand[0][index] if kind == 'card' else game.item_hand[0][index][0]
        view.update(index=index, card_id=card_id)
    if kind in ('move', 'horn') or (kind == 'card' and ',' in target):
        view['row'], view['col'] = map(int, target.split(','))
    if kind == 'stun':
        view['dr'], view['dc'] = map(int, target.split(','))
    return view


class PlaySession:
    def __init__(self, seed=13):
        self.seed = seed
        self.game = FinisherMatch(PLAYER_ROSTER, ENEMY_ROSTER, seed, 4, True, trace=True)
        self.version = 0
        self.phase = 'action'
        self.side = 0
        self.passes = 0
        self.log = []
        self.commands = []
        self._known_units = {}
        self.last_label = '第 1 回合开始'
        self._begin_round()

    def _drain_events(self):
        # Keep scores, internal IDs and Python tuple coordinates out of player UI.
        self._known_units.update({u.uid: ('我方' if u.team == 0 else '敌方') + u.name for u in self.game.units})
        units = self._known_units
        for raw in self.game.events:
            if '索敌' in raw:
                continue
            text = re.sub(r'；(?:位置评分提升|评分).*', '', raw)
            for uid in sorted(units, key=len, reverse=True):
                text = re.sub(r'(?<![A-Za-z0-9])' + re.escape(uid) + r'(?![A-Za-z0-9])', units[uid], text)
            text = text.replace('AF', '我方建筑').replace('BF', '敌方建筑')
            text = re.sub(r'\(([0-7]),\s*([0-5])\)',
                          lambda m: f'第{int(m[1])+1}排第{int(m[2])+1}列', text)
            text = re.sub(r'\bA(?=行动|出牌|使用|抽牌|收到|让过)', '我方', text)
            text = re.sub(r'\bB(?=行动|出牌|使用|抽牌|收到|让过)', '敌方', text)
            # Opponent draw contents remain hidden, including in the event feed.
            if text.startswith('敌方抽牌'):
                text = '敌方抽取一张普通牌'
            elif text.startswith('敌方收到物品'):
                text = '敌方获得一张物品'
            self.log.append({'round': self.game.round, 'text': text})
        self.game.events.clear()
        self.log = self.log[-400:]

    def _begin_round(self):
        self.game.round += 1
        self.game.start_round()
        self.game.auto_move()
        self.game.reveal()
        self.game.check()
        self.side = (self.game.round-1) % 2
        self.passes = 0
        self.phase = 'action'
        self.last_label = f'第 {self.game.round} 回合 · 自动行军完成'
        self._drain_events()
        self._ai_response([])

    def _finish_if_needed(self):
        self.game.check_victory()
        if self.game.finished:
            self.phase = 'finished'
            return True
        return False

    def _describe(self, action, team):
        _, kind, actor, target = action
        prefix = '我方' if team == 0 else '敌方'
        if kind in ('card', 'item'):
            cid = self.game.hand[team][int(actor)] if kind == 'card' else self.game.item_hand[team][int(actor)][0]
            return prefix + ('施放' if kind == 'card' else '使用') + CARDS[cid]['card_name']['schinese']
        unit = next(u for u in self.game.field(team) if u.uid == actor)
        return prefix + unit.name + ('移动' if kind == 'move' else '使用' + SKILLS[kind])

    def _ai_response(self, frames):
        if self.side != 1 or self.phase != 'action':
            return
        choices = self.game.actions(1)
        if choices:
            action = max(choices, key=lambda a: (round(a[0], 8), a[1], a[2], a[3]))
            self.last_label = self._describe(action, 1)
            self.game.take_action(action, 1)
            self.passes = 0
        else:
            self.last_label = '敌方让过'
            self.game.record('B让过')
            self.passes += 1
        self.game.check()
        self._known_units.update({u.uid: ('我方' if u.team == 0 else '敌方') + u.name for u in self.game.units})
        self._drain_events()
        self._finish_if_needed()
        self.side = 0
        frames.append(self._frame(self.last_label))
        if self.passes == 2 and self.phase != 'finished':
            self._combat(frames)

    def _combat(self, frames):
        frames.append(self._frame('双方让过 · 开始交战', phase='combat'))
        self.game.combat()
        self._drain_events()
        self.phase = 'finished' if self.game.finished else 'round_end'
        self.last_label = '交战结束 · 可查看损伤与阵亡'
        frames.append(self._frame(self.last_label))

    def _catalog(self):
        if self.phase != 'action' or self.side != 0 or self.game.finished:
            return []
        return [(action_view(self.game, a, self.version), a) for a in legal_actions(self.game)]

    def apply(self, version, action_id):
        if type(version) is not int or version != self.version:
            raise StaleAction('战场已更新，请按当前状态重新操作。')
        if self.phase == 'finished':
            raise InvalidAction('对局已经结束，可以开始新一局。')
        if action_id == 'concede':
            self.game.finished, self.game.winner, self.game.end_reason = True, 1, 'conceded'
            self.phase = 'finished'
            self.last_label = '你已认输'
            self.commands.append({'version': version, 'action_id': 'concede'})
            self.version += 1
            return self.packet()
        if action_id == 'next_round':
            if self.phase != 'round_end':
                raise InvalidAction('当前回合尚未交战结束。')
            self._begin_round()
            self.commands.append({'version': version, 'action_id': 'next_round'})
            self.version += 1
            return self.packet()
        if self.phase != 'action' or self.side != 0:
            raise InvalidAction('请等待当前阶段结束。')
        choices = {view['id']: action for view, action in self._catalog()}
        if action_id != 'pass' and action_id not in choices:
            raise InvalidAction('该操作现在不可用，请重新选择目标。')
        frames = []
        if action_id == 'pass':
            self.passes += 1
            self.last_label = '我方让过'
            self.game.record('A让过')
        else:
            action = choices[action_id]
            self.last_label = self._describe(action, 0)
            self.game.take_action(action, 0)
            self.passes = 0
        self.game.check()
        self._drain_events()
        self._finish_if_needed()
        frames.append(self._frame(self.last_label))
        if self.phase != 'finished':
            if self.passes == 2:
                self._combat(frames)
            else:
                self.side = 1
                self._ai_response(frames)
        self.commands.append({'version': version, 'action_id': action_id})
        self.version += 1
        return self.packet(frames)

    def _unit_view(self, u):
        target = self.game.target(u) if u.pos is not None and not u.stunned else None
        fort = self.game.building_target(u) if u.pos is not None and target is None and not u.stunned else None
        arrow = ARROWS[self.game.attack_direction(u, target)] if target else ('↑' if fort and fort.row < u.pos[0] else '↓' if fort else None)
        equipment = []
        for slot, cid in u.equipment.items():
            cd = u.horn_cd if cid == 10260 else u.blade_cd if cid == 10263 else None
            equipment.append({'slot': slot, 'id': cid, 'cooldown': cd})
        return {'key': u.uid, 'id': u.card_id, 'team': 'ally' if u.team == 0 else 'enemy',
                'hero': bool(u.hero), 'row': u.pos[0] if u.pos else None,
                'col': u.pos[1] if u.pos else None, 'hp': u.hp if u.pos else 0, 'maxHp': u.max_hp,
                'attack': self.game.attack(u, u.pos if u.pos is not None else (-99, -99)),
                'armor': u.armor, 'range': u.reach, 'cooldown': u.cd,
                'nextCooldown': u.next_cd, 'stunned': u.stunned, 'moved': u.moved,
                'firstMove': u.first_move, 'due': u.due, 'equipment': equipment,
                'siege': self.game.siege(u), 'cleave': self.game.cleave(u),
                'regeneration': self.game.regeneration(u) if u.pos else 0,
                'target': target.uid if target else fort.uid if fort else None, 'arrow': arrow}

    def _frame(self, label, phase=None):
        g = self.game
        return {'round': g.round, 'phase': phase or self.phase, 'label': label,
                'units': [self._unit_view(u) for u in g.field()],
                'heroes': [self._unit_view(u) for u in g.units if u.hero],
                'mana': g.mana[0], 'maxMana': min(10, g.round), 'gold': g.gold[0],
                'forts': [{'team': f.team, 'hp': max(0, f.hp), 'maxHp': f.max_hp,
                           'stage': f.stage, 'attack': g.fort_power(f),
                           'ready': g.round >= f.active_from, 'target': f.target_uid} for f in g.forts]}

    def snapshot(self):
        g = self.game
        state = self._frame(self.last_label)
        catalog = [view for view, _ in self._catalog()]
        state.update(version=self.version, seed=self.seed,
                     hand=list(g.hand[0]), items=[{'id': cid, 'paid': paid} for cid, paid in g.item_hand[0]],
                     deck=len(g.deck[0]), itemDeck=len(g.item_deck[0]),
                     opponent={'cards': len(g.hand[1]), 'items': len(g.item_hand[1]), 'gold': g.gold[1], 'mana': g.mana[1]},
                     improvements=[list(x) for x in g.improvements],
                     actions=catalog, passes=self.passes, winner=g.winner, endReason=g.end_reason,
                     log=self.log[-80:], stats=[dict(s) for s in g.stats],
                     rosters=[list(r) for r in g.rosters])
        return state

    def packet(self, frames=None):
        return {'state': self.snapshot(), 'frames': frames or []}

    def export(self):
        return {'schema_version': 1, 'seed': self.seed, 'rosters': [list(r) for r in self.game.rosters],
                'commands': deepcopy(self.commands), 'round': self.game.round,
                'phase': self.phase, 'winner': self.game.winner, 'reason': self.game.end_reason,
                'events': deepcopy(self.log)}
