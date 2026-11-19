# Godot 桌面试玩

桌面版是项目的主要调试界面。Godot 负责棋盘、输入、详情、日志与演出，Python 继续负责合法行动、AI、伤害、资源、预测和胜负。手机浏览器连接同一服务，GitHub Pages 通过浏览器 Worker 运行同一套 Python 规则。

## 运行

本工作区已准备 Godot 4.7.1。在 Windows 有 WSLg 的情况下可双击仓库根目录的 `运行桌面版.cmd`，也可以在 WSL 终端运行：

```sh
cd ~/projects/yf-artifact
./运行桌面版.sh
```

其他电脑可以安装 [Godot 4 标准版](https://godotengine.org/download/archive/) 和 Python 3.10 或以上，再运行 `python3 scripts/run_desktop.py --godot /path/to/Godot`。专门给手机联机时加 `--lan`。本机入口默认端口为 8782，启动器会复用已经运行的同版本归档服务；端口占用时可用 `--port` 改一处。

可单独运行 `python3 scripts/run_desktop.py --service-only --lan`，让手机在 Godot 窗口关闭后仍能继续玩。启动器自己启动的服务会在桌面游戏退出时关闭，盘上的对局可在服务重启后继续。

有 Godot 编辑器时可以打开 `desktop/project.godot`。编辑器运行仍需先开 Python 服务；独立启动器会自动传递服务地址和仓库美术路径。

## 桌面操作

- 单击英雄显示移动范围，右键棋子查看详情。按 Esc 取消当前目标选择。
- 战场单位使用同尺寸牌面。牌名在顶栏，插画在中间，攻、甲、血固定在底栏。插画取自仓库现有素材，当前规则数值由 Python 返回。
- 点击手牌在右边查看描述、费用和行动。构筑保存到下一局，普通牌仍为 21 张自选加 9 张专属。
- 交战记录与棋盘同时可见。右上角「特效预览」可重复检查对撞、塔炮格挡和阵亡，也可调速或关闭样例音效。
- 「记录文件」打开电脑归档目录，「导出对局」另存当前对局 JSON。

## 手机对局回收

| 从哪里玩 | 怎么留档和回收 |
| --- | --- |
| 手机连接电脑的局域网地址，打开 `/prototype/` | 用地址和端口连接。例如本机相同 Wi-Fi 上的 `http://192.168.1.3:8782/prototype/`。每次成功行动自动写入电脑，无需另传文件。 |
| 手机上打开 GitHub Pages 的浏览器版 | 兼容版更新部署后，菜单「本机对局」里可以下载每局的 JSON。回到同一 Wi-Fi 后，打开电脑的浏览器版，使用「收集对局文件」上传。 |
| 公网兼容版的旧存档 | 从旧界面导出当前局，再使用家里电脑的「收集对局文件」。缺少指纹或规则不一致的记录保留原文件及来源，标为待复核。 |

电脑目录为 `output/playtests/`，手机带回的记录在其 `imported/` 子目录。记录包含规则指纹、种子、构筑、命令、结果和可用的时间或统计信息。Git 忽略记录目录。清理手机浏览器的站点存储前，可先下载所需对局。

## 验证

`python3 -m unittest discover -s scripts -p 'test_*.py'` 覆盖共享规则、HTTP 和浏览器存档。可起一个使用临时归档目录的测试服务，再运行原生客户端的自动操作流程：

```sh
python3 scripts/serve_prototype.py --host 127.0.0.1 --port 18983 --archive-dir output/desktop-check/replays
```

在另一终端运行：

```sh
ARTIFACT_SERVER=http://127.0.0.1:18983 ARTIFACT_SEED=2 \
  XDG_DATA_HOME="$(mktemp -d)" \
  godot --headless --path desktop --script res://smoke_test.gd
```
