"""Check decodable images and measured target geometry from a player capture."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image


def vector(value):
    return np.array([value[k] for k in ('x', 'y', 'z')], dtype=float)


def rotate(q, v):
    xyz = vector(q)
    return v + 2 * np.cross(xyz, np.cross(xyz, v) + q['w'] * v)


def analyze(directory):
    root = Path(directory)
    capture = json.loads((root / 'capture.json').read_text())
    checks = {}
    measurements = {}
    topics = ['/robot_firstperson_rgb', '/robot_thirdperson_rgb', '/robot_overhead_rgb', '/center_depth']
    for topic in topics:
        images = capture['samples'].get(topic + '/compressed', [])
        infos = capture['samples'].get(topic + '/camera_info', [])
        checks[topic + ':images'] = len(images) == 3 and all(
            'decode_error' not in image and image.get('size') == [640, 480] for image in images)
        checks[topic + ':calibration_size'] = bool(infos) and all(
            info['width'] == 640 and info['height'] == 480 for info in infos)
        image_headers = [image.get('header', {}) for image in images]
        info_headers = [info['header'] for info in infos]
        checks[topic + ':matching_frames'] = bool(images and infos) and len({
            h.get('frame_id', '') for h in image_headers + info_headers}) == 1 and bool(image_headers[0].get('frame_id'))
        def stamp_key(header):
            stamp = header.get('stamp', {})
            return stamp.get('sec'), stamp.get('nanosec')
        checks[topic + ':paired_timestamps'] = len({stamp_key(h) for h in image_headers} &
            {stamp_key(h) for h in info_headers}) >= 2
        stamp = capture['stamps'].get(topic + '/compressed', {})
        checks[topic + ':advancing_time'] = stamp.get('last', 0) - stamp.get('first', 0) > 1 and stamp.get('regressions') == 0
        checks[topic + ':fresh'] = -0.1 <= capture['last_clock'] - stamp.get('last', 0) < 3
        checks[topic + ':count'] = capture['counts'].get(topic + '/compressed', 0) >= 3
    checks['no_decode_errors'] = not capture['decode_errors']
    fixture_path = root / 'fixture.json'
    if fixture_path.exists():
        fixture = json.loads(fixture_path.read_text())
        wall = vector(fixture['wallPosition'])
        normal = vector(fixture['wallNormal'])
        heading = math.radians(fixture['heading'])

        def body_flu(v):
            x, y, z = v
            bx = math.cos(heading) * x - math.sin(heading) * z
            bz = math.sin(heading) * x + math.cos(heading) * z
            return np.array([bz, -bx, y])

        for camera in fixture['cameras']:
            topic = camera['topic']
            if topic not in topics:
                continue
            tf = capture['transforms'].get(camera['frame'])
            if tf:
                position_error = np.linalg.norm(vector(tf['transform']['translation']) -
                    body_flu(vector(camera['position']) - vector(fixture['robotPosition'])))
                forward, up = vector(camera['forward']), vector(camera['up'])
                expected = [body_flu(np.cross(up, forward)), body_flu(-up), body_flu(forward)]
                axis_error = max(np.linalg.norm(rotate(tf['transform']['rotation'], np.eye(3)[i]) - expected[i])
                                 for i in range(3))
                measurements[topic + ':frame'] = {'position_error_m': float(position_error), 'axis_error': float(axis_error)}
                checks[topic + ':optical_frame'] = position_error < 0.002 and axis_error < 0.002
            else:
                checks[topic + ':optical_frame'] = False
        rgb = np.array(Image.open(root / 'robot_firstperson_rgb__compressed-3.png').convert('RGB'))
        info = capture['samples']['/robot_firstperson_rgb/camera_info'][-1]
        masks = [(rgb[:, :, 0] > 180) & (rgb[:, :, 1] < 80) & (rgb[:, :, 2] < 80),
                 (rgb[:, :, 1] > 180) & (rgb[:, :, 0] < 80) & (rgb[:, :, 2] < 80),
                 (rgb[:, :, 2] > 180) & (rgb[:, :, 0] < 80) & (rgb[:, :, 1] < 80),
                 (rgb[:, :, 0] > 180) & (rgb[:, :, 1] > 180) & (rgb[:, :, 2] < 80)]
        rgb_camera = next(c for c in fixture['cameras'] if c['topic'] == '/robot_firstperson_rgb')
        marker_distance = float(np.dot(wall - vector(rgb_camera['position']), vector(rgb_camera['forward']))) - 0.03
        errors = []
        centroids = []
        for index, mask in enumerate(masks):
            ys, xs = np.nonzero(mask)
            center = [float(xs.mean()), float(ys.mean())] if len(xs) else [None, None]
            centroids.append(center)
            # Marker front faces are 0.03m closer than the measured wall plane.
            expected = [info['k'][2] + info['k'][0] * (-1 if index % 2 == 0 else 1) / marker_distance,
                        info['k'][5] - info['k'][4] * (0.8 if index < 2 else -0.8) / marker_distance]
            errors.append(float(np.linalg.norm(np.array(center) - expected)) if len(xs) > 20 else 1e6)
        measurements['marker_centroids'] = centroids
        measurements['marker_projection_error_pixels'] = errors
        checks['rgb_orientation_and_projection'] = max(errors) < 3
        depth_camera = next(c for c in fixture['cameras'] if c['topic'] == '/center_depth')
        expected_depth = np.dot(wall - vector(depth_camera['position']), normal) / np.dot(vector(depth_camera['forward']), normal)
        packed = np.array(Image.open(root / 'center_depth__compressed-3.png').convert('RGBA'), dtype=float) / 255
        # The retained shader's fourth multiplier is 160581375 (legacy encoding).
        depth = (packed @ np.array([1, 1/255, 1/65025, 1/160581375])) * depth_camera['far']
        measured_depth = float(np.median(depth[237:243, 317:323]))
        measurements['depth'] = {'expected_m': float(expected_depth), 'measured_m': measured_depth}
        checks['depth_distance'] = abs(measured_depth - expected_depth) < 0.03
        scan = capture['samples']['/laser_raycast'][-1]
        laser_position = vector(fixture['laserPosition'])
        laser_forward = vector(fixture['laserForward'])
        laser_measurements = []
        for index in (0, 15, 30, 330, 345):
            angle = scan['angle_min'] + index * scan['angle_increment']
            c, s = math.cos(angle), math.sin(angle)
            x, y, z = laser_forward
            ray = np.array([c*x - s*z, y, s*x + c*z])
            expected_scan = float(np.dot(wall - laser_position, normal) / np.dot(ray, normal))
            measured_scan = scan['ranges'][index]
            laser_measurements.append({'index': index, 'expected_m': expected_scan, 'measured_m': measured_scan})
        measurements['laser'] = laser_measurements
        checks['laser_distance'] = all(scan['range_min'] <= m['expected_m'] <= scan['range_max'] and
            abs(m['measured_m'] - m['expected_m']) < 0.01 for m in laser_measurements)
        laser_tf = capture['transforms'].get(scan['header']['frame_id'])
        if laser_tf:
            position_error = float(np.linalg.norm(vector(laser_tf['transform']['translation']) -
                body_flu(laser_position - vector(fixture['robotPosition']))))
            forward_error = float(np.linalg.norm(rotate(laser_tf['transform']['rotation'], np.array([1, 0, 0])) -
                body_flu(laser_forward)))
            measurements['laser_frame'] = {'position_error_m': position_error, 'forward_error': forward_error}
            checks['laser_frame'] = position_error < 0.002 and forward_error < 0.002
        else:
            checks['laser_frame'] = False
    checks = {key: bool(value) for key, value in checks.items()}
    return {'passed': all(checks.values()), 'checks': checks, 'measurements': measurements}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    args = parser.parse_args()
    try:
        report = analyze(args.directory)
    except Exception as error:
        report = {'passed': False, 'error': str(error)}
    Path(args.directory, 'analysis.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
