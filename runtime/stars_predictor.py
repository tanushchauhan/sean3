"""Checkpoint-backed pedestrian forecasting using an external, pinned extension.

No model source or weights are redistributed. Forecasts have no robot, goal or
map conditioning. The bridge validates speed limits without clipping outputs.
"""
import hashlib
from pathlib import Path
import subprocess
import sys

from runtime.stars_bridge import require

EXTENSION_COMMIT = 'd72eb2295c3336f0674932796cf41b60636cde3e'
UPSTREAM_COMMIT = '13d840c5c0677ff52e928eea1679ba5ce1f19c14'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


class StarsPredictor:
    def __init__(self, checkpoint, extension, *, device='cpu', allow_dirty_training_source=False):
        import torch
        from torch_geometric.data import Data

        extension = Path(extension).resolve()
        require(git(extension, 'rev-parse', 'HEAD') == EXTENSION_COMMIT, 'Wrong extension revision')
        require(git(extension / 'references/stars', 'rev-parse', 'HEAD') == UPSTREAM_COMMIT,
                'Missing/wrong upstream STARS revision')
        for root in (extension, extension / 'references/stars'):
            require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'Model checkout has tracked changes')
        sys.path.insert(0, str(extension / 'src'))
        from baselines import stars_ma_model, stars_ma_graph
        require(Path(stars_ma_model.__file__).resolve().is_relative_to(extension / 'src'),
                'Another extension is already imported')
        checkpoint = Path(checkpoint).resolve()
        payload = torch.load(checkpoint, map_location='cpu', weights_only=True)
        require(payload.get('model') == 'stars_ma' and payload.get('phase') == 'forecast',
                'Expected multi-agent forecasting checkpoint')
        config = payload['run_config']
        require(config.get('git_commit') == EXTENSION_COMMIT and payload.get('upstream_commit') == UPSTREAM_COMMIT,
                'Checkpoint/model revision mismatch')
        require(config.get('git_dirty') is False or allow_dirty_training_source,
                'Training source was dirty; confirm its diff or explicitly allow provisional inference')
        # This first adapter deliberately accepts only the tested deterministic recipe.
        require(payload['decoder_recipe']['latent_dim'] == 0, 'Multimodal sampling needs an explicit intent policy')
        require(payload['window'] == dict(observation_steps=8, prediction_steps=12, dt=.4),
                'Unsupported checkpoint observation/prediction window')
        forecasting = config['forecasting_config']
        require(forecasting['signal'] == dict(input_mode='raw', target_mode='raw') and
                forecasting['standardization']['mode'] == 'none' and
                forecasting['features'] == dict(derivative_mode='none', representation='absolute_xy') and
                forecasting['coordinates']['frame'] == 'target_centric_se2_observations_only',
                'Unsupported preprocessing')
        self.torch, self.Data, self.graph = torch, Data, stars_ma_graph
        self.device = torch.device(device)
        self.steps, self.dt = 8, .4
        self.topology = payload['graph']
        self.model = stars_ma_model.StarsMultiAgentForecaster(
            self.steps, 12, dt=self.dt, encoder_recipe=payload['encoder_recipe'],
            decoder_recipe=payload['decoder_recipe'])
        self.model.load_state_dict(payload['state_dict'], strict=True)
        self.model.to(self.device).eval()
        self.metadata = dict(model='stars_ma', checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                             extension_commit=EXTENSION_COMMIT, upstream_commit=UPSTREAM_COMMIT,
                             training_source_dirty=config['git_dirty'], provisional=bool(config['git_dirty']),
                             window=payload['window'], graph=self.topology,
                             checkpoint_selection=payload['checkpoint_selection'], device=str(self.device))

    def reset(self, episode):
        # No predicted history or latent intent is retained between calls/episodes.
        pass

    def predict(self, history):
        require(len(history) == self.steps, 'Complete checkpoint observation window required')
        # Include inactive pedestrians as observed context, but never as actuated targets.
        ids = sorted(a['id'] for a in history[-1]['actors'] if not a['robot'])
        if not ids:
            return {}
        observed = []
        for sample in history:
            actors = {a['id']: a for a in sample['actors'] if not a['robot']}
            require(set(actors) == set(ids), 'Pedestrian population changed')
            observed.append([actors[k]['position'] for k in ids])
        torch = self.torch
        with torch.inference_mode():
            xy = torch.tensor(observed, dtype=torch.float32, device=self.device)
            valid = torch.ones(xy.shape[:2], dtype=torch.bool, device=self.device)
            data = self.Data(num_nodes=len(ids), **self.graph.build_graph(xy, valid, dt=self.dt, **self.topology))
            local = self.model.predict(data, samples=1)
            require(tuple(local.shape) == (1, len(ids), 12, 2) and bool(torch.isfinite(local).all()),
                    'Invalid forecaster output')
            # Rotate displacement directly: adding/subtracting large world origins loses precision.
            velocity = self.graph.rotate(local[0, :, 0], data.heading) / self.dt
            values = velocity.cpu().tolist()
        active = {a['id'] for a in history[-1]['actors'] if a['active'] and not a['robot']}
        return {k: values[i] for i, k in enumerate(ids) if k in active}
