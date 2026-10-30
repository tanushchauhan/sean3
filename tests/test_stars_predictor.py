"""Opt-in real-checkpoint tests; no downloaded model is needed by the base suite."""
import copy
import json
import math
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.stars_bridge import Session, receive, send


def request(index, episode='test'):
    return dict(version=1, kind='step', episode=episode, sequence=index, time=index*.4,
                time_token=repr(index*.4), actors=[
                    dict(id='robot', robot=True, active=True, position=[0, 0], velocity=[0, 0], max_speed=1),
                    dict(id='b', robot=False, active=True, position=[2-index*.04, 1], velocity=[-.1, 0], max_speed=10),
                    dict(id='a', robot=False, active=True, position=[index*.08, 0], velocity=[.2, 0], max_speed=10)])


def reset(episode='test'):
    return dict(version=1, kind='reset', episode=episode, observation_steps=8, dt=.4)


@unittest.skipUnless(os.environ.get('SEAN_STARS_CHECKPOINT') and os.environ.get('SEAN_STARS_EXTENSION'),
                     'Set SEAN_STARS_CHECKPOINT and SEAN_STARS_EXTENSION for real model tests')
class CheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from runtime.stars_predictor import StarsPredictor
        torch.set_num_threads(1)
        cls.predictor = StarsPredictor(os.environ['SEAN_STARS_CHECKPOINT'], os.environ['SEAN_STARS_EXTENSION'],
                                       allow_dirty_training_source=True)

    def history(self):
        return [request(i) for i in range(8)]

    def test_matches_direct_upstream_graph_and_forecast(self):
        p = self.predictor
        h = self.history()
        torch = p.torch
        xy = torch.tensor([[next(a['position'] for a in s['actors'] if a['id'] == k)
                            for k in ('a', 'b')] for s in h])
        with torch.inference_mode():
            data = p.Data(num_nodes=2, **p.graph.build_graph(xy, torch.ones((8, 2), dtype=torch.bool),
                                                            dt=.4, **p.topology))
            scene = p.graph.to_scene(p.model.predict(data)[0], data.origin, data.heading)
            expected = (scene[:, 0] - xy[-1]) / .4
        actual = p.predict(h)
        for i, key in enumerate(('a', 'b')):
            torch.testing.assert_close(torch.tensor(actual[key]), expected[i], atol=1e-6, rtol=1e-5)

    def test_equivariant_and_ignores_robot_and_order(self):
        p = self.predictor
        h = self.history()
        actual = p.predict(h)
        moved = copy.deepcopy(h)
        for s in moved:
            s['actors'].reverse()
            for a in s['actors']:
                x, y = a['position']
                a['position'] = [-y+3, x-2] if not a['robot'] else [999, 999]
        result = p.predict(moved)
        for k, (x, y) in actual.items():
            self.assertAlmostEqual(result[k][0], -y, places=5)
            self.assertAlmostEqual(result[k][1], x, places=5)

    def test_actual_history_reset_masks_and_empty_population(self):
        p = self.predictor
        h = self.history()
        original = copy.deepcopy(h)
        first = p.predict(h)
        p.reset('another')
        self.assertEqual(p.predict(h), first)
        self.assertEqual(h, original)
        for s in h:
            next(a for a in s['actors'] if a['id'] == 'b')['active'] = False
        self.assertEqual(set(p.predict(h)), {'a'})
        for s in h:
            s['actors'] = [a for a in s['actors'] if a['robot']]
        self.assertEqual(p.predict(h), {})

    def test_session_warmup_and_speed_fault(self):
        session = Session(self.predictor, 8, .4)
        session.handle(reset())
        for i in range(8):
            r = request(i)
            for a in r['actors']:
                if not a['robot']: a['max_speed'] = 0
            if i < 7:
                self.assertFalse(session.handle(r)['ready'])
            else:
                with self.assertRaisesRegex(ValueError, 'excessive'): session.handle(r)
        with self.assertRaisesRegex(ValueError, 'Faulted'): session.handle(reset('new'))

    def test_real_worker_round_trip(self):
        process = subprocess.Popen([sys.executable, '-u', str(ROOT/'runtime/stars_bridge.py'),
            '--checkpoint', os.environ['SEAN_STARS_CHECKPOINT'], '--extension', os.environ['SEAN_STARS_EXTENSION'],
            '--allow-dirty-training-source', '--port', '0', '--observation-steps', '8', '--dt', '.4'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([process.stdout], [], [], 30)[0], 'Startup timeout')
            startup = process.stdout.readline()
            self.assertTrue(startup, process.stderr.read() if process.poll() is not None else 'No startup packet')
            ready = json.loads(startup)
            self.assertEqual(ready['model'], 'stars_ma')
            with socket.create_connection(('127.0.0.1', ready['port']), timeout=5) as connection:
                send(connection, reset()); receive(connection)
                for i in range(9):
                    send(connection, request(i)); response = receive(connection)
                    self.assertEqual(response['ready'], i >= 7)
                    self.assertEqual([t['id'] for t in response['targets']], ['a', 'b'])
                    self.assertTrue(all(math.isfinite(v) for t in response['targets'] for v in t['velocity']))
                send(connection, reset('fresh')); receive(connection)
                send(connection, request(0, 'fresh')); self.assertFalse(receive(connection)['ready'])
            self.assertEqual(process.wait(timeout=10), 0)
        finally:
            if process.poll() is None: process.kill(); process.wait()
            process.stdout.close(); process.stderr.close()


if __name__ == '__main__':
    unittest.main()
