# 我们的 Artifact

参考 Artifact，供个人游玩的单路卡牌战斗游戏。Godot 桌面版用于主要试玩和调试，手机可用浏览器兼容版。两端共用 Python 规则引擎。

**当前版本：V0.4 成长 Demo。** 新玩法与执行约定见 [实现说明](docs/design/growth-implementation.md)，验证见 [发布记录](docs/releases/v0.4.md)，版本记录见 [更新记录](CHANGELOG.md)。

**Godot 桌面试玩**：在本工作区运行 `./运行桌面版.sh`，或在 Windows 双击 `运行桌面版.cmd`。默认端口 8786 支持手机局域网试玩与电脑归档，见[启动与数据说明](desktop/README.md)。

**[在线试玩](https://q871795224.github.io/yf-artifact/)** · [GitHub 仓库](https://github.com/q871795224/yf-artifact)

线上版在浏览器内运行完整规则与 AI，不依赖本机服务或同一 Wi-Fi。首次打开需要加载运行文件，后续可使用浏览器缓存；已发布版本的进度留在当前浏览器。局域网试玩会自动存到电脑，静态兼容版更新后可下载手机各局再手动收集。

双击 `运行原型.command`，或运行 `python3 scripts/serve_prototype.py --open`，打开[手机战场试玩版](prototype/README.md)。电脑访问 `http://127.0.0.1:8765/prototype/`，手机连接同一 Wi-Fi 后替换为电脑局域网 IP。我方狼人／陈／全能，对手斧王／军团／斯温。右上角提供构筑、玩法、行动记录和导出；普通牌30张（9专属＋21自选）、物品牌10张，保存构筑后下一局生效。

调试视觉效果可双击 `打开特效工作台.command`，打开 [本地特效工作台](http://127.0.0.1:8741/effects-lab/)。当前电脑已配置后台服务，登录 macOS 后自动启动；支持十三类效果、逐帧预览和参数预设，使用方式见 [工作台说明](effects-lab/README.md)，不进入 Pages 发布。

构建静态站点：`python3 scripts/build_pages.py`；发布到 Pages：`python3 scripts/deploy_pages.py`。静态文件在独立 `gh-pages` 分支，源代码和资料在 `main`；`output/`、本地缓存及生成的 `dist/` 不进入源码分支。

## 文档入口

- [文档导航](docs/README.md)：当前规格、历史实验、原作资料与维护约定。
- [当前源码规则](docs/design/growth-implementation.md)：成长、卡池、构筑、状态与仇恨的实现行为及执行边界。
- [成长 Demo 设计记录](docs/design/growth-demo.md)：三级成长、回合经验、红绿英雄与专属卡的设计沿革。
- [后续路线图](docs/design/roadmap.md)：本轮试玩反馈、已实现试验与后置事项。
- [决策记录](docs/design/decision-log.md)：为什么从随机箭头走向仇恨、为什么补双经济终端，以及被替代的方案。
- [开发复盘与运维](docs/development/lessons-and-operations.md)：问题、解决办法、缓存／版本／发布／本机服务的坑点。
- [V0.4 发布验证](docs/releases/v0.4.md)：成长规则、构筑、浏览器与静态站点验证；[V0.3 归档](docs/releases/v0.3.md)保留历史结果。
- [Classic 本地参考库](references/artifact-classic/README.md)与[原作美术](references/artifact-classic/assets/README.md)：日常离线查询与素材来源。

早期草案和全部推演入口保留在文档导航中；它们记录当时的地图、技能和实验假设，不作为当前规则的替代。重要结果写入已提交的归档，临时日志和截图保留在忽略的 `output/`。

参考相邻的 `../yf-pokemon` 工作区组织方式；该项目的技术选型与玩法不自动成为本项目约束。
