import copy
import unittest
from analyze_pedestrian_avoidance import analyze


def fixture():
    vector = {'x':0.,'y':0.,'z':0.}
    sample = {'time':.02,'clearance':.5,'goalDistance':.5,
              **{k:dict(vector) for k in ('person','robot','personVelocity','robotVelocity')}}
    episodes = []
    for mode in ('parked','absent','moving','yielding'):
        for heading in ((0,180) if mode == 'parked' else (0,)):
            for offset in ((-.35,0,.35) if mode == 'parked' else (-.35,.35)):
                samples = [copy.deepcopy(sample),copy.deepcopy(sample)]
                samples[1]['time'] = .04
                if mode in ('moving','yielding'):
                    for s in samples: s['robot']['z'] = .3*(.02+s['time'])
                episodes.append(dict(seed=7,mode=mode,heading=heading,offset=offset,contacts=0,
                                     reached=True,expectedRobotStart=dict(vector),samples=samples))
    return dict(step=.02,seeds=[7],complete=True,episodes=episodes)


class PedestrianAnalysisTests(unittest.TestCase):
    def test_complete_matrix_passes(self):
        self.assertTrue(analyze(fixture())['passed'])

    def test_setup_errors_and_false_success_fail(self):
        mutations = [lambda d: d.update(complete=False),
                     lambda d: d.update(seeds=[7,42]),
                     lambda d: d['episodes'].pop(),
                     lambda d: d['episodes'].__setitem__(0,copy.deepcopy(d['episodes'][1])),
                     lambda d: d['episodes'][0].update(reached=False),
                     lambda d: d['episodes'][0].update(contacts=1),
                     lambda d: d['episodes'][0].update(samples=[]),
                     lambda d: d['episodes'][0]['samples'][0].update(clearance=-.001),
                     lambda d: d['episodes'][0]['samples'][0].update(clearance=float('nan')),
                     lambda d: d['episodes'][0]['samples'][-1].update(goalDistance=2),
                     lambda d: d['episodes'][0]['samples'][-1].update(time=.1),
                     lambda d: d['episodes'][0]['samples'][-1].update(time=.01),
                     lambda d: d['episodes'][0]['samples'][-1]['robot'].update(x=1)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data = fixture(); mutation(data)
                self.assertFalse(analyze(data)['passed'])

    def test_larger_step_accounts_for_moving_initialization_without_accepting_wrong_pose(self):
        data = fixture(); data['step'] = .04
        for e in data['episodes']:
            for i,s in enumerate(e['samples']):
                s['time'] = (i+1)*.04
                if e['mode'] in ('moving','yielding'): s['robot']['z'] = .3*(.04+s['time'])
        self.assertTrue(analyze(data)['passed'])
        e = next(e for e in data['episodes'] if e['mode']=='moving')
        e['samples'][0]['robot']['z'] = 0
        self.assertFalse(analyze(data)['passed'])

    def test_requested_control_only_matrix_cannot_masquerade_as_full_run(self):
        data = fixture(); data['episodes'] = [e for e in data['episodes'] if e['mode']=='absent']
        self.assertFalse(analyze(data)['passed'])
        data['modes'] = ['absent']
        self.assertTrue(analyze(data)['passed'])
        self.assertEqual(analyze(data)['expected'],2)
