#!/usr/bin/env python3
import json
import re
import shlex
import sys

SEGMENT = re.compile(r'\n|;|&&|\|\||\||&')
WRAPPERS = {'sudo', 'env', 'time', 'nohup', 'setsid', 'command', 'exec'}
RUNNERS = {'pnpm', 'npm', 'npx', 'yarn', 'bun', 'node'}
RUN_WORDS = {'run', 'exec', 'dlx', 'x', '--filter', '-F', '-C', '--dir', '--prefix', '-w', '--workspace'}
DEV_SCRIPTS = {'dev', 'start', 'serve', 'preview', 'watch'}
DEV_BINARIES = {'vite', 'tsx', 'ts-node-dev', 'nodemon', 'next'}

MESSAGE = (
    '臨時開本機服務（dev server、watch、http.server）必須登記並設到期時間：'
    'python3 ~/tools/temp-service.py start --name <名稱> --ttl <例 4h> --purpose <用途> [--on-stop <收尾指令>] -- <原指令>。'
    '用完執行 stop，沒停的由計時器到期回收。細則見 ~/.agents/skills/temp-service/SKILL.md。'
)


def strip(tokens):
    index = 0
    while index < len(tokens) and (tokens[index] in WRAPPERS or ('=' in tokens[index] and not tokens[index].startswith('-'))):
        index += 1
    return tokens[index:]


def is_dev_server(tokens):
    tokens = strip(tokens)
    if not tokens:
        return False
    head = tokens[0].rsplit('/', 1)[-1]
    rest = tokens[1:]
    if head in ('python', 'python3') and '-m' in rest:
        position = rest.index('-m')
        return rest[position + 1:position + 2] == ['http.server']
    if head == 'next':
        return bool(rest) and rest[0] in ('dev', 'start')
    if head in DEV_BINARIES:
        return head not in ('tsx', 'vite') or 'watch' in rest or (head == 'vite' and 'build' not in rest)
    if head in RUNNERS:
        if head == 'node':
            return False
        words = [token for token in rest if not token.startswith('-') and token not in RUN_WORDS]
        for word in words[:3]:
            if word in DEV_SCRIPTS or word.startswith('dev:') or word.startswith('start:'):
                return True
            base = word.rsplit('/', 1)[-1]
            if base in DEV_BINARIES and (base != 'tsx' or 'watch' in rest):
                return base != 'next' or any(token in ('dev', 'start') for token in rest)
        return False
    return False


def commands(payload):
    stack = [payload]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ('command', 'cmd') and isinstance(item, str):
                    yield item
                elif isinstance(item, (dict, list)):
                    stack.append(item)
        elif isinstance(value, list):
            stack.extend(value)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    for command in commands(payload):
        if 'temp-service.py' in command:
            continue
        for segment in SEGMENT.split(command):
            try:
                tokens = shlex.split(segment)
            except ValueError:
                continue
            if is_dev_server(tokens):
                print(MESSAGE, file=sys.stderr)
                return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
