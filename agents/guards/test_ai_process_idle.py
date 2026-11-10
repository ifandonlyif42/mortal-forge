import os
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import ai_process_idle as guard


class IdleTests(unittest.TestCase):
    def test_pre_and_post_hook_records_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(guard, 'ROOT', Path(directory)):
            payload = {'hook_event_name': 'PreToolUse', 'tool_use_id': 'test',
                       'tool_input': {'command': 'printf hello'}}
            output = io.StringIO()
            with patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))), redirect_stdout(output):
                guard.main()
            rewritten = json.loads(output.getvalue())['hookSpecificOutput']['updatedInput']['command']
            self.assertTrue(rewritten.startswith('export AI_PROCESS_RUN='))
            self.assertTrue(rewritten.endswith('\nprintf hello'))
            state = json.loads((Path(directory) / 'state.json').read_text())
            self.assertEqual(len(state['active']), 1)
            payload['hook_event_name'] = 'PostToolUse'
            with patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))):
                guard.main()
            state = json.loads((Path(directory) / 'state.json').read_text())
            self.assertEqual(state['active'], {})
            self.assertEqual(len(state['runs']), 1)

    def test_real_marked_process_and_idle_cleanup(self):
        env = dict(os.environ, AI_PROCESS_RUN='a' * 32)
        child = subprocess.Popen(['sleep', '60'], env=env)
        try:
            state = guard.scan({}, 100, set())
            self.assertIn(str(child.pid), state['a' * 32]['processes'])
            guard.scan(state, 7299, set(), kill=True)
            self.assertIsNone(child.poll())
            guard.scan(state, 7301, {'a' * 32}, kill=True)
            self.assertIsNone(child.poll())
            guard.scan(state, 7302, set(), kill=True)
            child.wait(timeout=3)
            self.assertEqual(child.returncode, -15)
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait()

    def test_hook_tracks_background_shell_process(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(guard, 'ROOT', Path(directory)):
            payload = {'hook_event_name': 'PreToolUse', 'tool_use_id': 'test',
                       'tool_input': {'command': 'sleep 60 >/dev/null 2>&1 &'}}
            output = io.StringIO()
            with patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))), redirect_stdout(output):
                guard.main()
            command = json.loads(output.getvalue())['hookSpecificOutput']['updatedInput']['command']
            tag = json.loads((Path(directory) / 'state.json').read_text())['active']['test']
            subprocess.run(['/bin/bash', '-c', command], check=True)
            payload['hook_event_name'] = 'PostToolUse'
            with patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))):
                guard.main()
            state = json.loads((Path(directory) / 'state.json').read_text())
            members = state['runs'][tag]['processes']
            self.assertEqual(list(members.values()), ['sleep'])
            for pid in members:
                os.kill(int(pid), 15)

    def test_socket_and_changed_activity_reset_timer(self):
        env = dict(os.environ, AI_PROCESS_RUN='b' * 32)
        child = subprocess.Popen(['sleep', '60'], env=env)
        try:
            state = guard.scan({}, 100, set())
            state['b' * 32]['signature'][str(child.pid)][1] -= 1
            guard.scan(state, 7301, set(), kill=True)
            self.assertIsNone(child.poll())
            self.assertEqual(state['b' * 32]['idle_since'], 7301)
        finally:
            child.terminate()
            child.wait()

    def test_unmarked_process_not_tracked(self):
        child = subprocess.Popen(['sleep', '60'])
        try:
            state = guard.scan({}, time.time(), set(), kill=True)
            self.assertFalse(any(str(child.pid) in x.get('processes', {}) for x in state.values()))
            self.assertIsNone(child.poll())
        finally:
            child.terminate()
            child.wait()

    def test_socket_process_is_preserved(self):
        env = dict(os.environ, AI_PROCESS_RUN='c' * 32)
        child = subprocess.Popen([sys.executable, '-c', 'import socket,time;s=socket.socket();time.sleep(60)'], env=env)
        try:
            for _ in range(100):
                item = guard.process(child.pid)
                if item and item['socket']:
                    break
                time.sleep(0.01)
            self.assertTrue(item and item['socket'])
            state = guard.scan({}, 100, set())
            guard.scan(state, 7301, set(), kill=True)
            self.assertIsNone(child.poll())
        finally:
            child.terminate()
            child.wait()


if __name__ == '__main__':
    unittest.main()
