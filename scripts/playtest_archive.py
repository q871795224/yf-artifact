"""Local replay files for the desktop and LAN preview server."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from growth_playable import GrowthSession
from playable_match import InvalidAction, StaleAction


MAX_REPLAY_BYTES = 2 * 1024 * 1024
GAME_ID = re.compile(r"[a-f0-9]{32}")
ACTION_ID = re.compile(r"(?:[a-f0-9]{20}|pass|next_round|concede)")


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def replay(record):
    session = GrowthSession(record["seed"], record.get("deck_config"))
    for command in record["commands"]:
        session.apply(command["version"], command["action_id"])
    return session


class PlaytestArchive:
    def __init__(self, directory, engine_version):
        self.directory = Path(directory).resolve()
        self.engine_version = engine_version
        self.directory.mkdir(parents=True, exist_ok=True)

    def read_session(self, game_id):
        path = self.directory / f"{game_id}.json"
        if not path.is_file():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["engine_version"] != self.engine_version:
            raise StaleAction("规则已更新。旧局仍保存在电脑，可开始新一局。")
        return replay(record), record["source"], record["created_at"]

    @staticmethod
    def _write(path, record):
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
            temp = Path(output.name)
            try:
                json.dump(record, output, ensure_ascii=False, separators=(",", ":"))
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
                output.close()
                os.replace(temp, path)
            finally:
                temp.unlink(missing_ok=True)

    def save_session(self, game_id, session, source, created_at, packet):
        document = self.session_record(game_id, session, source, created_at)
        document.update(updated_at=timestamp(), stats=packet["state"]["stats"],
                        forts=packet["state"]["forts"])
        self._write(self.directory / f"{game_id}.json", document)

    def session_record(self, game_id, session, source, created_at):
        return {**session.export(), "game_id": game_id, "engine_version": self.engine_version,
                "source": source, "created_at": created_at}

    def import_replay(self, record):
        seed = record.get("seed")
        commands = record.get("commands")
        version = record.get("engine_version")
        if (record.get("schema_version") != 1 or type(seed) is not int or not 1 <= seed <= 1_000_000_000
                or not isinstance(commands, list) or len(commands) > 2000
                or (version is not None and (not isinstance(version, str) or not re.fullmatch(r"[a-f0-9]{64}", version)))):
            raise InvalidAction("这不是有效的对局导出文件。")
        for i, command in enumerate(commands):
            if (not isinstance(command, dict) or type(command.get("version")) is not int
                    or command["version"] != i or not isinstance(command.get("action_id"), str)
                    or not ACTION_ID.fullmatch(command["action_id"])):
                raise InvalidAction("对局操作记录的格式不正确。")
        core = {k: record.get(k) for k in ("engine_version", "seed", "deck_config", "commands")}
        key = sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
        path = self.directory / "imported" / f"{key}.json"
        if path.is_file():
            stored = json.loads(path.read_text(encoding="utf-8"))
            return {"archive_id": key, "verified": stored["verified"], "duplicate": True}
        verified = version == self.engine_version
        payload = {"archive_id": key, "imported_at": timestamp(), "verified": verified, "record": record}
        if verified:
            session = replay(record)
            state = session.snapshot()
            payload.update(replayed=session.export(), stats=state["stats"], forts=state["forts"])
        self._write(path, payload)
        return {"archive_id": key, "verified": verified, "duplicate": False}
