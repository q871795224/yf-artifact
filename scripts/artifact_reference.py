#!/usr/bin/env python3
"""Build, check and search the pinned Artifact Classic reference; stdlib only."""

import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ssl
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / "references/artifact-classic"
LANGUAGES = ("english", "schinese")
GROUPS = {
    "heroes": ("英雄", ("Hero",)),
    "creeps": ("小兵与其他非英雄单位", ("Creep",)),
    "spells": ("法术", ("Spell",)),
    "items": ("装备与消耗品", ("Item",)),
    "improvements": ("建筑改良", ("Improvement",)),
    "abilities": ("主动与被动技能", ("Ability", "Passive Ability")),
    "structures-and-paths": ("建筑与攻击路径内部记录", ("Stronghold", "Pathing")),
}
TYPE_FILE = {t: slug for slug, (_, types) in GROUPS.items() for t in types}
COLORS = {"red": "红", "green": "绿", "blue": "蓝", "black": "黑"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("br", "p", "div"):
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def plain_html(value):
    parser = PlainText()
    parser.feed(value)
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines()).strip()


def unquote_kv(value):
    # KV1 escapes, preserving Unicode and unknown escapes as written.
    escapes = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}
    return re.sub(r'\\([nrt"\\])', lambda m: escapes[m[1]], value)


def kv_pairs(path):
    pairs = []
    quoted_pair = re.compile(r'^\s*"((?:\\.|[^"\\])*)"\s+"((?:\\.|[^"\\])*)"(.*)$')
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        match = quoted_pair.match(line)
        if match:
            tail = match[3].strip()
            # Both upstream lore files have stray text outside CardLore_10323's
            # closing quote. Keep the original file and read only the KV value.
            known_tail = (path.name in ("dcg_lore_set_01_english.txt", "dcg_lore_set_01_schinese.txt")
                          and match[1] == "CardLore_10323" and tail == "— <i>")
            if tail and not tail.startswith("//") and not known_tail:
                raise ValueError(f"Unexpected KV suffix: {path}:{number}")
            pairs.append((unquote_kv(match[1]), unquote_kv(match[2])))
        elif line.count('"') >= 4 and not line.lstrip().startswith("//"):
            raise ValueError(f"Unparsed KV pair: {path}:{number}")
    return pairs


def source_check():
    manifest = read_json(ROOT / "sources.json")
    for source in manifest["sources"]:
        data = (ROOT / source["path"]).read_bytes()
        if len(data) != source["bytes"] or hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError(f"Source checksum mismatch: {source['path']}")
    return manifest


def load_cards():
    cards = []
    for set_id in (0, 1):
        path = f"raw/api-2018/set-{set_id:02}.json"
        card_set = read_json(ROOT / path)["card_set"]
        assert card_set["set_info"]["set_id"] == set_id
        for raw in card_set["card_list"]:
            card = dict(raw)
            card["source"] = {"path": path, "set_id": set_id}
            card["card_name"] = {lang: raw["card_name"].get(lang, "") for lang in LANGUAGES}
            card["card_text"] = {lang: plain_html(raw["card_text"].get(lang, "")) for lang in LANGUAGES}
            card["colors"] = [color for color in COLORS if raw.get("is_" + color)]
            cards.append(card)
    cards.sort(key=lambda c: c["card_id"])
    index = {c["card_id"]: c for c in cards}
    assert len(index) == len(cards), "Duplicate official card ID"
    client = ROOT / "raw/client-2021"
    remap = {int(a): int(b) for a, b in kv_pairs(client / "card_remap.txt")}
    for card in cards:
        card["legacy_ids"] = sorted(old for old, new in remap.items() if new == card["card_id"])
        card["client_2021"] = {lang: {} for lang in LANGUAGES}
    extras = {lang: {} for lang in LANGUAGES}
    for lang in LANGUAGES:
        for set_id in (0, 1):
            for filename in (f"card_set_{set_id:02}_{lang}.txt", f"dcg_lore_set_{set_id:02}_{lang}.txt"):
                for key, value in kv_pairs(client / filename):
                    match = re.fullmatch(r"Card[A-Za-z]+_(\d+)(?:_\d+)?", key)
                    if not match:
                        continue
                    card_id = int(match[1])
                    if card_id in index:
                        index[card_id]["client_2021"][lang][key] = value
                    else:
                        extras[lang][key] = value
    return cards, extras


def label(card):
    names = card["card_name"]
    return f"{names['schinese']} / {names['english']}"


def reference_link(card):
    return f"[{card['card_id']} · {label(card)}]({TYPE_FILE[card['card_type']]}.md#card-{card['card_id']})"


def render_group(title, cards, index):
    lines = [f"# {title}", "", f"共 {len(cards)} 条；数值与正文来自 2018-12-22 API 历史快照。", "", "`—` 表示 API 未提供该字段；技能、消耗品、衍生单位也可能有独立记录。2021 客户端文本另存于 cards.json，不覆盖此处旧版数值。", ""]
    for card in cards:
        card_id = card["card_id"]
        lines += [f'<a id="card-{card_id}"></a>', "", f"## {card_id} · {label(card)}", ""]
        color = "、".join(COLORS[c] for c in card["colors"]) or "无色"
        lines += [f"类型：{card['card_type']}；颜色：{color}；稀有度：{card.get('rarity', '—')}。", ""]
        fields = [("mana_cost", "法力"), ("gold_cost", "金币"), ("attack", "攻击"), ("armor", "护甲"), ("hit_points", "生命"), ("charges", "充能")]
        numbers = [f"{name} {card[key]}" for key, name in fields if key in card]
        if card["card_type"] in ("Hero", "Creep") and "armor" not in card:
            numbers.append("护甲 —")
        if numbers:
            lines += [" / ".join(numbers), ""]
        if card.get("sub_type"):
            lines += [f"子类型：{card['sub_type']}。", ""]
        for lang, prefix in (("schinese", "中文"), ("english", "English")):
            text = card["card_text"][lang]
            if text:
                lines += [f"{prefix}：", "", text, ""]
        for ref in card["references"]:
            count = f" ×{ref['count']}" if "count" in ref else ""
            lines += [f"- {ref['ref_type']}：{reference_link(index[ref['card_id']])}{count}"]
        if card["references"]:
            lines.append("")
    return ("\n".join(lines) + "\n").encode()


def generated_files():
    cards, extras = load_cards()
    index = {c["card_id"]: c for c in cards}
    for card in cards:
        for ref in card["references"]:
            if ref["card_id"] not in index:
                raise ValueError(f"Missing reference: {card['card_id']} -> {ref['card_id']}")
    metadata = {
        "schema_version": 1,
        "game": "Artifact Classic",
        "api_snapshot": "2018-12-22",
        "client_text_snapshot": "2021-04-21; build 6500791; stored separately",
        "counts": dict(sorted(Counter(c["card_type"] for c in cards).items())),
        "cards": cards,
    }
    outputs = {"cards.json": json_bytes(metadata), "client-only-tokens.json": json_bytes(extras)}
    for slug, (title, types) in GROUPS.items():
        outputs[f"{slug}.md"] = render_group(title, [c for c in cards if c["card_type"] in types], index)
    for lang in LANGUAGES:
        entries = dict(kv_pairs(ROOT / f"raw/client-2021/dcg_glossary_{lang}.txt"))
        outputs[f"glossary-{lang}.json"] = json_bytes(entries)
    return outputs


def search(args):
    dataset = read_json(ROOT / "cards.json")
    query = args.query.casefold()
    results = []
    for card in dataset["cards"]:
        if args.type and card["card_type"].casefold() != args.type.casefold():
            continue
        text = json.dumps([card["card_name"], card["card_text"], card["client_2021"]], ensure_ascii=False).casefold()
        if not query or query in text or query == str(card["card_id"]) or query in map(str, card["legacy_ids"]):
            results.append(card)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("Artifact Classic · 数值快照 2018-12-22（2021 文本仅用于附加检索）")
        for card in results:
            print(f"\n{card['card_id']} · {label(card)} [{card['card_type']}]")
            stats = " | ".join(f"{key}={card[key]}" for key in ("mana_cost", "gold_cost", "attack", "armor", "hit_points") if key in card)
            if stats:
                print(stats)
            print(card["card_text"]["schinese"] or card["card_text"]["english"] or "（无卡牌正文）")
            print(f"文档：{TYPE_FILE[card['card_type']]}.md#card-{card['card_id']}")
        print(f"\n共 {len(results)} 条。")


def fetch():
    # Recover exact pinned bytes only; never silently update the chosen revision.
    context = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if Path("/etc/ssl/cert.pem").exists() else ssl.create_default_context()
    for source in read_json(ROOT / "sources.json")["sources"]:
        target = ROOT / source["path"]
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == source["sha256"]:
            continue
        with urllib.request.urlopen(source["url"], context=context, timeout=40) as response:
            data = response.read()
        if len(data) != source["bytes"] or hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError(f"Downloaded source checksum mismatch: {source['url']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print(f"Fetched {source['path']}")
    source_check()
    print("Pinned sources ready; run build to regenerate the offline index.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("fetch", "build", "check"):
        commands.add_parser(command)
    finder = commands.add_parser("search")
    finder.add_argument("query", nargs="?", default="")
    finder.add_argument("--type", help="API type, e.g. Hero, Creep, Item, Spell")
    finder.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.command == "fetch":
        fetch()
    elif args.command == "search":
        search(args)
    else:
        manifest = source_check()
        outputs = generated_files()
        for name, data in outputs.items():
            target = ROOT / name
            if args.command == "build":
                target.write_bytes(data)
            elif not target.exists() or target.read_bytes() != data:
                raise ValueError(f"Generated file is missing or stale: {target}; run build")
        counts = read_json(ROOT / "cards.json")["counts"]
        print(f"{args.command}: {len(manifest['sources'])} sources, {sum(counts.values())} records; all IDs and references valid.")
        print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, AssertionError) as error:
        sys.exit(str(error))
