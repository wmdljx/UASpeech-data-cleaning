#!/usr/bin/env python3
"""Check the intended publication tree; local draft files are excluded explicitly."""
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = ['README.md', 'LICENSE.md', 'pyproject.toml', '.gitignore']
PUBLIC_DIRS = ['docs', 'metadata', 'uaspeech_cut', 'tests', 'examples']
PUBLIC_TOOLS = ['tools/check_release.py', 'tools/inspect_source_package.py']
ALLOWED = {'.md','.toml','.py','.json','.csv','.tsv','.svg','.png'}


def public_files():
    files = [ROOT / p for p in PUBLIC_FILES + PUBLIC_TOOLS]
    for name in PUBLIC_DIRS:
        files.extend(p for p in (ROOT/name).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and not p.name.endswith('_ZH.md'))
    return sorted(files)


def main():
    errors = []
    files = public_files()
    for p in files:
        rel = p.relative_to(ROOT)
        if p.is_symlink() or not p.is_file():
            errors.append(f'Missing file or symlink: {rel}')
            continue
        if p.suffix not in ALLOWED and p.name != '.gitignore':
            errors.append(f'Forbidden publication file type: {rel}')
        if p.suffix == '.png':
            if rel.as_posix() not in {'docs/assets/review-tool.png','docs/assets/waveform-demo.png'}:
                errors.append(f'Unreviewed bitmap: {rel}')
            continue
        s = p.read_text(encoding='utf-8')
        if p.name != 'check_release.py' and re.search(r'/mnt/afs/|/root/|BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{20,}',s):
            errors.append(f'Private path or secret marker: {rel}')
        if p.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)',s):
                if '://' in target or target.startswith('#'):
                    continue
                local = (p.parent / target.split('#')[0]).resolve()
                if not local.is_relative_to(ROOT) or not local.exists():
                    errors.append(f'Broken/local-escaping link: {rel}: {target}')
    sys.path.insert(0,str(ROOT))
    from uaspeech_cut.__main__ import validate
    result = validate(ROOT/'metadata')
    with (ROOT/'metadata/legacy_audit.csv').open() as f:
        audit = list(csv.DictReader(f))
    if len(audit) != 6246 or sum(int(r['confirmed_affected']) for r in audit) != 1246:
        errors.append('Historical audit totals changed')
    print(json.dumps(dict(status='FAIL' if errors else 'PASS',file_count=len(files),
        metadata=result,errors=errors,note='Bitmap has separate visual review; this scan cannot certify rights.'),indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
