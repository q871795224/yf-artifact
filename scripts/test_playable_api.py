from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
import urllib.error
import urllib.request

from serve_prototype import Handler, ROOT, SESSIONS


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class PlayableAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

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


if __name__ == '__main__':
    unittest.main()
