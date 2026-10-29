"""Model-independent history, protocol and worker-process regression tests."""
import copy
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.stars_bridge import HoldTestDouble, MAX_PACKET, Session, receive, send


def reset(episode='e'):
    return dict(version=1, kind='reset', episode=episode, observation_steps=3, dt=.4)


def step(index, episode='e', position=0):
    return dict(version=1, kind='step', episode=episode, sequence=index, time=index * .4,
                actors=[dict(id='robot', robot=True, active=True, position=[1, 2], velocity=[0, 0], max_speed=1),
                        dict(id='person', robot=False, active=True, position=[position, 0], velocity=[0, 0], max_speed=.6)])


class Predictor(HoldTestDouble):
    def __init__(self):
        self.calls, self.resets = [], []

    def reset(self, episode):
        self.resets.append(episode)

    def predict(self, history):
        self.calls.append(copy.deepcopy(history))
        return {'person': [.2, 0]}


class BridgeTests(unittest.TestCase):
    def test_warmup_uses_sample_instants_and_only_actual_feedback(self):
        predictor = Predictor()
        session = Session(predictor, 3, .4)
        session.handle(reset())
        for i in range(2):
            result = session.handle(step(i))
            self.assertFalse(result['ready'])
            self.assertEqual(result['targets'][0]['velocity'], [0, 0])
        result = session.handle(step(2, position=7))
        self.assertTrue(result['ready'])  # three instants span .8 seconds
        self.assertEqual(len(predictor.calls), 1)
        self.assertEqual(predictor.calls[0][-1]['actors'][0]['position'], [7, 0])
        session.handle(step(3, position=9))
        self.assertEqual(predictor.calls[-1][-1]['actors'][0]['position'], [9, 0])
        for actual, expected in zip([h['time'] for h in predictor.calls[-1]], [.4, .8, 1.2]):
            self.assertAlmostEqual(actual, expected)

    def test_reset_clears_history_and_predictor_state(self):
        predictor = Predictor()
        session = Session(predictor, 3, .4)
        session.handle(reset())
        session.handle(step(0))
        session.handle(reset('new'))
        self.assertFalse(session.handle(step(0, 'new'))['ready'])
        self.assertEqual(len(session.history), 1)
        self.assertEqual(predictor.resets, ['e', 'new'])

    def test_bad_requests_fault_the_connection(self):
        mutations = [lambda r: r.update(episode='old'), lambda r: r.update(sequence=2),
                     lambda r: r.update(time=.5), lambda r: r.update(version=9),
                     lambda r: r['actors'].pop(),
                     lambda r: r['actors'][1].update(active=False),
                     lambda r: r['actors'][1].update(id='new'),
                     lambda r: r['actors'][1].update(robot=True),
                     lambda r: r['actors'][1].update(position=[float('nan'), 0]),
                     lambda r: r['actors'][1].update(max_speed=-1),
                     lambda r: r['actors'][1].update(id='robot')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                session = Session(HoldTestDouble(), 3, .4)
                session.handle(reset()); session.handle(step(0))
                request = step(1); mutate(request)
                with self.assertRaises(ValueError): session.handle(request)
                with self.assertRaises(ValueError): session.handle(reset('new'))

    def test_reset_required_and_configuration_must_match(self):
        for request in [step(0), dict(reset(), dt=.2), dict(reset(), observation_steps=8)]:
            with self.assertRaises(ValueError): Session(HoldTestDouble(), 3, .4).handle(request)
        session = Session(HoldTestDouble(), 3, .4); session.handle(reset())
        with self.assertRaises(ValueError): session.handle(reset())

    def test_bad_predictions_are_not_clipped_or_partially_accepted(self):
        for output in [{}, {'robot': [0, 0]}, {'person': [2, 0]}, {'person': [float('inf'), 0]}]:
            predictor = HoldTestDouble(); predictor.predict = lambda h: output
            session = Session(predictor, 3, .4); session.handle(reset())
            session.handle(step(0)); session.handle(step(1))
            with self.assertRaises(ValueError): session.handle(step(2))

    def test_inactive_person_is_context_not_a_target(self):
        session = Session(HoldTestDouble(), 3, .4); session.handle(reset())
        request = step(0); request['actors'][1]['active'] = False
        self.assertEqual(session.handle(request)['targets'], [])
        self.assertEqual(len(session.history[-1]['actors']), 2)

    def test_transport_rejects_oversized_truncated_and_nonfinite_packets(self):
        for payload, exception in [(struct.pack('!I', MAX_PACKET + 1), ValueError),
                                   (struct.pack('!I', 2) + b'{', EOFError),
                                   (struct.pack('!I', 3) + b'NaN', ValueError)]:
            left, right = socket.socketpair()
            with left, right:
                left.sendall(payload); left.shutdown(socket.SHUT_WR)
                with self.assertRaises(exception): receive(right)

    def test_real_worker_process_round_trip_and_shutdown(self):
        script = Path(__file__).resolve().parents[1] / 'runtime/stars_bridge.py'
        process = subprocess.Popen([sys.executable, '-u', str(script), '--test-double', '--port', '0',
                                    '--observation-steps', '3', '--dt', '.4'], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            import select
            self.assertTrue(select.select([process.stdout], [], [], 5)[0], 'Worker startup deadline')
            startup = process.stdout.readline()
            self.assertTrue(startup, process.stderr.read() if process.poll() is not None else 'No startup packet')
            port = json.loads(startup)['port']
            with socket.create_connection(('127.0.0.1', port), timeout=2) as connection:
                send(connection, reset()); self.assertEqual(receive(connection)['kind'], 'reset')
                for i in range(3):
                    send(connection, step(i)); self.assertEqual(receive(connection)['ready'], i == 2)
                send(connection, reset('new')); self.assertEqual(receive(connection)['episode'], 'new')
            self.assertEqual(process.wait(timeout=5), 0)
        finally:
            if process.poll() is None: process.kill(); process.wait()
            process.stdout.close(); process.stderr.close()


if __name__ == '__main__':
    unittest.main()
