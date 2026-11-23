# Migoo 卡图批量提交

在项目根目录执行：

```sh
python3 scripts/migoo_submit_batch.py assets/migoo/dota-original-heroes-classic/batch-next-twenty-roster.json --dry-run
python3 scripts/migoo_submit_batch.py assets/migoo/dota-original-heroes-classic/batch-next-twenty-roster.json --jobs 3
```

批次 JSON 使用 `heroes: [{"hero": "slug"}]`。每位英雄在同目录的
`slug-v01/` 下提供 `request.json`、`prompt.txt`、`notes.txt`。
`request.json` 保存模型、分辨率、比例及 `references: [{"path": "本地图片路径"}]`。
参考可带已核对的 `media_id` 或公开 `url`，避免反复上传；本地路径仍保留供核对。
已有成图返工时，`request.json` 可带 `source_task`，以原任务成图创建修订任务。
修订生成仍会消耗额度；脚本同样通过 `yf-migoo` 提交。
相对图片路径以启动目录为基准，因此从项目根目录启动。历史 `output/` 路径缺失时，脚本通过 [参考归档映射](../references/card-art/catalog.json) 寻找仓库副本；`--dry-run` 也会检查可解析性。

所有提交均经 `yf-migoo`，沿用其免费余额与暂停日期策略。脚本不延长暂停日期。
最多三并发，提交前检查账户近期任务，其他会话的任务也占用名额。
脚本只为释放提交名额查询状态，不下载、不检查成图；最后一组受理后即结束。

同一命令可以续跑，已保存任务号的请求不重复创建。结果不明时停止，先按保存的
任务号或官方任务列表核实；不盲目重发。仅对服务明确表示“并发忙且未开始”的
失败最多补交两次。同一批次根目录的 `.migoo-submit.lock` 防止该批次被两份脚本同时提交；不同批次仍共享账户并发额度。

每位英雄保存提交原始回包和日志，批次旁生成 `*-submissions.json`。
其中任务状态可能仍是 `generating`，提交数不代表完成数。原始回包和日志可能带临时签名下载 URL，仅保留本地，不随公开 Git 提交。

验证：`python3 -m unittest discover -s scripts -p 'test_migoo_submit_batch.py' -v`。
