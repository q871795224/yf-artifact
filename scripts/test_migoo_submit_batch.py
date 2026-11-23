"""Verify queue behavior without contacting Migoo or consuming credits."""

import tempfile
import unittest
from pathlib import Path

from migoo_submit_batch import Queue, read, write


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.batch = self.root / "batch.json"

    def prepare(self, heroes):
        write(self.batch, {"heroes": [{"hero": h} for h in heroes]})
        for hero in heroes:
            directory = self.root / (hero + "-v01")
            directory.mkdir()
            (directory / "prompt.txt").write_text("canonical hero")
            (directory / "notes.txt").write_text("new composition")
            write(directory / "request.json", {
                "hero": hero, "name": hero, "status": "ready_to_submit",
                "model": "gpt-image-26-flare", "resolution": "1K",
                "ratio": "9:16", "references": [],
            })

    def test_resume_never_recreates_an_accepted_task(self):
        self.prepare(["one", "two"])
        path = self.root / "one-v01/request.json"
        request = read(path)
        request.update(status="generating", task_id="existing")
        write(path, request)
        calls = []

        def call(args):
            calls.append(args)
            if args[:2] == ["task", "get"]:
                return 0, {"task_id": "existing", "status": "completed"}, ""
            if args[:2] == ["task", "list"]:
                return 0, {"tasks": []}, ""
            return 0, {"task_id": "new", "status": "generating"}, ""

        summary = Queue(self.batch, jobs=1, call=call, sleep=lambda _: None).run()
        self.assertEqual(summary["submitted_count"], 2)
        self.assertEqual(sum(c[:2] == ["image", "create"] for c in calls), 1)
        self.assertTrue(all("--wait" not in c and "--output" not in c for c in calls))

    def test_unknown_submission_stops_without_resending(self):
        self.prepare(["one", "two"])
        creates = []

        def call(args):
            if args[:2] == ["task", "list"]:
                return 0, {"tasks": []}, ""
            creates.append(args)
            return 5, None, "network outcome unknown"

        queue = Queue(self.batch, jobs=1, call=call, sleep=lambda _: None)
        with self.assertRaises(RuntimeError):
            queue.run()
        with self.assertRaises(RuntimeError):
            queue.run()
        self.assertEqual(len(creates), 1)
        self.assertEqual(queue.request("two")["status"], "ready_to_submit")

    def test_uploaded_reference_is_reused_by_media_id(self):
        self.prepare(["one"])
        reference = self.root / "reference.png"
        reference.write_bytes(b"local-reference-audit-copy")
        path = self.root / "one-v01/request.json"
        request = read(path)
        request["references"] = [{"path": str(reference), "media_id": "existing-media"}]
        write(path, request)
        calls = []

        def call(args):
            calls.append(args)
            return 0, {"task_id": "new", "status": "generating"}, ""

        Queue(self.batch, call=call).submit("one")
        self.assertEqual(calls[0][calls[0].index("--image") + 1], "existing-media")

    def test_failed_request_is_not_reported_as_submitted(self):
        self.prepare(["one"])
        path = self.root / "one-v01/request.json"
        request = read(path)
        request.update(status="failed", task_id="not-started")
        write(path, request)
        summary = Queue(self.batch).summary()
        self.assertEqual(summary["submitted_count"], 0)
        self.assertEqual(summary["failed_count"], 1)

    def test_revision_uses_the_requested_original_task(self):
        self.prepare(["one"])
        path = self.root / "one-v01/request.json"
        request = read(path)
        request["source_task"] = "original-completed-task"
        write(path, request)
        calls = []

        def call(args):
            calls.append(args)
            return 0, {"task_id": "revision", "status": "generating"}, ""

        queue = Queue(self.batch, call=call)
        queue.submit("one")
        self.assertEqual(calls[0][calls[0].index("--source-task") + 1], "original-completed-task")
        self.assertEqual(queue.request("one")["task_id"], "revision")
        self.assertEqual(queue.request("one")["source_task"], "original-completed-task")

    def test_other_sessions_occupy_account_capacity(self):
        self.prepare(["one", "two", "three"])
        creates = []
        steps = [0]

        def call(args):
            if args[:2] == ["task", "list"]:
                return 0, {"tasks": [{"status": "generating"}] * 2}, ""
            if args[:2] == ["task", "get"]:
                return 0, {"task_id": args[2], "status": "completed"}, ""
            creates.append(args)
            return 0, {"task_id": str(len(creates)), "status": "generating"}, ""

        def sleep(_):
            steps[0] += 1
            self.assertEqual(len(creates), steps[0])

        queue = Queue(self.batch, jobs=3, call=call, sleep=sleep)
        self.assertEqual(queue.run()["submitted_count"], 3)
        self.assertEqual(steps[0], 2)

    def test_only_confirmed_not_started_busy_task_is_resubmitted(self):
        self.prepare(["one", "two"])
        creates = []

        def call(args):
            if args[:2] == ["task", "list"]:
                return 0, {"tasks": []}, ""
            if args[:2] == ["task", "get"]:
                if args[2] == "busy":
                    return 0, {
                        "task_id": "busy", "status": "failed",
                        "error": {"reason": "busy", "message": "Generation did not start"},
                    }, ""
                return 0, {"task_id": args[2], "status": "completed"}, ""
            creates.append(args)
            task_id = "busy" if len(creates) == 1 else str(len(creates))
            return 0, {"task_id": task_id, "status": "generating"}, ""

        queue = Queue(self.batch, jobs=1, call=call, sleep=lambda _: None)
        self.assertEqual(queue.run()["submitted_count"], 2)
        self.assertEqual(len(creates), 3)
        self.assertEqual(queue.request("one")["previous_attempts"][0]["task_id"], "busy")


if __name__ == "__main__":
    unittest.main()
