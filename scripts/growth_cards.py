"""The agreed red/green Demo catalog, separate from the Classic reference data."""
from collections import Counter
from copy import deepcopy
from simulate_match import CARDS

RELEASE_VERSION = '0.4'
RANGED_CREEP = 64004
TIMBERSAW, DROW = 10022, 10032
TIMBER_CHAIN, GUST = 63007, 63008
CHARGE, MARCH = 62020, 62021
EXPERIMENTS = ('heroes', 'spells', 'combined')
ROSTERS = ((10014, 10017, 10044), (10020, 10069, 10054))
EXPANSION_ROSTERS = ((10014, 10017, DROW), (10020, 10069, TIMBERSAW))
PANELS = {
    TIMBERSAW: ((2, 0, 7), (3, 0, 9), (4, 0, 11)),
    DROW: ((2, 0, 5), (3, 0, 6), (4, 0, 7)),
    10020: ((3, 0, 5), (4, 1, 8), (6, 2, 10)),
    10069: ((3, 0, 5), (4, 0, 7), (6, 1, 8)),
    10054: ((3, 0, 7), (4, 0, 9), (5, 0, 11)),
    10014: ((3, 0, 6), (4, 0, 8), (4, 0, 10)),
    10017: ((1, 0, 5), (2, 0, 7), (4, 0, 9)),
    10044: ((3, 0, 6), (4, 0, 9), (5, 0, 12)),
}
CATALOG = {}
ART_IDS = {10112, 10368, 10252, 10127, 10128, 10256, 10260, 10263, 10014, 10270, 10017, 10402, 10020, 10023, 10410, 10236, 10412, 10033, 10036, 3000, 3001, 3002, 3003, 10044, 3004, 3005, 3006, 10047, 10169, 10297, 10307, 10054, 10311, 10313, 10060, 10064, 10065, 10322, 10069, 10206, 10208, 10211, 10212, 10085, 10213, 10214, 1000, 1001, 10215, 10216, 10344, 1006, 10223, 10352, 10353, 10354, 10355, 10102, 10104, 10425, 10108, 10238, 10111}

def card(cid, name, kind, cost, text, color=None, art=1006, **extra):
    CATALOG[cid] = dict(card_id=cid, card_name={'schinese': name},
        card_text={'schinese': text}, card_type=kind, colors=[color] if color else [],
        mana_cost=cost if kind != 'Item' else 0, gold_cost=cost if kind == 'Item' else 0,
        art_id=art if art in ART_IDS else (10102 if color=="red" else 10104 if color=="green" else 3002), **extra)

# Unit names are working names; their panels and effects follow the approved table.
for i, (name, cost, atk, armor, hp, effect, text, art) in enumerate([
    ('前线新兵',1,1,0,2,'ping1','登场：随机对正四邻一名敌人造成1点物理伤害。',10083),
    ('嗜战斗士',2,2,0,3,'grow_kill','击杀单位后，永久+1攻击。',10092),
    ('披甲步兵',3,2,1,4,'','',10083),
    ('破势战士',4,3,0,3,'weaken','对单位造成伤害后，使其永久-1攻击。',10102),
    ('重装卫士',5,3,2,7,'','',10083),
    ('先锋掷斧手',6,6,0,6,'ping2','登场：随机对正四邻两名不同敌人各造成2点物理伤害。',10092),
    ('萌芽守卫',1,0,0,2,'death_buff','死亡：左右相邻友军永久+1攻击、+1生命。',10099),
    ('共生幼苗',2,1,0,2,'clone','登场：召唤一个复制体，继承强化；复制体不触发登场。',10104),
    ('林间向导',3,2,0,6,'swap','主动，CD1：与八邻一名友军交换位置。',10104),
    ('复苏守卫',4,3,0,6,'regen','恢复2。',10104),
    ('战场引路人',5,3,0,10,'redirect','主动，CD2，距离2：自身八邻友军将普通箭头转向选中的敌人。',10104),
    ('古林修复者',6,4,0,10,'repair','登场、死亡：己方防御塔恢复4生命。',10104),
]):
    card(61001+i,name,'Creep',cost,text or '无额外能力。','red' if i<6 else 'green',art,
         attack=atk, armor=armor, hit_points=hp, effect=effect)

SPELLS = [
 ('新命令',1,'orders','选择一名友军，再选择敌人，改变其普通攻击目标。',10313),
 ('鞭笞',1,'whip','一名单位受到1点物理伤害，本轮+2攻击。',10318),
 ('惹是生非',2,'pick','选择一名友方英雄，使其正四邻一名敌人本轮嘲讽锁定到该英雄。',10315),
 ('战斗训练',2,'train','一名英雄永久+2攻击。',10322),
 ('浴血奋战',3,'blood_draw','每有一名受伤的在场友方英雄，抽一张牌。',10307),
 ('一扫而空',4,'cleave','一名友方英雄本轮+4分裂。',10344),
 ('致残重击',4,'cripple','一名英雄永久-2攻击。',10328),
 ('废话少说',5,'combat','立即结束双方行动阶段，处理追击并交战。',10326),
 ('胜利时刻',8,'triumph','所有在场友方英雄永久+4攻击、护甲、生命、分裂、反伤和攻城。',10425),
 ('绕树',1,'juke','一名友军与其左右相邻的一名友军交换位置。',10368),
 ('治疗',1,'heal','一名单位恢复2生命。',10369),
 ('呵斥',2,'bellow','一名小兵移动至同行另一个随机空格。',10370),
 ('铁树枝干守护',2,'armor','一名单位获得3护甲，持续至本轮交战结束。',10371),
 ('魔霭福泽',3,'blessing','一名单位永久+2攻击。',10372),
 ('武装叛军',4,'arm','所有在场友方小兵永久+2攻击、+1护甲。',10311),
 ('妙手回春',4,'restore','己方防御塔恢复8生命。',10373),
 ('攻其不备',4,'unprepared','眩晕一名英雄，直到其装备一件物品。',10374),
 ('恫吓',5,'intimidate','将一名单位移动至其所属阵营的泉水，不治疗。',10375),
 ('衰退诅咒',6,'atrophy','所有在场敌方英雄永久-2攻击。',10376),
]
for i,(name,cost,effect,text,art) in enumerate(SPELLS):
    # An absent reference image uses an available hero portrait, never a broken URL.
    card(62001+i,name,'Spell',cost,text,'red' if i<9 else 'green',art if art in CARDS else (10020 if i<9 else 10044),effect=effect)

card(CHARGE,'破阵冲锋','Spell',2,'一名友方英雄沿正交直线移动1或2格，本轮+2攻击。','red',10297,effect='charge')
card(MARCH,'协同行军','Spell',3,'选定九格区域，至多三名友军各向敌方泉水前进1或2格。','green',10311,effect='march')

SIGNATURES = {TIMBERSAW:TIMBER_CHAIN,DROW:GUST,10020:63001,10069:63002,10054:63003,10014:63004,10017:63005,10044:63006}
for hero,name,cost,level,effect,text in [
 (10020,'狂战士之吼',4,1,'roar','斧王八邻敌人本轮嘲讽锁定到斧王。未移动者在交战前追击；斧王不增加攻击次数。'),
 (10069,'决斗',2,3,'duel','选择军团正四邻敌方英雄，本轮双方相互锁定；一方死亡后存活者永久+1攻击。'),
 (10054,'神之力量',4,2,'strength','本轮斯温自身攻击翻倍，重复使用不再翻倍；固定分裂不变。'),
 (10014,'野蛮灵狼',2,1,'wolves','按狼人等级花费2/3/4法力，召唤两只1/3、2/3或3/3灵狼，无成长。'),
 (10017,'上帝之手',7,3,'god','所有在场友军回满生命，本轮伤害免疫。'),
 (10044,'全视者恩泽',4,2,'favor','永久赋予一名绿色英雄：正四邻其他友军获得2恢复。'),
]:
    card(SIGNATURES[hero],name,'Spell',cost,text,CARDS[hero]['colors'][0],hero,
         hero_id=hero, unlock_level=level, effect=effect)
card(TIMBER_CHAIN,'伐木锯链','Spell',2,'移动至距离恰为2的空格或可被击杀的敌方格。中间格和落点敌人受2魔法伤害。','red',10020,hero_id=TIMBERSAW,unlock_level=2,effect='timber_chain')
card(GUST,'狂风','Spell',3,'以数箭齐发的范围沉默敌人至回合结束，并沿施放方向推退1格。','green',10044,hero_id=DROW,unlock_level=2,effect='gust')
GENERATED_SIGNATURES = {TIMBERSAW:TIMBER_CHAIN,DROW:GUST}

for level in (1,2,3):
    card(64000+level,f'{level}级灵狼','Creep',0,'召出后不随狼人升级。','green',10112,
         attack=level,armor=0,hit_points=3,effect='')
card(RANGED_CREEP,'远程小兵','Creep',0,'正交射程两格，可隔着友军射击。',
     attack=1,armor=0,hit_points=3)

ITEMS = {}
def item(cid,name,price,slot,text,art,atk=0,armor=0,hp=0,active=None,cd=0):
    card(cid,name,'Item',price,text,art=art,sub_type=slot,attack=atk,armor=armor,hit_points=hp,active=active,cooldown=cd)
    ITEMS[cid]=CATALOG[cid]
for i,(name,art,slot,price,atk,armor,hp) in enumerate([
 ('短剑',3002,'Weapon',3,2,0,0),('阔剑',10215,'Weapon',7,4,0,0),('大剑',10238,'Weapon',15,8,0,0),
 ('皮甲',3001,'Armor',3,0,1,0),('锁子甲',10214,'Armor',7,0,2,0),('板甲',10237,'Armor',15,0,4,0),
 ('旅者斗篷',3000,'Accessory',3,0,0,4),('毛皮大衣',10213,'Accessory',7,0,0,8),('生命斗篷',10236,'Accessory',15,0,0,16),
]): item(65001+i,name,price,slot,f'+{atk}攻击。' if atk else f'+{armor}护甲。' if armor else f'+{hp}生命。',art,atk,armor,hp)
for args in [
 (65010,'跳刀',7,'Weapon','主动CD2：瞬移到曼哈顿距离3内空格。',10206,0,0,0,'blink',2),
 (65011,'刃甲',7,'Armor','+1护甲、+2反伤；普攻实际掉血时触发。',10208,0,1,0,None,0),
 (65012,'黑皇杖',10,'Armor','主动CD3：驱散自身全部负面状态，本轮免疫魔法伤害与新负面状态。',10256,0,0,0,'bkb',3),
 (65013,'梅肯斯姆',8,'Accessory','自身和八邻友军+1恢复；主动CD2：这些单位恢复2生命。',10236,0,0,0,'mek',2),
 (65014,'点金手',7,'Accessory','主动CD3：消灭八邻敌方非英雄单位，固定获得5金，替代击杀赏金。',3005,0,0,0,'midas',3),
 (65015,'邪恶镰刀',15,'Weapon','主动CD2：八邻敌人本轮妖术，禁攻击、移动、技能和装备主动，保留护甲生命与装备被动。',10263,0,0,0,'hex',2),
 (65016,'紫苑',10,'Weapon','主动CD2：沉默八邻敌人，本轮不能使用技能，装备仍可用。',10215,0,0,0,'silence',2),
 (65017,'圣剑',15,'Weapon','+10攻击。死亡后强制转移给击杀英雄；非英雄击杀归对方物品手牌。多人共同致死随机一个。',10238,10,0,0,None,0),
 (65018,'魔龙枪',6,'Weapon','+1攻击，远程英雄+1射程。',10252,1,0,0,None,0),
 (65019,'治疗药膏',3,'Consumable','一名友军恢复6生命。',3003,0,0,0,'salve',0),
 (65020,'回春药水',4,'Consumable','一名友军回满生命。',3004,0,0,0,'flask',0),
 (65021,'知识秘典',5,'Consumable','抽一张普通牌。',3005,0,0,0,'knowledge',0),
 (65022,'回城卷轴',3,'Consumable','立即将友方英雄送回泉水并回满生命；不重置移动、冷却或首次移动。',3006,0,0,0,'teleport',0),
]: item(*args)

# Custom IDs cannot alter an original card's rules in historical experiments.
CARDS.update(CATALOG)

def default_deck(team=0, new_spells=False):
    color='green' if team==0 else 'red'
    ordinary=[cid for cid,c in CATALOG.items() if c['card_type'] in ('Creep','Spell') and c['colors']==[color] and not c.get('hero_id') and cid<63000]
    # Two of every unit, then nine simple spells.
    units=[cid for cid in ordinary if CATALOG[cid]['card_type']=='Creep']
    spells=[cid for cid in ordinary if CATALOG[cid]['card_type']=='Spell']
    ordinary=units*2+spells[:9]
    if new_spells:
        # Replace two copies within the existing 21-card ordinary deck.
        for cid in ((62010,62012) if team==0 else (62001,62003)):
            ordinary[ordinary.index(cid)]=MARCH if team==0 else CHARGE
    return {'ordinary':ordinary, 'items':[65001,65004,65007,65010,65011,65012,65013,65014,65015,65018]}

def validate_deck(config,team=0):
    config=deepcopy(default_deck(team) if config is None else config)
    if not isinstance(config,dict) or set(config)!={'ordinary','items'}:
        raise ValueError('构筑必须包含普通卡与物品两个牌堆。')
    color='green' if team==0 else 'red'
    for key,size in (('ordinary',21),('items',10)):
        cards=config[key]
        if not isinstance(cards,list) or len(cards)!=size or any(type(cid) is not int for cid in cards):
            raise ValueError(f'{"普通自选牌" if key=="ordinary" else "物品牌"}必须为{size}张。')
        if any(n>3 for n in Counter(cards).values()):
            raise ValueError('同名卡最多3张。')
        for cid in cards:
            c=CATALOG.get(cid)
            if not c or (key=='items' and cid not in ITEMS) or (key=='ordinary' and (cid>=63000 or color not in c['colors'])):
                raise ValueError('构筑包含不属于当前阵营或不可构筑的卡牌。')
    return config

def opponent_presets(new_spells=False):
    templates=(
        ('pressure','前线压迫','低费单位持续补线，先锋掷斧手处理邻近守军。',
         ((61001,3),(61002,3),(61003,2),(61004,2),(61005,1),(61006,3),
          (62002,1),(62004,2),(62006,2),(62009,2)),
         (65001,65004,65007,65010,65011,65014,65018,65019,65021,65002),
         (62002,62004)),
        ('equipment','装备成长','用重装卫士站稳战场，把金币投入高阶武器与护甲。',
         ((61001,1),(61002,2),(61003,2),(61004,2),(61005,3),(61006,2),
          (62004,3),(62007,2),(62009,2),(62008,1),(62006,1)),
         (65002,65003,65005,65006,65008,65009,65011,65012,65014,65017),
         (62007,62008)),
    )
    presets=[]
    for key,name,description,cards,items,replacements in templates:
        ordinary=[cid for cid,count in cards for _ in range(count)]
        if new_spells:
            for cid in replacements:
                ordinary[ordinary.index(cid)]=CHARGE
        deck=validate_deck({'ordinary':ordinary,'items':list(items)},1)
        presets.append({'id':key,'name':name,'description':description,'deck':deck})
    return presets

def full_deck(config,team,roster=None):
    if roster is None:
        roster=ROSTERS[team]
    return config['ordinary']+[SIGNATURES[h] for h in roster for _ in range(2 if h in GENERATED_SIGNATURES else 3)]

def catalog_view():
    heroes=[{k:deepcopy(v) for k,v in CARDS[h].items() if k in ('card_id','card_name','card_text','card_type','attack','armor','hit_points','colors')} for h in PANELS]
    hero_art={TIMBERSAW:(10020,'主动CD2：自身八邻敌人各受1魔法伤害。'),DROW:(10044,'主动CD3：选正交距离1或2的中心，对中心、前方与两侧的敌人各造成3物理伤害。')}
    for h in heroes:
        if h['card_id'] in hero_art:
            h['art_id'],description=hero_art[h['card_id']]
            h['card_text']['schinese']=description
            h['custom_art']=True
        if h['card_id']==10044:
            h['card_name']['schinese']='全能骑士'
    illustrated={CHARGE,MARCH,TIMBER_CHAIN,GUST,61007,62013,65011}
    cards=[dict(c,custom_art=True) if cid in illustrated else c for cid,c in CATALOG.items()]
    return {'release':RELEASE_VERSION,'cards':cards+heroes,'rosters':ROSTERS,
            'panels':PANELS,'signatures':SIGNATURES,'defaultDeck':default_deck(),
            'expansionRosters':EXPANSION_ROSTERS,'expansionDeck':default_deck(new_spells=True),
            'redDeck':default_deck(1),'expansionRedDeck':default_deck(1,new_spells=True),
            'opponentPresets':opponent_presets(),'expansionOpponentPresets':opponent_presets(new_spells=True)}
