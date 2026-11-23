# 卡牌插画工作流与试跑记录

当前生图入口已整理为[项目卡图 skill](../../.agents/skills/artifact-card-art/SKILL.md)，按类别查找[资源库](../../assets/art-library/README.md)和[参考归档](../../references/card-art/README.md)。下文保留早期模型试跑、旧操作方式和当时结论；现在常用“只提交，由用户在 Migoo 看图”，不默认下载和接入。历史余额、价格和暂停日期不作为实时依据。

更新于 2026-11-22。批量出图用 Migoo 的 GPT Image 2.6 Flare。从黑色法术起，卡图的画风主要参考 Artifact Classic 客户端无框原画，装备另用对应《刀塔》图标参考品类、主色与材质。11 月 21 日新增 150 张候选图，原图、缩略预览、提示词和任务记录见[候选插画索引](../../assets/migoo/README.md#11-月-21-日候选插画)。

## 出图决策

1. 按当前卡池和扩充方案核对缺图。规则已定的图用卡牌编号跟踪。储备图先定可画的动作或角色用途，用独立名称管理。法术先确定画面要读出的是攻击方向、目标变化还是站位变化。单位先确定体型、姿态和招牌器物。 [当前卡池](../../scripts/growth_cards.py) · [扩充方案](../design/demo-expansion-proposal.md)
2. 画面方向明确时直接用 Flare 出主图。早期曾在 108 的 WSL 用 Z-Image Turbo 试主体或构图；仅在用户当前明确要求连接该机器时使用。目标接近 Classic 画风时，每张用两张同题材的无框原画，分别参考绘画笔触、光线和空间感。
3. 每张单独写地点、时段、主光和动作。强调自然材质、清楚的大色块和松紧有别的边缘。高光集中到脸、手、器物或法术作用点，背景保留较宽的明暗层次。早期原创概念曾从《刀塔》的职业、能力主题和营地生态取材，独立设计外形。画原版英雄或装备时保留身份、种族、装备和标志性特征，只重新设计动作、镜头、场景和光线；普通单位与野怪按实际任务保留族群特征。
4. 以 9:16 满版纯插画交付，检查卡框、文字、编号、水印和白边。缩到约 48 像素宽看主体轮廓、武器和动作。保存原图、提示词、参考图、模型、尺寸和 SHA-256，选定主图与接入试玩分别记录。 [正式素材索引](../../assets/custom/README.md)

## 参考图来源

| 用途 | 来源 | 本地位置与恢复 |
| --- | --- | --- |
| Classic 无框原画 | 在 108 的 WSL 用 Source 2 Viewer CLI 从 Classic 的 `game/dcg/pak01_dir.vpk` 导出。两个卡包共 326 张 `full_art`，分辨率为 1024×1024，部分图有白边 | 完整原图已同步到本机的 `output/classic-full-art/set00/full_art/` 和 `set01/full_art/`，文件按 `<卡牌 ID>_psd.png` 命名。整包哈希见同目录的 `SHA256SUMS`，也可以在[插画审阅页](http://127.0.0.1:8741/effects-lab/art-review.html)筛选无框原画 |
| 《刀塔》装备图标 | 从 108 的 Steam 客户端 `game/dota/pak01_dir.vpk` 导出 `panorama/images/items/`。本批 12 件来自 VPK，另 8 件来自 Valve 的 Steam CDN | WSL 项目下的 `output/research/export/dota-native-items/panorama/images/items/`。本机客户端样图在 `output/dota-native-equipment/`，补齐的官方图标在其 `valve/` 子目录。CDN 为 `cdn.cloudflare.steamstatic.com`，路径为 `apps/dota2/images/dota_react/items/<物品 ID>.png` |
| 已有自制参考 | 只在早期批次混用。蓝色法术每张用了 Classic 无框图和一张已有自制图 | 参考路径在[蓝色法术提示词](../../assets/migoo/blue-spell-concepts/briefs.json)逐张记录 |

`briefs.json` 保留每张实际上传的路径和顺序。上一批用的 Classic 选图仍在 `output/blue-black-art-references/`，后续可从完整原图目录按卡牌 ID 选图。参考缓存和生成日志在 Git 忽略的 `output/` 下。装备生成时，第一张参考用对应官方图标，第二张用同类 Classic 插画。

## Migoo 批量生成与验收

本批实际返回模型为 GPT Image 2.6 Flare，模型 ID 为 `gpt-image-26-flare`。每单一张，1K、9:16，成图为 768×1360 PNG。提交前用 `yf-migoo models image --json` 和 `yf-migoo account --json` 查询当前模型、标价和余额。每波最多三单，等上一波完成后再提交。

```bash
yf-migoo image create "$art_description" \
  --notes "$art_style" --image "$art_reference_1" --image "$art_reference_2" \
  --model gpt-image-26-flare --resolution 1K --ratio 9:16 --count 1 \
  --skip-questions --wait --output "$art_batch_dir" --json
```

有任务 ID 时先用 `yf-migoo task get <task_id> --wait --output <目录>` 续查和下载。塔芯共振首单明确返回临时服务失败，同一组提示词和参考重试后成功。归档时核对 `status`、`applied.models`、文件完整性和尺寸，并记录任务 ID、媒体 ID 和 SHA-256。

| 观察 | 本轮结论 |
| --- | --- |
| 蓝色法术混用自制图与原版图 | 整体风格更接近此前的自制图。五点落雷的分叉偏多，小图更像范围雷暴。涡流牵阵里人物被拉向中心的动作偏弱。 [蓝色法术预览](../../assets/migoo/blue-spell-concepts/preview.jpg) |
| 黑色法术每张用两张 Classic 无框原画 | 手绘感和局部高光更接近目标。踏隙追击的动作清楚，换影突入的前后两个人影在小图上容易混在一起。 [原版与成图对照](../../assets/migoo/black-spell-concepts/style-comparison.jpg) |
| 四色单位与野怪强调轮廓 | 体型、装备和姿态能拉开角色。雷滩披甲兽的岩甲仍和石傀儡相近。 [四色小卡总览](../../assets/migoo/four-color-unit-concepts/small-preview.jpg) · [野怪预览](../../assets/migoo/neutral-camp-concepts/preview.jpg) |
| 装备使用官方图标和同类原画 | 清莲宝珠、黯灭、斯嘉蒂之眼的小图辨识度较好，白银之锋和深渊之刃更像普通刀剑。 [图标与成图对照](../../assets/migoo/dota-equipment-concepts/icon-comparison.jpg) |

11 月 21 日查询时，Flare 1K 的平台标价为每张 5.33。生成流水抽查为每单扣 1，含一次后续重试的失败任务。免费余额从这轮开始时的 100 读到末次的 50，余额变化与流水口径尚未对齐。

## 试跑与出图路线

| 路线 | 实测 | 用在什么地方 |
| --- | --- | --- |
| Mac 的 `yf-asset`，ComfyUI + FLUX.2 Klein 4B | M5 Pro／24 GB，陨星锤和铁树枝干守护各 768×1360，约 60 秒和 52 秒；前者轮廓醒目，后者有上下边带 | 设备离线时快速看轮廓和大构图 |
| 108 WSL，ComfyUI + Z-Image Turbo INT8 | RTX 4070 12 GB，两道题在 768×1360 用时约 10–32 秒；移除卡名、编号并直接描述画面后，复跑两张均无文字 | 默认出测试图，可据成片选择主图 |
| 108 WSL，HiDream-O1 FP8 | 两张裁剪后的参考图，1440×2560，40 步，约 6 分 47 秒；雨后石廊有质感，藤蔓却读成树，护盾较弱 | 需要多参考图时做单张对照 |
| Migoo，GPT Image 2.6 Flare | 前两批为 8 张和 54 张，均为 768×1360。11 月 21 日另生成 150 张候选图 | 需要更细的材质、场景层次或清晰的法术效果时出主图 |

108 的实验目录名是 `yf-artifact-image-lab`。在 WSL 内执行 `./run-z-image-lab.sh <工作流名>`，脚本从同目录读取 `<工作流名>.z-image.workflow.api.json`，结果写入 `output/yf-artifact/`。法术双参考图的复现命令是 `./run-hidream-lab.sh`。ComfyUI 仅在 WSL 回环地址启动，出图后退出。

## 当前素材覆盖

原型中编号为 61001–61012 的单位、62001–62019 的法术、63001–63006 的专属，以及 65001–65022 的装备与消耗品均已有独立插画。108 补足了最后 6 件装备和 4 件消耗品。扩充方案中已生成的两位英雄、专属、四张普通法术及五件装备也已入库。 [自制素材索引](../../assets/custom/README.md) · [首批扩充插画](../../assets/migoo/README.md)

新增 150 张放在候选素材目录，当前试玩仍按原有卡牌 ID 解析图片。上架前先选主图并确认卡牌或建筑映射，再生成游戏内 WebP。 [候选插画索引](../../assets/migoo/README.md#11-月-21-日候选插画)

## 遇到的问题与处理

| 问题 | 处理 |
| --- | --- |
| Codex Personal 的后续轮次反复报 `Broken pipe` | 会话卡在模型响应流，后续轮次未调用 Migoo。第一批已完成，先查会话与 Migoo 任务状态，再续做缺项。 |
| Migoo 有任务 ID 却没有图 | 平台当时最多并发生成 3 张，超出上限的记录显示未开跑。按任务阶段判断，已受理的继续查原任务，明确未启动的等空位再提交。 |
| 零点前提交仍出现零点后的扣额 | 11 月 20 日最后一单在上海时间 23:59:46 提交，最后三单在零点后各记 1 额度。想用当天额度，要给生成和入账留时间。 |
| 背景反复出现同一套森林或暗岩 | 先按法术、材质和气氛选不同参考，再单独写每张的地点、时段和主光。石廊、堡垒、雪地、工坊各有用途。 |
| 卡框或标题进入插画 | 图生图先裁掉原卡 UI。Z-Image 的纯文生图提示词省掉卡名、编号和操作说明，直接写画面内容。补图时知识秘典的翻页版带伪文字，改画合拢的书与封面，复跑后入库。 |
| 把机器号当成了 107 | 实际生图机是 108，SSH 先进入 Windows，再执行 WSL 命令。每次部署前用 `nvidia-smi` 核对显卡和空闲显存。 |
| 安装 CUDA 依赖和大权重耗时长 | 使用独立虚拟环境，优先复用已缓存且通过 CUDA 运算验证的 PyTorch。大文件分段下载并校验 SHA-256，网络波动时续传已有数据。 |

模型能力和许可见官方说明。榜单用于筛选，选图依据是同题样图。 [图像编辑榜](https://artificialanalysis.ai/image/leaderboard/editing) · [Z-Image Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) · [HiDream-O1-Image](https://huggingface.co/HiDream-ai/HiDream-O1-Image)
