#!/usr/bin/env python3
import json
import re
import sys

UNIT = re.compile(r'ExecStart\w*=[-@:+!]*\S*/(?:target|build|tmp)/')
RUN = re.compile(r'systemd-run\b[^\n;&|]*?\s\S*/(?:target|build|tmp)/')

MESSAGE = (
    '常駐服務、排程的啟動程式不得放在 target/、build/、tmp/ 底下，清除編譯檔會讓服務壞掉。'
    '先把發行版執行檔複製到 ~/.local/lib/<名稱>/，ExecStart 指向那裡。'
)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    for text in strings(payload.get('tool_input', {})):
        if UNIT.search(text) or RUN.search(text):
            print(MESSAGE, file=sys.stderr)
            return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
