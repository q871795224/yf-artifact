import unittest

from playable_match import PlaySession, legal_actions, InvalidAction, StaleAction
from simulate_finishers import FinisherUnit
from simulate_match import CARDS


def unit(uid, team, cid, pos):
    return FinisherUnit(uid, team, cid if CARDS[cid]['card_type'] == 'Hero' else None,
                        CARDS[cid]['hit_points'], pos, card_id=cid)


def empty_session():
    s = PlaySession(13)
    g = s.game
    g.units = []
    g.hand = [[], []]
    g.deck = [[], []]
    g.item_hand = [[], []]
    g.item_deck = [[], []]
    g.events.clear()
    g.round = 10
    g.mana = [10, 10]
    g.gold = [0, 0]
    g.tower_attack = 0
    return s


def choose(s, kind, actor=None, target=None):
    return next(view['id'] for view, action in s._catalog() if action[1] == kind
                and (actor is None or action[2] == actor)
                and (target is None or action[3] == target))


class PlayableTests(unittest.TestCase):
    def test_opening_is_real_first_round_with_two_heroes_each_and_contact(self):
        s = PlaySession(13)
        self.assertEqual(s.game.round, 1)
        for team in (0, 1):
            self.assertEqual(sum(bool(u.hero) for u in s.game.field(team)), 2)
        self.assertTrue(any(s.game.target(u) for u in s.game.field()))
        self.assertEqual(s.game.mana, [1, 1])
        self.assertEqual([len(x) for x in s.game.hand], [5, 5])
        self.assertEqual([len(x) for x in s.game.item_hand], [1, 1])

    def test_human_can_take_unprofitable_move_and_cannot_move_twice(self):
        s = empty_session()
        h = unit('hero', 0, 10020, (4, 2))
        h.first_move = False
        s.game.units = [h]
        self.assertNotIn((0, 'move', 'hero', '5,2'), s.game.actions(0))
        action = choose(s, 'move', 'hero', '5,2')
        s.apply(s.version, action)
        self.assertEqual(h.pos, (5, 2))
        self.assertTrue(h.moved)
        self.assertFalse(any(a[1] == 'move' for a in legal_actions(s.game)))

    def test_first_move_two_steps_requires_free_path(self):
        s = empty_session()
        h = unit('hero', 0, 10020, (7, 2))
        s.game.units = [h]
        self.assertIn((0, 'move', 'hero', '5,2'), legal_actions(s.game))
        s.game.units += [unit(f'c{col}', 0, 1006, (6, col)) for col in range(6)]
        self.assertNotIn((0, 'move', 'hero', '5,2'), legal_actions(s.game))

    def test_human_can_choose_every_spell_target_not_only_ai_best(self):
        s = empty_session()
        s.game.units = [unit('caster', 0, 10060, (7, 0)),
                        unit('small', 1, 1006, (1, 1)), unit('large', 1, 10069, (2, 2))]
        s.game.hand[0] = [10354]
        targets = {a[3] for a in legal_actions(s.game) if a[1] == 'card'}
        self.assertEqual(targets, {'small', 'large'})

    def test_stun_does_not_lock_card_color_but_blocks_movement_and_skills(self):
        s = empty_session()
        h = unit('hero', 0, 10033, (4, 2))
        h.stunned = True
        s.game.units = [h]
        s.game.hand[0] = [10412]
        choices = legal_actions(s.game)
        self.assertTrue(any(a[1] == 'card' for a in choices))
        self.assertFalse(any(a[1] in ('move', 'stun') for a in choices))
        h.hp = 0
        s.game.cleanup()
        self.assertFalse(any(a[1] == 'card' for a in legal_actions(s.game)))

    def test_skill_has_eight_directions_two_deep_and_no_mana_cost(self):
        s = empty_session()
        h = unit('hero', 0, 10033, (4, 2))
        e = unit('enemy', 1, 1006, (2, 4))
        s.game.units = [h, e]
        self.assertEqual(sum(a[1] == 'stun' for a in legal_actions(s.game)), 8)
        before = s.game.mana[0]
        s.apply(s.version, choose(s, 'stun', 'hero', '-1,1'))
        self.assertTrue(e.stunned)
        self.assertEqual((h.cd, s.game.mana[0]), (4, before))

    def test_equipment_replacement_is_legal_even_when_weaker_and_spends_only_gold(self):
        s = empty_session()
        h = unit('hero', 0, 10020, (4, 2))
        h.equipment['Weapon'] = 10263
        s.game.units = [h]
        s.game.item_hand[0] = [(3002, False)]
        s.game.gold[0] = CARDS[3002]['gold_cost']
        s.apply(s.version, choose(s, 'item', '0', 'hero'))
        self.assertEqual(h.equipment['Weapon'], 3002)
        self.assertEqual(s.game.gold[0], 0)
        self.assertEqual(s.game.mana[0], 10)

    def test_forged_or_stale_action_does_not_change_board_or_spend_resources(self):
        s = PlaySession(13)
        before = s.snapshot()
        with self.assertRaises(InvalidAction):
            s.apply(s.version, 'invented-target')
        self.assertEqual(s.snapshot(), before)
        with self.assertRaises(StaleAction):
            s.apply(s.version+1, 'pass')
        self.assertEqual(s.snapshot(), before)

    def test_every_player_action_gives_ai_exactly_one_reply_not_whole_round(self):
        s = PlaySession(13)
        s.apply(s.version, choose(s, 'move'))
        self.assertEqual(s.version, 1)
        self.assertEqual(s.phase, 'action')
        self.assertLessEqual(s.game.stats[1]['actions'], 1)
        self.assertEqual(s.side, 0)

    def test_two_passes_resolve_simultaneous_attacks_and_award_bounties(self):
        s = empty_session()
        a, b = unit('a', 0, 1006, (4, 2)), unit('b', 1, 1006, (3, 2))
        a.hp = b.hp = 2
        s.game.units = [a, b]
        packet = s.apply(s.version, 'pass')
        self.assertEqual(s.phase, 'round_end')
        self.assertFalse(s.game.field())
        self.assertEqual(s.game.gold, [1, 1])
        self.assertTrue(any(f['phase'] == 'combat' for f in packet['frames']))

    def test_ai_pass_followed_by_human_pass_also_enters_combat(self):
        s = empty_session()
        s.game.units = [unit('hero', 0, 10020, (4, 2))]
        s.apply(s.version, choose(s, 'move'))
        self.assertEqual(s.passes, 1)
        s.apply(s.version, 'pass')
        self.assertEqual(s.phase, 'round_end')

    def test_next_round_draws_spawns_and_mana_caps_at_ten(self):
        s = PlaySession(13)
        s.phase = 'round_end'
        before = len(s.game.deck[0])
        s.apply(s.version, 'next_round')
        self.assertEqual((s.game.round, s.game.mana[0]), (2, 2))
        self.assertEqual(len(s.game.deck[0]), before-2)
        self.assertEqual(sum(bool(u.hero) for u in s.game.field(0)), 3)
        self.assertEqual(sum(not u.hero for u in s.game.field(0)), 4)
        s.phase = 'round_end'
        s.apply(s.version, 'next_round')
        self.assertEqual(len(s.game.item_hand[0]), 2)

    def test_death_skips_one_round_then_respawns_with_equipment(self):
        s = empty_session()
        h = unit('hero', 0, 10020, (4, 2))
        h.equipment['Weapon'] = 10263
        s.game.units = [h]
        h.hp = 0
        s.game.cleanup()
        s.phase = 'round_end'
        s.apply(s.version, 'next_round')
        self.assertIsNone(h.pos)
        s.phase = 'round_end'
        s.apply(s.version, 'next_round')
        self.assertEqual(h.pos[0], 7)
        self.assertEqual(h.equipment['Weapon'], 10263)
        view = next(u for u in s.snapshot()['heroes'] if u['key'] == 'hero')
        self.assertEqual(view['attack'], 14)

    def test_tower_becomes_base_then_base_destruction_wins_immediately(self):
        s = empty_session()
        s.game.units = [unit('mage', 0, 10033, (4, 2))]
        s.game.hand[0] = [10353]
        s.game.forts[1].hp = 10
        s.apply(s.version, choose(s, 'card'))
        self.assertEqual((s.game.forts[1].stage, s.game.forts[1].hp), ('base', 80))
        self.assertFalse(any(a[1] == 'card' for a in legal_actions(s.game)))
        s.game.round += 1
        s.game.mana[0] = 10
        s.game.hand[0] = [10353]
        s.game.forts[1].hp = 20
        s.apply(s.version, choose(s, 'card'))
        self.assertEqual((s.phase, s.game.winner), ('finished', 0))
        with self.assertRaises(InvalidAction):
            s.apply(s.version, 'pass')

    def test_snapshot_does_not_leak_opponent_hand_or_future_draws(self):
        s = PlaySession(13)
        state = s.snapshot()
        self.assertIsInstance(state['opponent']['cards'], int)
        self.assertNotIn('hand', state['opponent'])
        self.assertNotIn('deck_cards', state)
        self.assertNotIn('敌方抽牌：', str(state['log']))

    def test_complete_matches_share_engine_actions_and_replay_deterministically(self):
        s = PlaySession(13)
        for _ in range(600):
            if s.phase == 'finished':
                break
            if s.phase == 'round_end':
                s.apply(s.version, 'next_round')
                continue
            choices = s.game.actions(0)
            if choices:
                best = max(choices, key=lambda a: (round(a[0], 8), a[1], a[2], a[3]))
                key = next(view['id'] for view, action in s._catalog() if action[1:] == best[1:])
            else:
                key = 'pass'
            s.apply(s.version, key)
        self.assertEqual((s.phase, s.game.round, s.game.winner), ('finished', 24, 0))
        replay = PlaySession(13)
        for command in s.export()['commands']:
            replay.apply(command['version'], command['action_id'])
        self.assertEqual(s.snapshot(), replay.snapshot())


if __name__ == '__main__':
    unittest.main()
