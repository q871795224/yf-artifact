"""Reference behavior checks against pinned upstream examples; no network needed."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import artifact_reference as reference


class ReferenceTests(unittest.TestCase):
    def test_official_unit_examples_and_hero_signature(self):
        cards, _ = reference.load_cards()
        index = {c["card_id"]: c for c in cards}
        creep = index[1006]
        self.assertEqual((creep["card_name"]["schinese"], creep["attack"], creep["hit_points"]), ("近战小兵", 2, 4))
        self.assertNotIn("armor", creep)
        axe = index[10020]
        self.assertEqual((axe["attack"], axe["armor"], axe["hit_points"]), (6, 2, 10))
        self.assertIn({"card_id": 10288, "ref_type": "includes", "count": 3}, axe["references"])
        self.assertEqual(index[10288]["card_name"]["english"], "Berserker's Call")
        self.assertIn(10037, index[4003]["legacy_ids"])
        self.assertEqual(len([c for c in cards if c["card_type"] == "Hero"]), 48)

    def test_same_name_ability_is_a_separate_record(self):
        cards, _ = reference.load_cards()
        matches = [c for c in cards if c["card_name"]["english"] == "Sister of the Veil"]
        self.assertEqual({c["card_type"] for c in matches}, {"Creep", "Ability"})
        self.assertEqual({c["card_id"] for c in matches}, {10077, 10454})

    def test_text_decoding_preserves_unicode_and_line_breaks(self):
        self.assertEqual(reference.plain_html("<b>主动</b><BR/>造成 2 伤害 &amp; 抽牌。"), "主动\n造成 2 伤害 & 抽牌。")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokens.txt"
            path.write_text('\ufeff"lang"\n{\n"CardText_1" "中文 \\"quoted\\"\\n下一行"\n}\n', encoding="utf-8")
            self.assertEqual(reference.kv_pairs(path), [("CardText_1", '中文 "quoted"\n下一行')])
            path.write_text('"a" "b" unexpected suffix', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unexpected KV suffix"):
                reference.kv_pairs(path)

    def test_client_text_is_separate_and_unmatched_tokens_survive(self):
        cards, extras = reference.load_cards()
        index = {c["card_id"]: c for c in cards}
        self.assertIn("CardText_10004", index[10004]["client_2021"]["english"])
        self.assertIn("CardName_7000", extras["english"])
        self.assertNotIn(7000, index)
        lore = index[10323]["client_2021"]["english"]["CardLore_10323"]
        self.assertTrue(lore.endswith("</i>"))

    def test_offline_rebuild_check_and_search(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("Offline operation used network")):
            reference.source_check()
            for name, data in reference.generated_files().items():
                self.assertEqual((reference.ROOT / name).read_bytes(), data, name)
            output = io.StringIO()
            with redirect_stdout(output):
                with patch("sys.argv", ["artifact_reference.py", "search", "10037", "--json"]):
                    reference.main()
            result = json.loads(output.getvalue())
            self.assertEqual([c["card_id"] for c in result], [4003])

    def test_corrupted_source_fails_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = b"original"
            source = {"path": "sample.json", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            (root / "sources.json").write_text(json.dumps({"sources": [source]}))
            (root / "sample.json").write_bytes(b"modified")
            with patch.object(reference, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    reference.source_check()


if __name__ == "__main__":
    unittest.main()
