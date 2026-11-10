#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import unittest

GUARD = Path(__file__).with_name('service_path_guard.py')


def hook(tool, tool_input):
    return subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps({'tool_name': tool, 'tool_input': tool_input}),
        capture_output=True, text=True, timeout=5,
    ).returncode


class ServicePathGuardTests(unittest.TestCase):
    def test_build_output_paths_are_rejected(self):
        cases = [
            ('Write', {'file_path': '/h/a.service', 'content': '[Service]\nExecStart=%h/w/aletheia/target/release/aletheia serve\n'}),
            ('Edit', {'file_path': '/h/a.service', 'new_string': 'ExecStart=/home/cash/w/x/target/debug/x'}),
            ('Write', {'file_path': '/h/a.service', 'content': 'ExecStart=-/opt/app/build/server'}),
            ('Write', {'file_path': '/h/a.service', 'content': 'ExecStartPre=/tmp/run.sh'}),
            ('Bash', {'command': "sed -i 's#^ExecStart=.*#ExecStart=/r/target/release/x#' a.service"}),
            ('Bash', {'command': 'systemd-run --user --unit=x /home/cash/w/target/release/x serve'}),
        ]
        for tool, tool_input in cases:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assertEqual(hook(tool, tool_input), 2)

    def test_installed_paths_are_accepted(self):
        cases = [
            ('Write', {'file_path': '/h/a.service', 'content': 'ExecStart=%h/.local/lib/aletheia/aletheia serve\n'}),
            ('Write', {'file_path': '/h/a.service', 'content': 'ExecStart=/usr/bin/python3 %h/tools/memory_manager/manager.py\n'}),
            ('Bash', {'command': 'systemd-run --user --unit=x /usr/bin/sleep 5'}),
            ('Bash', {'command': 'cargo build --release && ls target/release'}),
            ('Write', {'file_path': '/h/notes.md', 'content': 'target/release/aletheia 是編譯輸出'}),
        ]
        for tool, tool_input in cases:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assertEqual(hook(tool, tool_input), 0)


if __name__ == '__main__':
    unittest.main()
