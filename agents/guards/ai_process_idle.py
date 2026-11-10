import fcntl
import json
import os
import signal
import sys
import time
import uuid
from pathlib import Path


ROOT = Path.home() / ".local/state/ai-process-idle"
LIMIT = 7200
TAG = b"AI_PROCESS_RUN="


def process(pid):
    root = Path('/proc') / str(pid)
    try:
        if root.stat().st_uid != os.getuid():
            return None
        env = (root / 'environ').read_bytes().split(b'\0')
        tag = next((x[len(TAG):].decode('ascii') for x in env if x.startswith(TAG)), None)
        if not tag or len(tag) != 32:
            return None
        stat = (root / 'stat').read_text().rsplit(') ', 1)[1].split()
        io = dict(line.split(':', 1) for line in (root / 'io').read_text().splitlines())
        fds = list((root / 'fd').iterdir())
        links = [os.readlink(fd) for fd in fds]
        return {'tag': tag, 'start': stat[19], 'cpu': int(stat[11]) + int(stat[12]),
                'io': int(io['rchar']) + int(io['wchar']), 'name': (root / 'comm').read_text().strip(),
                'socket': any(x.startswith('socket:') for x in links)}
    except (OSError, ValueError, KeyError, StopIteration, UnicodeError):
        return None


def scan(state, now, active, kill=False):
    seen = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        item = process(int(path.name))
        if item:
            seen[path.name] = item
    groups = {}
    for pid, item in seen.items():
        groups.setdefault(item['tag'], {})[pid] = item
    for tag, members in groups.items():
        old = state.get(tag, {})
        signature = {pid: [p['start'], p['cpu'], p['io']] for pid, p in members.items()}
        changed = old.get('signature') != signature
        idle_since = now if changed or not old.get('idle_since') else old['idle_since']
        state[tag] = {'created': old.get('created', now), 'signature': signature, 'idle_since': idle_since, 'last_seen': now,
                      'processes': {pid: p['name'] for pid, p in members.items()}}
        if kill and tag not in active and now - idle_since >= LIMIT and not any(p['socket'] for p in members.values()):
            for pid, item in members.items():
                current = process(int(pid))
                if current and current['start'] == item['start'] and current['tag'] == tag:
                    try:
                        fd = os.pidfd_open(int(pid))
                        try:
                            confirmed = process(int(pid))
                            if confirmed == item:
                                signal.pidfd_send_signal(fd, signal.SIGTERM)
                        finally:
                            os.close(fd)
                    except ProcessLookupError:
                        pass
    for tag in set(state) - set(groups):
        state[tag]['last_seen'] = state[tag].get('last_seen', now)
    return state


def main():
    payload = json.load(sys.stdin)
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = ROOT / 'state.json'
        state = json.loads(path.read_text()) if path.exists() else {'runs': {}, 'active': {}}
        event = payload.get('hook_event_name')
        use_id = payload.get('tool_use_id', '')
        now = time.monotonic()
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if state.get('boot') != boot:
            state['boot'] = boot
            state['active'] = {}
            for run in state['runs'].values():
                run['idle_since'] = now
                run['signature'] = {}
        active = state['active']
        if event == 'PostToolUse':
            active.pop(use_id, None)
        scan(state['runs'], now, set(active.values()), kill=True)
        if event == 'PreToolUse':
            args = payload.get('tool_input', {})
            command = args.get('command')
            if isinstance(command, str) and use_id:
                tag = uuid.uuid4().hex
                active[use_id] = tag
                state['runs'][tag] = {'created': now, 'idle_since': now, 'signature': {}, 'processes': {}}
                args['command'] = f'export AI_PROCESS_RUN={tag}\n' + command
                print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow', 'updatedInput': args}}))
        tmp = ROOT / 'state.tmp'
        tmp.write_text(json.dumps(state))
        tmp.chmod(0o600)
        os.replace(tmp, path)


if __name__ == '__main__':
    main()
