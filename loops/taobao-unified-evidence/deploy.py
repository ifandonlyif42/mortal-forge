#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import tarfile

artifact = Path(os.environ['CASH_DELIVERY_ARTIFACT'])
version = os.environ['CASH_DELIVERY_SHA256']
if hashlib.sha256(artifact.read_bytes()).hexdigest() != version:
    raise ValueError('發布包版本不符')
home = Path('/home/cash')
destination = home / '.local/share/mortal-tools/taobao' / version
destination.mkdir(parents=True, exist_ok=True)
with tarfile.open(artifact) as bundle:
    bundle.extractall(destination, filter='data')
canonical = home / 'work_space/private/mortal-forge/skills/taobao'
roots = [home / '.agents/skills', home / '.claude/skills', home / '.codex/skills', home / '.config/orca/codex-accounts/6c3c101d-8ebe-46b6-bcfd-42ae562dec4a/home/skills']
previous = {}
for root in roots:
    link = root / 'taobao'
    if not link.is_symlink() or link.resolve() not in (canonical, destination / 'taobao'):
        raise ValueError(f'技能入口已被其他工作修改：{link}')
    previous[str(link)] = os.readlink(link)
(destination / 'links-before.json').write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n')
for root in roots:
    temporary = root / f'.taobao-{version[:12]}'
    if not temporary.is_symlink():
        temporary.symlink_to(destination / 'taobao', target_is_directory=True)
    os.replace(temporary, root / 'taobao')
print(json.dumps({'installed': str(destination), 'version_sha256': version}))
