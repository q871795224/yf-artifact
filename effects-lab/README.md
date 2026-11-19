# 本地特效工作台

设计沿革见 [决策记录](../docs/design/decision-log.md)；共享库、缓存、自动化与自启的坑点见 [开发复盘与运维](../docs/development/lessons-and-operations.md)。

双击根目录的 `打开特效工作台.command`，或访问 <http://127.0.0.1:8741/effects-lab/>。当前电脑已安装 macOS LaunchAgent，由 Python 静态服务器在后台提供页面；每次登录 macOS 后自动启动，关闭终端不影响服务，进程退出后会自动拉起。只监听本机 `127.0.0.1:8741`，无需联网。

该目录位于游戏发布目录之外，不进入 GitHub Pages 构建，没有调整英雄仇恨规则。也可以直接用浏览器打开此目录的 `index.html`，这种方式不需要服务器；页面仅引用自己的脚本与已有的本地 WebP 头像。

## 素材库

从页首“素材库”进入 <http://127.0.0.1:8741/effects-lab/assets.html>。默认以整页卡牌画廊展示 310 条原版完整卡面及项目已采用的自制图，可按名称、英文名、ID、类型及本地来源筛选；切换到小兵／召唤单位可浏览其中 50 条。原版使用本地 `cards.json` 与素材清单，自制图读取 `assets/custom/manifest.json`；不修改原作数据。

图片版本可切换方形头像、完整卡面、局内图标；原版本地已有 59 个条目的图片，共 130 张；另有已采用的自制夜魇近战小兵图，搜索“夜魇”可查看，打开原图进入保留的 PNG。其余条目从原索引 Valve CDN 加载，需联网，旧链接可能失效。点击卡牌打开大图详情，可切换图片版本、打开原图、复制名称和 ID；关闭后保留筛选与浏览位置。用户浏览并提供选中的卡牌名称或 ID 后，再单独选取素材。此页需要通过本地 HTTP 服务访问，不支持直接双击 HTML 读取 JSON。

## 后台服务

服务配置：`/Users/yifei.chen/Library/LaunchAgents/com.yifei.yf-artifact.effects-lab.plist`。日志：`/Users/yifei.chen/Library/Logs/yf-artifact-effects-lab/`。配置中使用当前仓库的绝对路径，移动仓库后需要修改配置并重新加载。

```sh
# 查看状态
launchctl print "gui/$(id -u)/com.yifei.yf-artifact.effects-lab"
# 重启
launchctl kickstart -k "gui/$(id -u)/com.yifei.yf-artifact.effects-lab"
# 停止服务，并取消当前登录会话中的自动重启
launchctl bootout "gui/$(id -u)" /Users/yifei.chen/Library/LaunchAgents/com.yifei.yf-artifact.effects-lab.plist
# 重新启用
launchctl bootstrap "gui/$(id -u)" /Users/yifei.chen/Library/LaunchAgents/com.yifei.yf-artifact.effects-lab.plist
```

若要永久取消登录自启，先停止服务，再移走上述 plist 文件。后台服务只安装在当前电脑，不随仓库或 Pages 发布。

## 怎么调

1. 左侧选择十三类效果：沟壑、近战挥砍、双单位对撞、远程弹道、受击、治疗、召唤、雷击、眩晕、护盾、增益光环、阵亡、防御塔炮击。
2. 默认停在中间关键帧。点击播放／暂停／重播，或拖动时间轴查看任意时刻；逐帧按钮按 60fps 前后移动一帧。
3. 右侧修改时长、线宽、光晕、力度、颜色与演示数字。修改后保留当前播放进度比例，便于比较同一关键帧。
4. 方向支持八向，距离支持一／两格；沟壑固定为直线两格。预览宽度可切换为手机、小屏或放大。棋盘上方的“地图”可在 5 列 × 8 排与 6 列 × 8 排间切换；保留方形格子，五列会增加棋盘高度，在手机上放大单位。地图选择会随预设保存，旧预设默认六列。
5. 输入预设名称后保存，同名保存会更新该预设。导出 JSON 可备份或交换，导入后点击保存可加入左侧“我的预设”。

空格切换播放／暂停，左右方向键前后移一帧；焦点位于输入框、下拉框或按钮时保留其原生键盘行为。支持 0.25×、0.5×、1×、2× 和循环播放。

预设与当前工作参数保存在该浏览器的本地存储中。不同浏览器、不同访问地址的记录可能不共享；从本地文件切换到 HTTP 地址时，可先导出 JSON，再在新地址导入。重要的方案请导出 JSON；存储不可用时页面仍可预览与导出。

## 新增效果

- 雷击：上方落雷、分叉电弧、二次闪击与落点冲击，适合宙斯等法术。
- 眩晕：头顶星环与三颗绕行星芒，单位暂时失色；没有伤害数字。
- 护盾：盾形屏障展开，模拟承受一次攻击，产生波纹后消散。
- 增益光环：显示目标周围八个邻格，符文环扩散、箭形光点上升，搭配友军预览。
- 阵亡：目标失色、逐渐消失，碎光与灵魂上升；拖回时间轴起点可恢复单位。
- 防御塔炮击：使用本地塔素材，炮口蓄力、炮弹沿抛物线飞行、落点爆炸。

这些只描述视觉过程，不新增护盾、伤害或死亡规则。原有预设继续兼容。

## 特效库

`../prototype/effects.js` 暴露 `window.ArtifactFX`，`app.js` 只负责工作台、预览场景和预设管理。V0.2 正式对局复用同一份特效库，工作台页面仍不进入 Pages 发布。所有效果由 SVG 与 Web Animations 绘制，可以暂停、拖动和取消；不执行伤害、仇恨或其他游戏结算。演示数字仅用于视觉预览。

```js
const effect = ArtifactFX.create(svgLayer, "projectile", {
  from: { x: 250, y: 450 },
  to: { x: 250, y: 250 },
  actorElement,  // 可选：施法者 DOM，用于前冲
  targetElement // 可选：目标 DOM，用于受击或出场
}, ArtifactFX.defaults("projectile"));

effect.seek(400);
effect.setRate(0.5);
effect.play();
effect.pause();
effect.dispose();
```

坐标空间使用（列数 × 100）×800，与五列／六列、八排的棋盘对应；沟壑额外接收 `cells: [{row, col}, ...]`，增益光环接收 `areaCells: [{row, col}, ...]` 显示受影响的邻格。预设 JSON 记录效果、视觉参数、场景和名称，不包含页面代码。正式对局通过 `prototype/game-effects.js` 接入这些效果；工作台参数可导出为预设，当前游戏使用库中的默认配色与按场景调整的时长。

## 检查

`scripts/check_effects_lab.js` 可通过 Playwright CLI 的 `run-code` 执行。检查十三类效果、往返拖动时间轴、播放／暂停／逐帧、速率、循环、参数保存、刷新恢复、新旧预设导入导出、无效预设处理，以及桌面和小屏布局。覆盖五／六列下所有效果的八向目标、坐标对齐、单位放大与旧预设兼容。还检查阵亡后回退恢复、八邻格光环与建筑素材。

本地文件测试需要 Playwright CLI 的官方配置 `allowUnrestrictedFileAccess: true`。测试配置放在忽略的 `output/playwright/effects-cli.config.json`，仅用于自动化访问本地 HTML，不是页面运行依赖。正常双击打开不需要此设置。
