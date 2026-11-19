"""Behavior checks for the approved growth Demo, independent of AI scores."""
from copy import deepcopy
import unittest

from growth_cards import CATALOG, ITEMS, PANELS, RANGED_CREEP, SIGNATURES, default_deck, validate_deck, full_deck
from growth_match import GrowthMatch, GrowthUnit
from growth_playable import GrowthSession
from browser_bridge import BrowserBridge


def unit(uid,team,cid,pos,level=1):
    hero=cid if cid in PANELS else None
    u=GrowthUnit(uid,team,hero,1,pos,card_id=cid,level=level,pending_level=level,first_move=False)
    u.hp=u.max_hp
    return u


def empty():
    g=GrowthMatch(trace=False)
    g.units=[]
    g.hand,g.deck=[[],[]],[[],[]]
    g.item_hand,g.item_deck=[[],[]],[[],[]]
    g.round=5
    g.mana=[10,10]
    g.tower_attack=0
    return g


def do(g,kind,actor,target,team=0):
    choices=[a for a in g.legal_actions(team) if a[1:]==(kind,str(actor),str(target))]
    if not choices:
        raise AssertionError(f'Not legal: {kind,actor,target}')
    g.take_action(choices[0],team)


class GrowthTests(unittest.TestCase):
    def test_opening_and_supply_are_one_hero_one_creep_then_one_each(self):
        g=GrowthMatch(13,trace=False)
        self.assertEqual([len(g.field(t)) for t in (0,1)],[2,2])
        self.assertEqual([len(h) for h in g.hand],[5,5])
        self.assertEqual([len(d) for d in g.deck],[25,25])
        self.assertEqual([len(d) for d in g.item_deck],[9,9])
        for r in (1,2,3):
            g.round=r;g.start_round()
            self.assertEqual(len([u for u in g.field(0) if u.hero]),r)
            self.assertEqual(len([u for u in g.field(0) if not u.hero]),r)
            self.assertEqual(g.mana,[r]*2)
        self.assertEqual([len(h) for h in g.hand],[7,7])
        self.assertEqual([len(h) for h in g.item_hand],[2,2])
        g.round=11;g.start_round()
        self.assertEqual(g.mana,[10,10])

    def test_both_sides_share_the_three_wave_cycle(self):
        g=GrowthMatch()
        for r,cid in enumerate((1006,1006,RANGED_CREEP)*2,1):
            g.round=r
            g.start_round()
            for team in (0,1):
                creep=[u for u in g.field(team) if not u.hero][-1]
                self.assertEqual(creep.card_id,cid)
            g.units=[u for u in g.units if u.hero]

    def test_ranged_creep_stops_and_shoots_through_friendly_frontline(self):
        g=empty()
        archer=unit('archer',0,RANGED_CREEP,(5,1))
        front=unit('front',0,1006,(4,1))
        enemy=unit('enemy',1,1006,(3,1))
        g.units=[archer,front,enemy]
        g.auto_move()
        self.assertEqual(archer.pos,(5,1))
        self.assertIs(g.target(archer),enemy)
        g.combat()
        self.assertEqual(enemy.hp,1)

    def test_auto_reinforcements_use_multiple_legal_columns_deterministically(self):
        def columns(seed):
            g=GrowthMatch(seed)
            picks=[]
            for r in range(2,10):
                g.units=[]
                g.round=r
                g.start_round()
                self.assertEqual(len(g.field()),2)
                picks.append(tuple(u.pos[1] for u in g.field()))
            return picks
        picks=columns(13)
        self.assertEqual(picks,columns(13))
        for team in (0,1):
            self.assertGreater(len({p[team] for p in picks}),1)
        g=GrowthMatch(13)
        self.assertIn((7,2),g.fountain_positions(0))
        self.assertIn((0,2),g.fountain_positions(1))

    def test_global_swap_allows_two_heroes_and_updates_targets(self):
        g=empty()
        a=unit('a',0,10014,(4,1))
        b=unit('b',0,10017,(3,2))
        foe=unit('foe',1,1006,(2,2))
        g.units=[a,b,foe]
        g.refresh_targets()
        self.assertIs(g.target(foe),b)
        do(g,'rally_swap','a','b')
        self.assertEqual((a.pos,b.pos,g.mana[0]),((3,2),(4,1),8))
        self.assertTrue(a.moved and b.moved)
        self.assertIs(g.target(foe),a)
        self.assertFalse(any(x[1]=='rally_swap' for x in g.legal_actions(0)))
        g.round+=1
        g.start_round()
        self.assertTrue(any(x[1]=='rally_swap' for x in g.legal_actions(0)))

    def test_global_swap_to_empty_space_can_move_a_creep_but_not_into_tower_or_enemy(self):
        g=empty()
        creep=unit('creep',0,1006,(5,2))
        enemy=unit('enemy',1,1006,(4,1))
        g.units=[creep,enemy]
        choices=[x[3] for x in g.legal_actions(0) if x[1:3]==('rally_swap','creep')]
        self.assertNotIn('6,2',choices)
        self.assertNotIn('4,1',choices)
        self.assertNotIn('3,2',choices)
        do(g,'rally_swap','creep','4,2')
        self.assertEqual((creep.pos,g.mana[0],creep.moved),((4,2),8,True))
        self.assertIs(g.target(creep),enemy)
        self.assertFalse(any(x[1]=='rally_swap' for x in g.legal_actions(0)))

    def test_direct_attack_orders_the_eight_neighbors_without_overwriting_taunt(self):
        g=empty()
        victim=unit('victim',0,10014,(4,2))
        distant=unit('distant',0,1006,(6,4))
        close=unit('close',1,10020,(3,2))
        diagonal=unit('diagonal',1,1006,(3,1))
        forced=unit('forced',1,1006,(4,3))
        outside=unit('outside',1,1006,(2,2))
        g.units=[victim,distant,close,diagonal,forced,outside]
        forced.forced_uid=distant.uid
        self.assertFalse(any(x[1]=='direct_attack' and x[3]=='distant' for x in g.legal_actions(1)))
        do(g,'direct_attack','','victim',1)
        self.assertEqual(g.mana[1],8)
        self.assertTrue(close.ordered and diagonal.ordered)
        self.assertFalse(forced.ordered or outside.ordered)
        self.assertIs(g.aggro_target(forced),distant)
        self.assertIs(g.aggro_target(diagonal),victim)
        self.assertIsNone(g.target(diagonal))
        g.chase()
        self.assertIs(g.target(diagonal),victim)
        self.assertFalse(any(x[1]=='direct_attack' for x in g.legal_actions(1)))

    def test_combat_frame_reports_damage_from_tower_and_full_block(self):
        session=GrowthSession(13)
        g=session.game=empty()
        g.tower_attack=4
        self.assertEqual([f.position for f in g.forts],[(6,2),(1,2)])
        enemy=unit('enemy',1,10020,(5,1))
        decoy=unit('z',1,1006,(6,1))
        ally=unit('ally',0,10014,(2,2))
        too_far=unit('far',0,1006,(3,2))
        enemy.permanent_armor=4
        g.units=[enemy,decoy,ally,too_far]
        g.refresh_targets()
        frames=[]
        session._combat(frames)
        self.assertEqual(frames[0]['fortShots'],[
            {'team':0,'target':'enemy','damage':0,'immune':False},
            {'team':1,'target':'ally','damage':4,'immune':False},
        ])
        g.units=[too_far]
        self.assertIsNone(g.fort_target(g.forts[1]))

    def test_experience_is_earned_alive_and_applied_next_start(self):
        g=empty();h=unit('hero',0,10020,(5,0));g.units=[h]
        h.hp=2
        for _ in range(3):g.combat()
        self.assertEqual((h.level,h.xp,h.pending_level,h.hp),(1,3,2,2))
        g.round+=1;g.start_round()
        self.assertEqual((h.level,h.max_hp,h.hp),(2,8,5))
        h.hp=0;g.cleanup()
        g.combat()
        self.assertEqual((h.xp,h.level),(3,2))
        g.round=h.due;g.start_round()
        self.assertEqual((h.hp,h.max_hp,h.xp),(8,8,3))
        g.combat()
        self.assertEqual(h.xp,4)

    def test_fountain_survivors_get_experience(self):
        g=empty();h=unit('h',0,10017,(7,0));g.units=[h]
        g.combat();self.assertEqual(h.xp,1)

    def test_hero_panels_and_fixed_cleave(self):
        g=empty();s=unit('s',1,10054,(3,2),2);g.units=[s]
        g.equip(s,65017)
        self.assertEqual((g.attack(s),g.cleave(s)),(14,2))
        g.play_card(63003,'all',1);g.play_card(63003,'all',1)
        self.assertEqual((g.attack(s),g.cleave(s)),(28,2))

    def test_locked_signatures_require_owner_on_board_and_level(self):
        g=empty();s=unit('s',1,10054,(3,2));g.units=[s];g.hand[1]=[63003]
        self.assertFalse([a for a in g.legal_actions(1) if a[1]=='card'])
        s.level=2
        self.assertTrue([a for a in g.legal_actions(1) if a[1]=='card'])
        s.pos=None
        self.assertFalse([a for a in g.legal_actions(1) if a[1]=='card'])

    def test_global_signatures_require_the_owner_on_board_after_unlocking(self):
        for hero,cid,level in ((10017,63005,3),(10044,63006,2)):
            g=empty();owner=unit('owner',0,hero,None,level);ally=unit('ally',0,10014,(4,2))
            ally.hp=1;g.units=[owner,ally];g.hand[0]=[cid]
            self.assertFalse([a for a in g.legal_actions(0) if a[1]=='card'])
            owner.pos=(5,2)
            do(g,'card',0,'all' if cid==63005 else 'ally')
            if cid==63005:self.assertEqual((ally.hp,ally.buffs.get('immune')),(6,True))
            else:self.assertEqual(ally.favor,1)

    def test_global_signatures_require_owner_level_even_when_in_play(self):
        for hero,cid,level in ((10017,63005,3),(10044,63006,2)):
            g=empty();owner=unit('owner',0,hero,(5,2),1);ally=unit('ally',0,10014,(4,2))
            g.units=[owner,ally];g.hand[0]=[cid]
            self.assertFalse([a for a in g.legal_actions(0) if a[1]=='card'])
            owner.level=level
            self.assertTrue([a for a in g.legal_actions(0) if a[1]=='card'])

    def test_wolves_use_current_level_and_do_not_grow_retroactively(self):
        g=empty();h=unit('h',0,10014,(4,2));g.units=[h];g.hand[0]=[63004]
        do(g,'card',0,'self')
        wolves=[u for u in g.field() if not u.hero]
        self.assertEqual([u.panel for u in wolves],[(1,0,3)]*2)
        self.assertTrue(all(abs(u.pos[0]-4)+abs(u.pos[1]-2)==1 for u in wolves))
        h.level=3
        self.assertEqual([u.panel for u in wolves],[(1,0,3)]*2)
        self.assertEqual(g.card_cost(63004,0),4)

    def test_reforge_draws_before_return_and_costs_no_mana(self):
        g=empty();g.hand[0]=[63005];g.deck[0]=[62010]
        do(g,'reforge',0,'draw')
        self.assertEqual((g.hand[0],g.deck[0],g.mana[0]),([62010],[63005],10))
        do(g,'reforge',0,'draw')
        self.assertEqual((g.hand[0],g.deck[0]),([63005],[62010]))
        g.deck[0]=[]
        self.assertFalse([a for a in g.legal_actions(0) if a[1]=='reforge'])

    def test_items_cannot_be_reforged(self):
        g=empty();g.item_hand[0]=[(65017,True)];g.item_deck[0]=[65001]
        self.assertFalse([a for a in g.legal_actions(0) if a[1]=='reforge_item'])

    def test_purification_can_target_the_holder(self):
        g=empty();h=unit('h',0,10044,(4,2),3);g.units=[h];h.hp=5
        do(g,'purify','h','h')
        self.assertEqual((h.hp,h.cd),(8,2))

    def test_taunt_chases_before_combat_and_forbids_manual_move(self):
        g=empty();axe=unit('axe',1,10020,(3,2));h=unit('h',0,10044,(2,3));g.units=[axe,h]
        g.negative(h,'taunt',axe.uid)
        self.assertFalse([a for a in g.legal_actions(0) if a[1]=='move'])
        self.assertIsNone(g.target(h))
        g.combat()
        self.assertEqual(axe.hp,2)
        self.assertEqual(h.hp,3)
        self.assertTrue(h.moved)
        self.assertEqual(abs(h.pos[0]-3)+abs(h.pos[1]-2),1)

    def test_swap_retargets_automatic_aggro_without_a_chase(self):
        g=empty()
        scout=unit('scout',0,61009,(4,1))
        creep=unit('creep',0,1006,(3,1))
        enemy=unit('enemy',1,1006,(2,1))
        g.units=[scout,creep,enemy]
        g.refresh_targets()
        self.assertIs(g.target(creep),enemy)
        do(g,'swap','scout','creep')
        self.assertIsNone(g.aggro_target(creep))
        self.assertIs(g.target(enemy),scout)
        g.chase()
        self.assertEqual(creep.pos,(4,1))

    def test_ordinary_aggro_retains_unreachable_target_and_chases_before_combat(self):
        g=empty();a=unit('a',0,10044,(4,2));v=unit('v',1,10020,(3,3));g.units=[a,v]
        a.target_uid='v';a.ordered=True
        g.refresh_targets()
        self.assertEqual(a.target_uid,'v')
        self.assertIsNone(g.target(a))
        self.assertTrue([x for x in g.legal_actions(0) if x[1]=='move'])
        g.combat()
        self.assertTrue(a.moved)
        self.assertEqual(v.hp,2)

    def test_normal_order_can_be_overridden_and_does_not_enable_extra_movement(self):
        g=empty();a=unit('a',0,10044,(4,2));v=unit('v',1,10020,(3,3));w=unit('w',1,1006,(4,3));g.units=[a,v,w]
        a.target_uid='v';a.ordered=True;a.moved=True
        g.refresh_targets();g.combat()
        self.assertEqual((a.pos,v.hp),((4,2),5))
        g=empty();a=unit('a',0,10044,(4,2));v=unit('v',1,10020,(3,3));w=unit('w',1,1006,(4,3));g.units=[a,v,w]
        a.target_uid='v';a.ordered=True;g.hand[0]=[62001]
        # Red color requirement is supplied independently of the target unit.
        red=unit('red',0,10020,(6,4));g.units.append(red)
        do(g,'card',0,'a|w')
        self.assertEqual((g.aggro_target(a).uid,a.forced_uid),('w',None))

    def test_already_moved_or_hexed_units_do_not_chase(self):
        for controlled in ('moved','hex'):
            g=empty();a=unit('a',1,10020,(3,2));h=unit('h',0,10044,(2,3));g.units=[a,h]
            g.negative(h,'taunt',a.uid)
            if controlled=='moved':h.moved=True
            else:g.negative(h,'hex')
            g.combat();self.assertEqual(h.pos,(2,3));self.assertEqual(a.hp,5)

    def test_retaliation_requires_normal_attack_with_positive_hp_damage(self):
        g=empty();a=unit('a',0,10017,(4,2));v=unit('v',1,10069,(3,2),2)
        g.units=[a,v];v.permanent_armor=4
        g.negative(v,'hex')  # No attack, but its passive retaliation remains active.
        g.combat()
        self.assertEqual(a.hp,5)
        v.permanent_armor=0
        g.combat()
        self.assertEqual((a.hp,v.hp),(3,6))

    def test_retaliation_is_not_triggered_by_spell_damage(self):
        g=empty();a=unit('a',0,10020,(4,2));v=unit('v',1,10069,(3,2),2);g.units=[a,v]
        g.hurt(v,1,a);g.cleanup()
        self.assertEqual(a.hp,5)

    def test_bkb_dispels_negative_growth_and_lock_but_keeps_positive_growth(self):
        g=empty();h=unit('h',0,10017,(4,2));g.units=[h];g.equip(h,65012)
        h.permanent_attack=3;g.negative(h,'attack_down',4);g.negative(h,'silence');g.negative(h,'taunt','enemy')
        do(g,'bkb','h','self')
        self.assertEqual((g.attack(h),h.forced_uid,h.debuffs),(4,None,{}))
        self.assertFalse(g.negative(h,'hex'))
        self.assertEqual(g.hurt(h,3,kind='magic'),0)
        self.assertEqual(g.hurt(h,2,kind='physical'),2)
        self.assertEqual(h.gear_cds[65012],3)
        g.round+=1;g.start_round()
        self.assertTrue(g.negative(h,'silence'))

    def test_hex_blocks_actives_but_keeps_passives_and_color(self):
        g=empty();h=unit('h',0,10014,(4,2),3);c=unit('c',0,1006,(4,3));g.units=[h,c]
        g.equip(h,65011);g.equip(h,65013);g.negative(h,'hex')
        self.assertEqual((h.armor,g.retaliate(h),g.attack(c),g.regeneration(h)),(1,2,4,1))
        g.hand[0]=[62011]
        self.assertTrue([a for a in g.legal_actions(0) if a[1]=='card'])
        self.assertFalse([a for a in g.legal_actions(0) if a[2]=='h'])

    def test_silence_blocks_hero_active_but_allows_equipment(self):
        g=empty();h=unit('h',0,10017,(4,2));c=unit('c',1,1006,(4,3));g.units=[h,c]
        g.equip(h,65012);g.negative(h,'silence')
        kinds={a[1] for a in g.legal_actions(0)}
        self.assertIn('bkb',kinds);self.assertNotIn('chen',kinds)

    def test_blink_is_manhattan_three_and_does_not_land_on_buildings(self):
        g=empty();h=unit('h',0,10017,(4,2));g.units=[h];g.equip(h,65010)
        targets={a[3] for a in g.legal_actions(0) if a[1]=='blink'}
        self.assertIn('7,2',targets);self.assertNotIn('2,4',targets);self.assertNotIn('6,2',targets)
        do(g,'blink','h','7,2')
        self.assertEqual((h.pos,h.gear_cds[65010]),((7,2),2))

    def test_midas_is_five_gold_total_and_cannot_target_heroes(self):
        g=empty();h=unit('h',0,10017,(4,2));c=unit('c',1,1006,(4,3));v=unit('v',1,10020,(3,2));g.units=[h,c,v]
        g.equip(h,65014)
        self.assertEqual([a[3] for a in g.legal_actions(0) if a[1]=='midas'],['c'])
        do(g,'midas','h','c')
        self.assertEqual(g.gold,[5,0]);self.assertNotIn(c,g.units)

    def test_mek_includes_holder_and_eight_neighbors(self):
        g=empty();h=unit('h',0,10017,(4,2));c=unit('c',0,1006,(5,3));g.units=[h,c]
        g.equip(h,65013);h.hp=2;c.hp=1
        self.assertEqual((g.regeneration(h),g.regeneration(c)),(1,1))
        do(g,'mek','h','self')
        self.assertEqual((h.hp,c.hp),(4,3))

    def test_rapier_forces_weapon_replacement_and_is_trace_independent(self):
        results=[]
        for trace in (False,True):
            g=empty();g.trace=trace
            dead=unit('d',0,10017,(4,2));killer=unit('k',1,10020,(3,2));g.units=[dead,killer]
            g.equip(dead,65017);g.equip(killer,65001)
            g.hurt(dead,dead.hp,killer,raw=True);g.cleanup()
            self.assertEqual(killer.equipment['Weapon'],65017)
            self.assertNotIn(65017,dead.equipment.values())
            results.append(deepcopy(killer.equipment))
        self.assertEqual(*results)

    def test_shared_lethal_rapier_contributions_choose_one_recipient_deterministically(self):
        recipients=[]
        for trace in (True,False):
            g=empty();g.trace=trace
            h=unit('h',0,10017,(4,2));a=unit('a',1,10020,(3,2));b=unit('b',1,10069,(4,3));g.units=[h,a,b]
            g.equip(h,65017)
            g.hurt(h,3,a);g.hurt(h,3,b);g.cleanup()
            owners=[u.uid for u in (a,b) if 65017 in u.equipment.values()]
            self.assertEqual(len(owners),1)
            recipients.append(owners[0])
        self.assertEqual(recipients[0],recipients[1])

    def test_simultaneously_dead_killer_receives_rapier_after_death_batch(self):
        g=empty();h=unit('h',0,10017,(4,2));k=unit('k',1,10020,(3,2));g.units=[h,k]
        g.equip(h,65017)
        g.hurt(h,h.hp,k,raw=True);k.hp=0;g.cleanup()
        self.assertEqual((h.pos,k.pos),(None,None))
        self.assertEqual(k.equipment['Weapon'],65017)
        self.assertFalse(g.item_hand[1])

    def test_nonhero_rapier_kill_puts_paid_item_in_opponent_hand(self):
        g=empty();h=unit('h',0,10017,(4,2));c=unit('c',1,1006,(3,2));g.units=[h,c];g.equip(h,65017)
        g.hurt(h,h.hp,c,raw=True);g.cleanup()
        self.assertEqual(g.item_hand[1],[(65017,True)])

    def test_teleport_immediately_heals_without_resetting_movement(self):
        g=empty();h=unit('h',0,10017,(4,2));g.units=[h];h.hp=1;h.moved=True;h.cd=3
        g.item_hand[0]=[(65022,False)];g.gold[0]=3
        do(g,'item',0,'h')
        self.assertEqual((h.pos[0],h.hp,h.moved,h.first_move,h.cd,g.gold[0]),(7,5,True,False,3,0))

    def test_clone_inherits_buffs_without_recursive_spawn(self):
        g=empty();original=g.create_unit(0,61008,(4,2),False)
        original.permanent_attack=2;original.permanent_health=3;original.hp=5
        clone=g.create_unit(0,61008,g.ordered_empty(original.pos)[0],False,original)
        self.assertEqual((len(g.field()),clone.pos,clone.permanent_attack,clone.max_hp,clone.hp),(2,(4,1),2,5,5))
        g.units=[];g.create_unit(0,61008,(4,2))
        self.assertEqual(len(g.field()),2)

    def test_arrow_redirect_is_not_a_taunt_lock(self):
        g=empty();h=unit('h',0,61011,(4,2));a=unit('a',0,10017,(4,3));v=unit('v',1,1006,(3,3));g.units=[h,a,v]
        do(g,'redirect','h','v')
        self.assertEqual((a.target_uid,a.forced_uid),('v',None))
        self.assertTrue([x for x in g.legal_actions(0) if x[1]=='move' and x[2]=='a'])

    def test_global_spells_and_permanent_debuffs(self):
        g=empty();a=unit('a',0,10014,(7,0));c=unit('c',0,1006,(1,4));v=unit('v',1,10020,(0,0));g.units=[a,c,v]
        g.hand[0]=[62015,62019]
        do(g,'card',0,'all')
        self.assertEqual((c.permanent_attack,c.permanent_armor),(2,1))
        do(g,'card',0,'all')
        self.assertEqual(g.attack(v),1)
        g.round+=1;g.start_round();self.assertEqual(g.attack(v),1)

    def test_unprepared_lasts_until_equipping_an_item(self):
        g=empty();h=unit('h',0,10017,(4,2));g.units=[h]
        g.negative(h,'unprepared');g.round+=1;g.start_round();self.assertTrue(h.stunned)
        g.item_hand[0]=[(65001,False)];g.gold[0]=3
        do(g,'item',0,'h');self.assertFalse(h.stunned)

    def test_siege_only_adds_damage_when_attacking_structure(self):
        g=empty();a=unit('a',0,10017,(2,2));a.permanent_siege=3;g.units=[a]
        g.combat();self.assertEqual(g.forts[1].hp,36)
        g=empty();a=unit('a',0,10017,(2,2));a.permanent_siege=3;v=unit('v',1,1006,(2,3));g.units=[a,v]
        g.combat();self.assertEqual(g.forts[1].hp,40)

    def test_forecast_does_not_mutate_growth_status_rng_or_equipment(self):
        s=GrowthSession(13);before=deepcopy(vars(s.game))
        s.combat_forecast();self.assertEqual(vars(s.game),before)

    def test_enough_magic_ends_actions_before_ai_can_respond(self):
        s=GrowthSession(13);g=empty();h=unit('h',0,10020,(4,2));g.units=[h];g.hand[0]=[62008];s.game=g
        action=next(v['id'] for v,a in s._catalog() if a[1]=='card')
        s.apply(0,action)
        self.assertEqual(s.phase,'round_end')
        self.assertEqual(g.stats[1]['actions'],0)
        self.assertEqual(h.xp,1)

    def test_duel_winner_bonus_survives_death_and_respawn(self):
        g=empty();a=unit('a',0,10069,(4,2),3);v=unit('v',1,10020,(3,2));g.units=[a,v]
        g.hand[0]=[63002]
        # Use the red side of the prototype catalog with a red hero on team zero.
        do(g,'card',0,'v')
        g.combat()
        self.assertEqual((a.permanent_attack,a.hp),(1,6))
        a.hp=0;g.cleanup();g.round=a.due;g.start_round()
        self.assertEqual((a.permanent_attack,g.attack(a)),(1,7))

    def test_hand_of_god_heals_and_blocks_physical_but_not_execution(self):
        g=empty();h=unit('h',0,10017,(4,2),3);c=unit('c',0,1006,(4,3));v=unit('v',1,10020,(3,3));g.units=[h,c,v]
        h.hp=c.hp=1;g.hand[0]=[63005]
        do(g,'card',0,'all')
        self.assertEqual((h.hp,c.hp),(9,4))
        self.assertEqual(g.hurt(c,100,v),0)
        g.equip(v,65014);do(g,'midas','v','c',1)
        self.assertEqual((c.pos,g.gold[1]),(None,5))

    def test_regeneration_resolves_before_death_cleanup(self):
        g=empty();c=unit('c',0,61010,(4,2));v=unit('v',1,10017,(3,2));g.units=[c,v]
        c.hp=1
        g.combat()
        self.assertEqual((c.hp,c.pos),(2,(4,2)))

    def test_red_six_cost_hits_two_distinct_cardinal_enemies(self):
        g=empty()
        foes=[unit(str(i),1,1006,p) for i,p in enumerate(((3,2),(4,1),(4,3),(3,3)))]
        g.units=list(foes)
        g.create_unit(0,61006,(4,2))
        self.assertEqual(sorted(v.hp for v in foes),( [2,2,4,4]))
        self.assertEqual(foes[-1].hp,4)

    def test_permanent_attack_reduction_survives_death_but_bkb_dispels_it(self):
        g=empty();h=unit('h',0,10017,(4,2));g.units=[h]
        g.negative(h,'attack_down',2);h.hp=0;g.cleanup()
        g.round=h.due;g.start_round()
        self.assertEqual(g.attack(h),0)
        g.equip(h,65012);do(g,'bkb','h','self')
        self.assertEqual(g.attack(h),1)

    def test_full_ai_match_reaches_base_victory_with_valid_states(self):
        g=GrowthMatch(4,trace=False)
        for r in range(1,121):
            g.round=r;g.start_round();g.auto_move();g.reveal()
            team=(r-1)%2;passes=0
            for _ in range(250):
                choices=g.actions(team)
                if choices:g.take_action(max(choices),team);passes=0
                else:passes+=1
                if passes==2 or g.force_combat:break
                team=1-team
            else:self.fail('Action phase never ended')
            g.combat();g.check()
            if g.finished:break
        self.assertTrue(g.finished)
        self.assertEqual(g.forts[1-g.winner].stage,'base')
        self.assertLessEqual(g.forts[1-g.winner].hp,0)

    def test_deck_validation_and_nine_fixed_signatures(self):
        config=default_deck();deck=full_deck(validate_deck(config),0)
        self.assertEqual(len(deck),30)
        for cid in (63004,63005,63006):self.assertEqual(deck.count(cid),3)
        for bad in ({'ordinary':[61007]*21,'items':config['items']}, {'ordinary':config['ordinary'][:-1],'items':config['items']}, {'ordinary':config['ordinary'],'items':[65001]*10}):
            with self.assertRaises(ValueError):validate_deck(bad)

    def test_custom_deck_survives_browser_replay(self):
        config=default_deck();config['items'][0]=65022
        bridge=BrowserBridge('growth-test')
        response=bridge.request('/api/games',{'seed':13,'deck_config':config},new_id='a'*32)
        self.assertEqual(response['status'],200)
        action=response['data']['state']['actions'][0]['id']
        after=bridge.request('/api/games/'+'a'*32+'/actions',{'version':0,'action_id':action})
        replay=BrowserBridge('growth-test').request('/api/games/'+'a'*32,None,after['save'])
        self.assertEqual(replay['data']['state'],after['data']['state'])
        self.assertEqual(after['save']['deck_config'],config)


if __name__=='__main__':unittest.main()
