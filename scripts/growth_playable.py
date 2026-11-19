"""Growth Demo presentation adapter, sharing turn/replay transport with V0.3."""
from copy import deepcopy
from growth_cards import RELEASE_VERSION, PANELS, ITEMS
from simulate_match import CARDS
from growth_match import GLOBAL_SKILLS, GLOBAL_SKILL_COST, GrowthMatch
from playable_match import PlaySession, action_view


class GrowthSession(PlaySession):
    def __init__(self,seed=13,deck_config=None):
        self.seed=seed
        self.game=GrowthMatch(seed,deck_config)
        self.version=0
        self.phase='action'
        self.side=0
        self.passes=0
        self.log=[]
        self.history=[]
        self.last_opponent=None
        self.commands=[]
        self._known_units={}
        self.last_label='第1回合开始'
        self._begin_round()

    def _describe(self,action,team):
        _,kind,actor,target=action
        prefix='我方' if team==0 else '敌方'
        if kind=='reforge':
            return prefix+'重铸普通牌'
        skill,name=GLOBAL_SKILLS[team]
        if kind==skill:
            return prefix+'使用'+name
        if kind in ('card','item','move'):
            return super()._describe(action,team)
        names={'chen':'劝化','purify':'洗礼','swap':'换位','redirect':'引导箭头',
               'blink':'跳刀','bkb':'黑皇杖','mek':'梅肯斯姆','midas':'点金手','hex':'邪恶镰刀','silence':'紫苑'}
        unit=next(u for u in self.game.field(team) if u.uid==actor)
        return prefix+unit.name+'使用'+names[kind]

    def _combat(self,frames):
        before={u.uid:u.pos for u in self.game.field()}
        self.game.chase()
        if any(before.get(u.uid)!=u.pos for u in self.game.field()):
            frames.append(self._frame('仇恨追击完成 · 准备交战',phase='chase'))
        combat=self._frame('双方行动结束 · 开始交战',phase='combat')
        frames.append(combat)
        combat['fortShots']=self.game.combat(chase=False)
        self._drain_events()
        self.phase='finished' if self.game.finished else 'round_end'
        self.last_label='交战结束 · 查看损伤、阵亡与经验'
        frames.append(self._frame(self.last_label))

    def _catalog(self):
        if self.phase!='action' or self.side!=0 or self.game.finished:
            return []
        return [(action_view(self.game,a,self.version),a) for a in self.game.legal_actions(0)]

    def _unit_view(self,u):
        v=super()._unit_view(u)
        for e in v['equipment']:
            e['cooldown']=u.gear_cds.get(e['id'],0) if ITEMS[e['id']].get('active') else None
            e['active']=ITEMS[e['id']].get('active')
        aggro=self.game.aggro_target(u) if u.pos else None
        if aggro:
            dr,dc=self.game.attack_direction(u,aggro)
            v['target']=aggro.uid
            v['arrow']={(-1,0):'↑',(1,0):'↓',(0,-1):'←',(0,1):'→',(-1,-1):'↖',(-1,1):'↗',(1,-1):'↙',(1,1):'↘'}[(dr,dc)]
        v['canAttack']=bool(self.game.target(u) or self.game.building_target(u)) if u.pos else False
        v.update(baseAttack=u.panel[0],level=u.level if u.hero else None,xp=u.xp if u.hero else None,
                 pendingLevel=u.pending_level if u.hero else None,
                 panels=PANELS.get(u.hero),debuffs=deepcopy(u.debuffs),buffs=deepcopy(u.buffs),
                 forcedTarget=u.forced_uid,retaliate=self.game.retaliate(u))
        v['skillKind']='chen' if u.hero==10017 else 'purify' if u.hero==10044 else {'swap':'swap','redirect':'redirect'}.get(CARDS[u.card_id].get('effect'))
        return v

    def _frame(self,*args,**kwargs):
        v=super()._frame(*args,**kwargs)
        v.update(release=RELEASE_VERSION,maxMana=self.game.max_mana)
        for view,fort in zip(v['forts'],self.game.forts):
            view['reach']=self.game.fort_reach(fort)
        return v

    def snapshot(self):
        v=super().snapshot()
        kind,name=GLOBAL_SKILLS[0]
        v['globalSkill']={'kind':kind,'name':name,'cost':GLOBAL_SKILL_COST,'used':self.game.global_skill_used[0]}
        v['cardCosts']={cid:self.game.card_cost(cid,0) for cid in self.game.hand[0]}
        return v

    def export(self):
        v=super().export()
        v.update(release=RELEASE_VERSION,deck_config=deepcopy(self.game.deck_config[0]))
        return v
