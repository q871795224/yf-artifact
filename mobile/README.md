# 河岸交战安卓客户端

`game/` 是完整对局界面，`project/` 保存棋盘场景、着色器、自制棋子边框和 Android 导出配置。`yf_match.py` 用同仓库的 Python 规则运行离线对局，`android/` 是连接 Godot 和 CPython 的桥接代码。

## 换电脑继续开发

从 GitHub 克隆仓库，再从原来的开发机复制 **YF-Riverbank-Local-Assets.zip** 到仓库的 `output/mobile-local-assets.zip`。然后在仓库根目录运行以下命令，将 `<godot>` 换成 Godot 4.7.1 可执行文件的路径。在 Windows 开发时也可以按以下步骤使用 WSL。

```sh
python3 mobile/build_apk.py --godot "<godot>" --stage-only
YF_MATCH_RULES="$PWD/mobile/yf_match.py" "<godot>" --path output/mobile-match/project
```

也可以在 Godot 编辑器打开 `output/mobile-match/project/project.godot`。长期修改请保存到仓库的 `mobile/game/` 或 `mobile/project/`，再运行准备命令同步到生成目录。规则和牌组代码在 `scripts/`。试玩存档在 Godot 的本机用户目录。

本地素材包包含这版外观依赖的原版模型、贴图、粒子、音效和字体。文件清单在 [local-assets.txt](local-assets.txt)。构建脚本会从压缩包读取所需文件并报告缺项。原开发机保留了两份预览工程，可以运行以下命令重新生成素材包。

```sh
python3 mobile/local_assets.py
```

生成文件位于 `output/mobile-local-assets.zip`。也可通过 `--art-project` 和 `--effects-project` 指定两份预览原始目录。

## 构建 APK

使用 Linux 或 WSL，准备 Godot 4.7.1、同版本 Android debug 导出模板、JDK 17、安装了 Android 平台 36 和 Build Tools 36.0.0 的 SDK、Zig、解包后的 CPython 3.14.0 Android arm64 库。CPython 目录应包含 `prefix/lib/libpython3.14.so`。在 Godot 的 Editor Settings 设置 Android SDK 和 Java SDK 路径，准备位于 `~/.android/debug.keystore` 的调试签名文件。可用 `--keystore` 指定其他路径，覆盖安装时要用相同签名。

```sh
python3 mobile/build_apk.py --godot "<godot>" --template "<android_debug.apk>" \
  --jdk "<jdk-17>" --sdk "<android-sdk>" --zig "<zig>" --arm "<cpython-arm64>"
```

如需 Android 模拟器包，再传 `--x86 "<cpython-x86_64>"`。输出在 `output/mobile-match/Riverbank-Match.apk`。可以用 `--assets` 指定素材 ZIP 的位置。
