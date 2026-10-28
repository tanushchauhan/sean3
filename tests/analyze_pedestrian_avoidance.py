"""Independent acceptance of the opt-in Kuri pedestrian diagnostic."""
import argparse
import json
import math
from pathlib import Path


def analyze(report):
    episodes = []
    step = report['step']
    for e in report['episodes']:
        samples = e['samples']
        points = [(s['person']['x'], s['person']['z']) for s in samples]
        length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        gaps = [b['time']-a['time'] for a, b in zip(samples, samples[1:])]
        finite = all(math.isfinite(s[k]) for s in samples for k in ('time', 'clearance', 'goalDistance'))
        finite = finite and all(math.isfinite(v) for s in samples for k in ('person','robot','personVelocity','robotVelocity') for v in s[k].values())
        overlap = min((s['clearance'] for s in samples), default=-math.inf)
        e_summary = {k:v for k,v in e.items() if k != 'samples'}
        e_summary.update(path_m=length, max_lateral_m=max((abs(p[0]-points[0][0]) for p in points),default=0),
                         max_sample_gap=max(gaps,default=0), overlap_frames=sum(s['clearance'] < 0 for s in samples))
        robot_start = tuple(e['expectedRobotStart'][k] for k in ('x','z'))
        robot_positions = [tuple(s['robot'][k] for k in ('x','z')) for s in samples]
        setup_ok = bool(samples and 0 < samples[0]['time'] <= step*1.5)
        if samples and e['mode'] in ('moving','yielding'):
            # One initialization physics step precedes the recorded episode clock.
            expected = (robot_start[0],robot_start[1]+.3*(step+samples[0]['time']))
            setup_ok = setup_ok and math.dist(robot_positions[0],expected) < .002
        elif samples:
            setup_ok = setup_ok and math.dist(robot_positions[0],robot_start) < .01
        if e['mode'] in ('parked','absent'):
            setup_ok = setup_ok and all(math.dist(p,robot_start)<.01 for p in robot_positions)
        e_summary['setup_ok'] = setup_ok
        e_summary['passed'] = bool(samples and setup_ok and finite and e['reached'] and samples[-1]['goalDistance'] <= 1 and e['contacts'] == 0 and overlap >= 0
                                   and all(0 < gap <= step*1.5 for gap in gaps))
        episodes.append(e_summary)
    expected_cases = {(seed,mode,heading,round(offset,2)) for seed in report['seeds']
                      for mode in ('parked','absent','moving','yielding')
                      for heading in ((0,180) if mode == 'parked' else (0,))
                      for offset in ((-.35,0,.35) if mode == 'parked' else (-.35,.35))}
    actual_cases = {(e['seed'],e['mode'],e['heading'],round(e['offset'],2)) for e in episodes}
    expected = len(expected_cases)
    return {'complete': report['complete'], 'passed': report['complete'] and len(episodes)==expected and actual_cases==expected_cases and expected>0 and all(e['passed'] for e in episodes),
            'episodes': episodes, 'expected': expected}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    result = analyze(json.loads(args.input.read_text()))
    args.input.with_name('summary.json').write_text(json.dumps(result,indent=2)+'\n')
    for e in result['episodes']:
        print(e)
    raise SystemExit(0 if result['passed'] else 1)
