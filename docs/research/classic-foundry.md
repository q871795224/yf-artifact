# Artifact Classic 与 Foundry 规则核对

调研日期：2026-11-11。用于设计讨论，不自动成为本作规则。

## Classic：复活与金币

- 英雄阵亡后在泉水完整等待一回合再部署；第二回合死、第三回合缺席、第四回合部署符合这个节奏。装备保留。
- 常规经济没有每轮固定工资；主要通过敌方单位死亡赏金和特定卡牌效果获得金币。
- 默认小兵赏金一金币、英雄五金币；赏金按敌方单位死亡发给另一方，不要求英雄补刀，也不取决于致死方式。因此双方小兵互相打死时，双方都能得到对方小兵的赏金。
- 这些是原版规则，本作的工资、赏金数值和不同召唤物的赏金仍须另定。

资料：

- [Mechanics — Artifact Wiki](https://artifact.fandom.com/wiki/Mechanics)：赏金按敌方单位死亡结算，不依赖死因或击杀来源。
- [How to Play Guide — Artifact Wiki](https://artifact.fandom.com/wiki/How_to_Play_Guide_for_Artifact%3A_The_Dota_Card_Game)：金币与卡牌、装备经济。
- [Artifact — Liquipedia](https://liquipedia.net/artifact/Artifact)：复活等待与装备保留。网页直接访问返回 403，规则内容通过搜索索引核对。

## Foundry 的主要变化

- Foundry 是 Artifact 2.0 Beta 更名后的版本。仍为五英雄、三路，不是单路版。
- Classic 顺序处理三路；Foundry 在同一行动阶段可以选择任意一路行动，各路共用法力。
- Classic 的单路可无限扩展；Foundry 每路每方固定五个位置，主动控制部署位置，减少开局随机。
- 随机攻击箭头改为默认向前，卡牌效果仍可改变攻击方向。
- 英雄与卡牌大幅重做，更强调英雄本身的能力。早期官方规则说明对行动、技能引入法力成本；这与本作已经确定的英雄技能只受 CD 限制不同，不建议直接沿用“所有行动花法力”。
- 护甲从每次受伤都减伤，改成每轮可消耗、回合开始刷新的护甲额度。
- 2020-12-23 更新尝试移除武器／护甲／饰品分类槽，英雄可装备两件不同装备；这比照抄早期 Foundry 的三分类槽更接近其后期版本。
- 新增单人战役、英雄选秀、英雄演示和解题等模式，适合作为个人游玩的参考。
- 商店在 Beta 多次重做；2020 年早期文章中的价格、初始金币和商店升级规则不可当作最终值。例如 2021-03-04 更新又将初始金币从十改为十五。本次不沿用商店具体数值。

官方资料：

- [Artifact Classic and Artifact Foundry，2021-03-04](https://steamcommunity.com/app/583950/allnews/)：版本定位、三路行动、随机性、英雄与模式差异。
- [Deployment Deep Dive，2020-04-13](https://store.steampowered.com/news/posts/?appgroupname=Artifact&appids=583950&enddate=1587420571&feed=steam_community_announcements)：五个固定位置、出兵和部署。
- [Mechanics!，2020-04-20](https://store.steampowered.com/oldnews/?appgroupname=Artifact&appids=583950&feed=steam_community_announcements)：共享法力、行动、箭头和护甲重做。属于 Beta 阶段说明，具体规则须结合后续更新。
- [Foundry 更新记录](https://steamcommunity.com/app/1269260/allnews/)：2020-12-23 装备槽实验、2021-03-04 初始金币及英雄演示和解题工具。

## 本作需要验证的设计问题

- 在单路保留“大量铺场”时，固定位置可以有多排；不必因为屏幕宽度不足就立即增加自动推进、自由移动与寻路。
- 普通兵死亡赏金和召唤物赏金应分开设计；若所有召唤物均给足额赏金，召唤流可能给对方送出过多经济。
- 若满场导致英雄不能复活，而每轮又继续自动出兵，可能出现兵占满英雄返场位置的问题；应先明确部署优先级。
- 塔破后基地是否等到下一轮可受伤，是结构性缓冲；额外金币、抽牌等补偿是独立平衡手段，均未定案。
- 棋盘、工资、补偿和具体卡牌建议必须经用户讨论后才能视为确定。
