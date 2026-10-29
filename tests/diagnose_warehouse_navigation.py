"""Summarize preserved Nav2 failures without changing their acceptance gates."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnose(directory, navigation_radius):
    encounter_file = directory / 'encounters.json'
    navigation_file = directory / 'warehouse-navigation.json'
    log_file = directory / 'nav2.log'
    encounters = json.loads(encounter_file.read_text())
    navigation = json.loads(navigation_file.read_text())
    lines = log_file.read_text().splitlines()
    starts = [i for i, line in enumerate(lines) if 'Begin navigating from current location' in line]
    if len(starts) != len(navigation['episodes']):
        raise ValueError('Cannot align Nav2 action logs with recorded episodes')
    result = dict(navigation_radius_m=navigation_radius, inputs={p.name: digest(p) for p in
                  (encounter_file, navigation_file, log_file)}, episodes=[])
    for action, nav in enumerate(navigation['episodes']):
        episode = next(e for e in encounters['episodes'] if e['index'] == nav['index'])
        samples = episode['samples']; last = samples[-1]
        segment = lines[starts[action]:starts[action + 1] if action + 1 < len(starts) else len(lines)]
        events = Counter()
        markers = ['detected collision ahead', 'Controller patience exceeded', 'Failed to make progress',
                   'backup failed', 'spin failed', 'Goal failed', 'Goal succeeded']
        for line in segment:
            for marker in markers:
                if marker in line: events[marker] += 1
        margins = [math.hypot(last['robot']['x']-p['x'], last['robot']['z']-p['z'])
                   - navigation_radius - person['radius'] for p, person in zip(last['people'], episode['people'])]
        # Retain a stable terminal-pose interval, distinct from the existing
        # 0.1-m-anchor pause metric. No threshold here affects acceptance.
        terminal = len(samples)-1
        while terminal > 0 and math.hypot(samples[terminal-1]['robot']['x']-last['robot']['x'],
                                          samples[terminal-1]['robot']['z']-last['robot']['z']) <= .001:
            terminal -= 1
        row = dict(index=nav['index'], status=nav['status'], passed=nav['passed'],
                   goal_error_m=nav['goal_error'], fresh_sensors=nav['fresh_sensors'],
                   log_events=dict(events), max_reported_recoveries=max((f['recoveries'] for f in nav['feedback']), default=0),
                   terminal_pose_start_seconds=samples[terminal]['time'],
                   terminal_pose_duration_seconds=last['time']-samples[terminal]['time'],
                   final_physical_clearances_m=last['robotClearances'],
                   final_navigation_circle_margins_m=margins,
                   navigation_circle_is_approximation=True,
                   physical_contacts={k:episode[k] for k in ('robotPersonContacts','robotObjectContacts','personPersonContacts','personObjectContacts')})
        map_file = directory / nav.get('final_costmap', 'missing-costmap')
        if map_file.is_file():
            costmap = json.loads(map_file.read_text())
            ox, oy, oz, ow = costmap['origin']
            if abs(oz) > 1e-6 or abs(ow-1) > 1e-6 or costmap['frame'] != 'map':
                raise ValueError('Diagnostic supports unrotated map-frame costmaps only')
            rx, ry = costmap['robot']; resolution = costmap['resolution']
            distances = [math.hypot(ox+(i % costmap['width']+.5)*resolution-rx,
                                    oy+(i // costmap['width']+.5)*resolution-ry)
                         for i, value in enumerate(costmap['data']) if value == 100]
            row['final_costmap'] = dict(sha256=digest(map_file),
                simulation_stamp_age_seconds=costmap['captured_simulation_time']-costmap['stamp'],
                received_age_wall_seconds=costmap['received_age_wall_seconds'],
                nearest_lethal_cell_center_m=min(distances) if distances else None,
                lethal_cell_centers_inside_navigation_circle=sum(d <= navigation_radius for d in distances),
                resolution_m=resolution)
        result['episodes'].append(row)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--navigation-radius', type=float, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if not math.isfinite(a.navigation_radius) or a.navigation_radius <= 0:
        p.error('Positive configured navigation radius required')
    a.output.write_text(json.dumps(diagnose(a.directory, a.navigation_radius), indent=2) + '\n')
