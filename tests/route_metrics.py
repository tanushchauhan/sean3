"""ROS-independent metrics for timestamped planar trajectories."""
import math


def path_geometry(points):
    segments = [(b[0]-a[0], b[1]-a[1]) for a, b in zip(points, points[1:])]
    segments = [(x, y) for x, y in segments if math.hypot(x, y) > 1e-6]
    headings = [math.atan2(y, x) for x, y in segments]
    return {'length_m': sum(math.hypot(x, y) for x, y in segments),
            'turn_radians': sum(abs(math.atan2(math.sin(b-a), math.cos(b-a)))
                                for a, b in zip(headings, headings[1:]))}


def trajectory_metrics(samples, movement_m=0.05, stall_seconds=20.0):
    """A stall is >=20 simulation seconds without 5 cm translation from an anchor.

    Includes rotations and intentional waits; it is a translation-stall signal,
    not proof of controller deadlock. Samples are [sim_time, x, y, yaw].
    """
    if not samples:
        raise ValueError('No trajectory samples')
    if any(not math.isfinite(value) for sample in samples for value in sample):
        raise ValueError('Nonfinite trajectory sample')
    if any(b[0] < a[0] for a, b in zip(samples, samples[1:])):
        raise ValueError('Trajectory clock regressed')
    longest, stalls = pause_windows(samples, movement_m, stall_seconds)
    bounded_longest, bounded_stalls = pause_windows(samples, 0.5, 15.0)
    result = path_geometry([s[1:3] for s in samples])
    result.update(sim_seconds=samples[-1][0]-samples[0][0],
                  yaw_turn_radians=sum(abs(math.atan2(math.sin(b[3]-a[3]), math.cos(b[3]-a[3])))
                                       for a, b in zip(samples, samples[1:])),
                  longest_translation_pause_seconds=longest, translation_stalls=stalls,
                  longest_bounded_motion_seconds=bounded_longest, bounded_motion_stalls=bounded_stalls,
                  max_sample_gap_seconds=max((b[0]-a[0] for a, b in zip(samples, samples[1:])), default=0))
    return result


def pause_windows(samples, movement_m, stall_seconds):
    anchor = samples[0]
    longest = 0.0
    stalls = []
    for sample in samples:
        duration = sample[0] - anchor[0]
        longest = max(longest, duration)
        if math.hypot(sample[1]-anchor[1], sample[2]-anchor[2]) >= movement_m:
            if duration >= stall_seconds:
                stalls.append([anchor[0], sample[0]])
            anchor = sample
    if samples[-1][0]-anchor[0] >= stall_seconds:
        stalls.append([anchor[0], samples[-1][0]])
    return longest, stalls


def receipt_lag_growth(samples):
    """Largest increase of (wall receipt - simulation stamp) after the first sample.

    Unity's clock cannot outrun wall time, so growth means a delivery backlog or a
    player stall: either way Nav2 acted on old state. Samples are [wall, sim].
    """
    if not samples:
        raise ValueError('No clock receipts')
    baseline = samples[0][0] - samples[0][1]
    return max(wall - sim for wall, sim in samples) - baseline
