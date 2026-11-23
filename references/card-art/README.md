# 卡图参考资源

这里归档已实际用于生图的参考图，并用 [catalog.json](catalog.json) 映射旧路径。原目录、原文件和旧版本全部保留；相同 SHA-256 的图片复用已有副本。卡图成品与任务按[资源分类索引](../../assets/art-library/README.md)查询，选图和提示词方法见[项目 skill](../../.agents/skills/artifact-card-art/SKILL.md)。

## 按用途找参考

| 用途 | 归档分类 | 使用方式 |
| --- | --- | --- |
| 绘画笔触、材质、明暗、空间 | `classic-style` | 从 Classic 客户端无框原画选同题材参考，上传前检查白边 |
| 原版英雄外貌、种族、装备 | `hero-identity` | Valve 官方透明渲染锁定身份；重新绘制动作、镜头和场景 |
| 原版装备轮廓、构件与主色 | `equipment-identity` | 先看官方图标，明确杖头、柄、刃、护手等关系 |
| 野怪种属和家族特征 | `neutral-identity` | 优先客户端渲染，再区分家族与成员 |
| 普通单位、族群和漫画配角 | `lore-and-comics` | 记录出处；原作种族与原创岗位分开表述 |
| 既有单位出场、施法者与目标 | `existing-art-or-cast` | 用作角色连续性参考；画法仍以 Classic 为准 |

分类由历史文件名和路径推断，具体对象以图片及原批次记录为准。`files/` 保存新增归档副本；已有仓库参考图直接复用，位置见 `aliases` 和每条 `asset`。

## 全量本地库与可移植子集

`catalog.json` 的 `local_collections` 记录整理时可见的本地参考库及逐图哈希，包括 Classic 无框原画、Valve 英雄图、装备图标、官方设定、漫画探索图和野怪客户端渲染。全量缓存仍在 Git 忽略的 `output/` 下；本次仅把已使用且仓库缺少副本的参考图复制入库。

`references` 列表记录本次引用的参考图；`portable: true` 表示仓库已有可用副本。`aliases` 把旧的 `output/...` 或历史素材路径映射到仓库文件。未使用的全量缓存保留本地，未声称全部随 Git 发布。

刷新索引：

```sh
python3 scripts/art_library.py
python3 scripts/art_library.py --archive-references
```

第二条命令按哈希复制新增已用参考，不移动或删除原件。批量提交器会在旧本地路径缺失时通过此映射寻找归档副本，原提示词和请求文件无需批量改写。原任务中的 media ID、模型和参考顺序仍以对应 `request.json` 或 `briefs.json` 为准。

## 来源恢复

Valve 官方英雄渲染地址形式：`https://cdn.cloudflare.steamstatic.com/apps/dota2/videos/dota_react/heroes/renders/<hero_key>.png`。官方装备图标地址形式：`https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/<item_id>.png`。具体 key、来源和旧路径看原批次记录，不凭中文名称猜文件名。

Classic 全量导出和客户端渲染的历史来源见[原工作流](../../docs/development/card-art-workflow.md#参考图来源)，漫画与设定来源见[设定美术交接](../../docs/research/dota-lore-art-handover.md)。需要全量库时先查现有本机缓存；连接 108 须遵循用户当前明确授权，不因恢复索引而自动连接。

原始任务回包、日志和临时签名下载 URL 保留本地并由 Git 忽略。公开仓库保存提示词、任务号、来源、分类索引及图片；不发布整份会话、账户信息或临时凭据。
