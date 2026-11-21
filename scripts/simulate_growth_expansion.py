"""Compare the confirmed Growth Demo additions on matched seeds."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from itertools import product
import json
from math import ceil
from pathlib import Path
from statistics import median

from growth_cards import CHARGE, GUST, ITEMS, MARCH, TIMBER_CHAIN
from growth_match import GrowthMatch

GROUPS = (None, 'heroes', 'spells', 'combined')
CARD_IDS = (CHARGE, MARCH, TIMBER_CHAIN, GUST)


def simulate(job, match_factory=None):
    experiment,seed,limit=job
    game=(match_factory or GrowthMatch)(seed,trace=False,experiment=experiment)
    for turn in range(1,limit+1):
        game.round=turn
        game.start_round()
        game.auto_move()
        game.reveal()
        game.check()
        team,passes=(turn-1)%2,0
        for _ in range(250):
            choices=game.actions(team)
            if choices:
                game.take_action(max(choices,key=lambda a:(round(a[0],8),a[1],a[2],a[3])),team)
                passes=0
            else:
                passes+=1
            if passes==2 or game.force_combat or game.finished:
                break
            team=1-team
        else:
            raise RuntimeError(f'Action phase exceeded its guard: {experiment}, seed {seed}, round {turn}')
        if not game.finished:
            game.combat()
        if game.finished:
            break
        if turn<limit:
            for side in (0,1):
                if len(game.item_hand[side])<2:
                    offers=game.shop_affordable(side)
                    if offers:
                        slot=max(offers,key=lambda slot:(ITEMS[offers[slot]]['gold_cost'],slot==1))
                        game.shop_buy(side,slot)
    return {'group':experiment or 'baseline','seed':seed,'round':game.round,
            'outcome':('green' if game.winner==0 else 'red') if game.winner is not None
                      else 'draw' if game.finished else 'unfinished',
            'first_tower_hit':game.first_tower_hit,'tower_hp':[f.hp for f in game.forts],
            'stats':[dict(s) for s in game.stats]}


def summarize(rows,limit):
    finished=sorted(r['round'] for r in rows if r['outcome']!='unfinished')
    outcomes=Counter(r['outcome'] for r in rows)
    first_hits=[r['first_tower_hit'] for r in rows if r['first_tower_hit'] is not None]
    stats=sum((Counter(s) for r in rows for s in r['stats']),Counter())
    def percentile(fraction):
        rank=ceil(len(rows)*fraction)
        return finished[rank-1] if rank<=len(finished) else None
    closeout=[r['round']-r['first_tower_hit'] for r in rows
              if r['outcome']!='unfinished' and r['first_tower_hit'] is not None]
    return {'games':len(rows),'cutoff':limit,
            'finished_by':{n:sum(r<=n for r in finished) for n in (9,15,20,limit)},
            'finished_in_8_to_9':sum(8<=r<=9 for r in finished),
            'finished_before_8':sum(r<8 for r in finished),
            'unfinished':outcomes['unfinished'],'outcomes':dict(outcomes),
            'finish_percentiles':{n:percentile(n/100) for n in (10,50,90)},
            'median_first_tower_hit_observed':median(first_hits) if first_hits else None,
            'median_rounds_from_hit_to_finish':median(closeout) if closeout else None,
            'no_tower_hit':len(rows)-len(first_hits),
            'tower_damage_by_team':[sum(r['stats'][i].get('building_damage',0) for r in rows) for i in (0,1)],
            'new_cards_used':{cid:stats[f'card_used_{cid}'] for cid in CARD_IDS},
            'new_skills_used':{name:stats[f'skill_{name}'] for name in ('whirl','multishot')}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds',type=int,default=24)
    parser.add_argument('--rounds',type=int,default=48)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--output',type=Path,default=Path('output/growth-expansion/results.json'))
    args=parser.parse_args()
    if args.seeds<1 or args.rounds<20 or args.workers<1:
        parser.error('需要至少一个种子、20 回合和一个工作进程。')
    jobs=product(GROUPS,range(1,args.seeds+1),(args.rounds,))
    with ProcessPoolExecutor(args.workers) as workers:
        rows=list(workers.map(simulate,jobs))
    summaries={group or 'baseline':summarize([r for r in rows if r['group']==(group or 'baseline')],args.rounds)
               for group in GROUPS}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'summary':summaries,'matches':rows},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summaries,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
