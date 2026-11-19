#!/usr/bin/env python3
"""Serve the mobile game, local art, and the shared Python match engine."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from copy import deepcopy
import json
import random
import re
import threading
import uuid
import webbrowser

from playable_match import InvalidAction, StaleAction
from growth_playable import GrowthSession as PlaySession
from growth_cards import catalog_view
from build_pages import engine_sources
from playtest_archive import PlaytestArchive, MAX_REPLAY_BYTES, timestamp


ROOT = Path(__file__).resolve().parents[1]
SESSIONS = {}
SESSIONS_LOCK = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, archive=None, **kwargs):
        self.archive = archive
        super().__init__(*args, **kwargs)

    def match_entry(self, game_id):
        with SESSIONS_LOCK:
            entry = SESSIONS.get(game_id)
            if entry is None and self.archive:
                saved = self.archive.read_session(game_id)
                if saved:
                    session, source, created_at = saved
                    entry = (session, threading.Lock(), source, created_at)
                    SESSIONS[game_id] = entry
            return entry

    def list_directory(self, path):
        self.send_error(404)
        return None

    def send_json(self, data, status=200):
        content = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path == '/api/catalog':
            self.send_json(catalog_view())
            return
        if self.path == '/api/health':
            self.send_json({'ok': True, 'mode': 'playable', 'archive': self.archive is not None,
                            'engine_version': self.archive.engine_version if self.archive else None})
            return
        route = re.fullmatch(r'/api/games/([a-f0-9]{32})(/export)?', self.path)
        if route:
            try:
                entry = self.match_entry(route[1])
            except StaleAction as error:
                self.send_json({'error': str(error)}, 409)
                return
            except (OSError, ValueError, KeyError) as error:
                self.log_error('Cannot restore playtest: %s', error)
                self.send_json({'error': '电脑上的对局文件暂时无法恢复。'}, 500)
                return
            if not entry:
                self.send_json({'error': '这局记录已不在服务中，请开始新一局。'}, 404)
                return
            session, lock, source, created_at = entry
            with lock:
                if route[2] and self.archive:
                    data = self.archive.session_record(route[1], session, source, created_at)
                else:
                    data = session.export() if route[2] else session.packet()
                self.send_json({'game_id': route[1], **data})
            return
        if self.path.startswith('/api/'):
            self.send_json({'error': '找不到该接口。'}, 404)
            return
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/prototype/")
            self.end_headers()
            return
        requested = Path(self.translate_path(self.path)).resolve()
        try:
            path = requested.relative_to(ROOT).as_posix()
        except ValueError:
            self.send_error(404)
            return
        if not (path in ('prototype', 'effects-lab', 'references/artifact-classic/cards.json',
                        'references/artifact-classic/assets/manifest.json')
                or path.startswith(('prototype/', 'effects-lab/', 'references/artifact-classic/assets/mobile/',
                                    'assets/custom/', 'scripts/fixtures/'))):
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self):
        try:
            if self.headers.get_content_type() != 'application/json':
                raise ValueError('请求需要使用 JSON。')
            length = int(self.headers.get('Content-Length', '0'))
            limit = MAX_REPLAY_BYTES if self.path == '/api/replays/import' else 16384
            if not 0 < length <= limit:
                raise ValueError('请求内容长度不正确。')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('请求内容应为对象。')
            if self.path == '/api/replays/import':
                if not self.archive:
                    self.send_json({'error': '本次服务未开启对局归档。'}, 404)
                    return
                self.send_json(self.archive.import_replay(body), 201)
                return
            if self.path == '/api/games':
                seed = body.get('seed', random.SystemRandom().randrange(1, 1000000)*3+1)
                if type(seed) is not int or not 1 <= seed <= 1000000000:
                    raise ValueError('对局种子不正确。')
                session, game_id = PlaySession(seed, body.get('deck_config')), uuid.uuid4().hex
                packet = session.packet()
                source = 'desktop' if body.get('source') == 'desktop' else 'lan-browser'
                created_at = timestamp()
                if self.archive:
                    self.archive.save_session(game_id, session, source, created_at, packet)
                with SESSIONS_LOCK:
                    SESSIONS[game_id] = (session, threading.Lock(), source, created_at)
                self.send_json({'game_id': game_id, **packet}, 201)
                return
            route = re.fullmatch(r'/api/games/([a-f0-9]{32})/actions', self.path)
            entry = self.match_entry(route[1]) if route else None
            if not entry:
                self.send_json({'error': '找不到当前对局，请重新打开战场。'}, 404)
                return
            session, lock, source, created_at = entry
            with lock:
                backup = deepcopy(session.__dict__)
                try:
                    result = session.apply(body.get('version'), body.get('action_id'))
                    if self.archive:
                        self.archive.save_session(route[1], session, source, created_at, result)
                except Exception:
                    session.__dict__.clear()
                    session.__dict__.update(backup)
                    raise
                self.send_json({'game_id': route[1], **result})
        except StaleAction as error:
            self.send_json({'error': str(error)}, 409)
        except (InvalidAction, ValueError, TypeError) as error:
            self.send_json({'error': str(error)}, 400)
        except Exception:
            import traceback
            traceback.print_exc()
            self.send_json({'error': '本次操作未完成，战场已恢复，请重新尝试。'}, 500)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--open", action="store_true", help="Open the local preview in a browser")
    parser.add_argument("--archive-dir", type=Path, default=ROOT / "output/playtests")
    args = parser.parse_args()
    archive = PlaytestArchive(args.archive_dir, engine_sources()[1])
    handler = partial(Handler, directory=str(ROOT), archive=archive)
    try:
        server = ThreadingHTTPServer((args.host, args.port), handler)
    except OSError as error:
        parser.exit(1, f"Cannot start preview: {error}. Try --port 8766.\n")
    url = f"http://127.0.0.1:{server.server_port}/prototype/"
    print(f"Mobile preview: {url}", flush=True)
    print(f"Phone on the same Wi-Fi: http://<this computer's LAN IP>:{server.server_port}/prototype/", flush=True)
    print(f"Playtests: {archive.directory}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
