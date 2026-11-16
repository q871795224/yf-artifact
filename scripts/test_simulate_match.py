import unittest
from collections import Counter

from simulate_match import Match, BattleUnit, CARDS, POOL, GEAR, sample_rosters, match_pairs


def unit(uid, team, card, pos):
    return BattleUnit(uid,team,card if CARDS[card]['card_type']=='Hero'else None,CARDS[card]['hit_points'],pos,card_id=card)


def empty(power=5, protect=False):
    r=sample_rosters();g=Match(r[0],r[1],tower_attack=power,protection=protect)
    g.units=[];g.hand=[[],[]];g.deck=[[],[]];g.item_hand=[[],[]];g.item_deck=[[],[]]
    g.round=1;g.mana=[10,10]
    return g


class MatchTests(unittest.TestCase):
    def test_pool_counts_tiers_and_no_signature_cards(self):
        self.assertEqual(Counter((c['category'],c['tier'])for c in POOL['items']),{(a,b):2 for a in ('consumable','equipment')for b in ('basic','medium','advanced')})
        self.assertEqual(Counter(c['colors'][0]for c in POOL['ordinary_cards']),{c:3 for c in ('red','blue','green','black')})
        signatures={r['card_id']for c in CARDS.values()if c['card_type']=='Hero'for r in c['references']if r['ref_type']=='includes'}
        self.assertFalse(signatures.intersection(c['card_id']for c in POOL['ordinary_cards']))
        self.assertEqual(len(match_pairs()[1]),36)

    def test_building_range_and_units_take_priority(self):
        g=empty();h=unit('h',0,10020,(1,2));g.units=[h]
        self.assertIs(g.building_target(h),g.forts[1])
        h.pos=(2,2);self.assertIsNone(g.building_target(h))
        h=unit('ranged',0,10064,(2,2));g.units=[h]
        self.assertIs(g.building_target(h),g.forts[1])
        h=unit('h',0,10020,(1,2));enemy=unit('c',1,1006,(1,3));g.units=[h,enemy]
        g.combat()
        self.assertEqual(g.forts[1].hp,40)

    def test_tower_one_shot_single_target_and_off_scenario(self):
        for power in (0,4,5,6):
            g=empty(power);a=unit('a',0,1006,(1,2));b=unit('b',0,1006,(2,2));g.units=[a,b]
            g.combat()
            self.assertEqual(a.pos is None,power>0)
            self.assertEqual(b.hp,4)
            self.assertEqual(g.stats[1]['fort_shots'],int(power>0))

    def test_base_same_position_double_attack_and_next_round_immunity(self):
        g=empty();g.round=3
        row=g.forts[1].row;g.damage_fort(1,55)
        f=g.forts[1]
        self.assertEqual((f.stage,f.hp,f.row,f.active_from),('base',80,row,4))
        self.assertEqual(g.fort_power(f),10)
        self.assertEqual(g.stats[0]['building_damage'],40)
        g.damage_fort(1,100);self.assertEqual(f.hp,80)
        g.round=4;g.damage_fort(1,80);g.check_victory()
        self.assertTrue(g.finished);self.assertEqual(g.winner,0)

    def test_simultaneous_base_destruction_is_draw(self):
        g=empty(0)
        for f in g.forts:f.stage,f.hp='base',1
        g.units=[unit('a',0,1006,(1,2)),unit('b',1,1006,(6,2))]
        g.combat()
        self.assertTrue(g.finished);self.assertIsNone(g.winner)
        self.assertEqual(g.end_reason,'simultaneous')

    def test_fountain_is_separate_and_hits_all_invaders(self):
        g=empty(0);a=unit('a',0,1006,(0,2));b=unit('b',0,1006,(0,3));g.units=[a,b]
        g.combat()
        self.assertFalse(g.field());self.assertEqual(g.stats[1]['fountain_hits'],2)
        self.assertEqual(g.forts[1].hp,36)  # Both attack before simultaneous fountain deaths.

    def test_creep_protection_switch_and_diagonal_no_op(self):
        for diagonal in (False,True):
            g=empty(protect=True)
            creep=unit('c',0,1006,(4,2));old=unit('old',1,1006,(3,2))
            attacker=unit('attacker',1,10020,(3,3)if diagonal else(4,3))
            victim=unit('victim',0,10069,(3,4)if diagonal else(4,4))
            creep.target_uid='old';attacker.target_uid='victim';g.units=[creep,old,attacker,victim]
            self.assertIs(g.target(creep),old if diagonal else attacker)
            g.protection=False;self.assertIs(g.target(creep),old)
            self.assertEqual(creep.pos,(4,2))

    def test_tower_protection_overrides_legal_creep_lock(self):
        g=empty(protect=True)
        c=unit('c',0,1006,(1,0));attacker=unit('h',0,10069,(2,3));victim=unit('v',1,10020,(2,2))
        attacker.target_uid='v';g.units=[c,attacker,victim];g.forts[1].target_uid='c'
        self.assertIs(g.fort_target(g.forts[1]),attacker)
        g.protection=False;self.assertIs(g.fort_target(g.forts[1]),c)
        g.protection=True;attacker.stunned=True
        self.assertIs(g.fort_target(g.forts[1]),c)

    def test_hypothetical_protection_uses_proposed_hero_position_without_mutating(self):
        g=empty(protect=True)
        c=unit('c',0,1006,(1,0));h=unit('h',0,10069,(3,3));v=unit('v',1,10020,(2,2))
        g.units=[c,h,v];g.forts[1].target_uid='c'
        self.assertIs(g.fort_target(g.forts[1],override=(h,(2,3))),h)
        self.assertEqual(h.pos,(3,3));self.assertEqual(g.forts[1].target_uid,'c')

    def test_equipment_cost_and_persistence_after_death(self):
        g=empty();h=unit('h',0,10020,(4,2));g.units=[h];g.item_hand[0]=[(3002,False)];g.gold[0]=3
        g.take_action((1,'item','0','h'),0)
        self.assertEqual((g.attack(h),g.gold[0],g.stats[0]['gold_spent']),(8,0,3))
        h.hp=0;g.cleanup();g.round=3;g.start_round()
        self.assertIsNotNone(h.pos);self.assertEqual(g.attack(h),8)

    def test_ai_defense_and_retreat_account_for_building_damage(self):
        g=empty(5);h=unit('h',0,10020,(1,2));g.units=[h];g.hand[0]=[10297]
        self.assertEqual(g.incoming_damage(h),3)
        self.assertTrue(any(a[1]=='card'and a[3]=='h'for a in g.actions(0)))
        h.hp=2;g.item_hand[0]=[(3006,False)];g.gold[0]=3
        self.assertTrue(any(a[1]=='item'and a[3]=='h'for a in g.actions(0)))

    def test_all_consumable_effects_and_ticket_does_not_charge_twice(self):
        for card,expected in ((3003,8),(3004,10)):
            g=empty();h=unit('h',0,10020,(4,2));h.hp=2;g.units=[h]
            g.item_hand[0]=[(card,False)];g.gold[0]=CARDS[card]['gold_cost']
            g.take_action((1,'item','0','h'),0);self.assertEqual(h.hp,expected)
        g=empty();h=unit('h',0,10020,(4,2));g.units=[h]
        g.item_hand[0]=[(3005,False)];g.gold[0]=5;g.deck[0]=[10313]
        g.take_action((1,'item','0','draw'),0);self.assertEqual(g.hand[0],[10313])
        g.item_hand[0]=[(10211,False)];g.gold[0]=10;g.improvements[1]=[10169]
        g.take_action((1,'item','0','improvement'),0);self.assertEqual(g.improvements[1],[])
        g.item_hand[0]=[(10216,False)];g.gold[0]=9
        before=g.stats[0]['gold_spent'];g.take_action((1,'item','0','ticket'),0)
        self.assertIn(g.item_hand[0][0][0],GEAR);self.assertTrue(g.item_hand[0][0][1])
        g.take_action((1,'item','0','h'),0)
        self.assertEqual(g.stats[0]['gold_spent']-before,9);self.assertEqual(g.gold[0],0)
        h.first_move=False;h.cd=3;g.item_hand[0]=[(3006,False)];g.gold[0]=3
        g.take_action((1,'item','0','h'),0)
        self.assertEqual(h.pos[0],7);self.assertFalse(h.first_move);self.assertEqual(h.cd,3)

    def test_draw_and_items_follow_separate_schedules(self):
        r=sample_rosters();g=Match(r[0],r[1])
        self.assertEqual((len(g.hand[0]),len(g.deck[0]),len(g.item_hand[0])),(5,13,1))
        g.round=1;g.start_round();self.assertEqual(len(g.hand[0]),5)
        g.round=2;g.start_round();self.assertEqual((len(g.hand[0]),len(g.item_hand[0])),(7,1))
        g.round=3;g.start_round();self.assertEqual((len(g.hand[0]),len(g.item_hand[0])),(9,2))

    def test_card_mana_color_and_cm_only_trigger_on_first_spell(self):
        g=empty();axe=unit('a',0,10020,(4,2));cm=unit('cm',0,10064,(5,2));g.units=[axe,cm]
        g.hand[0]=[10313,10313];g.mana[0]=1
        g.take_action((1,'card','0','a'),0);self.assertEqual(g.mana[0],1)
        g.take_action((1,'card','0','a'),0);self.assertEqual(g.mana[0],0)
        self.assertEqual(axe.temporary_attack,8);self.assertEqual(g.stats[0]['mana_refunded'],1)
        g.hand[0]=[10313]
        with self.assertRaises(AssertionError):g.take_action((1,'card','0','a'),0)
        self.assertEqual(g.hand[0],[10313])

    def test_summons_respect_cap_and_independent_bounty(self):
        g=empty();h=unit('h',0,10065,(4,2))
        places=[(r,c)for r in range(8)for c in range(6)if(r,c)!=(4,2)]
        g.units=[h]+[unit(f'c{i}',0,1006,p)for i,p in enumerate(places[:22])]
        g.summon(0,1006,3)
        self.assertEqual(len(g.field(0)),24);self.assertEqual(g.stats[0]['summons'],1)
        self.assertEqual(g.stats[0]['summons_blocked'],2)
        g.units[-1].hp=0;g.cleanup();self.assertEqual(g.gold[1],1)

    def test_growth_and_temporary_modifiers_have_separate_lifetimes(self):
        g=empty(0);s=unit('s',0,10111,(4,2));g.units=[s];g.improvements[0]=[10169]
        s.temporary_attack=4;g.combat();self.assertEqual(s.permanent_attack,2)
        g.round=2;g.start_round()
        self.assertEqual(s.temporary_attack,0);self.assertEqual(s.permanent_attack,3)

    def test_complete_match_reproducibility_and_gold_conservation(self):
        r=sample_rosters()
        a=Match(r[0],r[2],11,5,True,trace=True).run()
        b=Match(r[0],r[2],11,5,True,trace=True).run()
        self.assertEqual(a,b);self.assertIn(a['outcome'],('A','B','simultaneous','timeout'))
        for team,s in enumerate(a['stats']):
            self.assertEqual(s.get('bounty_income',0)+s.get('payday_income',0)-s.get('gold_spent',0),a['gold'][team])
        self.assertTrue(any(f['structures'][0]['stage']=='base'for f in a['frames']))


if __name__=='__main__':unittest.main()
