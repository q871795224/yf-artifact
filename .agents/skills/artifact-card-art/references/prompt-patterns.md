# 提示词结构与整批差异

## 单张结构

用户原话作为需求根，已确认的细化放进 `notes`。本项目有效提示词通常依次说明：

1. **参考分工**：每张图是谁／是什么、负责身份还是画法。
2. **必须保留**：原版身份、关键轮廓与构件，或普通单位可提炼的族群特征。
3. **本张叙事**：谁正在做什么，物件怎样摆放，法术在哪作用。
4. **镜头与空间**：俯仰、景别、主体占比、朝向、前中远景、接触／受力。
5. **主色与用光**：主光方向、硬软、反光与阴影形状；英雄／装备本色与背景色分开考虑。
6. **画法与交付**：Classic 宽笔触、材质与局部高光、虚实边缘、满版无框，9:16／1K 按本次参数。

```text
REFERENCE ROLES: Images 1..N identify the named characters or equipment.
The last two images define Artifact Classic brushwork, material, values,
edge control and depth only.

IDENTITY / SHAPE: [actual required head, anatomy, costume or equipment parts]
ACTION / EFFECT: [one concrete action, contact or state change]
CAMERA / SPACE: [view, scale, focal position and depth planes]
LIGHT / PALETTE: [one main light, shadow mass, reflected light, key colors]
PAINT: [selective detail, visible paint, tactile material, integrated scene]
DELIVERY: [full-bleed illustration, no frame, text, UI, logo or white margin]
```

模板中只保留本张适用项。不要把“全部原创外形”“单个全身角色”或“同一后侧金光”作为所有类别的通用串。若沿用旧提示词，先排除与本次身份和叙事冲突的句子。

## 整批先写差异表

| 维度 | 可改变的内容 | 保持条件 |
| --- | --- | --- |
| 镜头 | 低机位、俯视、贴水、侧面、透过近物 | 仍能读出关键身份或物件形状 |
| 景别 | 近景冲击、环境远景、局部作用点 | 普通单位全身要求按任务保留 |
| 动作 | 负重、旋身、跳跃、贴地、修理、急停 | 肢体、持物与重心可信 |
| 主体大小 | 小主体大环境、近景大刃口等 | 小卡仍可识别 |
| 主光 | 阴天天光、窄窗日光、月光、水面反光、局部火点 | 物件与环境光向统一 |
| 大色块 | 浅雾、暖白石、蓝灰水、赭墙、暗木 | 身份主色不被擅自重设 |

用户明确指出红卡不应全是红色熔岩，前六张旧英雄题材也集中偏暖。后来换冷蓝、紫灰、青绿只解决了一部分调色问题，镜头、姿态、背景和主体占比仍要分别设计。

避免用“高细节、电影光、体积光、橙红边光”等泛化词覆盖每张。具体写哪里精细、哪里松：脸、手、握持处、法术触点、刃口与宝石通常是焦点，其余留宽笔触。

## 建筑

塔、基地、泉水的主体是建筑本身。天辉可用木、石、植物与浅色矿物，夜魇可用深岩、裂隙与铁；先保留可读的结构功能，再分别设计高度、仰俯、近景遮挡与天候，不把同阵营六张都写成同一熔岩或树林。样例见[阵营建筑提示词](../../../../assets/migoo/faction-building-concepts/briefs.json)。

## 改图与观察措辞

局部返工写“原成图中哪个部位如何改变、哪些保持”，不要一边给保留要求，一边重写整个场景。用 `source_task` 绑定正确版本，并保留旧任务。

需要审阅时，先目视身份、肢体／构件、武器、动作与小图辨识度，再做尺寸或 OCR 等辅助检查。尺寸、OCR 和调色统计通过不能代替角色／物件画对。用户选择只提交时，将这些验收留给用户，不宣称自己已检查成图。
