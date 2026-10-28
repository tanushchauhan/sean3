import math
import unittest
from route_metrics import path_geometry, receipt_lag_growth, trajectory_metrics


class RouteMetricTests(unittest.TestCase):
    def test_distance_and_turns_with_duplicate_points(self):
        result = path_geometry([(0, 0), (0, 0), (3, 0), (3, 4)])
        self.assertEqual(result['length_m'], 7)
        self.assertAlmostEqual(result['turn_radians'], math.pi/2)

    def test_rotation_is_recorded_and_translation_stall_remains_visible(self):
        samples = [[i, 0, 0, i*0.1] for i in range(22)] + [[22, 0.1, 0, 2.2]]
        result = trajectory_metrics(samples)
        self.assertEqual(result['translation_stalls'], [[0, 22]])
        self.assertAlmostEqual(result['yaw_turn_radians'], 2.2)

    def test_slow_continuous_motion_does_not_accumulate_false_stalls(self):
        result = trajectory_metrics([[i, i*.01, 0, 0] for i in range(100)])
        self.assertEqual(result['translation_stalls'], [])
        self.assertLess(result['longest_translation_pause_seconds'], 7)

    def test_terminal_stall_and_clock_regression(self):
        self.assertEqual(trajectory_metrics([[0, 0, 0, 0], [20, 0, 0, 0]])['translation_stalls'], [[0, 20]])
        with self.assertRaisesRegex(ValueError, 'regressed'):
            trajectory_metrics([[1, 0, 0, 0], [0, 0, 0, 0]])

    def test_missing_or_nonfinite_samples_cannot_pass(self):
        for samples in ([], [[0, float('nan'), 0, 0]], [[float('inf'), 0, 0, 0]]):
            with self.assertRaises(ValueError):
                trajectory_metrics(samples)

    def test_small_circles_are_progress_stalls_despite_continuous_translation(self):
        result = trajectory_metrics([[i, .1*math.cos(i), .1*math.sin(i), i] for i in range(31)])
        self.assertEqual(result['translation_stalls'], [])
        self.assertEqual(result['bounded_motion_stalls'], [[0, 30]])

    def test_receipt_lag_growth_detects_backlog_but_not_steady_latency(self):
        self.assertAlmostEqual(receipt_lag_growth([[10+i, i] for i in range(20)]), 0)
        backlog = [[10+i, .8*i] for i in range(11)] + [[20.5, 9.5]]
        self.assertAlmostEqual(receipt_lag_growth(backlog), 2)
        with self.assertRaises(ValueError):
            receipt_lag_growth([])
