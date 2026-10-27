"""Capture a bounded rendered-player baseline; retain malformed payloads too."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
import rclpy
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import CameraInfo, CompressedImage, LaserScan
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--fixture', help='Wait for the player to finish placing measured targets')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    if args.fixture:
        deadline = time.monotonic() + 180
        while not Path(args.fixture).exists():
            if time.monotonic() > deadline:
                raise RuntimeError('Measured fixture did not become ready')
            time.sleep(0.2)
        (out / 'fixture.json').write_text(Path(args.fixture).read_text())
    rclpy.init()
    node = rclpy.create_node('sean_rendered_sensor_capture')
    subscriptions, counts, samples, stamps, errors = {}, {}, {}, {}, []
    types = {'sensor_msgs/msg/CompressedImage': CompressedImage,
             'sensor_msgs/msg/CameraInfo': CameraInfo,
             'sensor_msgs/msg/LaserScan': LaserScan,
             'nav_msgs/msg/Odometry': Odometry,
             'rosgraph_msgs/msg/Clock': Clock, 'tf2_msgs/msg/TFMessage': TFMessage}

    transforms = {}
    last_clock = [0.0]

    def receive(topic, msg):
        counts[topic] = counts.get(topic, 0) + 1
        if isinstance(msg, Clock):
            last_clock[0] = msg.clock.sec + msg.clock.nanosec * 1e-9
        if hasattr(msg, 'header'):
            stamp = msg.header.stamp
            value = stamp.sec + stamp.nanosec * 1e-9
            entry = stamps.setdefault(topic, {'first': value, 'last': value, 'regressions': 0})
            entry['regressions'] += int(value < entry['last'])
            entry['last'] = value
        if isinstance(msg, TFMessage):
            for tf in msg.transforms:
                transforms[tf.child_frame_id] = message_to_ordereddict(tf)
        if counts[topic] > 3:
            if isinstance(msg, CompressedImage):
                try:
                    Image.open(io.BytesIO(bytes(msg.data))).load()
                except Exception as exc:
                    if len(errors) < 20:
                        errors.append(topic + ': ' + str(exc))
            return
        key = topic.strip('/').replace('/', '__') + '-' + str(counts[topic])
        if isinstance(msg, CompressedImage):
            payload = bytes(msg.data)
            (out / (key + '.payload')).write_bytes(payload)
            sample = {'format': msg.format, 'bytes': len(payload),
                      'sha256': hashlib.sha256(payload).hexdigest(),
                      'header': message_to_ordereddict(msg.header)}
            try:
                im = Image.open(io.BytesIO(payload))
                im.load()
                pixels = np.array(im)
                sample.update(size=list(im.size), mode=im.mode,
                              minimum=int(pixels.min()), maximum=int(pixels.max()),
                              std=float(pixels.std()))
                im.save(out / (key + '.png'))
            except Exception as exc:
                sample['decode_error'] = str(exc)
                errors.append(topic + ': ' + str(exc))
        else:
            sample = message_to_ordereddict(msg)
        samples.setdefault(topic, []).append(sample)

    started = time.monotonic()
    graph = []
    try:
        while time.monotonic() - started < args.seconds:
            graph = node.get_topic_names_and_types()
            for topic, names in graph:
                if topic not in subscriptions and len(names) == 1 and names[0] in types:
                    subscriptions[topic] = node.create_subscription(
                        types[names[0]], topic, lambda msg, t=topic: receive(t, msg),
                        qos_profile_sensor_data)
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        report = {'seconds': time.monotonic() - started, 'topics': graph,
                  'counts': counts, 'stamps': stamps, 'samples': samples,
                  'decode_errors': errors, 'transforms': transforms, 'last_clock': last_clock[0],
                  'note': 'Exploratory capture; no geometry acceptance asserted.'}
        (out / 'capture.json').write_text(json.dumps(report, indent=2))
        print(json.dumps({'counts': counts, 'decode_errors': errors}, indent=2))
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
