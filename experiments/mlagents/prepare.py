"""Create a NEW isolated Unity project from the pinned release_21 checkout."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('upstream', type=Path)
p.add_argument('destination', type=Path)
a = p.parse_args()
revision = subprocess.check_output(['git', '-C', str(a.upstream), 'rev-parse', 'HEAD'], text=True).strip()
if revision != '7a03145ae48ad354821bd89e0243d99332149ace':
    p.error('Expected official release_21 commit 7a03145ae48ad354821bd89e0243d99332149ace')
if a.destination.exists():
    p.error('Destination must not exist')
shutil.copytree(Path(__file__).parent / 'Assets', a.destination / 'Assets')
(a.destination / 'Packages').mkdir()
(a.destination / 'Packages/manifest.json').write_text(json.dumps({'dependencies': {
    'com.unity.ml-agents': 'file:' + str((a.upstream / 'com.unity.ml-agents').resolve()),
    'com.unity.modules.physics': '1.0.0',
}}, indent=2) + '\n')
(a.destination / 'ProjectSettings').mkdir()
(a.destination / 'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 2022.3.62f3\n')
print(a.destination)
