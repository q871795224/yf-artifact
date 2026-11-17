# 我们的 Artifact

参考 Artifact，面向手机、供个人游玩的单路卡牌战斗游戏。已接入现有 Python 推演引擎，可在手机浏览器手动操作、与 AI 完成拆塔和基地胜负的完整对局。

**当前版本：V0.2（五列战场与战斗特效）。** V0.1 保留为原六列正式试玩版本，版本记录见 [更新记录](CHANGELOG.md)。

**[在线试玩](https://q871795224.github.io/yf-artifact/)** · [GitHub 仓库](https://github.com/q871795224/yf-artifact)

线上版在浏览器内运行完整规则与 AI，不依赖本机服务或同一 Wi-Fi。首次打开需要加载运行文件，后续可使用浏览器缓存；进度保存在当前浏览器，不跨设备同步。

双击 `运行原型.command`，或运行 `python3 scripts/serve_prototype.py --open`，打开[手机战场试玩版](prototype/README.md)。电脑访问 `http://127.0.0.1:8765/prototype/`，手机连接同一 Wi-Fi 后替换为电脑局域网 IP。固定阵容、预设牌库；右上角可查看玩法、行动记录及导出对局。

调试视觉效果可双击 `打开特效工作台.command`，打开 [本地特效工作台](http://127.0.0.1:8741/effects-lab/)。当前电脑已配置后台服务，登录 macOS 后自动启动；支持十二类效果、逐帧预览和参数预设，使用方式见 [工作台说明](effects-lab/README.md)，不进入 Pages 发布。

构建静态站点：`python3 scripts/build_pages.py`；发布到 Pages：`python3 scripts/deploy_pages.py`。静态文件在独立 `gh-pages` 分支，源代码和资料在 `main`；`output/`、本地缓存及生成的 `dist/` 不进入源码分支。

- [初步玩法与讨论记录](docs/design/initial-ideas.md)
- [战场与回合草案](docs/design/combat-draft.md)
- [纸面推演与临时数据](docs/design/paper-simulation.md)
- [六回合开局推演：四正向攻击](docs/design/simulations/opening-02.md)
- [英雄名单与自身能力草案](docs/design/heroes-draft.md)
- [英雄批量推演：2,400 局与逐步回放](docs/design/simulations/hero-batch-01/README.md)
- [自动索敌对照：4,800 局与成对回放](docs/design/simulations/hero-batch-02/README.md)
- [首批普通牌与物品牌池](docs/design/first-card-pool.md)
- [扩展牌池：每色六种普通牌与十二件装备](docs/design/expanded-card-pool.md)
- [完整对局实验：建筑、牌库、物品与八场景对照](docs/design/simulations/match-batch-01/README.md)
- [扩充牌池与推进 AI 的四组对照](docs/design/simulations/match-batch-02/README.md)
- [金币积压诊断：物品供给、消费与装备状态](docs/design/simulations/item-economy-01/README.md)
- [双经济终端候选：高费卡与 25 金进攻装备](docs/design/finisher-card-pool.md)
- [双经济终端对照：1,728 局与超时续测](docs/design/simulations/finisher-batch-01/README.md)
- [Artifact Classic 本地数据参考库](references/artifact-classic/README.md)：英雄、卡牌、小兵、技能与中英文文本，可离线查询。
- [首批原版美术素材](references/artifact-classic/assets/README.md)：已缓存 130 张原版图片，含十二名候选英雄头像及候选牌池中文卡面，已用于手机界面原型。

参考相邻的 `../yf-pokemon` 工作区组织方式；该项目的技术选型与玩法不自动成为本项目约束。
