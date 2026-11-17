# 我们的 Artifact

参考 Artifact，面向手机、供个人游玩的单路卡牌战斗游戏。已接入现有 Python 推演引擎，可在手机浏览器手动操作、与 AI 完成拆塔和基地胜负的完整对局。

**当前版本：V0.2（五列战场与战斗特效）。** V0.1 保留为原六列正式试玩版本，版本记录见 [更新记录](CHANGELOG.md)。

**[在线试玩](https://q871795224.github.io/yf-artifact/)** · [GitHub 仓库](https://github.com/q871795224/yf-artifact)

线上版在浏览器内运行完整规则与 AI，不依赖本机服务或同一 Wi-Fi。首次打开需要加载运行文件，后续可使用浏览器缓存；进度保存在当前浏览器，不跨设备同步。

双击 `运行原型.command`，或运行 `python3 scripts/serve_prototype.py --open`，打开[手机战场试玩版](prototype/README.md)。电脑访问 `http://127.0.0.1:8765/prototype/`，手机连接同一 Wi-Fi 后替换为电脑局域网 IP。固定阵容、预设牌库；右上角可查看玩法、行动记录及导出对局。

调试视觉效果可双击 `打开特效工作台.command`，打开 [本地特效工作台](http://127.0.0.1:8741/effects-lab/)。当前电脑已配置后台服务，登录 macOS 后自动启动；支持十二类效果、逐帧预览和参数预设，使用方式见 [工作台说明](effects-lab/README.md)，不进入 Pages 发布。

构建静态站点：`python3 scripts/build_pages.py`；发布到 Pages：`python3 scripts/deploy_pages.py`。静态文件在独立 `gh-pages` 分支，源代码和资料在 `main`；`output/`、本地缓存及生成的 `dist/` 不进入源码分支。

## 文档入口

- [文档导航](docs/README.md)：当前规格、历史实验、原作资料与维护约定。
- [V0.2 规则现状](docs/design/current-rules.md)：已确认方向、原型数值和待讨论项。
- [决策记录](docs/design/decision-log.md)：为什么从随机箭头走向仇恨、为什么补双经济终端，以及被替代的方案。
- [开发复盘与运维](docs/development/lessons-and-operations.md)：问题、解决办法、缓存／版本／发布／本机服务的坑点。
- [V0.2 验证归档](docs/releases/v0.2.md)：完整对局、动画、视口、公网验证及测试局限。
- [Classic 本地参考库](references/artifact-classic/README.md)与[原作美术](references/artifact-classic/assets/README.md)：日常离线查询与素材来源。

早期草案和全部推演入口保留在文档导航中；它们记录当时的地图、技能和实验假设，不作为当前规则的替代。重要结果写入已提交的归档，临时日志和截图保留在忽略的 `output/`。

参考相邻的 `../yf-pokemon` 工作区组织方式；该项目的技术选型与玩法不自动成为本项目约束。
