# 卡图资源分类索引

保留原图、原目录和原任务记录，通过分类索引归纳；条目包含备稿、修订和旧版本，不等同于独立卡牌数。本次整理不生成新图片，也不把候选图自动接入游戏。

- [项目生图 skill](../../.agents/skills/artifact-card-art/SKILL.md)：按类别选参考、写提示词与返工。
- [资源明细](catalog.json)：每个条目的任务号、提示词、参考图、图片可用状态和接入记录。
- [参考图归档](../../references/card-art/README.md)：已使用参考图的可移植副本与旧路径映射。
- [Migoo 原批次索引](../migoo/README.md)：既有预览、审阅页与提示词。

| 类别 | 批次 | 条目 | 本地图片 | 仅任务号 | 仅备稿 |
| --- | ---: | ---: | ---: | ---: | ---: |
| [原版英雄](categories/heroes.md) | 3 | 92 | 12 | 80 | 0 |
| [原版装备与返工](categories/equipment.md) | 5 | 73 | 20 | 53 | 0 |
| [普通单位与漫画配角](categories/units.md) | 12 | 203 | 203 | 0 | 0 |
| [野怪、家族与成员](categories/neutrals.md) | 4 | 37 | 37 | 0 | 0 |
| [原创法术与单位出场场景](categories/spells.md) | 8 | 48 | 48 | 0 | 0 |
| [英雄技能与专属卡](categories/hero-skills.md) | 5 | 42 | 36 | 0 | 6 |
| [建筑与泉水](categories/structures.md) | 1 | 6 | 6 | 0 | 0 |
| [旧方向与原创题材探索](categories/explorations.md) | 5 | 25 | 25 | 0 | 0 |

“本地图片”只表示文件已归档；“仅任务号”保留平台最近记录，未重新查询实时完成状态；“仅备稿”尚无任务号。用户认可单独看 `review_status` / `user_review`，游戏接入看 `integrated_asset_id`，不从存在图片推断验收通过。

`explorations` 中保留旧原创英雄、偏题英雄和背景合成实验，供追溯，不作为原版英雄身份参考。

刷新分类：`python3 scripts/art_library.py`。要将新增的已用本地参考图复制进归档，执行 `python3 scripts/art_library.py --archive-references`；按 SHA-256 复用已有副本，不移动、删除原件，不联系 Migoo，也不连接 108。
