# 原版英雄

## 有效做法

身份取自 Valve 官方英雄透明渲染，画法取自两张适合当前题材的 Classic 无框原画。保留头部、种族、体态、配色、标志装备和附肢，再重新安排动作、镜头、场景与光线。第一张美杜莎用蛇尾形成 S 形、转身引弓，与湿石阶统一绘制，用户认可后继续扩批。

官方图负责“是谁”；Classic 图负责笔触、材质、明暗和空间。不要因为风格参考是人形角色，就把非人英雄改成人类。多个英雄也不共用一套站姿、森林或左后金光。

## 写提示词时锁定的内容

| 对象 | 需要写清 |
| --- | --- |
| 头部与种族 | 面具、蛇发、喙、角、冰颅、昆虫头或水体面孔等决定辨识度的特征 |
| 身体拓扑 | 两臂／蛇尾、四足坐骑、翼与躯干连接；看过参考再写数量，不凭常识猜 |
| 标志装备 | 主宰的白面具与长刀、美杜莎的弓、发条的机械装甲等 |
| 新镜头与动作 | 主体占比、头部位置、动作方向、接地与受力、近中远景 |
| 画法 | 宽笔触、大明暗、局部硬边、自然材质；精细处集中在脸和关键持物处 |

参考语句：

```text
Image 1 strictly defines this named Dota hero's identity, species, anatomy,
costume and equipment. The last two images define Classic painting only.
Repaint the actual hero and environment together in a new pose and camera.
Keep the iconic head, weapon and silhouette readable at small card size.
```

角色颜色可以固定，背景主色、景别和主光仍可变化。红色英雄卡不必画红色夜魇熔岩；用户明确指出白云、浅森林等背景能提高一眼区分度。

## 参考获取与检查

Valve 透明图的路径在 **videos** 下：

```text
https://cdn.akamai.steamstatic.com/apps/dota2/videos/dota_react/heroes/renders/<hero_key>.png
```

`images/dota_react/heroes/<hero_key>.png` 通常是小头像，不要标作高清全身图。官网海报也要检查实际对象：本次 `warlock.png` 是召唤物，不能拿它定义人类术士；后来使用官方术士头像锁定人脸与红兜帽，提示词明确画人类英雄。

已用高分辨率图与旧路径见[参考索引](../../../../references/card-art/catalog.json)。旧完整渲染、截图与载入画面仍留在本地缓存，源图用途应分别标为默认人设、饰品／动作参考等。

## 已证实的偏题

- 把美杜莎改成“盐镜守门人”、水人改成“撑桥泥灵”，提示词还要求独立设计种族、外形与装备，丢失了用户要求。见[旧英雄题材稿](../../../../assets/migoo/dota-hero-role-concepts/briefs.json)。这些图保留为探索记录，不能作为原版英雄模板。
- 生成背景后贴官方透明图，没有完成英雄与场景的统一重绘。见[背景合成实验](../../../../assets/migoo/dota-hero-portrait-layout/)。
- 只换冷暖色不能解决相同站姿、景别和背景。每人独立写镜头、动作、主光、主体占比。

当前已有[90 位英雄任务清单](../../../../assets/migoo/dota-original-heroes-classic/all-90-submissions.json)。用户后来明确停止余下 37 位；这是已停任务的记录，未来如需继续由新的用户请求决定，不因资源可用而自动提交。
