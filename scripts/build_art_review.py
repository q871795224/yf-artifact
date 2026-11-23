#!/usr/bin/env python3
"""Index the current catalog and artwork for the local art review page."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

from growth_cards import catalog_view


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/art-review"
CLASSIC = ROOT / "references/artifact-classic"
CLASSIC_FULL_ART = ROOT / "output/classic-full-art"
MIGOO = ROOT / "assets/migoo"
BASIC_UNIT_IDS = (64001, 64002, 64003, 64004)
BATCHES = {
    "dota-neutral-reference-concepts": ("Dota 野怪参考", "Creep", ""),
    "dota-neutral-client-family-concepts": ("Dota 野怪家族", "Creep", ""),
    "dota-neutral-client-member-concepts": ("Dota 野怪成员", "Creep", ""),
    "dota-lore-unit-concepts": ("Dota 故事单位", "Creep", ""),
    "dota-lore-unit-concepts-more": ("Dota 故事单位", "Creep", ""),
    "dota-lore-unit-concepts-third": ("Dota 故事单位", "Creep", ""),
    "red-unit-redesign": ("红色单位重画", "Creep", "red"),
    "blue-spell-concepts": ("蓝色法术", "Spell", "blue"),
    "black-spell-concepts": ("黑色法术", "Spell", "black"),
    "blue-black-unit-concepts": ("蓝黑单位", "Creep", ""),
    "four-color-unit-concepts": ("四色单位", "Creep", ""),
    "neutral-camp-concepts": ("营地野怪", "Creep", ""),
    "dota-equipment-concepts": ("共享装备", "Item", ""),
    "faction-building-concepts": ("阵营建筑", "Stronghold", ""),
    "hero-archetype-concepts": ("原创英雄", "Hero", ""),
    "hero-archetype-concepts-more": ("原创英雄", "Hero", ""),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def url(path):
    return "../" + path.relative_to(ROOT).as_posix() if path.is_file() else ""


def artwork(path, label, thumb=None):
    original = url(path)
    return {"label": label, "src": original, "thumb": (url(thumb) if thumb else "") or original}


def write_atomically(path, data):
    with NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        scratch = Path(temporary.name)
        try:
            temporary.write(data)
            temporary.close()
            scratch.replace(path)
        finally:
            scratch.unlink(missing_ok=True)


def card_entry(card, **extra):
    names = card["card_name"]
    card_text = card.get("card_text", {})
    return {
        "id": card["card_id"], "name": names.get("schinese") or names.get("english"),
        "english": names.get("english", ""),
        "kind": card["card_type"], "colors": card.get("colors", []),
        "text": card_text.get("schinese") or card_text.get("english", ""),
        **{key: card[key] for key in ("mana_cost", "gold_cost", "attack", "armor", "hit_points") if key in card},
        **extra,
    }


def classic_cards(cache_downloads=False):
    index = read(CLASSIC / "cards.json")["cards"]
    local = {(item["card_id"], item["kind"]): CLASSIC / "assets" / item["path"]
             for item in read(CLASSIC / "assets/manifest.json")["assets"]}
    unframed = {}
    reference_subset = ROOT / "output/blue-black-art-references"
    for path in [*sorted(reference_subset.glob("*_psd.png")),
                 *sorted(CLASSIC_FULL_ART.glob("set*/full_art/*_psd.png"))]:
        match = re.fullmatch(r"(\d+)_psd.png", path.name)
        if match:
            unframed[int(match[1])] = path
    downloads = []
    entries = {}
    for card in index:
        cid = card["card_id"]
        images = []
        for kind, label in (("large_image", "原版卡面"), ("mini_image", "原版头像"), ("ingame_image", "局内图标")):
            fields = card.get(kind, {})
            remote = fields.get("schinese") or fields.get("def") or fields.get("english")
            original = local.get((cid, kind))
            cached = OUTPUT / "classic" / f"{cid}.png"
            mobile = CLASSIC / "assets/mobile" / kind / f"{cid}.webp"
            if original and original.is_file():
                images.append(artwork(original, label, mobile))
            elif kind == "large_image" and cached.is_file():
                images.append(artwork(cached, label))
            elif remote:
                images.append({"label": label, "src": remote, "thumb": remote})
                if kind == "large_image":
                    downloads.append((remote, cached, images[-1]))
        if cid in unframed:
            images.append(artwork(unframed.pop(cid), "Classic 无框原画"))
        if images:
            entries[cid] = card_entry(card, key=f"classic:{cid}", images=images)
    for cid, path in sorted(unframed.items()):
        entries[cid] = card_entry({
            "card_id": cid, "card_name": {"schinese": f"原画 {cid}"}, "card_type": "Artwork",
        }, key=f"classic:{cid}", images=[artwork(path, "Classic 无框原画")])
    if cache_downloads:
        (OUTPUT / "classic").mkdir(exist_ok=True)

        def fetch(task):
            remote, path, image = task
            try:
                with urlopen(remote, timeout=10) as response:
                    data = response.read()
                if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                    return False
                write_atomically(path, data)
                image.update(artwork(path, image["label"]))
                return True
            except OSError:
                return False

        with ThreadPoolExecutor(max_workers=12) as pool:
            saved = sum(pool.map(fetch, downloads))
        print(f"Classic downloaded: {saved}/{len(downloads)}")
    return entries


def project_cards(classic):
    catalog = catalog_view()
    cards = catalog["cards"]
    card_ids = {c["card_id"] for c in cards}
    custom = read(ROOT / "assets/custom/manifest.json")["assets"]
    migoo = read(MIGOO / "manifest.json")["assets"]
    custom_by_id = {entry["card_id"]: entry for entry in custom if "card_id" in entry}
    migoo_by_id = {entry["card_id"]: entry for entry in migoo if "card_id" in entry}
    custom_by_key = {entry["id"]: entry for entry in custom}
    hero_names = {c["card_id"]: c["card_name"]["schinese"] for c in cards if c["card_type"] == "Hero"}
    entries = []
    for card in cards:
        cid = card["card_id"]
        image_path = ROOT / f"prototype/assets/cards/{cid}.webp"
        own = image_path.is_file() or cid == 64004
        images = []
        if image_path.is_file():
            custom_source = custom_by_id.get(cid, {}).get("source", {}).get("path")
            migoo_source = migoo_by_id.get(cid, {}).get("path")
            path = ROOT / (custom_source or migoo_source) if custom_source or migoo_source else image_path
            images.append(artwork(path, "项目立绘", image_path))
        if cid == 64004:
            for key in ("radiant-ranged", "dire-ranged"):
                art = custom_by_key[key]
                images.append(artwork(ROOT / art["source"]["path"], art["name"]["schinese"],
                                      ROOT / art["images"]["large_image"]))
        choice = classic.get(cid) if own else classic.get(card.get("art_id") or cid)
        if choice:
            for art in choice["images"]:
                images.append({**art, "label": art["label"] if own or cid == choice["id"] else
                               art["label"].replace("原版", "借用").replace("Classic", "借用 Classic")})
        entry = card_entry(card, key=f"current:{cid}", images=images, own=own,
                           hero=hero_names.get(card.get("hero_id"), ""), levels=catalog["panels"].get(cid, []))
        if entry["hero"]:
            entry["kind"] = "Signature"
        elif card.get("sub_type") == "Consumable":
            entry["kind"] = "Consumable"
        entries.append(entry)

    melee = custom_by_key["dire-melee"]
    reference = classic[1006]
    entries.append({**reference, "key": "current:1006", "own": True,
                    "images": [*reference["images"], artwork(ROOT / melee["source"]["path"], "夜魇近战立绘",
                                                              ROOT / melee["images"]["large_image"])]})
    unassigned = []
    for art in custom:
        if art.get("card_id") in card_ids or art["id"] in ("dire-melee", "dire-ranged", "radiant-ranged"):
            continue
        path = ROOT / art["source"]["path"]
        if path.is_file():
            unassigned.append({"key": f"custom:{art['id']}", "id": art["id"], "name": art["name"]["schinese"],
                               "kind": art["card_type"], "colors": [], "batch": "早期项目素材",
                               "text": art.get("usage", ""), "images": [artwork(path, "项目原图")]})
    for art in migoo:
        if art.get("card_id") in card_ids:
            continue
        unassigned.append({"key": f"migoo:{art['asset_key']}", "id": art["asset_key"], "name": art["name"],
                           "kind": art["kind"], "colors": [art["color"]], "batch": "扩充试玩候选",
                           "images": [artwork(ROOT / art["path"], "候选原图")]})
    kinds = ("Hero", "Creep", "Spell", "Signature", "Item", "Consumable")
    order = {kind: rank for rank, kind in enumerate(kinds)}
    entries.sort(key=lambda entry: (entry["id"] in (*BASIC_UNIT_IDS, 1006), order.get(entry["kind"], len(order))))
    return entries, unassigned


def candidate_art():
    entries = []
    for folder, (batch, kind, default_color) in BATCHES.items():
        directory = MIGOO / folder
        manifest = read(directory / "manifest.json")
        jobs = read(directory / "briefs.json")["jobs"]
        if isinstance(jobs, dict):
            jobs = [job for group in jobs.values() for job in group]
        briefs = {job["slug"]: job for job in jobs}
        for art in manifest["images"]:
            path = directory / (art.get("image") or art["file"])
            slug = path.parent.name
            job = briefs.get(slug, {})
            color = art.get("color") or job.get("color") or default_color
            if folder == "blue-black-unit-concepts":
                color = slug.split("-", 1)[0]
            entries.append({
                "key": f"candidate:{folder}/{slug}", "id": slug, "name": art["name"],
                "kind": kind, "colors": [color] if color in ("red", "blue", "green", "black") else [],
                "batch": batch, "text": job.get("description") or job.get("brief", ""),
                "inspiration": job.get("inspiration", art.get("inspiration", "")),
                "images": [artwork(path, "候选原图")],
            })
    return entries


def build(cache_downloads=False):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    classic = classic_cards(cache_downloads)
    candidates = candidate_art()
    encoder = shutil.which("cwebp")
    if encoder:
        thumb_dir = OUTPUT / "thumbs"
        thumb_dir.mkdir(exist_ok=True)
        for entry in [*candidates, *classic.values()]:
            for index, image in enumerate(entry["images"]):
                if index > 0 and image["label"] != "Classic 无框原画":
                    continue
                if not image["src"].startswith("../") or image["src"] != image["thumb"]:
                    continue
                original = ROOT / image["src"].removeprefix("../")
                key = entry["key"] + ("-full-art" if image["label"] == "Classic 无框原画" else "")
                target = thumb_dir / (re.sub(r"[^a-zA-Z0-9_-]", "-", key) + ".webp")
                if not target.exists() or original.stat().st_mtime > target.stat().st_mtime:
                    subprocess.run([encoder, "-quiet", "-resize", "224", "0", "-q", "80",
                                    str(original), "-o", str(target)], check=True)
                image["thumb"] = url(target)
    current, extra = project_cards(classic)
    collections = {"current": current, "candidate": candidates + extra, "classic": list(classic.values())}
    index = json.dumps({"collections": collections}, ensure_ascii=False).encode()
    write_atomically(OUTPUT / "index.json", index)
    return {key: len(entries) for key, entries in collections.items()}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-classic", action="store_true", help="Cache full Classic card faces locally")
    options = parser.parse_args()
    print(build(options.cache_classic))
