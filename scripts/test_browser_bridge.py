import json
import tempfile
from pathlib import Path
import unittest

from browser_bridge import BrowserBridge, handle_json
from build_pages import build, ROOT


class BrowserBridgeTests(unittest.TestCase):
    def create(self):
        bridge = BrowserBridge('test-engine')
        packet = bridge.request('/api/games', {'seed': 13}, new_id='a'*32)
        self.assertEqual(packet['status'], 200)
        return bridge, packet

    def test_browsers_share_the_exact_existing_opening_rules(self):
        bridge, packet = self.create()
        self.assertEqual(packet['data']['state']['round'], 1)
        self.assertEqual(packet['data']['state']['version'], 0)
        self.assertEqual(packet['save']['commands'], [])
        self.assertEqual(len(packet['data']['state']['units']), 8)

    def test_restore_replays_a_saved_command_and_preserves_state(self):
        bridge, packet = self.create()
        action = packet['data']['state']['actions'][0]['id']
        after = bridge.request('/api/games/'+'a'*32+'/actions', {'version': 0, 'action_id': action})
        restored = BrowserBridge('test-engine').request('/api/games/'+'a'*32, None, after['save'])
        self.assertEqual(restored['status'], 200)
        self.assertEqual(restored['data']['state'], after['data']['state'])

    def test_stale_click_does_not_add_a_saved_command(self):
        bridge, packet = self.create()
        command = {'version': 0, 'action_id': 'pass'}
        bridge.request('/api/games/'+'a'*32+'/actions', command)
        self.assertEqual(bridge.request('/api/games/'+'a'*32+'/actions', command)['status'], 409)
        self.assertEqual(len(bridge.save_record()['commands']), 1)

    def test_changed_engine_does_not_silently_apply_an_incompatible_save(self):
        _, packet = self.create()
        restored = BrowserBridge('updated-engine').request('/api/games/'+'a'*32, None, packet['save'])
        self.assertEqual(restored['status'], 409)

    def test_forged_saved_action_cannot_be_executed(self):
        _, packet = self.create()
        packet['save']['commands'] = [{'version': 0, 'action_id': 'fake'}]
        result = BrowserBridge('test-engine').request('/api/games/'+'a'*32, None, packet['save'])
        self.assertEqual(result['status'], 400)

    def test_missing_local_game_and_bad_seed_are_reported(self):
        bridge = BrowserBridge('test-engine')
        self.assertEqual(bridge.request('/api/games/'+'b'*32, None)['status'], 404)
        self.assertEqual(bridge.request('/api/games', {'seed': True}, new_id='a'*32)['status'], 400)

    def test_browser_export_uses_the_same_json_format_as_the_local_game(self):
        bridge, _ = self.create()
        bridge.request('/api/games/'+'a'*32+'/actions', {'version': 0, 'action_id': 'concede'})
        data = bridge.request('/api/games/'+'a'*32+'/export', None)['data']
        self.assertEqual((data['winner'], data['phase'], data['seed']), (1, 'finished', 13))
        self.assertEqual(data['commands'], [{'version': 0, 'action_id': 'concede'}])
        parsed = json.loads(handle_json(bridge, json.dumps({'path':'/api/games/'+'a'*32, 'body':None})))
        self.assertEqual(parsed['data']['state']['phase'], 'finished')


class StaticBuildTests(unittest.TestCase):
    def test_static_build_is_self_contained_and_preserves_engine_source(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'site'
            first = build(out)
            self.assertGreater(first['bytes'], 10000000)
            self.assertLess(first['bytes'], 18000000)
            self.assertIn('"browser"', (out/'prototype/runtime-config.js').read_text())
            bundle = json.loads((out/'prototype/engine-files.json').read_text())
            engine = next(f for f in bundle['files'] if f['path'] == 'scripts/playable_match.py')
            self.assertEqual(engine['content'], (ROOT/'scripts/playable_match.py').read_text())
            for file in bundle['files']:
                if file['path'].endswith('.json'):
                    self.assertEqual(json.loads(file['content']), json.loads((ROOT/file['path']).read_text()))
            self.assertTrue((out/'vendor/pyodide/pyodide.asm.wasm').is_file())
            self.assertTrue((out/'references/artifact-classic/assets/mobile/mini_image/10020.webp').is_file())
            self.assertFalse(list((out/'references/artifact-classic/assets').rglob('*.png')))
            self.assertTrue((out/'runtime-cache.js').is_file())
            self.assertFalse((out/'output').exists())
            self.assertFalse((out/'effects-lab').exists())
            self.assertEqual((out/'prototype/effects.js').read_text(), (ROOT/'prototype/effects.js').read_text())
            self.assertTrue((out/'prototype/game-effects.js').is_file())
            self.assertEqual(json.loads((out/'version.json').read_text())['release'], '0.3')
            self.assertTrue((out/'.nojekyll').is_file())
            self.assertEqual(build(out)['engine_version'], first['engine_version'])

    def test_builder_refuses_to_replace_user_files(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out/'keep.txt').write_text('keep this')
            with self.assertRaises(ValueError):
                build(out)
            self.assertEqual((out/'keep.txt').read_text(), 'keep this')


if __name__ == '__main__':
    unittest.main()
