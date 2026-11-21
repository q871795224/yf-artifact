"""Measure two versus four ordinary direct AOE cards per Growth Demo deck."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from itertools import product
import json
from pathlib import Path

from growth_match import GrowthMatch, parse_pos, pos_text
from simulate_growth_expansion import simulate, summarize
from simulate_match import CARDS

PROBES = (62991, 62992)
COST, DAMAGE = 5, 4
# The first two replacements define the matched 2-copy control.
REPLACEMENTS = ((62011,62017,62013,62014), (62002,62005,62004,62007))


class AOEMatch(GrowthMatch):
    def __init__(self, seed, *, copies, **kwargs):
        super().__init__(seed, **kwargs)
        for team,cid in enumerate(PROBES):
            CARDS[cid]={'card_id':cid,'card_name':{'schinese':'实验十字范围伤害'},
                        'card_type':'Spell','colors':['red' if team else 'green'],
                        'mana_cost':COST,'effect':'aoe_probe'}
            replaced=set(REPLACEMENTS[team][:copies])
            # The normal opening draw and shuffle have already run. Slot-for-slot
            # substitution preserves the matched seed's position for every card.
            found=0
            for pile in (self.hand[team],self.deck[team]):
                for i,original in enumerate(pile):
                    if original in replaced:
                        pile[i]=cid
                        found+=1
            if found!=copies:
                raise ValueError(f'Expected {copies} replacements for team {team}, got {found}')

    def probe_targets(self,team):
        positions={}
        for u in self.field(1-team):
            row,col=u.pos
            for p in ((row,col),(row-1,col),(row+1,col),(row,col-1),(row,col+1)):
                if 0<=p[0]<8 and 0<=p[1]<self.columns:
                    positions.setdefault(p,[]).append(u)
        return positions

    def card_targets(self,cid,team):
        if cid!=PROBES[team]:
            return super().card_targets(cid,team)
        return [pos_text(p) for p in self.probe_targets(team)] if any(u.hero for u in self.field(team)) else []

    def actions(self,team):
        choices=super().actions(team)
        indices=[i for i,cid in enumerate(self.hand[team]) if cid==PROBES[team]]
        if not indices or self.mana[team]<COST or not any(u.hero for u in self.field(team)):
            return choices
        for pos,targets in self.probe_targets(team).items():
            value=self.area_value(targets,DAMAGE,'magic')-2
            if value>.05:
                for index in indices:
                    choices.append((value,'card',str(index),pos_text(pos)))
        return choices

    def play_card(self,cid,target_id,team):
        if cid!=PROBES[team]:
            return super().play_card(cid,target_id,team)
        center=parse_pos(target_id)
        targets=self.probe_targets(team)[center]
        stats=self.stats[team]
        stats['aoe_casts']+=1
        for target in targets:
            damage=self.hurt(target,DAMAGE,kind='magic')
            stats['aoe_damage']+=damage
            if damage and target.hp<=0:
                stats['aoe_kills']+=1
                for label,side in (('own',team),('enemy',1-team)):
                    r,c=self.forts[side].position
                    if abs(target.pos[0]-r)+abs(target.pos[1]-c)<=2:
                        stats[f'aoe_kills_near_{label}_tower']+=1


def run(job):
    copies,seed,limit=job
    result=simulate(('combined',seed,limit),match_factory=partial(AOEMatch,copies=copies))
    result['group']=f'{copies}-aoe'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds',type=int,default=64)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--output',type=Path,default=Path('output/growth-expansion/aoe-density.json'))
    args=parser.parse_args()
    if args.seeds<1 or args.workers<1:
        parser.error('种子数和进程数必须为正。')
    with ProcessPoolExecutor(args.workers) as workers:
        rows=list(workers.map(run,product((2,4),range(1,args.seeds+1),(48,))))
    summary={}
    for copies in (2,4):
        group=f'{copies}-aoe'
        matches=[r for r in rows if r['group']==group]
        summary[group]=summarize(matches,48)
        metrics=('aoe_casts','aoe_damage','aoe_kills','aoe_kills_near_enemy_tower','aoe_kills_near_own_tower')
        summary[group]['aoe_by_team']=[{k:sum(r['stats'][side].get(k,0) for r in matches) for k in metrics}
                                      for side in (0,1)]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'replacements':REPLACEMENTS,'summary':summary,'matches':rows},
                                      ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
