"""Prevent ignored controller flags or invalid settings from becoming a run."""
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

launcher = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'sean3'))


class ControllerSelectionTests(unittest.TestCase):
    def args(self, **changes):
        values = dict(pedestrian_controller='orca', orca_decision_period=.1,
                      orca_neighbor_distance=5, orca_max_neighbors=64,
                      orca_agent_horizon=2.5, orca_obstacle_horizon=2.5)
        values.update(changes)
        return SimpleNamespace(**values)

    def test_requested_controller_and_parameters_reach_player(self):
        options = launcher['controller_player_args'](self.args())
        self.assertEqual(options[:2], ['-pedestrian-controller', 'orca'])
        self.assertEqual(dict(zip(options[::2], options[1::2]))['-orca-max-neighbors'], '64')
        self.assertEqual(launcher['controller_player_args'](self.args(pedestrian_controller='social_forces')),
                         ['-pedestrian-controller', 'social_forces', '-pedestrian-actuation', 'root_motion'])
        self.assertEqual(dict(zip(options[::2],options[1::2]))['-pedestrian-actuation'],'velocity_body')

    def test_joint_controller_cannot_select_root_motion(self):
        with self.assertRaises(launcher['Failure']):
            launcher['controller_player_args'](self.args(pedestrian_actuation='root_motion'))

    def test_nonfinite_or_nonpositive_parameters_fail_before_startup(self):
        for key in ('orca_decision_period','orca_neighbor_distance','orca_max_neighbors','orca_agent_horizon','orca_obstacle_horizon'):
            for value in (0, -1, float('nan'), float('inf')):
                with self.subTest(key=key, value=value), self.assertRaises(launcher['Failure']):
                    launcher['controller_player_args'](self.args(**{key: value}))

    def test_older_or_wrong_controller_player_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'player.log'
            self.assertFalse(launcher['controller_announced'](log,'orca'))
            log.write_text('SEAN pedestrian controller: SF\n')
            self.assertFalse(launcher['controller_announced'](log,'orca'))
            log.write_text('SEAN pedestrian controller: ORCA\n')
            self.assertTrue(launcher['controller_announced'](log,'orca'))
            self.assertFalse(launcher['actuation_announced'](log,'velocity_body'))
            log.write_text('SEAN pedestrian controller: ORCA\nSEAN pedestrian actuation: VelocityTargetsV1\n')
            self.assertTrue(launcher['actuation_announced'](log,'velocity_body'))


if __name__ == '__main__':
    unittest.main()
