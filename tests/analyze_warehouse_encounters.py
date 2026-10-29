"""Independent, strict acceptance and descriptive headroom metrics for Warehouse encounters."""
import argparse
import itertools
import json
import math
from pathlib import Path

MODES = ('absent', 'parked', 'yielding', 'oblivious', 'nav2')
LAYOUTS = ('aisle', 'rack_end')


def xy(v):
    return (v['x'], v['z'])


def finite(value):
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, list):
        return all(finite(v) for v in value)
    return not isinstance(value, (int, float)) or math.isfinite(value)


def distribution(values):
    if not values:
        return None
    values = sorted(values)
    def percentile(p):
        i = (len(values)-1)*p
        a = int(i)
        return values[a] + (values[min(a+1,len(values)-1)]-values[a])*(i-a)
    return dict(p50=percentile(.5), p95=percentile(.95), maximum=values[-1])


def longest_stop(samples, key, index=None):
    """Seconds without leaving a 0.1 m anchor; include waits, do not label them deadlocks."""
    if not samples:
        return math.inf
    pos = lambda s: xy(s[key] if index is None else s[key][index])
    anchor, started, longest = pos(samples[0]), samples[0]['time'], 0
    for s in samples:
        if math.dist(pos(s), anchor) > .1:
            anchor, started = pos(s), s['time']
        longest = max(longest, s['time']-started)
    return longest


def analyze(report, navigation=None):
    controller = report.get('pedestrianController', 'social_forces')
    expected = set(itertools.product(report['seeds'], report['layouts'], (-1, 1), report['modes']))
    nav = {e['index']: e for e in (navigation or {}).get('episodes', [])}
    episodes = []
    for e in report['episodes']:
        samples = e.get('samples', [])
        people = e.get('people', [])
        errors = []
        if not e.get('setup') or not e.get('complete') or e.get('error'):
            errors.append('setup or episode incomplete')
        if controller == 'orca':
            identities = {s.get('controllerEpisodeId') for s in samples}
            sequences = [s.get('controllerSequence', -1) for s in samples]
            if (e.get('controllerFaulted') or not e.get('inferenceMilliseconds') or
                    any(not isinstance(v,(int,float)) or not math.isfinite(v) or v < 0
                        for v in e.get('inferenceMilliseconds', []))):
                errors.append('controller failure or missing inference timings')
            if (len(identities) != 1 or not all(identities) or not sequences or max(sequences) < 0 or
                    any(b < a for a,b in zip(sequences,sequences[1:]))):
                errors.append('controller episode or sequence corruption')
            if any(len(s.get(k, [])) != 4 for s in samples for k in ('personTargetVelocities','personActualVelocities')):
                errors.append('missing controller velocity telemetry')
        center = (-5,5) if e['layout'] == 'aisle' else (-5,-8)
        expected_robot = (1,-15) if e['mode'] == 'absent' else (center if e['mode'] == 'parked' else ((center[0],center[1]-4) if e['layout']=='aisle' else (center[0]-4*e['mirror'],center[1])))
        expected_goal = (center[0],center[1]+4) if e['layout']=='aisle' else (center[0]+4*e['mirror'],center[1])
        if math.dist(xy(e['robotStart']),expected_robot) > .2 or math.dist(xy(e['robotGoal']),expected_goal) > .2:
            errors.append('fixed robot placement mismatch')
        for i,p in enumerate(people):
            lane = -.65 if i%2 == 0 else .65
            depth = 3.5 if i < 2 else 5
            start = (center[0]+lane*e['mirror'],center[1]+depth)
            goal_depth = 5 if i < 2 else 3.5
            goal = (start[0],center[1]-goal_depth) if e['layout'] == 'aisle' else (center[0]+(4+lane)*e['mirror'],center[1]-goal_depth)
            if math.dist(xy(p['start']),start) > .2 or math.dist(xy(p['goal']),goal) > .2:
                errors.append('fixed person placement mismatch')
        if not finite(e):
            errors.append('nonfinite telemetry')
        if len(people) != 4 or len(samples) < 2:
            errors.append('missing people or samples')
        shape_ok = all(len(s['people']) == len(s['robotClearances']) == len(s['goalDistances']) == 4
                       and len(s['personClearances']) == 6 for s in samples)
        if not shape_ok:
            errors.append('invalid sample shape')
        if samples:
            times = [s['time'] for s in samples]
            if times[0] != 0 or any(not 0 < b-a <= report['step']*1.5 for a,b in zip(times,times[1:])):
                errors.append('sampling gap or invalid start time')
            if times[-1] > report['deadline']+.01 or abs(times[-1]-e['duration']) > .01:
                errors.append('deadline or duration mismatch')
            if math.dist(xy(samples[0]['robot']), xy(e['robotStart'])) > .01:
                errors.append('robot start mismatch')
        if samples and any(abs(s['robot']['y']-e['robotStart']['y']) > .01 for s in samples):
            errors.append('robot height drift')
        if len(people) == 4 and samples and shape_ok:
            if any(abs(s['people'][i]['y']-p['start']['y']) > .25 for i,p in enumerate(people) for s in samples):
                errors.append('person left floor height')
            for i,p in enumerate(people):
                if math.dist(xy(samples[0]['people'][i]), xy(p['start'])) > .05:
                    errors.append('person start mismatch')
                if not .19 <= p['radius'] <= .21 or not p['avatar'] or len(p['plan']) < 2:
                    errors.append('invalid person metadata')
                reached = [s['time'] for s in samples if s['goalDistances'][i] <= 1]
                if not reached or p['reachedSeconds'] < 0 or abs(p['reachedSeconds']-reached[0]) > report['step']*1.5:
                    errors.append('person missed goal')
                for s in samples:
                    if abs(math.dist(xy(s['people'][i]),xy(p['goal']))-s['goalDistances'][i]) > .002:
                        errors.append('goal metric mismatch'); break
            for s in samples:
                gaps = [math.dist(xy(s['people'][i]),xy(s['people'][j]))-people[i]['radius']-people[j]['radius']
                        for i,j in itertools.combinations(range(4),2)]
                if any(abs(a-b) > .002 for a,b in zip(gaps,s['personClearances'])):
                    errors.append('person clearance mismatch'); break
        min_robot = min((v for s in samples for v in s['robotClearances']), default=-math.inf)
        min_person = min((v for s in samples for v in s['personClearances']), default=-math.inf)
        robot_goal_error = math.dist(xy(samples[-1]['robot']),xy(e['robotGoal'])) if samples else math.inf
        if e['mode'] in ('absent','parked'):
            if any(math.dist(xy(s['robot']),xy(e['robotStart'])) > .01 for s in samples):
                errors.append('stationary control moved')
        elif robot_goal_error > .4:
            errors.append('robot missed goal')
        if len(e.get('robotPlan', [])) < 2:
            errors.append('missing robot path')
        if e['mode'] == 'nav2':
            n = nav.get(e['index'], {})
            if not n.get('passed') or n.get('status') != 4:
                errors.append('Nav2 did not qualify')
        # Environment/person collisions invalidate every mode; robot/person risk is
        # an outcome for the explicitly oblivious control, a safety gate otherwise.
        if e.get('personPersonContacts', 0) or e.get('personObjectContacts', 0) or e.get('robotObjectContacts', 0) or min_person < 0:
            errors.append('person/person or environment contact')
        safe = e.get('robotPersonContacts', 0) == 0 and min_robot >= 0
        if e['mode'] != 'oblivious' and not safe:
            errors.append('robot/person contact')
        following_errors, moving_errors, stationary_errors, achieved_speeds = [], [], [], []
        if shape_ok:
            for a,b in zip(samples,samples[1:]):
                dt = b['time']-a['time']
                if dt <= 0:
                    continue
                for i in range(4):
                    actual = tuple((v-u)/dt for u,v in zip(xy(a['people'][i]),xy(b['people'][i])))
                    speed = math.hypot(*actual)
                    achieved_speeds.append(speed)
                    # Samples are captured after physics; the interval-ending
                    # sample carries the target applied for that physics tick.
                    if len(b.get('personTargetVelocities',[])) == 4:
                        target = xy(b['personTargetVelocities'][i])
                        error = math.dist(actual,target)
                        following_errors.append(error)
                        (moving_errors if max(speed,math.hypot(*target))>.01 else stationary_errors).append(error)
        episodes.append(dict(index=e['index'], seed=e['seed'], layout=e['layout'], mirror=e['mirror'], mode=e['mode'],
            passed=not errors, safe=safe, errors=sorted(set(errors)), duration=e.get('duration'),
            min_robot_clearance_m=min_robot, min_person_clearance_m=min_person,
            robot_goal_error_m=robot_goal_error, robot_person_contacts=e.get('robotPersonContacts',0),
            person_person_callbacks=e.get('personPersonContacts',0), person_object_contacts=e.get('personObjectContacts',0),
            robot_object_contacts=e.get('robotObjectContacts',0),
            person_completion_seconds=[p['reachedSeconds'] for p in people],
            robot_path_m=sum(math.dist(xy(a['robot']),xy(b['robot'])) for a,b in zip(samples,samples[1:])),
            person_paths_m=[sum(math.dist(xy(a['people'][i]),xy(b['people'][i])) for a,b in zip(samples,samples[1:])) for i in range(4)] if shape_ok else [],
            longest_robot_pause_s=longest_stop(samples,'robot'),
            longest_person_pauses_s=[longest_stop(samples,'people',i) for i in range(4)] if shape_ok else [],
            yielding_seconds=sum(b['time']-a['time'] for a,b in zip(samples,samples[1:]) if a['yielding']),
            inference_latency_ms=distribution([v for v in e.get('inferenceMilliseconds',[]) if isinstance(v,(int,float)) and math.isfinite(v)]),
            achieved_target_velocity_error_mps=distribution(following_errors),
            moving_velocity_error_mps=distribution(moving_errors),
            stationary_velocity_error_mps=distribution(stationary_errors),
            achieved_speed_mps=distribution(achieved_speeds)))
    nav_indices = {e['index'] for e in episodes if e['mode']=='nav2'}
    nav_episodes = (navigation or {}).get('episodes',[])
    navigation_ok = (not nav_indices or bool(navigation and navigation.get('passed') and not navigation.get('error')
        and not navigation.get('forced_nav2_kill') and len(nav_episodes)==len(nav_indices)
        and {e['index'] for e in nav_episodes}==nav_indices
        and all(e.get('published_people')==4 and e.get('fresh_sensors') and e.get('plan_status')==4
                and len(e.get('plan',[]))>=2 and e.get('goal_error',math.inf)<=.4
                and e.get('scan_statistics',{}).get('positive_infinity_samples',0)>0
                and not any(e.get('scan_statistics',{}).get(k,0) for k in ('nan_samples','negative_infinity_samples','invalid_finite_samples')) for e in nav_episodes)))
    actual = {(e['seed'],e['layout'],e['mirror'],e['mode']) for e in episodes}
    controller_schema_ok = (controller == 'social_forces' and report.get('model') == 'ColliderV1')
    actuation = report.get('actuationModel','AnimatedRootMotionV1')
    controller_schema_ok = controller_schema_ok and actuation in ('AnimatedRootMotionV1','VelocityTargetsV1')
    if controller == 'orca':
        settings = report.get('orcaSettings') or {}
        controller_schema_ok = (report.get('model') == 'ORCA-RVO2-v2.0.1' and
            actuation == 'VelocityTargetsV1' and
            report.get('orcaSourceRevision') == '5b7147d36d5cc6310c8e74c6955145c0fdc5fe06' and
            report.get('geometryModel') == 'NavMeshBoundaryV1' and report.get('controllerRobotRadius',0) > 0 and
            report.get('controllerObstacleCount',0) > 0 and finite(settings) and
            all(isinstance(settings.get(k),(int,float)) and settings[k] > 0 for k in
                ('decisionPeriod','neighborDistance','maxNeighbors','agentHorizon','obstacleHorizon')))
        if controller_schema_ok:
            cadence = settings['decisionPeriod']/report['step']
            controller_schema_ok = (isinstance(settings['maxNeighbors'],int) and cadence >= 1 and abs(cadence-round(cadence))<1e-4)
    schema_ok = (report.get('schema') == 2 and report.get('laserNoReturn') == 'PositiveInfinity' and report.get('layoutVersion') == 3 and controller_schema_ok
                 and report.get('contactModel') == 'VelocityBodyV1' and any(abs(report['step']-v)<1e-6 for v in (.02,.04))
                 and report['deadline'] == 45 and abs(report['desiredSpeed']-.6) < 1e-6
                 and len(set(report['seeds'])) == len(report['seeds'])
                 and len(set(report['modes'])) == len(report['modes']) and set(report['modes']) <= set(MODES)
                 and len(set(report['layouts'])) == len(report['layouts']) and set(report['layouts']) <= set(LAYOUTS))
    pairs = []
    for seed,layout,mirror in itertools.product(report['seeds'],report['layouts'],(-1,1)):
        modes = {e['mode']:e for e in episodes if (e['seed'],e['layout'],e['mirror']) == (seed,layout,mirror)}
        if 'yielding' in modes and 'oblivious' in modes:
            y,o = modes['yielding'],modes['oblivious']
            benefit = y['min_robot_clearance_m']-o['min_robot_clearance_m']
            pairs.append(dict(seed=seed,layout=layout,mirror=mirror,clearance_benefit_m=benefit,
                              contact_reduction=o['robot_person_contacts']-y['robot_person_contacts'],
                              yielding_delay_s=y['duration']-o['duration'],
                              distinguishes=benefit >= .1 or o['robot_person_contacts'] > y['robot_person_contacts']))
    return dict(complete=report['complete'], pedestrian_controller=controller, pedestrian_actuation=actuation, expected=len(expected),
                passed=bool(report['complete'] and not report.get('error') and schema_ok and expected
                            and navigation_ok and len(episodes)==len(expected) and actual==expected and all(e['passed'] for e in episodes)),
                headroom_demonstrated=bool(pairs and all(p['distinguishes'] for p in pairs)),
                headroom_pairs=pairs, episodes=episodes)


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('input',type=Path); p.add_argument('--navigation',type=Path)
    a=p.parse_args()
    result=analyze(json.loads(a.input.read_text()),json.loads(a.navigation.read_text()) if a.navigation else None)
    def serializable(v):
        if isinstance(v,dict):return {k:serializable(x) for k,x in v.items()}
        if isinstance(v,list):return [serializable(x) for x in v]
        return None if isinstance(v,float) and not math.isfinite(v) else v
    a.input.with_name('summary.json').write_text(json.dumps(serializable(result),indent=2,allow_nan=False)+'\n')
    for e in result['episodes']: print(e)
    print('qualified',result['passed'],'headroom',result['headroom_demonstrated'])
    raise SystemExit(0 if result['passed'] else 1)
