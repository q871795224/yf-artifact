import unittest

from analyze_item_economy import EconomyMatch
from simulate_expanded_match import ExpandedUnit
from simulate_match import CARDS, sample_rosters


def hero(uid, team, cid, pos):
    return ExpandedUnit(uid, team, cid, CARDS[cid]['hit_points'], pos, card_id=cid)


def empty():
    rosters = sample_rosters()
    g = EconomyMatch(rosters[0], rosters[1], pool='expanded', policy='greedy', tower_attack=0)
    g.units = []; g.hand = [[], []]; g.deck = [[], []]
    g.item_hand = [[], []]; g.item_deck = [[], []]
    g.received_items = [[], []]; g.round = 6
    return g


class EconomyTests(unittest.TestCase):
    def test_empty_hand_and_unavoidable_gold_from_limited_supply(self):
        g = empty(); g.gold[0] = 20; g.stats[0]['bounty_income'] = 20
        s = g.economy_snapshot(0)
        self.assertEqual(s['reason'], 'empty_item_hand')
        self.assertEqual(s['minimum_gold_if_all_drawn_items_bought'], 20)

    def test_affordable_equipment_needs_a_hero_and_positive_ai_upgrade(self):
        g = empty(); g.gold[0] = 15
        self.assertEqual(g.item_reason(0, 3002, False), 'no_hero_in_field')
        h = hero('h', 0, 10020, (4, 2)); g.units = [h]
        self.assertEqual(g.item_reason(0, 3002, False), 'usable_by_ai')
        h.equipment['Weapon'] = 10238
        self.assertEqual(g.item_reason(0, 3002, False), 'no_upgrade_by_ai')

    def test_price_and_free_generated_item_are_distinct(self):
        g = empty(); g.units = [hero('h', 0, 10020, (4, 2))]
        self.assertEqual(g.item_reason(0, 10238, False), 'unaffordable')
        self.assertEqual(g.item_reason(0, 10238, True), 'usable_by_ai')

    def test_full_purchase_ceiling_counts_natural_draws_not_ticket_gifts(self):
        g = empty(); g.gold[0] = 21; g.stats[0]['bounty_income'] = 30
        g.stats[0]['gold_spent'] = 9; g.received_items[0] = [10216]
        g.item_hand[0] = [(10238, True)]
        s = g.economy_snapshot(0)
        self.assertEqual((s['drawn_item_value'], s['minimum_gold_if_all_drawn_items_bought']), (9, 21))

    def test_consumable_reasons_are_ai_preferences_not_illegal_actions(self):
        g = empty(); g.gold[0] = 15
        h = hero('h', 0, 10020, (4, 2)); g.units = [h]
        self.assertEqual(g.item_reason(0, 3003, False), 'no_wounded_friend')
        self.assertEqual(g.item_reason(0, 3005, False), 'ordinary_deck_empty')
        self.assertEqual(g.item_reason(0, 10211, False), 'no_enemy_improvement')
        self.assertEqual(g.item_reason(0, 3006, False), 'no_lethal_retreat_by_ai')
        h.hp = 3
        self.assertEqual(g.item_reason(0, 3003, False), 'usable_by_ai')

    def test_draw_observation_does_not_change_game(self):
        rosters = sample_rosters(); g = EconomyMatch(rosters[0], rosters[1])
        self.assertEqual([len(x) for x in g.received_items], [1, 1])
        g.round = 3; g.start_round()
        self.assertEqual([len(x) for x in g.received_items], [2, 2])


if __name__ == '__main__':
    unittest.main()
