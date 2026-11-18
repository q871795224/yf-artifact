# 开发复盘与运维

> V0.4 更新：当前规则见[成长版实现说明](../design/growth-implementation.md)，发布核验见[V0.4 归档](../releases/v0.4.md)。新版引擎入口为 `growth_cards.py`、`growth_match.py`、`growth_playable.py`；浏览器使用 `scripts/check_growth_prototype.js`。下文 V0.3 固定回放和旧浏览器脚本仅用于历史对照，不能直接作为成长版发布基准。

整理于 2026-11-17，适用当前 V0.3；历史问题保留当时背景。玩法理由见[决策记录](../design/decision-log.md)，规则与未定项见[当前规格](../design/current-rules.md)。本页区分已经遇到的问题与今后的操作注意，不把尚未实现的功能写成修复成果。

## 已遇到的问题与处理

| 问题 | 原因／定位 | 已采用的处理 | 后续注意 |
| --- | --- | --- | --- |
| 所有人从后场出发，第一轮无法交战 | 出生距离与首轮要求冲突 | 首轮两英雄两兵直接前线部署，后续增援仍从泉水来 | 调地图或出生时重查首轮目标 |
| 后排不能跟进，整队隔格等待 | 只看移动开始时的占位 | 意图、争格、跟进依赖分开处理，两步移动逐步检查 | 不用固定遍历顺序吞掉争格随机规则 |
| 射程内有敌却不普攻 | 随机箭头没有指到敌人 | 自动仇恨，箭头展示当前目标 | “无敌在射程”仍可能正常发生，不是同一个问题 |
| AI 位置试算可能污染真实锁定 | 查询目标与提交锁定混在一起会让候选遍历顺序影响对局 | 目标查询只读，真实局面改变后统一刷新锁定 | 调 AI 时继续检查同种子可复现性 |
| 保护转火被过早判断为拖局 | 只看 24 轮截止，忽略超时原因和续跑 | 同局续跑 48 轮、核对前段一致，撤回一刀切关闭建议 | 完成率、超时、已完成局平均轮数要分开 |
| 金币结余多，被怀疑完全未消费 | 收入与实际收到物品的购买容量不匹配 | 核对收支恒等式、手牌原因与理想消费上限，补双经济终端 | 扩池不等于发更多购买机会；余额不要求归零 |
| 图片与首次加载慢 | 原版 PNG 太大，首次还需下载 Python 浏览器运行环境 | 130 张移动 WebP，图片约 43.0 MB → 1.13 MB；Pyodide 本站托管，资料与运行时并行加载，固定版本运行文件缓存 | 原 PNG 留资料库，Pages 只放压缩副本；首次仍需网络 |
| 改五列后特效与棋子错位 | 浏览器复用旧六列 CSS，而新 JS 已生成 40 格／500 宽坐标 | 样式与脚本更新缓存查询版本，列数统一驱动网格和 SVG；加入落点几何检查 | 不能只改 HTML 格数；出生、召唤、回城、AI 试算也有列数边界 |
| 隐藏的预设 JSON 读成空字符串 | 自动化用 `innerText()` 读取折叠 details 内的 pre | 改用 `textContent()`，验证导出再导入 | 不要把测试读不到内容误诊成 JSON 导出坏了 |
| Playwright 默认拒绝 file URL | 自动化访问边界，与页面本身能否双击运行不同 | 文件测试用官方 `allowUnrestrictedFileAccess: true` 配置；HTTP 服务测试无需这个配置 | 不去修改全局浏览器安全设置；配置留忽略的输出目录 |
| headless 长截图出现重复片段 | 全页截图与实际视口渲染出现差异 | 看 DOM 元素数量、视口截图与滚动后的截图交叉核对 | 不仅凭一张拼接长图修改正常页面布局 |
| LaunchAgent bootstrap 报错或找不到配置 | 工具环境的 HOME 被重定向，写到了 `.codex-personal/home`，不是 macOS 账户主目录 | 用系统账户目录定位真实 `Library/LaunchAgents`，以当前用户 gui 域加载 | 不把 launchctl 的通用报错直接理解成必须提权 |
| GitHub 推送静态资源时 HTTP 500 | 上传链路与较大请求兼容问题 | 推送使用 150 MiB `http.postBuffer` 与 HTTP/1.1，部署脚本中保留这组参数 | 失败后先读远端提交，不能仅据退出码断定没写入 |
| 创建 Pages 的 API 返回不明确 | 失败响应仍可能已在远端生效 | 创建后再 GET 读取最终 Pages 配置，确认状态后报告 | 不盲目重放写操作 |
| Python HTTPS 验证失败，本机报 CA 缺失 | 本机 Python 的信任链问题；同网址可由系统 curl／浏览器正常验证 | 使用系统信任链的 curl／浏览器核对发布 | 不通过关闭 TLS 校验掩盖问题，也不把它当成线上站点故障 |

## 架构边界

规则链为 `simulate_heroes.py` → `simulate_match.py` → `simulate_expanded_match.py` → `simulate_finishers.py`，由 `playable_match.py` 提供真人合法操作、交替行动与公开快照。HTTP 服务和浏览器 Worker 都调用同一个适配器，不在 JavaScript 再写一套伤害算法。

玩家合法操作与 AI 的正收益候选分开：真人可以走评分不佳的位置、替换较弱装备。不能把 AI 不愿意做的操作误写成规则禁止。提交操作校验对局操作版本，拒绝陈旧／伪造动作，错误时恢复状态，避免重复消费。

正式游戏与工作台共用 `prototype/effects.js`；`game-effects.js` 只把实际行动和状态变化映射成效果。AI 帧携带已经公开的出牌信息，不能泄露其剩余手牌。特效先后不决定攻击先后，飘字来自实际生命变化，不能直接把工作台默认演示数字当成战斗伤害。播放完取消动画并移除节点，减少动态效果设置下跳过动画，仍完成真实结算。

早期模拟器默认仍支持六列，以保留实验用途；正式对局由 `playable_match.py` 的 `BOARD_COLUMNS=5` 明确指定。更改默认列数前先查所有调用，不能为改正式战场顺手改变历史实验语义。

## 原作资料与内容适配

优先离线查询[本地参考库](../../references/artifact-classic/README.md)：

```sh
python3 scripts/artifact_reference.py search 斧王
python3 scripts/artifact_reference.py search 1006
python3 scripts/artifact_reference.py check
```

2018-12-22 数值与 2021-04-21 客户端文本分别保存，后者不是已经核验的最终平衡数值；Classic 与 Foundry 也不是同一套规则。385 条记录包含技能、建筑和衍生单位，不等于 385 张可构筑牌。同名卡／技能不能按名称去重，使用 card ID。

原作卡面说明不是本作最终规则。沟壑、光环范围、攻城与终端主动等适配写在本作规则／牌池和引擎里，原数据不覆盖。新增内容要补公开说明与合法目标，不只把图片加进 `cards.js`。

## 启动方式与本机服务

| 场景 | 地址／入口 | 依赖与存档 |
| --- | --- | --- |
| 公网试玩 | [GitHub Pages](https://q871795224.github.io/yf-artifact/prototype/?v=0.3) | 浏览器 Worker 跑 Python；存种子和操作记录，按引擎版本恢复 |
| 本地游戏 | `python3 scripts/serve_prototype.py --open`，端口 8765 | Python HTTP API；内存对局，服务重启后旧局清空；同 Wi-Fi 手机可用电脑局域网 IP |
| 本机特效工作台 | `http://127.0.0.1:8741/effects-lab/`，或双击打开脚本 | 已配置 LaunchAgent；浏览器保存参数／预设，与游戏存档分开 |
| 无服务器特效预览 | 浏览器直接打开 `effects-lab/index.html` | 不用 Python；仍需保留相对目录中的共享脚本和美术 |

8741 的服务只监听本机；它不是公网部署，也不是默认允许手机局域网访问的游戏服务。静态服务器以仓库根目录为根，保证 `../prototype/`、`../references/` 路径能访问；只服务 `effects-lab/` 子目录会缺资源。

特效服务配置位于 `/Users/yifei.chen/Library/LaunchAgents/com.yifei.yf-artifact.effects-lab.plist`，日志在 `/Users/yifei.chen/Library/Logs/yf-artifact-effects-lab/`。登录 macOS 后自动启动，关闭终端不受影响，进程退出会拉起；不是未登录前就运行的系统守护进程。配置使用仓库和 Python 的绝对路径，移动目录／更换 Python 后要更新并重新加载。换电脑克隆仓库不会自动安装这个本机服务，可先用直接打开 HTML 或临时静态服务器。

查看、重启、停止与取消自启见[工作台说明](../../effects-lab/README.md#后台服务)。自动化环境中如 HOME 被重定向，可通过 `pwd.getpwuid(os.getuid()).pw_dir` 查询 macOS 账户主目录。

## 四种“版本”与缓存

| 名称 | 用途 | 不应混淆成 |
| --- | --- | --- |
| 正式版本 V0.3 | 产品发布、Git 标签、更新记录，定义于 `RELEASE_VERSION` | 第 3 次操作 |
| 引擎 SHA-256 | 静态构建按打包规则与数据生成，校验存档兼容性 | 仅靠产品版本号就能恢复任意旧局 |
| `view.version` | 单局已执行操作的版本，防止陈旧／重复提交 | 游戏发行版本 |
| Pyodide 314.0.8 | 固定运行环境与缓存桶版本 | 本作规则版本 |

另外，HTML 中脚本／CSS 与 Worker URL 的查询版本负责缓存更新。改动后要同时核对页面、样式、客户端、Worker 与规则包，不依赖刷新一定会换掉旧缓存。Service Worker 当前只缓存固定运行时，不缓存整套游戏；运行时断网可读取不代表页面、美术与全部对局流程已经离线可玩。

浏览器存档依赖种子、命令序列和相同引擎。V0.1 六列存档不强行迁移至 V0.2 五列；版本不符时提示新开局。不同浏览器／域名／端口／file URL 不共享存储，工作台参数迁移用 JSON 导入导出。游戏目前可导出记录供复查，没有开放导入任意对局的 UI。

## 验证与发布

先读变更范围，再选检查；仅改文档时检查事实、链接和 diff，不重新跑整套比赛。涉及规则、地图或动画的发布基准：

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
node --check prototype/app.js
node --check prototype/effects.js
node --check prototype/game-effects.js
python3 scripts/build_pages.py
```

在静态构建的 Chrome 中执行 `scripts/check_mobile_prototype.js`（真实按钮完整对局）、`scripts/check_game_feedback.js`（可见动画与缓存）、`scripts/check_battle_effects.js`（完整动画流程）。工作台变更用 `scripts/check_effects_lab.js`；Playwright CLI 函数接收 `page`，不要误写成解构参数。自动化使用独立 profile，不能抢用户日常浏览器、清空其存储或关闭别人的会话。

固定回放 `scripts/fixtures/playthrough-13.json` 包含种子、合法动作、回合与预期结局。规则改变可能改变动作 ID、坐标和完成轮数；应审查新回放、验证胜负与重放一致，再更新基准，不能只把断言改到绿灯。历史批量结果保留当时参数，当前脚本已演进，直接在最新代码重跑不保证与旧目录逐字一致；严格复现需要匹配代码提交和输入。

审查后提交并推送源码与版本标签，再发布：

```sh
python3 scripts/deploy_pages.py --repo q871795224/yf-artifact
gh run list --branch gh-pages --limit 3
curl -fsS 'https://q871795224.github.io/yf-artifact/version.json'
```

`main` 保存源代码与文档；`gh-pages` 保存构建产物。版本标签指向源码提交，不能把两个分支的提交 SHA 混用。发布脚本不负责替你提交／推送源码；也不要仅凭它输出网站地址就宣布上线，要等部署成功，并从公网确认 `version.json`、版本号、40 格棋盘与真实技能播放。

构建白名单只发布界面、共享特效、压缩美术、运行时、必要规则资料与回归 fixture；工作台、原 PNG、临时输出不进入 Pages。`dist/`、`output/` 忽略于源码，构建目录有标记保护，不能拿任意用户目录作为输出。

下一版改规则后要重启本地 Python 服务：它可能仍在内存中使用旧导入代码，而浏览器已经拿到新界面；只刷新网页不能更新服务进程。不要为此结束不属于本项目的服务。

## 收到试玩问题时怎样查

1. 先记录显示版本、设备／浏览器、回合、阶段；导出本局记录，并说明期望与实际发生的行为。
2. 检查模式和资源：公网是否为 browser runtime，本地是否仍是旧 Python 进程，脚本／CSS／规则包是否来自同次发布。
3. 规则问题核对合法动作、坐标、颜色、CD、资源、原型容量与阶段；自动索敌问题分“有敌未选到”与“射程内无敌”。
4. 视觉问题对比结算状态和显示效果；检查网格列数、SVG viewBox、真实目标、动画清理和减少动态效果设置。不要为修视觉随意改变伤害。
5. 拖局／余额问题保留回放与同轮经济数据，区分内容、供给、AI 和规则；增加单变量对照，不直接堆补偿或强制终局。

当前仍需真人验证实体手机点选、长局性能、五列拥堵和节奏；候选英雄完整可选流程、音效、构筑与商店均未交付；完整交战预测已在 V0.3 接入。不要将桌面 Chrome 的视口模拟、六局回归或当前固定 AI 的结果当成这些项目已经完成。

## V0.3 发布注意

- 用户七点反馈中，单位留白和河流／树木明确暂缓，当前继续铺满；交互采用棋子内技能／装备按钮，不把双击设为必要入口。
- 地图仍有 40 个节点，其中双方泉水中央各一格为建筑，38 格可放单位。出生／返场各有四个泉水单位格；原五格返场基准不能直接沿用。
- 素材库独立使用页面样式，卡牌按钮高度随图片撑开，避免继承特效工作台的 34px 固定按钮高度而重叠。
- 自制夜魇近战兵原件和来源记录在 `assets/custom/`，游戏使用 `prototype/assets/units/dire-melee.webp`；Pages 继续只发布游戏副本。素材库仍为本地工作台入口。
