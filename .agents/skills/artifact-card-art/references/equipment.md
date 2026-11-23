# 装备与局部返工

## 新图的参考分工

官方 Dota 图标锁定器物类别、轮廓、配色、关键部件；同类 Classic 无框装备原画提供厚涂笔触、反射、磨损和空间。小图标也能作为形状依据，但要如实记录它只有约 88×64，不宣称是高清实物图。

Classic 有同名装备时可以同时核对共同特征；没有同名卡时选同材质／同品类的画法参考，不把参考中的另一件装备替换成目标物件。用户先认可了[10 件样张](../../../../assets/migoo/dota-equipment-classic-pilot/manifest.json)，之后扩到[50 件及当前修订任务](../../../../assets/migoo/dota-equipment-classic-batch-03/all-50-task-ids.tsv)。这些记录中的“提交”不自动表示都已目视验收。

## 决定成败的提示词

| 部位／问题 | 写法 |
| --- | --- |
| 标志轮廓 | 明写是何种器物与原版独特形状，例如幻影斧的大 C 形刃口、先锋盾的紫色盾面与浅色中心纹样 |
| 构件关系 | 杖头、连接颈、柄是一体；剑刃与护手连续；锤柄真实连到锤头 |
| 数量 | 一把完整武器；鞋靴按本张目标写一双；倒影是倒影，不变成额外实物 |
| 空盔／面具／甲 | 明确是空装备、有内腔与支撑，不生成穿戴者、活人脸或悬空肢体 |
| 布、金属、晶体 | 局部反射和接触阴影，比通体发光更能表现做工；背景与器物共享光向 |
| 批次变化 | 斜靠、平放、挂靠、俯视、低机位分别选；器物主色固定，环境与主光可变 |

器物通常完整占主体，留出刃尖和柄端。漂浮展示、同一石台、同一金光不作为每件的默认布局。可借石阶、军械架、雪境、旧木箱、窗台等交代支撑与材质。

语句示例：

```text
Paint the actual named Dota equipment. Image 1 defines the recognizable
outline, functional parts and main colors. The last two images define
Classic painting only. Repaint one complete coherent object and its setting
together. Keep contact, weight and material differences readable.
```

## 三根法杖的实际返工

用户对幽魂权杖、原力法杖、Eul 的神圣法杖提出：杖头要直，柄稍短。采用原成图 `source_task` 修订，要求：

1. 杖头中心、连接颈与杖柄中轴共线，消除单侧弯钩、垂头和折颈；整件仍可保持原来的斜放角度。
2. 只将下段直柄缩短约 20%，头部尺寸与柄的粗细基本保留，不把整件等比缩小。
3. 保留原场景、主光、材料、主色和标志部件。Eul 的风纹环绕直轴排列，用户这次的形体纠正优先于图标中的弯曲形状。

这是一组具体返工经验，不能把“所有法杖都必须直头”写成对未来全部物件的普遍规则。用户要沿用原版弯形器物时按新任务要求。

见[返工提示词与原任务关联](../../../../assets/migoo/dota-equipment-classic-staff-rework-01/manifest.json)。修订任务已提交；保留原图、旧任务与每次版本，不覆盖历史记录，不把“已提交修订”写成“已确认改好”。

旧[装备题材概念](../../../../assets/migoo/dota-equipment-concepts/briefs.json)包含“发明新造型”等早期要求；可参考构图探索，不能继承为当前原版装备的人设规则。
