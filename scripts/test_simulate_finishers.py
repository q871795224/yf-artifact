import unittest

from simulate_finishers import FinisherMatch, FinisherUnit, GOLD_REPLACEMENTS, MANA_REPLACEMENTS
from simulate_expanded_match import ExpandedMatch
from simulate_match import CARDS, sample_rosters


def unit(uid, team, cid, pos):
    return FinisherUnit(uid, team, cid if CARDS[cid]['card_type'] == 'Hero' else None,
                        CARDS[cid]['hit_points'], pos, card_id=cid)


def empty():
    rosters = sample_rosters()
    g = FinisherMatch(rosters[0], rosters[1], tower_attack=0, protection=True)
    g.units = []; g.hand = [[], []]; g.deck = [[], []]
    g.item_hand = [[], []]; g.item_deck = [[], []]; g.round = 10; g.mana = [10, 10]
    return g


class FinisherTests(unittest.TestCase):
    def test_off_switch_preserves_original_game(self):
        rosters = sample_rosters()
        old = ExpandedMatch(rosters[0], rosters[1], 11, 4, True, policy='greedy').run()
        new = FinisherMatch(rosters[0], rosters[1], 11, 4, True, gold_finishers=False).run()
        for key in old:
            self.assertEqual(old[key], new[key], key)

    def test_switches_preserve_deck_lengths_and_card_positions(self):
        rosters = sample_rosters()
        a = FinisherMatch(rosters[0], rosters[1], 11, gold_finishers=False)
        b = FinisherMatch(rosters[0], rosters[1], 11, mana_finishers=False)
        for team in (0, 1):
            self.assertEqual(b.hand[team], [MANA_REPLACEMENTS.get(i, i) for i in a.hand[team]])
            self.assertEqual(b.deck[team], [MANA_REPLACEMENTS.get(i, i) for i in a.deck[team]])
            self.assertEqual(b.item_hand[team], [(GOLD_REPLACEMENTS.get(i, i), paid) for i, paid in a.item_hand[team]])
            self.assertEqual(b.item_deck[team], [GOLD_REPLACEMENTS.get(i, i) for i in a.item_deck[team]])
            self.assertEqual(len(b.hand[team])+len(b.deck[team]), 36)
            self.assertEqual(len(b.item_hand[team])+len(b.item_deck[team]), 18)

    def test_paid_terminal_requires_25_gold(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); g.units = [h]
        g.item_hand[0] = [(10263, False)]; g.gold[0] = 24
        self.assertFalse(any(a[1] == 'item' for a in g.actions(0)))
        g.gold[0] = 25; g.take_action((1, 'item', '0', 'h'), 0)
        self.assertEqual((g.gold[0], g.attack(h), h.armor, h.max_hp, g.siege(h)), (0, 14, 2, 10, 4))
        self.assertEqual(g.stats[0]['finisher_equipped_paid'], 1)

    def test_blade_condemn_kills_high_health_unit_without_changing_printed_damage(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); h.equipment['Weapon'] = 10263
        e = unit('e', 1, 10108, (4, 3)); g.units = [h, e]
        self.assertEqual(g.primary_damage(h, e), 14)
        g.combat()
        self.assertIsNone(e.pos)  # 25 HP is not enough to survive battle-damage condemnation.
        self.assertEqual(g.stats[0]['blade_condemns'], 1)

    def test_zero_damage_does_not_condemn(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); h.equipment['Weapon'] = 10263
        e = unit('e', 1, 10108, (4, 3)); e.permanent_armor = 20; g.units = [h, e]
        g.combat(); self.assertEqual(e.hp, 25)
        self.assertEqual(g.stats[0]['blade_condemns'], 0)

    def test_blade_condemn_applies_to_svens_battle_splash_not_all_neighbors(self):
        g = empty(); h = unit('h', 0, 10054, (4, 2)); h.equipment['Weapon'] = 10263
        main = unit('main', 1, 10108, (4, 3)); side = unit('side', 1, 10108, (3, 3))
        far = unit('far', 1, 10108, (3, 4)); g.units = [h, main, side, far]
        g.combat()
        self.assertIsNone(main.pos); self.assertIsNone(side.pos); self.assertIsNotNone(far.pos)

    def test_regeneration_does_not_cancel_condemn(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); h.equipment['Weapon'] = 10263
        e = unit('e', 1, 10108, (4, 3)); heal = unit('heal', 1, 10036, (3, 3))
        g.units = [h, e, heal]; g.combat(); self.assertIsNone(e.pos)

    def test_blade_active_removes_improvements_and_current_targets_equipment(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); h.equipment['Weapon'] = 10263
        e = unit('e', 1, 10069, (4, 3)); e.equipment = {'Accessory': 10236, 'Armor': 3001}
        e.hp = e.max_hp; g.units = [h, e]; g.improvements[1] = [10169, 10169]
        g.take_action((1, 'blade', 'h', 'e'), 0)
        self.assertEqual((g.improvements[1], e.equipment, e.hp, h.blade_cd), ([], {}, 8, 1))
        self.assertEqual(g.mana[0], 10)
        self.assertFalse(any(a[1] == 'blade' for a in g.actions(0)))

    def test_horn_free_active_uses_cd_and_summons_printed_pack(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); g.units = [h]
        g.item_hand[0] = [(10260, False)]; g.gold[0] = 25
        g.take_action((1, 'item', '0', 'h'), 0)
        self.assertEqual(h.max_hp, 14)
        action = next(a for a in g.actions(0) if a[1] == 'horn')
        g.take_action(action, 0)
        pack = next(u for u in g.field(0) if u.card_id == 10102)
        self.assertEqual((g.attack(pack), pack.hp, pack.armor, g.siege(pack)), (14, 14, 0, 6))
        self.assertEqual((g.gold[0], g.mana[0], h.horn_cd), (0, 10, 2))
        self.assertFalse(any(a[1] == 'horn' for a in g.actions(0)))
        h.hp = 0; g.cleanup(); g.round = 11; g.start_round()
        self.assertEqual(h.horn_cd, 1)
        g.round = 12; g.start_round()
        self.assertEqual((h.horn_cd, h.max_hp), (0, 14))
        self.assertTrue(any(a[1] == 'horn' for a in g.actions(0)))

    def test_stun_disables_actives_but_does_not_remove_passives(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2))
        h.equipment = {'Weapon': 10263, 'Accessory': 10260}; h.stunned = True
        g.units = [h]; g.improvements[1] = [10169]
        self.assertFalse(any(a[1] in ('blade', 'horn') for a in g.actions(0)))
        self.assertEqual((g.attack(h), g.siege(h), h.max_hp), (14, 4, 14))

    def test_free_ticket_equipment_is_separate_from_25_gold_purchase(self):
        g = empty(); h = unit('h', 0, 10020, (4, 2)); g.units = [h]
        g.item_hand[0] = [(10263, True)]
        g.take_action((1, 'item', '0', 'h'), 0)
        self.assertEqual((g.gold[0], g.stats[0]['finisher_equipped_paid'], g.stats[0]['finisher_equipped_free']), (0, 0, 1))


if __name__ == '__main__':
    unittest.main()
