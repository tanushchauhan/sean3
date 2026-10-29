"""Fail on unexpected managed/native runtime errors while retaining full logs."""
import argparse
import json
from pathlib import Path
import re

PATTERN=re.compile(r'\b(?:NullReferenceException|InvalidOperationException|ArgumentException|ArgumentOutOfRangeException|IndexOutOfRangeException|AssertionException|MissingReferenceException)\b|Native Crash Reporting|Got a SIGSEGV|Warehouse encounter setup rejected')


def audit(root):
    matches=[]
    for name in ('player.log','player-console.log','nav2.log','navigation-console.log'):
        path=root/name
        if path.exists():
            for number,line in enumerate(path.read_text(errors='replace').splitlines(),1):
                if PATTERN.search(line) or 'Traceback (most recent call last)' in line:
                    matches.append(dict(file=name,line=number,text=line[:500]))
    return dict(passed=not matches,errors=matches)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();r=audit(a.root)
    (a.root/'script-log-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
    raise SystemExit(0 if r['passed'] else 1)
