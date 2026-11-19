from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
import urllib.error
import urllib.request

from serve_prototype import Handler, ROOT, SESSIONS
from playtest_archive import PlaytestArchive


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class PlayableAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = TemporaryDirectory()
        cls.archive = PlaytestArchive(cls.storage.name, 'b'*64)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(
            QuietHandler, directory=str(ROOT), archive=cls.archive))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.storage.cleanup()

    def setUp(self):
        self.created = []

    def tearDown(self):
        for key in self.created:
            SESSIONS.pop(key, None)

    def call(self, path, body=None, content_type='application/json'):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base+path, data=data,
                                         headers={'Content-Type': content_type})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as response:
            return response.code, json.loads(response.read())

    def create(self):
        status, packet = self.call('/api/games', {'seed': 13})
        self.assertEqual(status, 201)
        self.created.append(packet['game_id'])
        return packet

    def test_create_reload_and_export(self):
        first = self.create()
        key = first['game_id']
        status, current = self.call('/api/games/'+key)
        self.assertEqual((status, current['state']), (200, first['state']))
        status, exported = self.call('/api/games/'+key+'/export')
        self.assertEqual((status, exported['seed'], exported['commands']), (200, 13, []))
        self.assertNotIn('opponent_hand', exported)

    def test_duplicate_command_is_rejected_without_a_second_action(self):
        packet = self.create()
        path = '/api/games/'+packet['game_id']+'/actions'
        command = {'version': 0, 'action_id': packet['state']['actions'][0]['id']}
        status, first = self.call(path, command)
        self.assertEqual(status, 200)
        self.assertEqual(first['state']['version'], 1)
        self.assertEqual(self.call(path, command)[0], 409)
        self.assertEqual(self.call('/api/games/'+packet['game_id'])[1]['state'], first['state'])

    def test_simultaneous_browser_submissions_only_spend_one_action(self):
        packet = self.create()
        path = '/api/games/'+packet['game_id']+'/actions'
        command = {'version': 0, 'action_id': 'pass'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: self.call(path, command), range(2)))
        self.assertEqual(sorted(r[0] for r in responses), [200, 409])
        self.assertEqual(self.call('/api/games/'+packet['game_id'])[1]['state']['version'], 1)

    def test_invalid_target_cannot_change_mana_gold_or_board(self):
        packet = self.create()
        path = '/api/games/'+packet['game_id']+'/actions'
        self.assertEqual(self.call(path, {'version': 0, 'action_id': 'forged', 'mana': 999})[0], 400)
        self.assertEqual(self.call('/api/games/'+packet['game_id'])[1]['state'], packet['state'])

    def test_unknown_game_and_malformed_creation_are_explicit_errors(self):
        self.assertEqual(self.call('/api/games/'+'a'*32)[0], 404)
        self.assertEqual(self.call('/api/games', {'seed': True})[0], 400)
        self.assertEqual(self.call('/api/games', [], 'application/json')[0], 400)
        self.assertEqual(self.call('/api/games', {}, 'text/plain')[0], 400)

    def test_concede_finishes_and_rejects_further_play(self):
        packet = self.create()
        path = '/api/games/'+packet['game_id']+'/actions'
        status, end = self.call(path, {'version': 0, 'action_id': 'concede'})
        self.assertEqual((status, end['state']['phase'], end['state']['winner']), (200, 'finished', 1))
        self.assertEqual(self.call(path, {'version': 1, 'action_id': 'pass'})[0], 400)

    def test_archive_restores_and_imports_export_without_showing_local_files(self):
        packet = self.create()
        key = packet['game_id']
        path = '/api/games/'+key
        self.call(path+'/actions', {'version': 0, 'action_id': 'pass'})
        before = self.call(path)[1]['state']
        SESSIONS.pop(key)
        self.assertEqual(self.call(path)[1]['state'], before)
        saved = json.loads((Path(self.storage.name)/f'{key}.json').read_text())
        self.assertEqual(saved['source'], 'lan-browser')
        self.assertEqual(saved['commands'], [{'version': 0, 'action_id': 'pass'}])
        self.assertEqual(len(saved['forts']), 2)
        _, exported = self.call(path+'/export')
        status, imported = self.call('/api/replays/import', exported)
        self.assertEqual((status, imported['verified'], imported['duplicate']), (201, True, False))
        self.assertTrue(self.call('/api/replays/import', exported)[1]['duplicate'])
        foreign = dict(exported, engine_version='a'*64)
        status, result = self.call('/api/replays/import', foreign)
        self.assertEqual((status, result['verified']), (201, False))
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.base+'/output/playtests/'+key+'.json')
        self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
