#!/usr/bin/env python3
"""Submit prepared canonical-hero requests without downloading or reviewing art."""

import argparse
import fcntl
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from art_library import resolve_reference_path

TERMINAL = {"completed", "failed", "cancelled", "canceled", "stopped", "expired"}
READY = {"ready_to_submit", "busy_not_started_retry_ready"}
ATTENTION = {"awaiting_approval", "awaiting_input", "needs_input", "needs_approval"}


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def cli(args):
    result = subprocess.run(
        ["yf-migoo", *args, "--json"], capture_output=True, text=True
    )
    data = None
    for line in result.stdout.splitlines():
        try:
            candidate = json.loads(line)
            if isinstance(candidate, dict):
                data = candidate
        except ValueError:
            pass
    return result.returncode, data, result.stderr + "\n" + result.stdout


class Queue:
    def __init__(self, batch, jobs=2, poll_seconds=8, call=cli, sleep=time.sleep):
        self.batch = Path(batch).resolve()
        self.root = self.batch.parent
        self.heroes = [entry["hero"] for entry in read(self.batch)["heroes"]]
        if len(set(self.heroes)) != len(self.heroes):
            raise ValueError("Duplicate heroes in batch")
        self.jobs, self.poll_seconds = jobs, poll_seconds
        self.call, self.sleep = call, sleep
        self.report = self.batch.with_name(self.batch.stem + "-submissions.json")

    def directory(self, hero):
        return self.root / (hero + "-v01")

    def request(self, hero):
        return read(self.directory(hero) / "request.json")

    def persist(self, hero, request):
        write(self.directory(hero) / "request.json", request)

    def summary(self):
        entries = []
        for hero in self.heroes:
            request = self.request(hero)
            entries.append({key: request.get(key) for key in (
                "hero", "name", "task_id", "status", "model", "actual_models",
                "attempt", "cli_exit_code",
            )})
        result = {
            "requested": len(entries),
            "submitted_count": sum(bool(e["task_id"]) and e["status"] != "failed" for e in entries),
            "failed_count": sum(e["status"] == "failed" for e in entries),
            "workflow": "submit only; status queries release concurrency slots; no downloads",
            "tasks": entries,
        }
        write(self.report, result)
        return result

    def submit(self, hero):
        directory = self.directory(hero)
        request = self.request(hero)
        if request["status"] not in READY:
            raise ValueError(f"Refusing duplicate/uncertain submission: {hero}")
        args = [
            "image", "create", (directory / "prompt.txt").read_text().strip(),
            "--notes", (directory / "notes.txt").read_text().strip(),
            "--model", request["model"], "--resolution", request["resolution"],
            "--count", "1", "--ratio", request["ratio"], "--skip-questions",
        ]
        if request.get("source_task"):
            args += ["--source-task", request["source_task"]]
        for reference in request["references"]:
            local = resolve_reference_path(reference["path"])
            if not local or not local.is_file():
                raise FileNotFoundError(reference["path"])
            args += ["--image", reference.get("media_id") or reference.get("url") or str(local)]
        request.update(status="submitting", attempt=request.get("attempt", 0) + 1)
        request.pop("task_id", None)
        self.persist(hero, request)  # A crash after this point must never resend blindly.
        code, data, log = self.call(args)
        (directory / "submission.log").write_text(log)
        request["cli_exit_code"] = code
        if data and data.get("task_id"):
            write(directory / "submission-result.json", data)
            request.update(task_id=data["task_id"], status=data.get("status", "submitted"))
            request["actual_models"] = data.get("applied", {}).get("models")
        else:
            request["status"] = "policy_blocked" if code == 20 else "submission_unknown"
        self.persist(hero, request)
        print(f"{request.get('name', hero)}: {request['status']} {request.get('task_id', '')}", flush=True)
        return request

    def refresh(self, hero):
        request = self.request(hero)
        code, data, log = self.call(["task", "get", request["task_id"]])
        if not data or data.get("task_id") != request["task_id"]:
            if code:
                raise RuntimeError(f"Cannot verify {hero}; resume using the existing task ID")
            return
        directory = self.directory(hero)
        write(directory / "admission-status.json", data)
        request["status"] = data.get("status", request["status"])
        if data.get("applied", {}).get("models"):
            request["actual_models"] = data["applied"]["models"]
        error = data.get("error", {})
        confirmed_busy = (
            error.get("reason") == "busy"
            and ("did not start" in error.get("message", "")
                 or "wasn't started" in data.get("message", ""))
        )
        if request["status"] == "failed" and confirmed_busy and len(request.get("previous_attempts", [])) < 2:
            previous = request.setdefault("previous_attempts", [])
            previous.append({"task_id": request["task_id"], "error": error})
            request.pop("task_id")
            request["status"] = "busy_not_started_retry_ready"
        self.persist(hero, request)

    def run(self):
        # Resume accepted tasks; leave uncertain submissions for explicit reconciliation.
        for hero in self.heroes:
            request = self.request(hero)
            if request["status"] not in READY | TERMINAL | ATTENTION and not request.get("task_id"):
                raise RuntimeError(f"Reconcile uncertain submission before resuming: {hero}")
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            while True:
                ready = [h for h in self.heroes if self.request(h)["status"] in READY]
                if not ready:
                    return self.summary()  # Last accepted tasks may still be generating.
                active = [h for h in self.heroes if self.request(h).get("task_id")
                          and self.request(h)["status"] not in TERMINAL | ATTENTION]
                for hero in active:
                    self.refresh(hero)
                active = [h for h in self.heroes if self.request(h).get("task_id")
                          and self.request(h)["status"] not in TERMINAL | ATTENTION]
                slots = max(0, self.jobs - len(active))
                if slots:
                    # The account limit is three; account-wide tasks include other sessions.
                    code, data, log = self.call(["task", "list", "--type", "image", "--limit", "20"])
                    if code or not data or not isinstance(data.get("tasks"), list):
                        raise RuntimeError("Cannot verify account concurrency; no new tasks submitted")
                    busy = sum(t.get("status") not in TERMINAL | ATTENTION for t in data["tasks"])
                    slots = min(slots, max(0, 3 - busy))
                    ready = [h for h in self.heroes if self.request(h)["status"] in READY]
                    requests = list(pool.map(self.submit, ready[:slots]))
                    self.summary()
                    if any(r["status"] in {"policy_blocked", "submission_unknown"} for r in requests):
                        raise RuntimeError("Submission stopped; inspect the saved report before resuming")
                self.summary()
                if any(self.request(h)["status"] in READY for h in self.heroes):
                    self.sleep(self.poll_seconds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--jobs", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--poll-seconds", type=float, default=8)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds < 1:
        parser.error("--poll-seconds must be at least 1")
    queue = Queue(args.batch, args.jobs, args.poll_seconds)
    if args.dry_run:
        for hero in queue.heroes:
            request = queue.request(hero)
            for reference in request["references"]:
                local = resolve_reference_path(reference["path"])
                if not local or not local.is_file():
                    parser.error(f"Missing reference: {reference['path']}")
            for filename in ("prompt.txt", "notes.txt"):
                if not (queue.directory(hero) / filename).read_text().strip():
                    parser.error(f"Empty {hero}/{filename}")
        print(json.dumps(queue.summary(), ensure_ascii=False, indent=2))
        return
    with (queue.root / ".migoo-submit.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another batch submitter holds the project queue lock")
        try:
            summary = queue.run()
        except Exception:
            queue.summary()
            raise
    print(f"BATCH_SUBMITTED {summary['submitted_count']}/{summary['requested']} report={queue.report}")
    if summary["failed_count"]:
        raise SystemExit("Some requests failed; inspect the saved report")


if __name__ == "__main__":
    main()
