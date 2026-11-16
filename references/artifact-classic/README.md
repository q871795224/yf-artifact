# Artifact Classic 本地参考库

用于本作讨论与数值推演。原始数据、离线索引和分类文档均已保存到本地；日常查询无需联网。这里的数值属于原作，不自动成为本作规则。

## 先看什么

| 内容 | 条目数 | 本地文档 |
| --- | ---: | --- |
| 英雄（含四名基础英雄） | 48 | [英雄](heroes.md) |
| 小兵、卡牌单位与衍生单位 | 50 | [单位](creeps.md) |
| 法术 | 118 | [法术](spells.md) |
| 装备与消耗品 | 48 | [物品](items.md) |
| 建筑改良 | 39 | [改良](improvements.md) |
| 主动／被动技能 | 46 / 29 | [技能](abilities.md) |
| 建筑／攻击路径内部记录 | 3 / 4 | [其他记录](structures-and-paths.md) |
| 合计 | 385 | [完整 JSON](cards.json) |

这些是 API 的记录数量，**不等于可构筑卡牌数量**。技能、衍生单位、路径和建筑也有独立 ID。同名物品及其主动技能是不同条目，不能按名称去重。两个卡包分别有 27 和 358 条记录，无重复 ID，所有引用均能在本地解析。

## 版本与来源

1. **数值与分类文档：2018-12-22 历史快照。** 来源是 [Artifactoid 保存的 Valve 卡包 API 响应](https://github.com/nminchow/Artifactoid/tree/e4d7fd3254bf07ea046e327178477a5c4ea49489/Artifact/RawSets)，包含基础套牌（00）和武装号召（01）。原始 JSON 完整保存在 [raw/api-2018](raw/api-2018)，含 28 种语言及图片 URL；整理索引只提取英文与简体中文。
2. **补充文本：2021-04-21 Classic 客户端，build 6500791。** 来源是 [GameTracking-Artifact](https://github.com/SteamTracking/GameTracking-Artifact/tree/e2e4f8371324e66bc815b8199c0c2743a4331b10)，保存了中英文卡牌文本、背景故事、术语表、旧 ID 映射和版本文件，位于 [raw/client-2021](raw/client-2021)。这些文本在 `cards.json` 的 `client_2021` 字段单独保存，**不会覆盖 2018 数值和正文**。
3. [Valve 官方 API 说明](https://github.com/ValveSoftware/ArtifactDeckCode/tree/c4a1611c554273339755eee549c4d7b780021d59)已保存至 [raw/api-spec](raw/api-spec)。2026-11-11 检查旧版 `playartifact.com/cardset/00/` 时，返回的是跳转 Steam 商店的 HTML，而非卡包 JSON，因此采用固定提交的历史响应。

这不是已经核验过的 Classic 最终平衡版本，也不是 Foundry 数据。后续如需采用某次更新后的数值，应新增独立快照，核对差异后再选版本。完整下载来源、提交、字节数和 SHA-256 见 [sources.json](sources.json)。

## 离线查询

在项目根目录执行；仅依赖 Python 3 标准库：

```sh
# 按中文名、英文名、正文、官方 ID 或旧 ID 检索
python3 scripts/artifact_reference.py search 斧王
python3 scripts/artifact_reference.py search 1006
python3 scripts/artifact_reference.py search "Crystal Maiden" --type Hero
python3 scripts/artifact_reference.py search --type Item --json

# 从本地原件重新生成索引与文档；不会联网
python3 scripts/artifact_reference.py build

# 校验原件哈希、ID、引用以及生成文件是否与原件一致
python3 scripts/artifact_reference.py check

# 仅在原件遗失或损坏时，从固定来源恢复；这是唯一联网命令
python3 scripts/artifact_reference.py fetch
```

检索同时覆盖两个版本的文本；普通输出只展示 2018 版数值和正文。需要查看 2021 文本时加 `--json`，阅读 `client_2021` 字段；其中保留客户端原始标记和变量，不冒充解析后的完整规则。也可以直接用编辑器搜索分类 Markdown。

## 字段与使用边界

- `cards.json` 保留官方 `card_id`、`base_card_id`、类型、费用、攻防血、颜色标记、稀有度、物品子类型、图片 URL、跨线／快速标记、充能及 `references`。`source` 指向原件和卡包；`legacy_ids` 来自客户端的七条 ID 映射。
- `card_name`、`card_text` 是英文／简中索引；正文只去 HTML 标签、解码实体，原始 HTML 与其他语言仍在原件中。空正文可以是白板卡；缺失数值不会擅自补成零，Markdown 用 `—` 表示。部分上游文本自身存在残留标记，未推测修订。
- `references` 的 `includes` 表示英雄专属卡及数量，`active_ability` / `passive_ability` 指向独立技能，`references` 表示普通关联。技能 CD 有时只写在所属英雄或物品正文中，API 没有统一数值字段；本库不猜测补齐。
- 基础近战小兵是 **1006，2 攻／4 血，API 未列护甲**。原件还带 `mana_cost: 3`，这是接口字段，不能据此认为自动出兵要支付 3 水晶。原版自动出兵没有另一种“基础远程小兵”；本作的远程兵需另定。
- 术语表原文另存为 [英文](glossary-english.json)／[简中](glossary-schinese.json)，可以核对赏金、部署、护甲等规则。没有把术语描述自动转换成每个单位的赏金数值。
- [client-only-tokens.json](client-only-tokens.json)保留未匹配到 API 条目的客户端文本，其中包含作弊、变异等内部条目；没有将它们自动当成正式可构筑卡。
- 两份客户端背景故事文件中，`CardLore_10323` 的结束引号后原本多出 `— <i>`。原文件未改动，索引仅取引号内的 KV 值；解析器只对这一项已知异常作处理。
- 全量图片 URL 均保留。2026-11-16 已下载[首批本地美术素材](assets/README.md)：十二名候选英雄及候选牌池关联图片共 130 张，含头像、中文完整卡面和英雄局内小图标；尚非全量图片或客户端 UI 资源。名称、数值、效果、关系和背景故事可以离线查。此库是资料快照，不包含可执行的技能逻辑。

## 归属与校验

Artifact、卡牌文字及相关素材属于 Valve／相应权利人。镜像项目的 [MIT 许可](raw/api-2018/LICENSE.md)、[Valve 示例代码许可](raw/api-spec/LICENSE)及[客户端第三方声明](raw/client-2021/thirdpartylegalnotices.txt)均随原件保留；镜像代码许可不改变卡牌素材的权利归属。

本地校验涵盖 19 份原始文件的 SHA-256、385 个唯一 ID、全部专属卡／技能引用、生成文件一致性；另有针对 Unicode、KV 转义、HTML 文本、源文件损坏检测及离线重建的回归检查：

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
```
