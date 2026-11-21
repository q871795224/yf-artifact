# 项目自制素材

与 `references/artifact-classic/assets/` 的 Valve 原始资料分开保存。`manifest.json` 记录用户提供的文件名、原件位置、SHA-256 与游戏派生资源。

**卡面缺口与生图提示词**：[card-art-brief.md](card-art-brief.md)，一份文件列出缺哪些图、每张画什么、完整提示词与参考图路径。

## 已采用

| 素材 | 来源 | 用途 |
| --- | --- | --- |
| 夜魇近战小兵 `dire-melee` | 用户提供 `imagen_original_1794905680_8b171272.png`，768×1360 | 敌方基础近战兵（卡牌 ID 1006）的棋盘、详情与行动留影；原版 2 攻／4 血和近战规则保持不变 |
| 夜魇远程小兵 `dire-ranged` | 用户提供 `imagen_original_1795014831_86228e3b.png`，768×1360 | 熔岩树人持符文法杖；用于敌方自动远程兵 |
| 夜魇攻城车 `dire-siege` | 用户提供 `imagen_original_1795014653_7645a68b.png`，768×1360 | 焦黑尖刺投石车；**仅素材，未接入** |
| 天辉远程小兵 `radiant-ranged` | 用户提供 `imagen_original_1795013292_6ac84ebd.png`，768×1360 | 秋叶树精持发光木杖；用于我方自动远程兵 |
| 天辉攻城车 `radiant-siege` | 用户提供 `imagen_original_1795013729_9b91b995.png`，768×1360 | 石木混合投石车；**仅素材，未接入** |

新入库 4 张按「双方 × 远程兵／攻城车」规范命名，全部 768×1360，SHA-256 已写入 `manifest.json`，远程兵的 `integration` 标为 `linked`，攻城车标为 `pending`。生成时右下角带 Migoo 水印，后续统一风格时应去掉。

原件：`originals/dire-melee.png`，保留完整构图。游戏使用 `prototype/assets/units/dire-melee.webp`，宽 352px、40,430 字节，静态构建随界面复制。棋盘通过 CSS 定位显示头部和上半身，详情展示完整立绘。素材库支持搜索“夜魇”或 `dire-melee`，并打开原始 PNG。

重新生成轻量副本：

```sh
cwebp -quiet -q 85 -m 6 -resize 352 0 assets/custom/originals/dire-melee.png -o prototype/assets/units/dire-melee.webp
```

重新生成后同步清单中的派生 SHA-256。

## 素材覆盖与后续缺口

| 类别 | 当前状态 | 数量／优先级 |
| --- | --- | --- |
| 天辉近战兵 | 已有原版素材 1006 | 可继续使用 |
| 夜魇近战兵 | 已采用自制图 | 已齐 |
| 双方远程兵与攻城车 | 远程兵立绘已接入，攻城车立绘已入库 | 攻城车待定 |
| 防御塔／基地 | 当前使用塔与遗迹图标 | 双方各塔、基地一张，共 4 张；P2 |
| 泉水 | 当前使用区域标记与图标 | 双方各 1 张，可后补 |
| 英雄头像 | 原版 `mini_image` 可用 | 建议先不改 |
| 新卡卡面（37 张） | 已按卡牌编号接入试玩 | 原图见下方 |
| 物品（18 件装备、4 件消耗品） | 已按卡牌编号接入试玩 | 另有 5 件扩充装备的候选图 |

远程兵规则见[成长 Demo 实现](../../docs/design/growth-implementation.md)。攻城车的身材、射程与出兵规则待定。

卡面缺口与生图提示词见 [card-art-brief.md](card-art-brief.md)。

<!-- migoo-card-art-start -->
## Migoo 卡牌插画

共 54 张，原图为 768×1360 PNG，按卡牌编号或物品名称保存。素材暂存于仓库。

已有卡牌编号的原图派生为 `prototype/assets/cards/<卡牌编号>.webp`，手牌、详情和牌组编辑器共用该副本。清单记录原图、派生路径和哈希。

上批两位英雄、专属和新增法术共八张，见[首批插画](../migoo/README.md)。

### 单位（12 张）

- [前线新兵](originals/unit-61001.png)
- [嗜战斗士](originals/unit-61002.png)
- [披甲步兵](originals/unit-61003.png)
- [破势战士](originals/unit-61004.png)
- [重装卫士](originals/unit-61005.png)
- [先锋掷斧手](originals/unit-61006.png)
- [萌芽守卫](originals/unit-61007.png)
- [共生幼苗](originals/unit-61008.png)
- [林间向导](originals/unit-61009.png)
- [复苏守卫](originals/unit-61010.png)
- [战场引路人](originals/unit-61011.png)
- [古林修复者](originals/unit-61012.png)

### 英雄专属（6 张）

- [狂战士之吼](originals/signature-63001.png)
- [决斗](originals/signature-63002.png)
- [神之力量](originals/signature-63003.png)
- [野蛮灵狼](originals/signature-63004.png)
- [上帝之手](originals/signature-63005.png)
- [全视者恩泽](originals/signature-63006.png)

### 法术（19 张）

- [新命令](originals/spell-62001.png)
- [鞭笞](originals/spell-62002.png)
- [惹是生非](originals/spell-62003.png)
- [战斗训练](originals/spell-62004.png)
- [浴血奋战](originals/spell-62005.png)
- [一扫而空](originals/spell-62006.png)
- [致残重击](originals/spell-62007.png)
- [废话少说](originals/spell-62008.png)
- [胜利时刻](originals/spell-62009.png)
- [绕树](originals/spell-62010.png)
- [治疗](originals/spell-62011.png)
- [呵斥](originals/spell-62012.png)
- [铁树枝干守护](originals/spell-62013.png)
- [魔霭福泽](originals/spell-62014.png)
- [武装叛军](originals/spell-62015.png)
- [妙手回春](originals/spell-62016.png)
- [攻其不备](originals/spell-62017.png)
- [恫吓](originals/spell-62018.png)
- [衰退诅咒](originals/spell-62019.png)

### 物品（17 张）

- [短剑](originals/item-65001.png)
- [阔剑](originals/item-65002.png)
- [大剑](originals/item-65003.png)
- [皮甲](originals/item-65004.png)
- [锁子甲](originals/item-65005.png)
- [板甲](originals/item-65006.png)
- [黑皇杖](originals/item-65012.png)
- [梅肯斯姆](originals/item-65013.png)
- [点金手](originals/item-65014.png)
- [邪恶镰刀](originals/item-65015.png)
- [紫苑](originals/item-65016.png)
- [圣剑](originals/item-65017.png)
- [狂战斧](originals/item-battle-fury.png)
- [电锤](originals/item-maelstrom.png)
- [陨星锤](originals/item-meteor-hammer.png)
- [辉耀](originals/item-radiance.png)
- [希瓦的守护](originals/item-shivas-guard.png)

<!-- migoo-card-art-end -->

## 108 补齐物品插画

这批 10 张为 Z-Image Turbo 在 108 上生成的候选图，均为 768×1360 PNG。生成和入库流程见[卡牌插画工作流](../../docs/development/card-art-workflow.md)。

- [旅者斗篷](originals/item-65007.png)
- [毛皮大衣](originals/item-65008.png)
- [生命斗篷](originals/item-65009.png)
- [跳刀](originals/item-65010.png)
- [刃甲](originals/item-65011.png)
- [魔龙枪](originals/item-65018.png)
- [治疗药膏](originals/item-65019.png)
- [回春药水](originals/item-65020.png)
- [知识秘典](originals/item-65021.png)
- [回城卷轴](originals/item-65022.png)
