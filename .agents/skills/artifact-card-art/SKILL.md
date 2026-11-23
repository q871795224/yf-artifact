---
name: artifact-card-art
description: 为 yf-artifact 选择和组织卡图参考、编写分类提示词、用 Migoo 批量生图或返工，并查找已有图与任务。适用于英雄、装备、普通单位、野怪、法术、英雄技能和建筑卡图；不自动改游戏规则或发布站点。
---

# Artifact 卡图生图

先明确本次画的是哪一类、是原版对象还是原创单位、要新图还是改已有图，再按下面的分类读取。项目当前偏好为 **Dota 身份参考 + Artifact Classic 客户端无框原画作画法参考**，默认请求 Migoo `gpt-image-26-flare`、1K、9:16、满版纯插画；用户本次明确选择优先。

## 新会话先找已有资源

从仓库根目录执行命令。先读[分类索引](../../../assets/art-library/README.md)，按名称、批次或任务号查询 [catalog.json](../../../assets/art-library/catalog.json)，再看对应批次的 `briefs.json` 或 `prompt.txt` / `notes.txt`。参考图、已下载候选、仅有任务号和未提交备稿分开记录。

- [参考图目录与旧路径映射](../../../references/card-art/README.md)：复制归档了已用参考，原件仍保留。旧提示词里的 `output/` 路径可通过参考索引定位归档副本。
- [项目批量提交器](../../../scripts/migoo-submit-batch.md)：支持限流、续跑、复用 media ID、`source_task` 返工；不下载或目视验收生成结果。
- [会话经验依据](references/evidence.md)：区分用户已认可的方向、失败实验和仍待看图的版本。

## 按类别读取

| 本次任务 | 读取 | 主要决策 |
| --- | --- | --- |
| Dota 原版英雄 | [英雄](references/heroes.md) | 锁定身份、种族、装备，重画动作、镜头和场景 |
| Dota 原版装备、法杖等返工 | [装备](references/equipment.md) | 锁定物件轮廓和构件关系，改变摆放与光线；返工只改用户指出的部位 |
| 普通小兵、居民、漫画配角 | [普通单位与野怪](references/units-and-neutrals.md) | 从 Dota 已有族群取材，区分出处事实与原创岗位 |
| 野怪家族／成员 | [普通单位与野怪](references/units-and-neutrals.md#野怪家族与成员) | 用可靠种属参考，家族共享特征，成员拉开体型与动作 |
| 原创法术、已有单位出场 | [法术与英雄技能](references/spells-and-skills.md) | 作用点、方向、受力反应优先，可局部入画 |
| Dota 英雄技能／终极技能 | [法术与英雄技能](references/spells-and-skills.md#英雄技能) | 先核对官方能力，再安排施法者、目标与空间关系 |
| 塔、基地、泉水 | [提示词结构](references/prompt-patterns.md#建筑) | 阵营材质与形体清楚，镜头与环境分别设计 |

需要整批拉开差异、搭参考顺序或起草提示词时，再读[提示词结构与批次差异](references/prompt-patterns.md)。

## 执行边界

生图、重绘和 `task reply` 都会消耗额度。执行 Migoo 时遵循当前机器的 `migoo-imagegen` skill，通过 `yf-migoo` 查询实时模型、账户与 `policy`；本 skill 不延长暂停日期，不充值，不把历史余额、单价或旧会话授权当作本次授权。

用户已说明数量、模型或“你来选”时直接在已授权范围内做，不反复询问是否提交。新方向是否先做样张按实际任务判断；已明确要求一批 10/20 张时不自行追加逐张批准关卡。当前项目常用交付方式是**只提交并汇报，由用户在 Migoo 看图**；只有用户要求本地审阅／下载／接入时才做相应后续。

提交、额度暂停、并发冲突、返工和落盘细节见[操作与归档](references/operations.md)。提交完成、平台完成、本地下载、用户认可和接入游戏是不同状态，汇报必须对应已有证据。
