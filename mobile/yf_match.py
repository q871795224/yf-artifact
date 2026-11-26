"""Mobile protocol over the existing authoritative match. Also runnable as line-delimited JSON on desktop."""
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

# Desktop checkout or the private runtime directory installed by the Android bridge.
ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "scripts/growth_playable.py").exists():
    ROOT = Path(sys.prefix) / "game"
sys.path.insert(0, str(ROOT / "scripts"))
from growth_cards import catalog_view, default_deck, opponent_presets
from growth_playable import GrowthSession
from playable_match import InvalidAction, StaleAction

session = None
FORMAT = 1


def save(path, game):
    data = {"format": FORMAT, "seed": game.seed, "deck": game.game.deck_config[0], "commands": game.commands}
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        json.dump(data, stream, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(stream.name, path)
    finally:
        Path(stream.name).unlink(missing_ok=True)


def restore(path):
    record = json.loads(path.read_text())
    if record["format"] != FORMAT:
        raise ValueError("这个存档来自其他版本。")
    game = GrowthSession(record["seed"], record["deck"])
    for command in record["commands"]:
        game.apply(command["version"], command["action_id"])
    return game


def handle(q):
    global session
    op = q["op"]
    path = Path(q["storage"]) / "river-match-v1.json"
    if op == "lobby":
        cat = catalog_view()
        return {"saved": path.is_file(), "cards": cat["cards"],
                "opponents": [{"id": p["id"], "name": p["name"]} for p in opponent_presets()]}
    if op == "resume":
        session = restore(path)
        return session.packet()
    if op == "new":
        expanded = q.get("preset") == "expansion"
        deck = default_deck(0, expanded)
        deck["name"] = "红绿扩充" if expanded else "经典绿组"
        if expanded:
            deck["experiment"] = "combined"
        enemy = next(p for p in opponent_presets(expanded) if p["id"] == q.get("enemy", "pressure"))
        deck["opponent"] = dict(enemy["deck"], name=enemy["name"])
        game = GrowthSession(int(q["seed"]), deck)
        result = game.packet()
        save(path, game)
        session = game
        return result
    if op != "act":
        raise ValueError("未知操作。")
    if session is None:
        session = restore(path)
    try:
        result = session.apply(int(q["version"]), q["action"])
        save(path, session)
        return result
    except (InvalidAction, StaleAction):
        raise
    except Exception:
        session = None
        raise


def request(serialized):
    try:
        result = handle(json.loads(serialized))
        if "state" in result:
            # The current action list and recent log suffice on the phone.
            result["state"].pop("history", None)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        result = {"error": str(e)}
    return json.dumps(result, ensure_ascii=True, separators=(",", ":"))


if __name__ == "__main__":
    for line in sys.stdin:
        print(request(line), flush=True)
