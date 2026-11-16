from collections import Counter
from itertools import combinations
import unittest

from simulate_heroes import Game, IDS, PANELS, Unit, roster_kind, sample_rosters


def hero(uid, team, card_id, pos):
    return Unit(uid, team, card_id, PANELS[card_id]["hit_points"], pos)


def empty_game(probes=False, targeting="arrows"):
    game = Game(IDS[:3], IDS[3:6], probes=probes, targeting=targeting)
    game.units = []
    game.round = 1
    return game


class HeroSimulationTests(unittest.TestCase):
    def test_combination_counts_and_sample_coverage(self):
        counts = Counter(roster_kind(r) for r in combinations(IDS, 3))
        self.assertEqual(counts, {"pure": 4, "dual": 108, "triple": 108})
        sample = sample_rosters()
        self.assertEqual(len(set(sample)), 20)
        self.assertEqual(Counter(roster_kind(r) for r in sample), {"pure": 4, "dual": 12, "triple": 4})
        self.assertEqual(Counter(h for r in sample for h in r), {h: 5 for h in IDS})

    def test_combat_is_simultaneous(self):
        game = empty_game()
        a = Unit("a", 0, None, 2, (4, 2), arrow=(-1, 0))
        b = Unit("b", 1, None, 2, (3, 2), arrow=(1, 0))
        game.units = [a, b]
        game.combat()
        self.assertEqual(game.field(), [])
        self.assertEqual(game.gold, [1, 1])
        for stats in game.stats:
            self.assertEqual(stats["creep_attack_opportunities"], 1)
            self.assertEqual(stats["creep_attacks"], 1)
            self.assertEqual(stats["hero_attack_opportunities"], 0)

    def test_cardinal_range_and_friend_does_not_block_ranged_attack(self):
        game = empty_game()
        cm = hero("cm", 0, 10064, (4, 2))
        friend = Unit("f", 0, None, 4, (3, 2))
        enemy = Unit("e", 1, None, 4, (2, 2))
        game.units = [cm, friend, enemy]
        self.assertIs(game.target(cm), enemy)
        cm.hero = 10020
        self.assertIsNone(game.target(cm))  # Melee does not inherit ranged reach.
        enemy.pos = (3, 3)
        self.assertIsNone(game.target(cm))  # Eight-neighbor movement is not diagonal attack.

    def test_first_two_step_move_cannot_jump_an_occupied_ring(self):
        game = empty_game()
        unit = hero("h", 0, 10020, (4, 2))
        game.units = [unit] + [Unit(f"c{i}", 0, None, 4, (4+dr, 2+dc)) for i, (dr, dc) in enumerate(((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)))]
        self.assertEqual(game.reachable(unit), [])

    def test_enemy_occupied_fountain_delays_hero_without_replacing_enemy(self):
        game = empty_game()
        unit = hero("h", 0, 10020, None)
        unit.hp, unit.due = 0, 3
        game.round = 3
        game.units = [unit] + [Unit(f"e{c}", 1, None, 4, (7,c)) for c in range(6)]
        game.spawn_hero(unit)
        self.assertIsNone(unit.pos)
        self.assertEqual(len(game.field(1)), 6)
        self.assertEqual(game.gold, [0,0])
        self.assertEqual(game.stats[0]["hero_spawn_wait"], 1)

    def test_sven_splash_hits_only_two_sides_and_rounds_down(self):
        game = empty_game()
        sven = hero("s", 0, 10054, (4, 2))
        enemies = [Unit(str(i), 1, None, 4, pos, stunned=True) for i, pos in enumerate(((3, 2), (3, 1), (3, 3), (2, 2)))]
        game.units = [sven] + enemies
        game.combat()
        self.assertIsNone(enemies[0].pos)
        self.assertEqual([u.hp for u in enemies[1:]], [2, 2, 4])

    def test_retaliation_occurs_on_lethal_attack_and_respects_armor(self):
        game = empty_game()
        legion = hero("l", 0, 10069, (4, 2))
        legion.hp, legion.stunned = 1, True
        creep = Unit("c", 1, None, 2, (3, 2), arrow=(1, 0))
        game.units = [legion, creep]
        game.combat()
        self.assertEqual(game.field(), [])
        self.assertEqual(game.gold, [1, 5])
        # Axe's two armor absorbs two ordinary retaliation damage.
        legion = hero("l2", 0, 10069, (4, 2))
        legion.stunned = True
        axe = hero("a2", 1, 10020, (3, 2))
        axe.arrow = (1, 0)
        game.units = [legion, axe]
        game.combat()
        self.assertEqual(axe.hp, 10)

    def test_spell_does_not_trigger_retaliation(self):
        game = empty_game(probes=True)
        cm = hero("cm", 0, 10064, (5, 2))
        legion = hero("l", 1, 10069, (3, 2))
        legion.hp = 1
        game.units = [cm, legion]
        game.mana = [1, 1]
        game.spells[0] = {"damage"}
        game.take_action((1, "damage", "spell", "l"), 0)
        self.assertEqual(cm.hp, cm.max_hp)
        self.assertIsNone(legion.pos)

    def test_eight_neighbor_aura_excludes_wolf_itself(self):
        game = empty_game()
        wolf = hero("w", 0, 10014, (4, 2))
        creep = Unit("c", 0, None, 4, (3, 3))
        game.units = [wolf, creep]
        self.assertEqual(game.attack(wolf), 4)
        self.assertEqual(game.attack(creep), 4)
        wolf.pos = (6, 2)
        self.assertEqual(game.attack(creep), 2)

    def test_regeneration_resolves_before_combat_death(self):
        game = empty_game()
        sven = hero("s", 0, 10054, (4, 2))
        creep = Unit("c", 1, None, 4, (3, 2), stunned=True)
        deer = hero("d", 1, 10036, (2, 1))
        deer.stunned = True
        game.units = [sven, creep, deer]
        game.combat()
        self.assertEqual(creep.hp, 1)  # 4 - 5 + 2; deliberate Classic-style test assumption.
        self.assertIsNotNone(creep.pos)

    def test_diagonal_stun_reaches_second_square_through_empty_first(self):
        game = empty_game()
        ox = hero("o", 0, 10033, (4, 2))
        enemy = hero("e", 1, 10060, (2, 4))
        game.units = [ox, enemy]
        self.assertIn("stun", {a[1] for a in game.actions(0)})
        game.take_action((1, "stun", "o", "-1,1"), 0)
        self.assertTrue(enemy.stunned)
        self.assertEqual(game.actions(1), [])

    def test_conversion_preserves_state_and_does_not_award_bounty(self):
        game = empty_game()
        chen = hero("h", 0, 10017, (4, 2))
        creep = Unit("c", 1, None, 2, (2, 3), arrow=(0, 1))
        game.units = [chen, creep]
        game.take_action((1, "chen", "h", "c"), 0)
        self.assertEqual((creep.team, creep.hp, creep.pos, creep.arrow), (0, 2, (2, 3), (0, 1)))
        self.assertEqual(game.gold, [0, 0])

    def test_mana_refund_is_capped_and_once_per_round(self):
        game = empty_game(probes=True)
        cm = hero("cm", 0, 10064, (4, 2))
        cm.hp = 3
        creep = Unit("c", 1, None, 4, (3, 2))
        game.units = [cm, creep]
        game.mana = [1, 1]
        game.spells[0] = {"damage", "heal"}
        game.take_action((1, "damage", "spell", "c"), 0)
        self.assertEqual(game.mana[0], 1)
        game.take_action((1, "heal", "spell", "cm"), 0)
        self.assertEqual(game.mana[0], 0)
        self.assertEqual(game.stats[0]["mana_refunded"], 1)

    def test_cooldown_ticks_during_death_and_does_not_reset_on_return(self):
        game = empty_game()
        lion = hero("l", 0, 10060, (4, 2))
        creep = Unit("c", 1, None, 4, (3, 2))
        game.units = [lion, creep]
        game.take_action((1, "lion", "l", "c"), 0)
        self.assertEqual((lion.cd, lion.next_cd), (4, 3))
        lion.hp = 0
        game.cleanup()
        self.assertEqual(lion.due, 3)
        for turn in (2, 3):
            game.round = turn
            game.start_round()
        self.assertEqual(lion.cd, 2)
        self.assertEqual(lion.hp, lion.max_hp)
        self.assertIsNotNone(lion.pos)

    def test_auto_move_follows_and_resolves_cross_team_conflict(self):
        game = empty_game()
        game.round = 2
        game.units = [Unit(str(i), 0, None, 4, (r, 2), first_move=False) for i, r in enumerate((4, 5, 6))]
        game.auto_move()
        self.assertEqual([u.pos for u in game.units], [(3, 2), (4, 2), (5, 2)])
        game.units = [Unit("a", 0, None, 4, (4, 2), first_move=False), Unit("b", 1, None, 4, (2, 2), first_move=False)]
        game.auto_move()
        self.assertEqual(sum(u.pos == (3, 2) for u in game.units), 1)
        self.assertEqual(len({u.pos for u in game.units}), 2)

    def test_seed_replays_exactly_and_all_actions_are_bounded(self):
        rosters = sample_rosters()
        first = Game(rosters[1], rosters[3], seed=12, probes=True, trace=True).run(8)
        second = Game(rosters[1], rosters[3], seed=12, probes=True, trace=True).run(8)
        self.assertEqual(first, second)
        self.assertTrue(any("冰女触发" in event for frame in first["frames"] for event in frame["events"]))
        for stats in first["stats"]:
            self.assertEqual(stats.get("arrow_misses", 0), 0)
            self.assertEqual(stats.get("attacks", 0)+stats.get("arrow_misses", 0)+stats.get("out_of_range", 0), stats["attack_opportunities"])
            for metric in ("attack_opportunities", "attacks", "arrow_misses", "out_of_range"):
                self.assertEqual(stats.get(f"hero_{metric}", 0)+stats.get(f"creep_{metric}", 0), stats.get(metric, 0))
            for group in ("hero", "creep"):
                self.assertEqual(sum(stats.get(f"{group}_{m}", 0) for m in ("attacks", "arrow_misses", "out_of_range")), stats.get(f"{group}_attack_opportunities", 0))

    def test_aggro_keeps_legal_target_across_rounds_then_retargets_on_death(self):
        game = empty_game(targeting="aggro")
        cm = hero("cm", 0, 10064, (4, 2))
        far = Unit("z", 1, None, 4, (2, 2))
        game.units = [cm, far]
        game.refresh_targets()
        self.assertEqual(cm.target_uid, "z")
        near = Unit("a", 1, None, 4, (4, 3))
        game.units.append(near)
        game.round = 2
        game.start_round()
        game.reveal()
        self.assertEqual(cm.target_uid, "z")  # New, closer enemy does not steal a legal lock.
        far.hp = 0
        game.cleanup()
        game.refresh_targets()
        self.assertEqual(cm.target_uid, "a")

    def test_aggro_nearest_and_tie_break_are_independent_of_iteration_order(self):
        game = empty_game(targeting="aggro")
        cm = hero("cm", 0, 10064, (4, 2))
        far = Unit("0", 1, None, 4, (2, 2))
        left = Unit("a", 1, None, 4, (4, 1))
        right = Unit("z", 1, None, 4, (4, 3))
        game.units = [cm, far, right, left]
        self.assertIs(game.target(cm), left)
        game.units.reverse()
        self.assertIs(game.target(cm), left)

    def test_aggro_hypothetical_move_does_not_mutate_actual_lock(self):
        game = empty_game(targeting="aggro")
        cm = hero("cm", 0, 10064, (4, 2))
        far = Unit("z", 1, None, 4, (2, 2))
        near = Unit("a", 1, None, 4, (4, 3))
        cm.target_uid = far.uid
        game.units = [cm, far, near]
        before = [(u.pos, u.target_uid) for u in game.units]
        self.assertIs(game.target(cm, pos=(4, 1)), near)
        game.actions(0)
        self.assertEqual([(u.pos, u.target_uid) for u in game.units], before)
        game.take_action((1, "move", "cm", "4,1"), 0)
        self.assertEqual(cm.target_uid, near.uid)

    def test_aggro_clears_out_of_range_target_without_moving_or_using_diagonal(self):
        game = empty_game(targeting="aggro")
        axe = hero("axe", 0, 10020, (4, 2))
        foe = Unit("foe", 1, None, 4, (3, 2))
        game.units = [axe, foe]
        game.refresh_targets()
        self.assertEqual(axe.target_uid, "foe")
        foe.pos = (3, 3)
        game.refresh_targets()
        self.assertIsNone(axe.target_uid)
        self.assertEqual(axe.pos, (4, 2))

    def test_aggro_conversion_invalidates_all_now_friendly_targets(self):
        game = empty_game(targeting="aggro")
        chen = hero("chen", 0, 10017, (4, 2))
        friend = Unit("friend", 0, None, 4, (3, 2))
        foe = Unit("foe", 1, None, 4, (2, 2))
        game.units = [chen, friend, foe]
        game.refresh_targets()
        self.assertEqual(friend.target_uid, "foe")
        self.assertEqual(foe.target_uid, "friend")
        game.take_action((1, "chen", "chen", "foe"), 0)
        self.assertTrue(all(u.target_uid is None for u in game.units))

    def test_aggro_sven_splash_and_replay_follow_actual_target_direction(self):
        game = empty_game(targeting="aggro")
        game.trace = True
        sven = hero("s", 0, 10054, (4, 2))
        main = Unit("main", 1, None, 4, (4, 3), stunned=True)
        above = Unit("above", 1, None, 4, (3, 3), stunned=True)
        below = Unit("below", 1, None, 4, (5, 3), stunned=True)
        game.units = [sven, main, above, below]
        game.refresh_targets()
        game.frame("test")
        preview = next(u for u in game.frames[0]["units"] if u['id'] == "s")
        self.assertEqual((preview['arrow'], preview['target']), ("→", "main"))
        game.combat()
        self.assertIsNone(main.pos)
        self.assertEqual((above.hp, below.hp), (2, 2))

    def test_aggro_keeps_simultaneous_attacks_when_both_are_lethal(self):
        game = empty_game(targeting="aggro")
        game.units = [Unit("a", 0, None, 2, (4, 2)), Unit("b", 1, None, 2, (3, 2))]
        game.combat()
        self.assertEqual(game.field(), [])
        self.assertEqual(game.gold, [1, 1])


if __name__ == "__main__":
    unittest.main()
