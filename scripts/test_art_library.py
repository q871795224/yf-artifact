"""Behavioral checks for non-destructive art inventory and portable references."""

import hashlib
from pathlib import Path
import tempfile
import unittest

from art_library import build, read_json, resolve_reference_path, write_json


class ArtLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.batch = self.root / "assets/migoo/dota-equipment-classic-test"
        self.job = self.batch / "staff-v01"
        self.job.mkdir(parents=True)

    def request(self, **extra):
        data = {"hero": "staff", "name": "法杖", "status": "completed", "task_id": "task-one",
                "references": [], **extra}
        write_json(self.job / "request.json", data)

    def test_completed_platform_record_without_local_image_is_task_only(self):
        self.request()
        catalog = build(self.root)
        self.assertEqual(catalog["summary"]["entries"], 1)
        entry = catalog["entries"][0]
        self.assertEqual(entry["availability"], "task-only")
        self.assertNotIn("review_status", entry)
        self.assertNotIn("integrated_asset_id", entry)

    def test_archive_copies_reference_without_modifying_original_and_resolves_old_alias(self):
        source = self.root / "output/classic-full-art/set01/full_art/10210_psd.png"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"original-reference-bytes")
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        self.request(references=[str(source)])
        result = build(self.root, archive_references=True)
        self.assertEqual(result["issues"], [])
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
        ref = read_json(self.root / "references/card-art/catalog.json")["references"][0]
        archived = self.root / ref["asset"]
        self.assertNotEqual(source, archived)
        self.assertEqual(archived.read_bytes(), source.read_bytes())
        # Simulate a fresh checkout whose ignored output cache does not exist.
        source.rename(source.with_suffix(".local-backup"))
        self.assertEqual(resolve_reference_path("output/classic-full-art/set01/full_art/10210_psd.png", self.root), archived)

    def test_existing_identical_reference_is_reused_without_extra_copy(self):
        original = self.root / "output/source.png"
        original.parent.mkdir()
        original.write_bytes(b"same-image")
        existing = self.batch / "references/known.png"
        existing.parent.mkdir()
        existing.write_bytes(b"same-image")
        self.request(references=["output/source.png"])
        build(self.root, archive_references=True)
        aliases = read_json(self.root / "references/card-art/catalog.json")["aliases"]
        self.assertEqual(aliases["output/source.png"], existing.relative_to(self.root).as_posix())
        self.assertFalse((self.root / "references/card-art/files").exists())
        self.assertTrue(original.exists())

    def test_archive_prefers_named_original_over_ignored_download_duplicate(self):
        original = self.job / "original.png"
        original.write_bytes(b"existing-art-reference")
        duplicate = self.job / "mt_old_task_1.png"
        duplicate.write_bytes(original.read_bytes())
        self.request(references=[duplicate.relative_to(self.root).as_posix()])
        build(self.root, archive_references=True)
        aliases = read_json(self.root / "references/card-art/catalog.json")["aliases"]
        self.assertEqual(aliases[duplicate.relative_to(self.root).as_posix()], original.relative_to(self.root).as_posix())
        self.assertTrue(duplicate.is_file())

    def test_prepared_jobs_and_completed_legacy_outputs_share_one_entry_per_job(self):
        self.batch.rename(self.batch.with_name("unit-cast-spells-test"))
        batch = self.batch.with_name("unit-cast-spells-test")
        local = batch / "first"
        local.mkdir()
        (local / "original.png").write_bytes(b"generated-image")
        write_json(batch / "briefs.json", {"jobs": [{"slug": "first", "name": "第一张"}, {"slug": "second", "name": "第二张"}]})
        write_json(batch / "manifest.json", {"images": [{"slug": "first", "name": "第一张", "image": "first/original.png", "task_id": "first-task"}]})
        result = build(self.root)
        self.assertEqual(result["summary"]["entries"], 2)
        self.assertEqual(result["summary"]["availability"], {"local": 1, "prepared": 1})

    def test_catalog_excludes_signed_urls_and_account_identity(self):
        self.request(email="private@example.test", references=["https://sg.migoo.ai/beeai/api/v1/media/signed/private.png?sig=secret"])
        build(self.root)
        text = (self.root / "assets/art-library/catalog.json").read_text()
        self.assertNotIn("secret", text)
        self.assertNotIn("private@example.test", text)

    def test_iteration_keeps_both_versions_with_parent_relationship(self):
        self.request()
        (self.job / "original.png").write_bytes(b"current-version")
        old = self.job / "iterations/v01"
        old.mkdir(parents=True)
        (old / "original.png").write_bytes(b"historical-version")
        result = build(self.root)
        self.assertEqual(result["summary"]["entries"], 2)
        historical = next(entry for entry in result["entries"] if entry.get("version_role") == "historical-iteration")
        self.assertEqual(historical["variant_of"], self.job.relative_to(self.root).as_posix())
        self.assertEqual((self.root / historical["local_image"]).read_bytes(), b"historical-version")
        self.assertEqual((self.job / "original.png").read_bytes(), b"current-version")

    def test_composite_experiment_and_its_background_are_indexed_without_original_png(self):
        batch = self.batch.with_name("dota-hero-portrait-layout")
        self.batch.rename(batch)
        composite = batch / "staff-v01"
        (composite / "preview.png").write_bytes(b"composite-preview")
        (composite / "background.png").write_bytes(b"generated-background")
        result = build(self.root)
        self.assertEqual(result["summary"]["entries"], 1)
        entry = result["entries"][0]
        self.assertEqual(entry["category"], "explorations")
        self.assertEqual(entry["availability"], "local")
        self.assertEqual((self.root / entry["local_image"]).read_bytes(), b"composite-preview")
        self.assertTrue(entry["references"][0].endswith("background.png"))

    def test_legacy_miscast_hero_experiment_is_separate_from_canonical_heroes(self):
        self.batch.rename(self.batch.with_name("dota-hero-role-concepts"))
        batch = self.batch.with_name("dota-hero-role-concepts")
        (batch / "staff-v01/original.png").write_bytes(b"old-experiment")
        result = build(self.root)
        self.assertEqual(result["entries"][0]["category"], "explorations")


if __name__ == "__main__":
    unittest.main()
