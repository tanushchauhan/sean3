"""Versioned lockstep worker boundary. No trained STARS model is bundled.

Run with --test-double to exercise transport with zero velocity outputs.
An eventual checkpoint adapter implements predict(history), returning world
velocity pairs keyed by active pedestrian ID, and reset(episode).
"""
import argparse
from collections import deque
import json
import math
import socket
import struct

VERSION = 1
MAX_PACKET = 4 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def pair(value):
    return isinstance(value, list) and len(value) == 2 and all(finite(x) for x in value)


def receive(stream):
    def exact(count):
        data = bytearray()
        while len(data) < count:
            block = stream.recv(count - len(data))
            if not block:
                raise EOFError('Worker peer disconnected')
            data.extend(block)
        return data
    length = struct.unpack('!I', exact(4))[0]
    require(0 < length <= MAX_PACKET, 'Packet length out of bounds')
    return json.loads(exact(length), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def send(stream, message):
    payload = json.dumps(message, allow_nan=False, separators=(',', ':')).encode()
    require(0 < len(payload) <= MAX_PACKET, 'Packet length out of bounds')
    stream.sendall(struct.pack('!I', len(payload)) + payload)


class HoldTestDouble:
    """Transport-only test double; never reported as STARS inference."""
    def reset(self, episode):
        pass

    def predict(self, history):
        return {a['id']: [0., 0.] for a in history[-1]['actors'] if a['active'] and not a['robot']}


class PreferredVelocityTestDouble(HoldTestDouble):
    """For animated transport tests only; no inference or learned avoidance."""
    def predict(self, history):
        return {a['id']: a['preferred_velocity'] for a in history[-1]['actors']
                if a['active'] and not a['robot']}


class Session:
    def __init__(self, predictor, observation_steps, dt):
        require(type(observation_steps) is int and observation_steps >= 2, 'Need at least two observation instants')
        require(finite(dt) and dt > 0, 'Positive sample cadence required')
        self.predictor, self.steps, self.dt = predictor, observation_steps, dt
        self.episode = None
        self.seen = set()
        self.faulted = False

    def handle(self, request):
        try:
            return self._handle(request)
        except Exception:
            self.faulted = True
            raise

    def _handle(self, request):
        require(not self.faulted, 'Faulted session requires a new connection')
        require(request.get('version') == VERSION, 'Unsupported protocol version')
        episode = request.get('episode')
        require(isinstance(episode, str) and episode.strip(), 'Episode ID required')
        if request.get('kind') == 'reset':
            require(episode not in self.seen, 'Episode IDs cannot be reused')
            require(request.get('observation_steps') == self.steps and
                    finite(request.get('dt')) and abs(request['dt'] - self.dt) < 1e-7,
                    'Worker/owner sampling configuration differs')
            self.predictor.reset(episode)
            self.seen.add(episode)
            self.episode, self.sequence, self.population = episode, -1, None
            self.history = deque(maxlen=self.steps)
            return dict(version=VERSION, kind='reset', episode=episode)
        require(request.get('kind') == 'step' and episode == self.episode, 'Reset required before matching step')
        require(type(request.get('sequence')) is int and request['sequence'] == self.sequence + 1, 'Nonconsecutive sequence')
        t = request.get('time')
        require(finite(t) and t >= 0, 'Invalid simulation time')
        if self.history:
            require(abs(t - self.history[-1]['time'] - self.dt) < 1e-4, 'Missing/off-cadence actual observation')
        actors = request.get('actors')
        require(isinstance(actors, list) and actors, 'Actors required')
        for a in actors:
            require(isinstance(a.get('id'), str) and a['id'].strip(), 'Actor ID required')
            require(type(a.get('robot')) is bool and type(a.get('active')) is bool, 'Explicit actor masks required')
            require(pair(a.get('position')) and pair(a.get('velocity')), 'Invalid executed state')
            require(finite(a.get('max_speed')) and a['max_speed'] >= 0, 'Invalid speed limit')
        actors = sorted(actors, key=lambda a: a['id'])
        require(len({a['id'] for a in actors}) == len(actors) and sum(a['robot'] for a in actors) == 1,
                'Unique IDs and exactly one robot required')
        population = [(a['id'], a['robot'], a['active'], a['max_speed']) for a in actors]
        if self.population is None:
            self.population = population
        require(population == self.population, 'Population/mask changes need an explicit new episode')
        # History contains observations only; outputs are never appended as state.
        self.history.append(dict(time=t, actors=actors))
        self.sequence = request['sequence']
        ready = len(self.history) == self.steps
        velocities = self.predictor.predict(tuple(self.history)) if ready else {
            a['id']: [0., 0.] for a in actors if a['active'] and not a['robot']}
        expected = {a['id'] for a in actors if a['active'] and not a['robot']}
        require(set(velocities) == expected, 'Predictor must supply the whole pedestrian batch only')
        for a in actors:
            if a['id'] in velocities:
                velocity = velocities[a['id']]
                require(pair(velocity) and math.hypot(*velocity) <= a['max_speed'] + 1e-6,
                        'Invalid or excessive predictor velocity; clipping is forbidden')
        return dict(version=VERSION, kind='decision', episode=episode, sequence=self.sequence,
                    time=t, valid_until=t + self.dt, ready=ready,
                    targets=[dict(id=k, velocity=velocities[k]) for k in sorted(expected)])


def serve(port, observation_steps, dt, timeout, moving_test_double=False):
    # Intentionally loopback only: this boundary has no authentication.
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', port))
        listener.listen(1)
        print(json.dumps(dict(event='listening', port=listener.getsockname()[1],
                              model='preferred_velocity_test_double' if moving_test_double else 'hold_test_double',
                              observation_steps=observation_steps, dt=dt)), flush=True)
        connection, _ = listener.accept()
        with connection:
            connection.settimeout(timeout)
            session = Session(PreferredVelocityTestDouble() if moving_test_double else HoldTestDouble(), observation_steps, dt)
            while True:
                try:
                    request = receive(connection)
                except EOFError:
                    break
                send(connection, session.handle(request))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', type=int, required=True)
    p.add_argument('--observation-steps', type=int, required=True)
    p.add_argument('--dt', type=float, required=True)
    p.add_argument('--timeout', type=float, default=30)
    p.add_argument('--test-double', action='store_true', required=True)
    p.add_argument('--moving-test-double', action='store_true', help='Echo preferred velocities after warm-up; no learned inference')
    a = p.parse_args()
    require(math.isfinite(a.timeout) and a.timeout > 0, 'Positive wall timeout required')
    serve(a.port, a.observation_steps, a.dt, a.timeout, a.moving_test_double)
