import unittest
from collections import Counter

from simulate_match import Match, CARDS, sample_rosters
from simulate_expanded_match import ExpandedMatch, ExpandedUnit, EXPANDED_POOL


def unit(uid, team, cid, pos):
    return ExpandedUnit(uid, team, cid if CARDS[cid]['card_type'] == 'Hero' else None,
                        CARDS[cid]['hit_points'], pos, card_id=cid)


def empty(policy='push'):
    rosters = sample_rosters()
    g = ExpandedMatch(rosters[0], rosters[1], tower_attack=0, protection=True, policy=policy)
    g.units = []; g.hand = [[], []]; g.deck = [[], []]
    g.item_hand = [[], []]; g.item_deck = [[], []]
    g.round = 10; g.mana = [10, 10]
    return g


class ExpandedMatchTests(unittest.TestCase):
    def test_original_fields_and_signature_exclusion(self):
        self.assertEqual(Counter(c['colors'][0] for c in EXPANDED_POOL['ordinary_cards']),
                         {c: 6 for c in ('red', 'blue', 'green', 'black')})
        self.assertEqual(Counter(c['category'] for c in EXPANDED_POOL['items']),
                         {'equipment': 12, 'consumable': 6})
        signatures = {r['card_id'] for c in CARDS.values() if c['card_type'] == 'Hero'
                      for r in c['references'] if r['ref_type'] == 'includes'}
        for c in EXPANDED_POOL['ordinary_cards'] + EXPANDED_POOL['items']:
            self.assertNotIn(c['card_id'], signatures)
            for k in ('gold_cost', 'mana_cost', 'attack', 'armor', 'hit_points', 'card_text'):
                if k in c:
                    self.assertEqual(c[k], CARDS[c['card_id']][k])

    def test_old_pool_and_policy_reproduce_complete_original_game(self):
        rosters = sample_rosters()
        old = Match(rosters[0], rosters[2], 11, 4, True).run()
        new = ExpandedMatch(rosters[0], rosters[2], 11, 4, True, pool='first', policy='greedy').run()
        for key in old:
            self.assertEqual(old[key], new[key], key)

    def test_deck_expansion_preserves_draw_and_item_schedules(self):
        rosters = sample_rosters()
        g = ExpandedMatch(rosters[0], rosters[1])
        self.assertEqual((len(g.hand[0]), len(g.deck[0]), len(g.item_hand[0])), (5, 31, 1))
        self.assertEqual(set(Counter(g.hand[0]+g.deck[0]).values()), {6})
        g.round = 2; g.start_round()
        self.assertEqual((len(g.hand[0]), len(g.item_hand[0])), (7, 1))
        g.round = 3; g.start_round()
        self.assertEqual((len(g.hand[0]), len(g.item_hand[0])), (9, 2))

    def test_siege_damages_in_range_building_while_unit_remains_priority(self):
        g = empty(); h = unit('h', 0, 10020, (1, 1)); e = unit('e', 1, 10097, (1, 2))
        h.equipment['Weapon'] = 10223
        g.units = [h, e]; g.combat()
        self.assertEqual(e.hp, 8)  # Axe 6 + maul 2, not 13.
        self.assertEqual(g.forts[1].hp, 35)  # Only siege 5 reaches the tower.
        self.assertEqual(g.stats[0]['siege_damage'], 5)

    def test_siege_does_not_attack_building_from_midfield(self):
        g = empty(); h = unit('h', 0, 10020, (4, 1)); e = unit('e', 1, 10097, (4, 2))
        h.equipment['Weapon'] = 10223
        g.units = [h, e]; g.combat()
        self.assertEqual(g.forts[1].hp, 40)

    def test_cleave_only_splashes_two_perpendicular_enemy_squares(self):
        g = empty(); h = unit('h', 0, 10020, (4, 1)); h.equipment['Weapon'] = 10212
        main = unit('main', 1, 10097, (4, 2))
        side = unit('side', 1, 10097, (3, 2)); far = unit('far', 1, 10097, (3, 3))
        g.units = [h, main, side, far]; g.combat()
        self.assertEqual((main.hp, side.hp, far.hp), (8, 14, 16))

    def test_pike_growth_survives_death_and_replacement_removes_growth(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); h.equipment['Weapon'] = 10252
        g.units = [h]; g.combat(); self.assertEqual(g.attack(h), 9)
        h.hp = 0; g.cleanup(); g.round = 12; g.start_round()
        self.assertEqual(g.attack(h), 9)
        g.item_hand[0] = [(10215, False)]; g.gold[0] = 7
        g.take_action((1, 'item', '0', 'h'), 0)
        self.assertEqual(g.attack(h), 10)  # No inherited growth on the broadsword.

    def test_pierce_and_equip_purge_stun(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); e = unit('e', 1, 10104, (4, 3))
        g.units = [h, e]; h.stunned = True
        g.item_hand[0] = [(10256, False)]; g.gold[0] = 5
        g.take_action((1, 'item', '0', 'h'), 0)
        self.assertFalse(h.stunned)
        self.assertEqual(g.primary_damage(h, e), 8)  # Armor 2 does not reduce it.

    def test_triumph_modifiers_persist_and_temporary_cleave_expires(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); g.units = [h]
        g.hand[0] = [10425]; g.take_action((1, 'card', '0', 'all'), 0)
        self.assertEqual((g.attack(h), h.armor, h.hp, h.max_hp, g.cleave(h), g.siege(h)),
                         (10, 6, 14, 14, 4, 4))
        g.mana[0] = 4; g.hand[0] = [10344]
        g.take_action((1, 'card', '0', 'all'), 0); self.assertEqual(g.cleave(h), 8)
        g.round = 11; g.start_round(); self.assertEqual(g.cleave(h), 4)
        h.hp = 0; g.cleanup(); g.round = 13; g.start_round()
        self.assertEqual((h.hp, h.max_hp, h.armor, g.attack(h)), (14, 14, 6, 10))

    def test_arm_rebellion_only_modifies_current_friendly_nonheroes(self):
        g = empty(); h = unit('h', 0, 10017, (4, 2)); c = unit('c', 0, 1006, (4, 3))
        e = unit('e', 1, 1006, (2, 2)); g.units = [h, c, e]
        g.hand[0] = [10311]; g.take_action((1, 'card', '0', 'all'), 0)
        self.assertEqual((g.attack(c), c.armor, g.attack(h), g.attack(e)), (4, 1, 4, 2))
        g.summon(0, 1006)
        self.assertEqual((g.attack(g.units[-1]), g.units[-1].armor), (2, 0))

    def test_blue_spell_refund_and_draw_and_ten_mana_finisher(self):
        g = empty(); h = unit('h', 0, 10064, (4, 2)); g.units = [h]
        g.hand[0] = [10307]; g.deck[0] = [10353, 10412]
        g.take_action((1, 'card', '0', 'draw'), 0)
        self.assertEqual((g.mana[0], g.hand[0]), (8, [10412, 10353]))
        g.mana[0] = 10; g.forts[1].stage = 'base'; g.forts[1].hp = 20
        best = max(g.actions(0), key=lambda a: a[0])
        self.assertEqual(best[1:3], ('card', '1'))
        g.take_action(best, 0)
        self.assertEqual((g.finished, g.winner, g.mana[0]), (True, 0, 0))

    def test_slay_cannot_target_hero_or_consume_resources_on_illegal_target(self):
        g = empty(); h = unit('h', 0, 10060, (4, 2)); e = unit('e', 1, 10020, (4, 3))
        g.units = [h, e]; g.hand[0] = [10410]
        self.assertFalse(any(a[1] == 'card' for a in g.actions(0)))
        with self.assertRaises(AssertionError):
            g.take_action((1, 'card', '0', 'e'), 0)
        self.assertEqual((g.mana[0], g.hand[0], e.hp), (10, [10410], 10))

    def test_two_step_policy_can_sidestep_a_friendly_wall(self):
        g = empty(); h = unit('h', 0, 10020, (5, 2)); h.first_move = False
        g.units = [h] + [unit(str(c), 0, 1006, (4, c)) for c in (1, 2, 3)]
        actions = g.movement_actions(0)
        lateral = [a for a in actions if a[3] in ('5,1', '5,3')]
        self.assertTrue(lateral)
        self.assertEqual(g.position_score(h, (5, 1)), g.position_score(h, h.pos))
        g.take_action(lateral[0], 0)
        self.assertEqual(g.movement_actions(0), [])  # Planning does not grant a second move.

    def test_ai_clears_the_blocker_that_frees_a_building_attack(self):
        g = empty(); axe = unit('axe', 0, 10020, (1, 1)); lion = unit('lion', 0, 10060, (4, 4))
        blocker = unit('blocker', 1, 1006, (1, 2)); other = unit('z_other', 1, 1006, (3, 4))
        blocker.hp = other.hp = 2
        g.units = [axe, lion, blocker, other]; g.hand[0] = [10354]
        cards = [a for a in g.actions(0) if a[1] == 'card']
        best = max(cards, key=lambda a: a[0])
        self.assertEqual(best[3], 'blocker')
        g.take_action(best, 0); g.combat()
        self.assertEqual(g.forts[1].hp, 34)

    def test_late_siege_creep_keeps_printed_stats_and_reduces_attack_for_allies(self):
        g = empty(); shadow = unit('s', 0, 10085, (1, 2)); h = unit('h', 0, 10060, (4, 2))
        g.units = [shadow, h]
        self.assertEqual((g.attack(shadow), g.siege(shadow), shadow.max_hp), (13, 5, 5))
        g.units += [unit(str(i), 0, 1006, (7, i)) for i in range(6)]
        self.assertEqual(g.attack(shadow), 1)

    def test_new_pool_full_match_gold_conservation(self):
        rosters = sample_rosters()
        r = ExpandedMatch(rosters[0], rosters[1], 11, 4, True).run()
        for team, s in enumerate(r['stats']):
            self.assertEqual(s.get('bounty_income', 0)+s.get('payday_income', 0)-s.get('gold_spent', 0), r['gold'][team])
        self.assertTrue(r['timeline'])


if __name__ == '__main__':
    unittest.main()
