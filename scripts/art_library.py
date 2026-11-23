#!/usr/bin/env python3
"""Build a non-destructive, offline catalog of card art and its references."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
CATEGORIES = {
    "heroes": "原版英雄",
    "equipment": "原版装备与返工",
    "units": "普通单位与漫画配角",
    "neutrals": "野怪、家族与成员",
    "spells": "原创法术与单位出场场景",
    "hero-skills": "英雄技能与专属卡",
    "structures": "建筑与泉水",
    "explorations": "旧方向与原创题材探索",
    "unclassified": "待分类",
}


def read_json(path, default=None):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def repo_path(value, root=ROOT, base=None):
    if not isinstance(value, str) or not value or "://" in value or value.isdigit():
        return None
    path = Path(value)
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(Path(root).resolve())
        except ValueError:
            return None
    if path.parts and path.parts[0] in {"assets", "output", "references", "prototype", "temp"}:
        return root / path
    if base:
        candidate = base / path
        if candidate.exists():
            return candidate
    return root / path


def relative(path, root):
    return path.relative_to(root).as_posix()


def resolve_reference_path(value, root=ROOT):
    """Resolve historical output/ aliases after the source image has been archived."""
    direct = Path(value)
    if direct.is_absolute() and direct.is_file():
        return direct.resolve()
    path = repo_path(value, root)
    if path and path.is_file():
        return path
    aliases = read_json(root / "references/card-art/catalog.json", {}).get("aliases", {})
    key = relative(path, root) if path else value
    archived = repo_path(aliases.get(key), root)
    return archived if archived and archived.is_file() else path


def category(name):
    if name in {"dota-hero-role-concepts", "dota-hero-portrait-layout", "red-unit-redesign"} or name.startswith("hero-archetype"):
        return "explorations"
    if "equipment" in name:
        return "equipment"
    if name.startswith("dota-original-heroes") or name in {"hero-drow-ranger", "hero-timbersaw"}:
        return "heroes"
    if name.startswith(("hero-skill", "hero-ultimates", "signature-")):
        return "hero-skills"
    if "spell" in name:
        return "spells"
    if "neutral" in name:
        return "neutrals"
    if "building" in name:
        return "structures"
    if "unit" in name or name.startswith("comic-npc"):
        return "units"
    return "unclassified"


def reference_kind(path):
    text = path.as_posix().lower()
    if "classic" in text or re.search(r"/\d{4,5}_psd\.", text) or "blue-black-art-references" in text:
        return "classic-style"
    if "equipment" in text or "native-items" in text:
        return "equipment-identity"
    if "hero-art-references" in text or "/hero-" in text:
        return "hero-identity"
    if "neutral-client" in text or "neutral-reference" in text:
        return "neutral-identity"
    if "comic" in text or "lore-reference" in text or "handover" in text:
        return "lore-and-comics"
    if "migoo" in text:
        return "existing-art-or-cast"
    return "other"


def safe_source_url(value):
    if not isinstance(value, str) or not value.startswith(("https://", "http://")):
        return None
    parts = urlsplit(value)
    if "/media/signed/" in parts.path:
        return None
    if re.search(r"(?:^|&)(?:sig|signature|token|key|expires)=", parts.query, re.I):
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return value


def rows(document):
    if isinstance(document, list):
        return [entry for entry in document if isinstance(entry, dict)]
    if not isinstance(document, dict):
        return []
    for key in ("jobs", "images", "equipment", "assets", "items", "entries"):
        if key not in document:
            continue
        value = document[key]
        if isinstance(value, dict):
            return [entry for group in value.values() if isinstance(group, list) for entry in group if isinstance(entry, dict)]
        return rows(value)
    return []


def build(root=ROOT, archive_references=False):
    root = Path(root).resolve()
    migoo = root / "assets/migoo"
    entries, reference_paths, issues = {}, set(), []
    hash_cache = {}

    def digest(path):
        if path not in hash_cache:
            hash_cache[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        return hash_cache[path]

    def add_references(record, base):
        refs = record.get("references", record.get("reference_images", [])) or []
        if isinstance(refs, str):
            refs = [refs]
        paths = []
        for ref in refs:
            value = ref.get("path") if isinstance(ref, dict) else ref
            path = repo_path(value, root, base)
            if path:
                reference_paths.add(path)
                paths.append(relative(path, root))
        for cast in record.get("cast", []) or []:
            if not isinstance(cast, dict):
                continue
            for key in ("source_image", "reference"):
                path = repo_path(cast.get(key), root, base)
                if path:
                    reference_paths.add(path)
        return paths

    def job_directory(batch, record):
        for key in ("image", "file", "path"):
            path = repo_path(record.get(key), root, batch)
            if path and path.suffix.lower() in IMAGE_SUFFIXES:
                return path.parent
        slug = record.get("slug") or record.get("item_id") or record.get("hero") or record.get("asset_key")
        if isinstance(slug, str):
            choices = [batch / (slug + "-v01"), batch / slug]
            if record.get("color"):
                choices.insert(0, batch / str(record["color"]) / slug)
            return next((path for path in choices if path.is_dir()), choices[1])
        name = record.get("name")
        for entry in entries.values():
            if entry["batch"] == batch.name and entry["name"] == name:
                return root / entry["directory"]
        return None

    def merge(batch, directory, record, source, authoritative=False):
        if not directory or not directory.is_relative_to(migoo):
            return
        key = relative(directory, root)
        entry = entries.setdefault(key, {
            "id": key, "directory": key, "batch": batch.name,
            "category": category(batch.name), "name": record.get("name") or directory.name,
            "task_id": None, "platform_status": "unknown", "references": [],
            "metadata": [], "source_task": None,
        })
        if source not in entry["metadata"]:
            entry["metadata"].append(source)
        if authoritative or not entry["task_id"]:
            entry["task_id"] = record.get("task_id") or entry["task_id"]
            entry["platform_status"] = record.get("status", entry["platform_status"])
        for field in ("name", "source_task", "review_status", "user_review", "latest_revision_task_id"):
            if record.get(field) is not None:
                entry[field] = record[field]
        for field in ("image", "file", "path"):
            image = repo_path(record.get(field), root, batch)
            if image and image.is_file() and image.suffix.lower() in IMAGE_SUFFIXES:
                entry["recorded_image"] = relative(image, root)
        entry["references"] = sorted(set(entry["references"] + add_references(record, batch)))
        remote = []
        for ref in record.get("references", record.get("reference_images", [])) or []:
            value = ref.get("url") if isinstance(ref, dict) else ref
            url = safe_source_url(value)
            if url:
                remote.append(url)
        if remote:
            entry["reference_urls"] = sorted(set(entry.get("reference_urls", []) + remote))
        models = record.get("actual_models") or record.get("models_returned") or record.get("applied", {}).get("models")
        if models:
            entry["models_returned"] = models
        model = record.get("model") or record.get("model_requested") or record.get("requested_model")
        if model:
            entry["model_requested"] = model
        for field in ("official_source", "source_url"):
            url = safe_source_url(record.get(field))
            if url:
                entry[field] = url
        for key in ("description", "prompt", "brief", "notes"):
            if isinstance(record.get(key), str):
                entry.setdefault("prompt_excerpt", record[key][:320])
        for filename, field in (("prompt.txt", "prompt_file"), ("notes.txt", "notes_file")):
            if (directory / filename).is_file():
                entry[field] = relative(directory / filename, root)

    batches = [path for path in sorted(migoo.iterdir()) if path.is_dir()] if migoo.exists() else []
    for batch in batches:
        for name in ("briefs.json", "manifest.json"):
            path = batch / name
            for record in rows(read_json(path, {})):
                merge(batch, job_directory(batch, record), record, relative(path, root))
        for path in sorted(batch.rglob("request.json")):
            if "attempts" in path.relative_to(batch).parts:
                continue
            record = read_json(path)
            if record:
                merge(batch, path.parent, record, relative(path, root), authoritative=True)
        for original in sorted(batch.rglob("original.png")):
            if "references" in original.relative_to(batch).parts:
                continue
            result = read_json(original.parent / "task-result.json", {})
            merge(batch, original.parent, result, relative(original, root))
        if batch.name == "dota-hero-portrait-layout":
            for preview in batch.glob("*/preview.png"):
                receipt = read_json(preview.parent / "task-result.json", {})
                record = {"name": "美杜莎背景合成实验", "image": relative(preview, root),
                          "task_id": receipt.get("task_id"),
                          "references": [relative(path, root) for path in preview.parent.glob("background.png")]}
                merge(batch, preview.parent, record, relative(preview, root))
    for record in rows(read_json(migoo / "manifest.json", {})):
        directory = repo_path(record.get("path"), root)
        if directory:
            merge(directory.parent, directory.parent, record, "assets/migoo/manifest.json")

    integrations = {}
    for asset in rows(read_json(root / "assets/custom/manifest.json", {})):
        sha = asset.get("source", {}).get("sha256")
        if sha:
            integrations[sha] = asset.get("id")

    for entry in entries.values():
        directory = root / entry["directory"]
        original = directory / "original.png"
        if not original.is_file() and entry.get("recorded_image"):
            original = root / entry["recorded_image"]
        if not original.is_file() and entry["task_id"]:
            original = directory / (entry["task_id"] + "_1.png")
        entry["local_image"] = relative(original, root) if original.is_file() else None
        entry["availability"] = "local" if entry["local_image"] else "task-only" if entry["task_id"] else "prepared"
        if original.is_file():
            entry["sha256"] = digest(original)
            if entry["sha256"] in integrations:
                entry["integrated_asset_id"] = integrations[entry["sha256"]]
        entry["candidate_only"] = not bool(entry.get("integrated_asset_id"))
        parts = directory.relative_to(migoo).parts
        if "iterations" in parts:
            index = parts.index("iterations")
            entry["variant_of"] = relative(migoo.joinpath(*parts[:index]), root)
            entry["version_role"] = "historical-iteration"
        elif entry.get("source_task"):
            entry["version_role"] = "source-task-revision"

    # Existing image copies are reused by hash; originals and failed attempts remain untouched.
    existing_by_hash = {}
    for base in (root / "assets/migoo", root / "assets/custom", root / "references/card-art/files"):
        if base.exists():
            # Named originals are portable; old mt_* download duplicates may be ignored.
            for path in sorted(base.rglob("*"), key=lambda item: (item.name != "original.png", item.as_posix())):
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                    existing_by_hash.setdefault(digest(path), path)

    old_refs = read_json(root / "references/card-art/catalog.json", {})
    old_aliases = old_refs.get("aliases", {})
    reference_paths.update(root.glob("imagen_original_*.png"))
    aliases, refs = {}, []
    for source in sorted(reference_paths):
        key = relative(source, root)
        actual = source if source.is_file() else resolve_reference_path(key, root)
        if not actual or not actual.is_file():
            refs.append({"source": key, "kind": reference_kind(source), "available": False})
            issues.append({"kind": "missing-reference", "path": key})
            continue
        sha = digest(actual)
        target = existing_by_hash.get(sha)
        kind = reference_kind(source)
        if target is None and archive_references:
            target = root / "references/card-art/files" / kind / f"{source.stem}-{sha[:12]}{source.suffix.lower()}"
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(actual, target)
            existing_by_hash[sha] = target
        canonical = target or actual
        aliases[key] = relative(canonical, root)
        refs.append({"source": key, "asset": aliases[key], "kind": kind, "sha256": sha,
                     "available": True, "portable": not relative(canonical, root).startswith(("output/", "temp/"))})

    # Keep past mappings when a source batch is no longer on disk; never remove its archive.
    for key, value in old_aliases.items():
        if key not in aliases and (root / value).is_file():
            aliases[key] = value
    collections = []
    for name, source, pattern in (
        ("classic-full-art", "output/classic-full-art", "set*/full_art/*.png"),
        ("valve-heroes", "output/dota-hero-art-references/valve", "*.png"),
        ("dota-equipment-icons", "output/dota-native-equipment", "**/*.png"),
        ("official-lore", "output/dota-lore-references", "**/*"),
        ("comic-exploration", "output/dota-comic-npc-exploration", "**/*"),
        ("neutral-client-renders", "output/dota-neutral-client-render", "shots/*"),
    ):
        images = [path for path in sorted((root / source).glob(pattern))
                  if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]
        collections.append({"id": name, "source": source, "local_count": len(images),
                            "images": [{"source": relative(path, root), "sha256": digest(path),
                                        "published_alias": aliases.get(relative(path, root))} for path in images]})
    reference_catalog = {"schema_version": 1, "aliases": dict(sorted(aliases.items())),
                         "references": refs, "local_collections": collections}
    write_json(root / "references/card-art/catalog.json", reference_catalog)

    items = sorted(entries.values(), key=lambda entry: (entry["category"], entry["batch"], entry["id"]))
    batch_rows = []
    for name in sorted({entry["batch"] for entry in items}):
        group = [entry for entry in items if entry["batch"] == name]
        path = migoo / name
        batch_rows.append({
            "id": name, "category": group[0]["category"], "entries": len(group),
            "availability": dict(Counter(entry["availability"] for entry in group)),
            "briefs": relative(path / "briefs.json", root) if (path / "briefs.json").is_file() else None,
            "review": next((relative(path / f, root) for f in ("review.html", "index.html", "preview.jpg") if (path / f).is_file()), None),
        })
    summary = {"entries": len(items), "batches": len(batch_rows),
               "by_category": dict(Counter(entry["category"] for entry in items)),
               "availability": dict(Counter(entry["availability"] for entry in items)),
               "referenced_images": len(refs), "portable_references": sum(ref.get("portable", False) for ref in refs)}
    catalog = {"schema_version": 1, "summary": summary, "batches": batch_rows, "entries": items, "issues": issues}
    write_json(root / "assets/art-library/catalog.json", catalog)
    write_navigation(root, catalog)
    return catalog


def write_navigation(root, catalog):
    base = root / "assets/art-library"
    base.mkdir(parents=True, exist_ok=True)
    rows_out = []
    for key, title in CATEGORIES.items():
        group = [batch for batch in catalog["batches"] if batch["category"] == key]
        if not group:
            continue
        counts = Counter()
        for batch in group:
            counts.update(batch["availability"])
        rows_out.append(f"| [{title}](categories/{key}.md) | {len(group)} | {sum(counts.values())} | {counts['local']} | {counts['task-only']} | {counts['prepared']} |")
        page = base / "categories" / (key + ".md")
        lines = [f"# {title}", "", "保留原批次目录；下表按可用资源分类。任务记录、下载文件、用户认可和游戏接入分别记录。", "",
                 "| 批次 | 条目 | 本地图片 | 仅任务号 | 仅备稿 | 审阅入口 |", "| --- | ---: | ---: | ---: | ---: | --- |"]
        for batch in group:
            link = os.path.relpath(root / "assets/migoo" / batch["id"], page.parent)
            review = f"[查看]({os.path.relpath(root / batch['review'], page.parent)})" if batch["review"] else "见任务清单"
            count = batch["availability"]
            lines.append(f"| [{batch['id']}]({link}) | {batch['entries']} | {count.get('local', 0)} | {count.get('task-only', 0)} | {count.get('prepared', 0)} | {review} |")
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = """# 卡图资源分类索引

保留原图、原目录和原任务记录，通过分类索引归纳；条目包含备稿、修订和旧版本，不等同于独立卡牌数。本次整理不生成新图片，也不把候选图自动接入游戏。

- [项目生图 skill](../../.agents/skills/artifact-card-art/SKILL.md)：按类别选参考、写提示词与返工。
- [资源明细](catalog.json)：每个条目的任务号、提示词、参考图、图片可用状态和接入记录。
- [参考图归档](../../references/card-art/README.md)：已使用参考图的可移植副本与旧路径映射。
- [Migoo 原批次索引](../migoo/README.md)：既有预览、审阅页与提示词。

| 类别 | 批次 | 条目 | 本地图片 | 仅任务号 | 仅备稿 |
| --- | ---: | ---: | ---: | ---: | ---: |
""" + "\n".join(rows_out) + """

“本地图片”只表示文件已归档；“仅任务号”保留平台最近记录，未重新查询实时完成状态；“仅备稿”尚无任务号。用户认可单独看 `review_status` / `user_review`，游戏接入看 `integrated_asset_id`，不从存在图片推断验收通过。

`explorations` 中保留旧原创英雄、偏题英雄和背景合成实验，供追溯，不作为原版英雄身份参考。

刷新分类：`python3 scripts/art_library.py`。要将新增的已用本地参考图复制进归档，执行 `python3 scripts/art_library.py --archive-references`；按 SHA-256 复用已有副本，不移动、删除原件，不联系 Migoo，也不连接 108。
"""
    (base / "README.md").write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-references", action="store_true", help="copy referenced local images into the repository; keep originals")
    args = parser.parse_args()
    result = build(archive_references=args.archive_references)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"missing reference records: {len(result['issues'])}")


if __name__ == "__main__":
    main()
