#!/usr/bin/env python3
"""Read-only source inventory for local/remote integration handoffs."""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args])


def inventory(path):
    path = path.resolve()
    untracked = []
    for raw in git(path, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0'):
        if not raw:
            continue
        name = raw.decode('utf-8', errors='surrogateescape')
        file = path / name
        if file.is_symlink():
            digest = hashlib.sha256(str(file.readlink()).encode()).hexdigest()
        elif file.is_file():
            h = hashlib.sha256()
            with file.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(chunk)
            digest = h.hexdigest()
        else:
            digest = None
        untracked.append({'path': name, 'sha256': digest})
    return {
        'path': str(path),
        'head': git(path, 'rev-parse', 'HEAD').decode().strip(),
        'branch': git(path, 'rev-parse', '--abbrev-ref', 'HEAD').decode().strip(),
        'status': git(path, 'status', '--short', '--untracked-files=all').decode(),
        'tracked_diff_sha256': hashlib.sha256(git(path, 'diff', 'HEAD', '--binary')).hexdigest(),
        'untracked': untracked,
        # This records child revisions and dirtiness markers, not the full
        # contents of dirty child repositories. Inventory children separately
        # before claiming an exact executable source fingerprint.
        'submodules': git(path, 'submodule', 'status', '--recursive').decode(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repositories', nargs='+', type=Path)
    args = parser.parse_args()
    result = {
        'schema_version': 1,
        'captured_utc': datetime.now(timezone.utc).isoformat(),
        'host': platform.node(),
        'platform': platform.platform(),
        'python': sys.version,
        'tools': {name: shutil.which(name) for name in ('docker', 'podman', 'python3', 'Unity')},
        'repositories': [inventory(path) for path in args.repositories],
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
