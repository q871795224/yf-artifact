"""JSON interface for the same PlaySession inside a browser Python worker."""

from copy import deepcopy
import json
import re

from playable_match import PlaySession, InvalidAction, StaleAction


class BrowserBridge:
    def __init__(self, engine_version):
        self.engine_version = engine_version
        self.game_id = None
        self.session = None

    def _restore(self, game_id, record):
        if self.game_id == game_id and self.session is not None:
            return
        if not record or record.get('game_id') != game_id:
            raise LookupError('没有找到这局的浏览器存档，请开始新一局。')
        if record.get('engine_version') != self.engine_version:
            raise StaleAction('游戏版本已更新，旧对局无法继续，请开始新一局。')
        session = PlaySession(record['seed'])
        for command in record['commands']:
            session.apply(command['version'], command['action_id'])
        self.session, self.game_id = session, game_id

    def save_record(self):
        return {'schema_version': 1, 'engine_version': self.engine_version,
                'game_id': self.game_id, 'seed': self.session.seed,
                'commands': deepcopy(self.session.commands)}

    def request(self, path, body, record=None, new_id=None, seed=None):
        try:
            if path == '/api/games' and body is not None:
                chosen_seed = body.get('seed', seed)
                if type(chosen_seed) is not int or not 1 <= chosen_seed <= 1000000000:
                    raise InvalidAction('对局种子不正确。')
                session = PlaySession(chosen_seed)
                self.session, self.game_id = session, new_id
                return self._response(session.packet(), save=True)
            route = re.fullmatch(r'/api/games/([a-f0-9]{32})(/actions|/export)?', path)
            if not route:
                raise LookupError('找不到该对局。')
            self._restore(route[1], record)
            if route[2] == '/export' and body is None:
                return self._response(self.session.export())
            if route[2] == '/actions' and body is not None:
                backup = deepcopy(self.session)
                try:
                    packet = self.session.apply(body.get('version'), body.get('action_id'))
                except Exception:
                    self.session = backup
                    raise
                return self._response(packet, save=True)
            if route[2] is None and body is None:
                return self._response(self.session.packet())
            raise InvalidAction('当前操作不可用。')
        except LookupError as error:
            return {'status': 404, 'data': {'error': str(error)}}
        except StaleAction as error:
            return {'status': 409, 'data': {'error': str(error)}}
        except (InvalidAction, ValueError, TypeError, KeyError) as error:
            return {'status': 400, 'data': {'error': str(error)}}

    def _response(self, data, save=False):
        response = {'status': 200, 'data': {'game_id': self.game_id, **data}}
        if save:
            response['save'] = self.save_record()
        return response


def handle_json(bridge, serialized):
    return json.dumps(bridge.request(**json.loads(serialized)), ensure_ascii=False)
