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

## 后续素材清单

| 类别 | 当前状态 | 数量／优先级 |
| --- | --- | --- |
| 天辉近战兵 | 已有原版素材 1006 | 可继续使用 |
| 夜魇近战兵 | 已采用自制图 | 已齐 |
| 双方远程兵与攻城车 | 远程兵立绘已接入，攻城车立绘已入库 | 攻城车待定 |
| 防御塔／基地 | 当前使用塔与遗迹图标 | 双方各塔、基地一张，共 4 张；P2 |
| 泉水 | 当前使用区域标记与图标 | 双方各 1 张，可后补 |
| 英雄头像 | 原版 `mini_image` 可用 | 建议先不改 |
| 新卡卡面（37 张） | 全部借用原版图或头像占位 | **P0／P1，见 card-art-brief.md** |
| 装备（22 件） | 16 件有原版参考图，6 件占位错位 | 参考图改图 |

远程兵规则见[成长 Demo 实现](../../docs/design/growth-implementation.md)。攻城车的身材、射程与出兵规则待定。

卡面缺口与生图提示词见 [card-art-brief.md](card-art-brief.md)。
