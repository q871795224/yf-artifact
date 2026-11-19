"""Single-lane growth Demo. Classic experiments remain in simulate_*.py."""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass, field

from simulate_heroes import EIGHT, CARDINAL, distance, valid
from simulate_match import Match, BattleUnit, Fort, CARDS
from growth_cards import PANELS, ITEMS, ROSTERS, SIGNATURES, RANGED_CREEP, validate_deck, full_deck

GLOBAL_SKILLS = (('rally_swap', '调位'), ('direct_attack', '指引攻击'))
GLOBAL_SKILL_COST = 2


@dataclass
class GrowthUnit(BattleUnit):
    level: int = 1
    xp: int = 0
    pending_level: int = 1
    permanent_health: int = 0
    permanent_armor: int = 0
    permanent_cleave: int = 0
    permanent_retaliate: int = 0
    permanent_siege: int = 0
    temporary_cleave: int = 0
    debuffs: dict = field(default_factory=dict)
    buffs: dict = field(default_factory=dict)
    gear_cds: dict = field(default_factory=dict)
    favor: int = 0
    forced_uid: str | None = None
    ordered: bool = False
    damage_sources: set = field(default_factory=set)
    bounty_override: int | None = None
    horn_cd: int = 0
    blade_cd: int = 0

    @property
    def name(self):
        return "全能骑士" if self.hero==10044 else super().name

    @property
    def panel(self):
        return PANELS[self.hero][self.level-1] if self.hero else (CARDS[self.card_id].get('attack',0),CARDS[self.card_id].get('armor',0),CARDS[self.card_id]['hit_points'])

    @property
    def max_hp(self):
        return self.panel[2]+self.permanent_health+sum(ITEMS[i]['hit_points'] for i in self.equipment.values())

    @property
    def armor(self):
        return max(0,self.panel[1]+self.permanent_armor+self.temporary_armor+sum(ITEMS[i]['armor'] for i in self.equipment.values()))

    @property
    def reach(self):
        if self.hero==10017:
            return 2+(65018 in self.equipment.values())
        return 2 if self.card_id==RANGED_CREEP else 1


class GrowthMatch(Match):
    def __init__(self, seed=13, deck_config=None, trace=True):
        self.seed,self.trace,self.round=seed,trace,0
        self.columns,self.targeting,self.protection,self.tower_attack=5,'aggro',True,4
        self.rosters=ROSTERS
        self.deck_config=[validate_deck(deck_config),validate_deck(None,1)]
        self.forts=[Fort(t,position=(6 if t==0 else 1,2)) for t in (0,1)]
        self.finished,self.winner,self.end_reason=False,None,None
        self.stats=[Counter(),Counter()]
        self.gold,self.mana=[0,0],[0,0]
        self.events,self.frames,self.units=[],[],[]
        self.hand,self.deck=[[],[]],[[],[]]
        self.item_hand,self.item_deck=[[],[]],[[],[]]
        self.improvements=[[],[]]
        self.spells=[set(),set()]
        self.first_spell=[False,False]
        self.probes=False
        self.created=0
        self.duels=[]
        self.force_combat=False
        self.global_skill_used=[False,False]
        self.gear_ids=[i for i,c in ITEMS.items() if c['sub_type']!='Consumable']
        columns=self.rng('growth-opening').sample([0,1,3,4],2)
        for team,roster in enumerate(self.rosters):
            row=4 if team==0 else 3
            for n,h in enumerate(roster):
                self.units.append(GrowthUnit(f'{"AB"[team]}H{n+1}',team,h,PANELS[h][0][2],(row,columns[0]) if n==0 else None,
                    card_id=h,due=n+1 if n else 0,first_move=False if n==0 else True,next_cd=2 if h==10044 else 4))
            self.create_unit(team,1006,(row,columns[1]),trigger=False).first_move=False
            self.deck[team]=full_deck(self.deck_config[team],team)
            self.item_deck[team]=list(self.deck_config[team]['items'])
            self.rng(f'deck:{team}').shuffle(self.deck[team])
            self.rng(f'items:{team}').shuffle(self.item_deck[team])
            self.draw(team,5)
            self.draw_item(team)
        self.check()

    def start_round(self):
        self.force_combat=False
        self.duels=[]
        self.global_skill_used=[False,False]
        for u in self.units:
            u.buffs.clear()
            u.debuffs={k:v for k,v in u.debuffs.items() if k in ('attack_down','unprepared')}
            u.stunned='unprepared' in u.debuffs
            u.forced_uid=None
            u.ordered=False
            u.temporary_attack=u.temporary_armor=u.temporary_cleave=0
            u.bonus=0
            u.moved=False
            u.cd=max(0,u.cd-1)
            u.gear_cds={k:max(0,v-1) for k,v in u.gear_cds.items()}
            if u.pending_level>u.level:
                before=u.max_hp
                u.level=u.pending_level
                u.hp+=u.max_hp-before
                self.record(f'{u.uid}升至{u.level}级，生命上限增加{u.max_hp-before}')
            if u.hero and u.pos is None and self.round>=u.due:
                self.spawn_hero(u)
        for team in (0,1):
            if self.round>1:
                cells=self.fountain_positions(team)
                if cells and len(self.field(team))<24:
                    creep=RANGED_CREEP if self.round%3==0 else 1006
                    self.create_unit(team,creep,self.rng(f'creep-spawn:{team}').choice(cells),trigger=False)
                self.draw(team,1)
            if self.round%3==0:
                self.draw_item(team)
        self.mana=[self.max_mana]*2
        self.refresh_targets()

    @property
    def max_mana(self):
        return min(10,self.round)

    def fort_reach(self,fort):
        return 1 if fort.stage=='tower' else super().fort_reach(fort)

    def fountain_positions(self,team):
        occupied={u.pos for u in self.field()}|self.blocked_positions()
        return [(7 if team==0 else 0,c) for c in range(self.columns) if (7 if team==0 else 0,c) not in occupied]

    def stops_marching(self,u):
        if u.card_id==RANGED_CREEP and (self.target(u) or self.building_target(u)):
            return True
        return super().stops_marching(u)

    def spawn_hero(self,u):
        cells=self.fountain_positions(u.team)
        if not cells:
            # Preserve the existing full-fountain fallback: replace a friendly creep.
            candidates=[v for v in self.field(u.team) if not v.hero and v.pos[0]==(7 if u.team==0 else 0)]
            if candidates:
                victim=min(candidates,key=lambda v:(v.hp,v.uid))
                victim.hp=0
                self.cleanup()
                cells=self.fountain_positions(u.team)
        if cells and len(self.field(u.team))<24:
            u.pos=cells[0]
            u.hp=u.max_hp
            u.first_move=True
            self.record(f'{u.uid}在泉水登场 {u.pos}')

    def attack(self,u,pos=None):
        pos=u.pos if pos is None else pos
        aura=sum((2 if v.level==3 else 1) for v in self.field(u.team) if v.hero==10014 and v is not u and distance(v.pos,pos)==1)
        amount=u.panel[0]+u.permanent_attack+u.temporary_attack+u.bonus+sum(ITEMS[i]['attack'] for i in u.equipment.values())+aura-u.debuffs.get('attack_down',0)
        return max(0,amount)*(2 if u.buffs.get('strength') else 1)

    def primary_damage(self,u,target,pos=None):
        return self.damage_amount(target,self.attack(u,pos),'physical')

    def damage_amount(self,target,amount,kind='physical'):
        if target.buffs.get('immune') or (kind=='magic' and target.buffs.get('bkb')):
            return 0
        return max(0,amount-(target.armor if kind=='physical' else 0))

    def hurt(self,target,amount,source=None,kind='physical',raw=False):
        actual=self.damage_amount(target,amount,kind) if not raw else (0 if target.buffs.get('immune') else amount)
        target.hp-=actual
        if actual>0:
            target.damage_sources.add(source.uid if source else 'spell')
        return actual

    def heal(self,u,amount):
        actual=max(0,min(amount,u.max_hp-u.hp))
        u.hp+=actual
        return actual

    def negative(self,u,name,value=1):
        if u.buffs.get('bkb'):
            return False
        if name=='attack_down':
            u.debuffs[name]=u.debuffs.get(name,0)+value
        elif name=='taunt':
            if u.forced_uid:
                return False
            u.forced_uid=value
            u.debuffs[name]=1
        else:
            u.debuffs[name]=value
        u.stunned=bool(u.debuffs.get('unprepared') or u.debuffs.get('hex'))
        return True

    def can_act(self,u):
        return not u.stunned and not u.debuffs.get('hex')

    def can_skill(self,u):
        return self.can_act(u) and not u.debuffs.get('silence')

    def protecting_heroes(self,team,observer=None,override=None):
        if not self.protection:
            return []
        result=[]
        for h in self.field(1-team):
            if not h.hero or not self.can_act(h):
                continue
            p=override[1] if override and h is override[0] else h.pos
            victim=self.target(h,pos=p,override=override)
            if victim and victim.hero and victim.team==team and (observer is None or distance(observer,p)<=1):
                result.append(h)
        return result

    def aggro_target(self,u,pos=None,override=None):
        """Explicit orders survive being out of range; automatic targets follow position."""
        foes=self.field(1-u.team)
        p=u.pos if pos is None else pos
        def position(v):
            return override[1] if override and v is override[0] else v.pos
        if u.forced_uid:
            return next((v for v in foes if v.uid==u.forced_uid),None)
        if u.ordered:
            old=next((v for v in foes if v.uid==u.target_uid),None)
            if old:
                return old
        if not u.hero and not u.ordered:
            protected=[v for v in self.protecting_heroes(u.team,observer=p,override=override)
                       if (p[0]==position(v)[0] or p[1]==position(v)[1]) and distance(p,position(v))<=u.reach]
            if protected:
                return next((v for v in protected if v.uid==u.target_uid),min(protected,key=lambda v:(distance(p,position(v)),v.uid)))
        return super().target(u,pos,override)

    def target(self,u,pos=None,override=None):
        if not self.can_act(u):
            return None
        v=self.aggro_target(u,pos,override)
        if v is None:
            return None
        p=u.pos if pos is None else pos
        q=override[1] if override and v is override[0] else v.pos
        return v if (p[0]==q[0] or p[1]==q[1]) and 0<distance(p,q)<=u.reach else None

    def refresh_targets(self):
        # Commit explicit intents and legal automatic targets.
        for u in self.field():
            v=self.aggro_target(u)
            if u.ordered and (not v or v.uid!=u.target_uid):
                u.ordered=False
            u.target_uid=v.uid if v else None
        for f in self.forts:
            v=self.fort_target(f)
            f.target_uid=v.uid if v else None

    def building_target(self,u,pos=None):
        return None if u.forced_uid or self.aggro_target(u,pos) or not self.can_act(u) else super().building_target(u,pos)

    def cleave(self,u):
        return u.permanent_cleave+u.temporary_cleave+((1 if u.level==1 else 2) if u.hero==10054 else 0)

    def retaliate(self,u):
        return u.permanent_retaliate+(2 if u.hero==10069 and u.level>=2 else 0)+(2 if 65011 in u.equipment.values() else 0)

    def siege(self,u):
        return u.permanent_siege

    def regeneration(self,u):
        own=2 if CARDS[u.card_id].get('effect')=='regen' else 0
        for v in self.field(u.team):
            if 65013 in v.equipment.values() and distance(v.pos,u.pos)<=1:
                own+=1
            if v is not u and v.favor and abs(v.pos[0]-u.pos[0])+abs(v.pos[1]-u.pos[1])==1:
                own+=2*v.favor
        return own

    def ordered_empty(self,center,wolves=False):
        occupied={u.pos for u in self.field()}|self.blocked_positions()
        offsets=CARDINAL if wolves else ((0,-1),(0,1),(-1,0),(1,0))
        first=[(center[0]+dr,center[1]+dc) for dr,dc in offsets]
        first += [(center[0]+dr,center[1]+dc) for dr,dc in EIGHT if dr and dc]
        rest=sorted(((r,c) for r in range(8) for c in range(self.columns) if (r,c) not in first),key=lambda p:(distance(p,center),abs(p[0]-center[0])+abs(p[1]-center[1]),p))
        return [p for p in first+rest if valid(p,self.columns) and p not in occupied]

    def spawn_positions(self,team):
        occupied={u.pos for u in self.field()}|self.blocked_positions()
        return [(r,c) for r in range(8) for c in range(self.columns) if (r,c) not in occupied and
            (r==(7 if team==0 else 0) or any(distance((r,c),h.pos)==1 for h in self.field(team) if h.hero))]

    def create_unit(self,team,cid,pos,trigger=True,copy=None):
        if len(self.field(team))>=24:
            return None
        self.created+=1
        u=GrowthUnit(f'{"AB"[team]}U{self.created}',team,None,CARDS[cid]['hit_points'],pos,card_id=cid)
        if copy:
            u=deepcopy(copy)
            u.uid=f'{"AB"[team]}U{self.created}'
            u.pos=pos
            u.damage_sources=set()
        self.units.append(u)
        self.record(f'{u.uid}召唤{u.name} {pos}')
        if trigger:
            effect=CARDS[cid].get('effect')
            if effect in ('ping1','ping2'):
                targets=[v for v in self.field(1-team) if abs(v.pos[0]-pos[0])+abs(v.pos[1]-pos[1])==1]
                targets=self.rng(f'enter:{u.uid}').sample(targets,min(len(targets),1 if effect=='ping1' else 2))
                for v in targets:
                    self.hurt(v,1 if effect=='ping1' else 2,u)
            elif effect=='clone' and len(self.field(team))<24:
                cells=self.ordered_empty(pos)
                if cells:
                    self.create_unit(team,cid,cells[0],False,u)
            elif effect=='repair':
                self.repair(team,4)
        return u

    def repair(self,team,amount):
        f=self.forts[team]
        if f.stage=='tower':
            f.hp=min(f.max_hp,f.hp+amount)

    def cleanup(self):
        dead=[u for u in self.field() if u.hp<=0]
        if not dead:
            return
        dead_ids={u.uid for u in dead}
        for a,b in self.duels:
            for loser,winner in ((a,b),(b,a)):
                survivor=next((u for u in self.field() if u.uid==winner),None)
                if loser in dead_ids and winner not in dead_ids and survivor:
                    survivor.permanent_attack+=1
                    self.record(f'{survivor.uid}赢得决斗，永久+1攻击')
        self.duels=[pair for pair in self.duels if not dead_ids.intersection(pair)]
        rapier_transfers=[]
        # Death triggers inspect the original positions of all simultaneous casualties.
        for u in dead:
            effect=CARDS[u.card_id].get('effect')
            if effect=='death_buff':
                for v in self.field(u.team):
                    if v.uid not in dead_ids and v.pos in ((u.pos[0],u.pos[1]-1),(u.pos[0],u.pos[1]+1)):
                        v.permanent_attack+=1
                        v.permanent_health+=1
                        v.hp+=1
            elif effect=='repair':
                self.repair(u.team,4)
            sources=[v for v in self.units if v.uid in u.damage_sources and v.team!=u.team]
            for v in sources:
                if CARDS[v.card_id].get('effect')=='grow_kill' and v.uid not in dead_ids:
                    v.permanent_attack+=1
            bounty=u.bounty_override if u.bounty_override is not None else (5 if u.hero else 1)
            self.gold[1-u.team]+=bounty
            self.stats[1-u.team]['gold_earned']+=bounty
            self.record(f'{u.uid}阵亡，对方获得{bounty}金币')
            if 65017 in u.equipment.values():
                del u.equipment['Weapon']
                # Every positive damage contributor is eligible, including nonhero effects.
                contributors=sorted(u.damage_sources) or ['environment']
                chosen=self.rng(f'rapier:{u.uid}:{self.stats[0]["actions"]}:{self.stats[1]["actions"]}').choice(contributors)
                recipient=next((v for v in self.units if v.uid==chosen and v.hero and v.team!=u.team),None)
                rapier_transfers.append((1-u.team,recipient))
        for u in dead:
            u.pos=None
            u.target_uid=None
            u.due=self.round+2
            u.damage_sources.clear()
            u.bounty_override=None
            u.debuffs={k:v for k,v in u.debuffs.items() if k in ('attack_down','unprepared')}
            u.buffs.clear()
            u.forced_uid=None
            u.stunned='unprepared' in u.debuffs
        # Apply transfers after the entire death batch so a simultaneously dead
        # killer remains a valid hero recipient without recursively dropping a new item.
        for team,recipient in rapier_transfers:
            if recipient:
                self.equip(recipient,65017)
                self.record(f'圣剑转移至{recipient.uid}，强制替换武器')
            else:
                self.item_hand[team].append((65017,True))
                self.record('圣剑归对方所有，加入已付费物品手牌')
        self.units=[u for u in self.units if u.hero or u.pos is not None]
        for u in self.field():
            if u.forced_uid in dead_ids:
                u.forced_uid=None
                u.debuffs.pop('taunt',None)

    def equip(self,u,cid):
        before=u.max_hp
        slot=ITEMS[cid]['sub_type']
        old=u.equipment.get(slot)
        u.equipment[slot]=cid
        if old!=cid:
            if old:
                u.gear_cds.pop(old,None)
            u.gear_cds[cid]=0
        u.hp=max(1,min(u.max_hp,u.hp+max(0,u.max_hp-before)))
        u.debuffs.pop('unprepared',None)
        u.stunned=bool(u.debuffs.get('hex'))

    def card_cost(self,cid,team):
        if CARDS[cid].get('effect')=='wolves':
            h=next(u for u in self.units if u.team==team and u.hero==10014)
            return h.level+1
        return CARDS[cid]['mana_cost']

    def move_unit(self,u,pos):
        u.pos=pos
        u.moved=True
        u.first_move=False

    def swap_positions(self,a,b):
        old=a.pos
        self.move_unit(a,b.pos)
        self.move_unit(b,old)

    def commandable(self,team):
        return [u for u in self.field(team) if self.can_act(u) and not u.forced_uid]

    def direct_attack_units(self,team,target):
        return [u for u in self.commandable(team) if distance(u.pos,target.pos)==1]

    def card_targets(self,cid,team):
        c=CARDS[cid]
        friends,foes=self.field(team),self.field(1-team)
        units=friends+foes
        heroes=[u for u in friends if u.hero]
        if c.get('hero_id'):
            caster=next((h for h in heroes if h.hero==c['hero_id'] and h.level>=c['unlock_level']),None)
            if not caster:
                return []
        if not any(set(CARDS[h.hero]['colors']).intersection(c['colors']) for h in heroes):
            return []
        if c['card_type']=='Creep':
            return [f'{r},{col}' for r,col in self.spawn_positions(team)] if len(friends)<24 else []
        effect=c['effect']
        if effect=='duel':
            return [u.uid for u in foes if u.hero and abs(u.pos[0]-caster.pos[0])+abs(u.pos[1]-caster.pos[1])==1 and not u.forced_uid and not caster.forced_uid and not u.buffs.get('bkb')]
        if effect=='wolves':
            return ['self'] if len(friends)<=22 and len(self.ordered_empty(caster.pos,True))>=2 else []
        if effect in ('roar','strength','god','blood_draw','combat','triumph','arm','restore','atrophy'):
            return ['all']
        if effect=='favor':
            return [u.uid for u in units if u.hero and 'green' in CARDS[u.hero]['colors']]
        if effect in ('orders','pick','juke'):
            pairs=[]
            for u in friends:
                if (effect in ('orders','pick') and u.forced_uid) or (effect=='pick' and not u.hero):
                    continue
                for v in (friends if effect=='juke' else foes):
                    if effect=='pick' and abs(u.pos[0]-v.pos[0])+abs(u.pos[1]-v.pos[1])!=1:
                        continue
                    if effect=='pick' and (v.forced_uid or v.buffs.get('bkb')):
                        continue
                    if effect=='juke' and (u.pos[0]!=v.pos[0] or abs(u.pos[1]-v.pos[1])!=1 or u.forced_uid or v.forced_uid or not self.can_act(u) or not self.can_act(v)):
                        continue
                    pairs.append(u.uid+'|'+v.uid)
            return pairs
        if effect in ('train','cripple','unprepared'):
            return [u.uid for u in units if u.hero]
        if effect=='cleave':
            return [u.uid for u in heroes]
        if effect=='bellow':
            occupied={u.pos for u in self.field()}|self.blocked_positions()
            return [u.uid for u in units if not u.hero and any((u.pos[0],col) not in occupied for col in range(self.columns))]
        if effect=='intimidate':
            return [u.uid for u in units if self.fountain_positions(u.team)]
        return [u.uid for u in units]

    def legal_actions(self,team):
        out=[]
        def add(kind,actor,target):
            out.append((0,kind,str(actor),str(target)))
        friends,foes=self.field(team),self.field(1-team)
        for u in friends:
            if u.hero and self.can_act(u) and not u.moved and not u.forced_uid:
                for p in self.reachable(u):
                    add('move',u.uid,f'{p[0]},{p[1]}')
            if self.can_skill(u) and u.cd==0:
                if u.hero==10017 and len(friends)<24:
                    for v in foes:
                        if not v.hero and distance(u.pos,v.pos)<=2:
                            add('chen',u.uid,v.uid)
                if u.hero==10044:
                    for v in friends:
                        if distance(u.pos,v.pos)<=1:
                            add('purify',u.uid,v.uid)
                if CARDS[u.card_id].get('effect')=='swap' and not u.forced_uid:
                    for v in friends:
                        if distance(u.pos,v.pos)==1 and not v.forced_uid and self.can_act(v):
                            add('swap',u.uid,v.uid)
                if CARDS[u.card_id].get('effect')=='redirect':
                    for v in foes:
                        if distance(u.pos,v.pos)<=2:
                            add('redirect',u.uid,v.uid)
            if u.hero and self.can_act(u):
                for cid in u.equipment.values():
                    item=ITEMS[cid]
                    active=item.get('active')
                    if not active or u.gear_cds.get(cid,0):
                        continue
                    if active=='blink' and not u.forced_uid:
                        occupied={v.pos for v in self.field()}|self.blocked_positions()
                        for r in range(8):
                            for c in range(self.columns):
                                if (r,c) not in occupied and abs(r-u.pos[0])+abs(c-u.pos[1])<=3:
                                    add(active,u.uid,f'{r},{c}')
                    elif active in ('bkb','mek'):
                        add(active,u.uid,'self')
                    elif active in ('midas','hex','silence'):
                        for v in foes:
                            if distance(u.pos,v.pos)==1 and (active!='midas' or not v.hero):
                                add(active,u.uid,v.uid)
        for i,cid in enumerate(self.hand[team]):
            if self.deck[team]:
                add('reforge',i,'draw')
            if self.card_cost(cid,team)<=self.mana[team]:
                for t in self.card_targets(cid,team):
                    add('card',i,t)
        for i,(cid,paid) in enumerate(self.item_hand[team]):
            if (0 if paid else ITEMS[cid]['gold_cost'])>self.gold[team]:
                continue
            item=ITEMS[cid]
            if item['sub_type']!='Consumable':
                targets=[u.uid for u in friends if u.hero]
            elif item['active']=='knowledge':
                targets=['draw']
            elif item['active']=='teleport':
                targets=[u.uid for u in friends if u.hero and self.fountain_positions(team)]
            else:
                targets=[u.uid for u in friends]
            for t in targets:
                add('item',i,t)
        if self.mana[team]>=GLOBAL_SKILL_COST and not self.global_skill_used[team]:
            kind,_=GLOBAL_SKILLS[team]
            if kind=='rally_swap':
                units={u.pos:u for u in self.commandable(team)}
                occupied={u.pos for u in self.field()}|self.blocked_positions()
                for u in units.values():
                    for dr,dc in EIGHT:
                        pos=(u.pos[0]+dr,u.pos[1]+dc)
                        v=units.get(pos)
                        if v:
                            add(kind,u.uid,v.uid)
                        elif valid(pos,self.columns) and pos not in occupied:
                            add(kind,u.uid,f'{pos[0]},{pos[1]}')
            else:
                for v in foes:
                    if self.direct_attack_units(team,v):
                        add(kind,'',v.uid)
        return out

    def take_action(self,action,team):
        _,kind,actor_id,target_id=action
        index={u.uid:u for u in self.field()}
        for u in self.field():
            u.damage_sources.clear()
        actor,target=index.get(actor_id),index.get(target_id)
        self.stats[team]['actions']+=1
        if kind=='reforge':
            i=int(actor_id)
            old=self.hand[team][i]
            self.draw(team,1)
            self.hand[team].pop(i)
            self.deck[team].insert(self.rng(f'reforge:{team}:{self.stats[team]["actions"]}').randrange(len(self.deck[team])+1),old)
            self.record(f'{"AB"[team]}重铸一张普通牌，先抽牌再归库')
        elif kind=='move':
            self.move_unit(actor,tuple(map(int,target_id.split(','))))
            self.record(f'{actor.uid}移动至{actor.pos}')
        elif kind in ('rally_swap','direct_attack'):
            self.mana[team]-=GLOBAL_SKILL_COST
            self.global_skill_used[team]=True
            if kind=='rally_swap':
                if target:
                    self.swap_positions(actor,target)
                    self.record(f'{"AB"[team]}全局技能 调位：{actor.uid} ↔ {target.uid}')
                else:
                    self.move_unit(actor,tuple(map(int,target_id.split(','))))
                    self.record(f'{"AB"[team]}全局技能 调位：{actor.uid} → {actor.pos}')
            else:
                units=self.direct_attack_units(team,target)
                for u in units:
                    u.target_uid=target.uid
                    u.ordered=True
                self.record(f'{"AB"[team]}全局技能 指引攻击：{",".join(u.uid for u in units)} → {target.uid}')
        elif kind in ('chen','purify','swap','redirect'):
            actor.cd=4 if kind=='chen' else 2 if kind in ('purify','redirect') else 1
            if kind=='chen':
                target.team=team
                target.target_uid=None
                target.forced_uid=None
                target.debuffs.pop('taunt',None)
            elif kind=='purify':
                self.heal(target,actor.level)
            elif kind=='swap':
                self.swap_positions(actor,target)
            else:
                for u in self.field(team):
                    if u is not actor and distance(actor.pos,u.pos)==1 and not u.forced_uid:
                        u.target_uid=target.uid
                        u.ordered=True
            self.record(f'{actor.uid}使用{kind} → {target_id}')
        elif kind=='card':
            cid=self.hand[team].pop(int(actor_id))
            cost=self.card_cost(cid,team)
            self.mana[team]-=cost
            self.stats[team]['cards_played']+=1
            self.play_card(cid,target_id,team)
            self.record(f'{"AB"[team]}出牌 {CARDS[cid]["card_name"]["schinese"]}，消耗{cost}法力')
        elif kind=='item':
            cid,paid=self.item_hand[team].pop(int(actor_id))
            self.gold[team]-=0 if paid else ITEMS[cid]['gold_cost']
            item=ITEMS[cid]
            if item['sub_type']!='Consumable':
                self.equip(target,cid)
            elif item['active']=='knowledge':
                self.draw(team,1)
            elif item['active']=='teleport':
                target.pos=self.fountain_positions(team)[0]
                target.hp=target.max_hp
            else:
                self.heal(target,6 if item['active']=='salve' else target.max_hp)
            self.record(f'{"AB"[team]}使用 {item["card_name"]["schinese"]} → {target_id}')
        else:
            cid=next(i for i in actor.equipment.values() if ITEMS[i].get('active')==kind)
            actor.gear_cds[cid]=ITEMS[cid]['cooldown']
            if kind=='blink':
                actor.pos=tuple(map(int,target_id.split(',')))
                actor.moved=True
                actor.first_move=False
            elif kind=='bkb':
                actor.debuffs.clear()
                actor.forced_uid=None
                actor.stunned=False
                actor.buffs['bkb']=True
                self.duels=[pair for pair in self.duels if actor.uid not in pair]
            elif kind=='mek':
                for u in self.field(team):
                    if distance(actor.pos,u.pos)<=1:
                        self.heal(u,2)
            elif kind=='midas':
                target.hp=0
                target.damage_sources={actor.uid}
                target.bounty_override=5
            else:
                self.negative(target,kind)
            self.record(f'{actor.uid}使用 {ITEMS[cid]["card_name"]["schinese"]} → {target_id}')
        self.cleanup()
        self.refresh_targets()
        self.check_victory()
        self.check()

    def play_card(self,cid,target_id,team):
        c=CARDS[cid]
        if c['card_type']=='Creep':
            self.create_unit(team,cid,tuple(map(int,target_id.split(','))))
            return
        index={u.uid:u for u in self.field()}
        target=index.get(target_id)
        friends,foes=self.field(team),self.field(1-team)
        caster=next((u for u in friends if u.hero==c.get('hero_id')),None)
        effect=c['effect']
        if effect in ('orders','pick','juke'):
            a,b=(index[k] for k in target_id.split('|'))
            if effect=='orders':
                a.target_uid=b.uid
                a.ordered=True
            elif effect=='pick':
                self.negative(b,'taunt',a.uid)
            else:
                self.swap_positions(a,b)
        elif effect=='whip':
            self.hurt(target,1)
            target.temporary_attack+=2
        elif effect in ('train','blessing'):
            target.permanent_attack+=2
        elif effect in ('cripple','atrophy'):
            for u in ([target] if effect=='cripple' else [v for v in foes if v.hero]):
                self.negative(u,'attack_down',2)
        elif effect=='blood_draw':
            self.draw(team,sum(u.hero is not None and u.hp<u.max_hp for u in friends))
        elif effect=='cleave':
            target.temporary_cleave+=4
        elif effect=='combat':
            self.force_combat=True
        elif effect=='triumph':
            for u in friends:
                if u.hero:
                    u.permanent_attack+=4
                    u.permanent_armor+=4
                    u.permanent_health+=4
                    u.hp+=4
                    u.permanent_cleave+=4
                    u.permanent_retaliate+=4
                    u.permanent_siege+=4
        elif effect=='heal':
            self.heal(target,2)
        elif effect=='bellow' and (target.team==team or not target.buffs.get('bkb')):
            occupied={u.pos for u in self.field()}|self.blocked_positions()
            choices=[(target.pos[0],col) for col in range(self.columns) if (target.pos[0],col) not in occupied]
            target.pos=self.rng(f'bellow:{team}:{self.stats[team]["actions"]}').choice(choices)
            target.moved=True
        elif effect=='armor':
            target.temporary_armor+=3
        elif effect=='arm':
            for u in friends:
                if not u.hero:
                    u.permanent_attack+=2
                    u.permanent_armor+=1
        elif effect=='restore':
            self.repair(team,8)
        elif effect=='unprepared':
            self.negative(target,'unprepared')
        elif effect=='intimidate' and (target.team==team or not target.buffs.get('bkb')):
            target.pos=self.fountain_positions(target.team)[0]
            target.moved=True
        elif effect=='roar':
            for u in foes:
                if distance(caster.pos,u.pos)==1:
                    self.negative(u,'taunt',caster.uid)
        elif effect=='duel':
            if self.negative(target,'taunt',caster.uid):
                # The voluntary duel lock on the caster is a buff, the opponent's is a debuff.
                caster.forced_uid=target.uid
                caster.buffs['duel']=True
                self.duels.append((caster.uid,target.uid))
        elif effect=='strength':
            caster.buffs['strength']=True
        elif effect=='wolves':
            for _ in range(2):
                self.create_unit(team,64000+caster.level,self.ordered_empty(caster.pos,True)[0],False)
        elif effect=='god':
            for u in friends:
                u.hp=u.max_hp
                u.buffs['immune']=True
        elif effect=='favor':
            target.favor+=1

    def chase(self):
        occupied={u.pos for u in self.field()}|self.blocked_positions()
        intents=defaultdict(list)
        for u in self.field():
            if u.moved or not self.can_act(u) or self.target(u):
                continue
            target=self.aggro_target(u)
            if not target:
                continue
            choices=[p for dr,dc in EIGHT if valid(p:=(u.pos[0]+dr,u.pos[1]+dc),self.columns) and p not in occupied]
            def merit(p):
                legal=(p[0]==target.pos[0] or p[1]==target.pos[1]) and distance(p,target.pos)<=u.reach
                return (not legal,distance(p,target.pos),abs(p[0]-target.pos[0])+abs(p[1]-target.pos[1]),p)
            choices=sorted(choices,key=merit)
            if choices and (not merit(choices[0])[0] or distance(choices[0],target.pos)<distance(u.pos,target.pos)):
                intents[choices[0]].append(u)
        for p,contenders in sorted(intents.items()):
            winner=self.rng(f'chase:{p}').choice(sorted(contenders,key=lambda u:u.uid))
            self.record(f'{winner.uid}仇恨追击 {winner.pos} → {p}')
            winner.pos=p
            winner.moved=True
            winner.first_move=False
        self.refresh_targets()

    def combat(self,chase=True):
        if chase:
            self.chase()
        units=self.field()
        damage=Counter()
        building=Counter()
        sources=defaultdict(set)
        fort_shots=[]
        weaken=[]
        regen={u.uid:self.regeneration(u) for u in units}
        def hit(attacker,v,amount):
            actual=self.damage_amount(v,amount)
            damage[v.uid]+=actual
            if actual:
                sources[v.uid].add(attacker.uid if attacker else 'environment')
            return actual
        for u in units:
            if not self.can_act(u):
                continue
            v,fort=self.target(u),self.building_target(u)
            if v:
                amount=hit(u,v,self.attack(u))
                self.record(f'{u.uid}普攻 {v.uid}：{amount}')
                if amount:
                    hit(v,u,self.retaliate(v))
                    if CARDS[u.card_id].get('effect')=='weaken':
                        weaken.append(v)
                dr,dc=self.attack_direction(u,v)
                sides=((v.pos[0]+dc,v.pos[1]-dr),(v.pos[0]-dc,v.pos[1]+dr))
                for e in units:
                    if e.team!=u.team and e.pos in sides:
                        extra=hit(u,e,self.cleave(u))
                        if extra and CARDS[u.card_id].get('effect')=='weaken':
                            weaken.append(e)
            elif fort:
                building[fort.team]+=self.attack(u)+self.siege(u)
                self.record(f'{u.uid}攻击{fort.uid}：{self.attack(u)+self.siege(u)}')
        for fort in self.forts:
            v=self.fort_target(fort)
            if v:
                actual=hit(None,v,self.fort_power(fort))
                fort_shots.append({'team':fort.team,'target':v.uid,'damage':actual,
                                   'immune':bool(v.buffs.get('immune'))})
                self.record(f'{fort.uid}建筑攻击 {v.uid}：{actual}')
            for e in units:
                if e.team!=fort.team and e.pos[0]==(7 if fort.team==0 else 0):
                    hit(None,e,10)
        for u in units:
            u.hp-=damage[u.uid]
            u.damage_sources=sources[u.uid]
            self.heal(u,regen[u.uid])
        for v in weaken:
            self.negative(v,'attack_down')
        self.cleanup()
        for team,amount in building.items():
            self.damage_fort(team,amount)
        self.check_victory()
        for u in self.field():
            if u.hero:
                u.xp+=1
                u.pending_level=3 if u.xp>=6 else 2 if u.xp>=3 else 1
                if u.pending_level>u.level:
                    self.record(f'{u.uid}经验{u.xp}，下回合升至{u.pending_level}级')
            u.damage_sources.clear()
        self.refresh_targets()
        self.check()
        return fort_shots

    def actions(self,team):
        """AI uses the same complete legal catalog as the player, scored for useful actions."""
        out=[]
        index={u.uid:u for u in self.field()}
        for _,kind,actor_id,target_id in self.legal_actions(team):
            actor,target=index.get(actor_id),index.get(target_id)
            value=0
            if kind=='move':
                p=tuple(map(int,target_id.split(',')))
                value=self.position_score(actor,p)-self.position_score(actor,actor.pos)
                # Advance through a temporarily unattractive square toward the enemy fort.
                foe=self.aggro_target(actor)
                destination=foe.pos if foe else self.forts[1-team].position
                value=max(value,(distance(actor.pos,destination)-distance(p,destination))*.7)
            elif kind=='chen':
                value=5+self.attack(target)+target.hp*.3
            elif kind=='purify':
                value=min(actor.level,target.max_hp-target.hp)*1.5
            elif kind=='redirect':
                value=sum(self.attack(u)*.2 for u in self.field(team) if u is not actor and distance(u.pos,actor.pos)==1 and not u.forced_uid and u.target_uid!=target_id)
            elif kind in ('swap','rally_swap'):
                pos=target.pos if target else tuple(map(int,target_id.split(',')))
                value=self.position_score(actor,pos)-self.position_score(actor,actor.pos)
                if target:
                    value+=self.position_score(target,actor.pos)-self.position_score(target,target.pos)
                if kind=='rally_swap':
                    value-=1
            elif kind=='direct_attack':
                for u in self.direct_attack_units(team,target):
                    old=self.target(u)
                    if (u.pos[0]==target.pos[0] or u.pos[1]==target.pos[1]) and old is not target:
                        damage=self.primary_damage(u,target)
                        current=self.primary_damage(u,old)*(1.5 if old.hero else 1) if old else 0
                        value+=(damage*(1.5 if target.hero else 1)-current)*.5
                        if damage:
                            value+=.35
                value-=.5
            elif kind=='card':
                cid=self.hand[team][int(actor_id)]
                c=CARDS[cid]
                effect=c.get('effect')
                if c['card_type']=='Creep':
                    r,col=map(int,target_id.split(','))
                    value=2+c['attack']*.7+c['hit_points']*.15-distance((r,col),self.forts[1-team].position)*.15
                elif effect in ('train','blessing','armor','cleave','favor'):
                    value=(3 if target.team==team else -3)+(1 if self.target(target) else 0)
                elif effect in ('cripple','unprepared'):
                    value=3 if target.team!=team and not target.buffs.get('bkb') else -3
                elif effect=='heal':
                    value=min(2,target.max_hp-target.hp) if target.team==team else -2
                elif effect in ('arm','triumph','atrophy','god'):
                    value=len(self.field(team))*1.5
                elif effect=='blood_draw':
                    value=sum(h.hero is not None and h.hp<h.max_hp for h in self.field(team))*2
                elif effect=='restore':
                    value=min(8,self.forts[team].max_hp-self.forts[team].hp)*.5 if self.forts[team].stage=='tower' else 0
                elif effect=='wolves':
                    value=5
                elif effect in ('roar','strength','duel'):
                    h=next(u for u in self.field(team) if u.hero==c['hero_id'])
                    value=3 if self.target(h) else 0
                elif effect=='intimidate':
                    value=4 if target.team!=team else 1 if target.hp<3 else 0
                elif effect=='whip':
                    value=1 if target.team==team and target.hp>1 and self.target(target) else 0
                elif effect=='combat':
                    value=0
                elif effect in ('orders','pick'):
                    a,b=(index[k] for k in target_id.split('|'))
                    if effect=='orders':
                        value=1 if a.target_uid!=b.uid and (a.pos[0]==b.pos[0] or a.pos[1]==b.pos[1]) and distance(a.pos,b.pos)<=a.reach else 0
                    else:
                        value=1 if a.hp>b.hp else 0
            elif kind=='item':
                cid,paid=self.item_hand[team][int(actor_id)]
                c=ITEMS[cid]
                if c['sub_type']!='Consumable':
                    old=ITEMS.get(target.equipment.get(c['sub_type']),{})
                    value=(c['attack']-old.get('attack',0))*1.1+(c['armor']-old.get('armor',0))*2+(c['hit_points']-old.get('hit_points',0))*.3
                    value+=2 if c.get('active') and not old.get('active') else 0
                elif c['active'] in ('salve','flask'):
                    value=min(6 if c['active']=='salve' else target.max_hp,target.max_hp-target.hp)*.6
                elif c['active']=='knowledge':
                    value=2 if self.deck[team] else 0
                elif c['active']=='teleport':
                    value=3 if target.hp<target.max_hp/3 else 0
            elif kind in ('hex','silence'):
                value=3 if not target.debuffs.get(kind) and not target.buffs.get('bkb') else 0
            elif kind=='midas':
                value=7
            elif kind=='mek':
                value=sum(min(2,u.max_hp-u.hp) for u in self.field(team) if distance(u.pos,actor.pos)<=1)
            elif kind=='bkb':
                value=3 if actor.debuffs else 0
            elif kind=='blink':
                p=tuple(map(int,target_id.split(',')))
                value=self.position_score(actor,p)-self.position_score(actor,actor.pos)
            # Reforge is a player tool; AI never creates infinite free draw cycles.
            if value>.05:
                out.append((value,kind,actor_id,target_id))
        return out
