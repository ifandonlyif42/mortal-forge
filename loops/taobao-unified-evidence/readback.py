#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import tarfile

version = os.environ['CASH_DELIVERY_SHA256']
home = Path('/home/cash')
destination = home / '.local/share/mortal-tools/taobao' / version
roots = [home / '.agents/skills', home / '.claude/skills', home / '.codex/skills', home / '.config/orca/codex-accounts/6c3c101d-8ebe-46b6-bcfd-42ae562dec4a/home/skills']
for root in roots:
    if (root / 'taobao').resolve() != destination / 'taobao':
        raise ValueError(f'技能入口讀回不符：{root}')
count = 0
with tarfile.open(os.environ['CASH_DELIVERY_ARTIFACT']) as bundle:
    for member in bundle.getmembers():
        if not member.isfile():
            continue
        stream = bundle.extractfile(member)
        if stream is None or hashlib.sha256(stream.read()).digest() != hashlib.sha256((destination / member.name).read_bytes()).digest():
            raise ValueError(f'安裝內容讀回不符：{member.name}')
        count += 1
print(json.dumps({'version_sha256': version, 'result': 'pass', 'checks': [{'name': '四個入口共用一份已安裝技能', 'result': 'pass'}, {'name': f'{count}個發布檔逐一比對', 'result': 'pass'}]}, ensure_ascii=False))
