# 文档导航

更新日期：2026-11-18，当前版本为 **V0.4 成长 Demo**，V0.2／V0.3 保留历史发布归档。先看当前规格，再按需要回查讨论与实验；早期文件中的“当前”“待定”“下一步”描述的是写作时点。

## 当前入口

| 想了解什么 | 文档 |
| --- | --- |
| 当前源码怎么玩，哪些只是原型数值 | [V0.4 成长 Demo 实现](design/growth-implementation.md) |
| 三级成长、红绿 Demo、英雄面板与专属卡讨论沿革 | [成长 Demo：结论、候选与未定项](design/growth-demo.md) |
| 第一期 6 人名单、第二期备选、强势期与关键字原则 | [第一期英雄对齐结论](design/hero-roster-alignment.md)（2026-11-18 已对齐） |
| 这轮改什么、以后再改什么 | [路线图](design/roadmap.md) |
| 为什么这样设计，哪些方案被替代，哪些还没定 | [决策记录](design/decision-log.md) |
| 遇到的问题、处理办法、启动／发布与排查步骤 | [开发复盘与运维](development/lessons-and-operations.md) |
| V0.4 测过什么 | [发布验证](releases/v0.4.md) |
| V0.3 测过什么 | [历史发布验证](releases/v0.3.md)、[V0.3 规则现状](design/current-rules.md) |
| V0.2 测过什么、结果与局限 | [V0.2 验证归档](releases/v0.2.md) |
| 版本区别与标签 | [更新记录](../CHANGELOG.md) |
| 本地／在线试玩与界面操作 | [游戏说明](../prototype/README.md) |
| 本地调特效、参数预设与后台服务 | [特效工作台](../effects-lab/README.md) |

阅读约定：**已确认方向**记录用户接受的玩法；**原型基线**记录当前代码采用的可调整数值；**待讨论**没有自动升级为定案。若代码、当前规格和旧记录不一致，应明确标出差异再处理，不用历史草案覆盖已发布规则。

## 设计沿革与证据

下列文档保留原来的阶段背景，不重新改写实验结果。除 V0.2 验证归档外，早期对照不是五列战场的平衡结论；英雄早期实验还使用过纯眩晕沟壑、白板英雄或测试法术。

| 阶段 | 记录与用途 |
| --- | --- |
| 最初讨论 | [初步想法](design/initial-ideas.md)、[战场草案](design/combat-draft.md)、[英雄草案](design/heroes-draft.md) |
| 白板推演 | [推演方法](design/paper-simulation.md)、[开局 01](design/simulations/opening-01.md)、[开局 02](design/simulations/opening-02.md)、[移动场景](design/simulations/movement-cases.md) |
| 英雄与索敌 | [英雄批量样本](design/simulations/hero-batch-01/README.md)、[随机箭头／自动索敌对照](design/simulations/hero-batch-02/README.md) |
| 建筑与超时 | [完整对局实验](design/simulations/match-batch-01/README.md)、[超时与保护转火复查](design/simulations/match-batch-01/timeout-review.md) |
| 内容与 AI | [扩池／推进策略对照](design/simulations/match-batch-02/README.md)、[金币供给诊断](design/simulations/item-economy-01/README.md) |
| 双经济终端 | [终端对照](design/simulations/finisher-batch-01/README.md)；区分 24 轮截止与同局续跑 48 轮 |
| 卡池定义 | [首批池](design/first-card-pool.md)、[扩展池](design/expanded-card-pool.md)、[终端适配](design/finisher-card-pool.md)，均附结构化 JSON |
| 原作研究 | [Classic 与 Foundry](research/classic-foundry.md)、[Classic 商店](research/classic-shop.md)，不自动成为本作机制 |

## 本地资料与代码

- [Classic 数据参考库](../references/artifact-classic/README.md)：2018 数值快照与独立保存的 2021 客户端文本。
- [原作图片](../references/artifact-classic/assets/README.md)：原始图片与压缩 WebP 副本。
- [成长版行动适配器](../scripts/growth_playable.py)与[基础适配器](../scripts/playable_match.py)：当前成长玩法与共用的行动、回放和公开状态。
- [特效库](../prototype/effects.js)与[对局适配器](../prototype/game-effects.js)：工作台／正式游戏共用视觉实现，后者映射真实行动与状态变化。

新增决策写入决策记录，当前行为改变时同步规则现状与更新记录；发布验证结果写入对应版本归档。临时日志和截图留在忽略的 `output/`，重要结论应提炼到已提交的文档里。
