import unittest

import write_guard
from node_stdin_guard import problem


class NodeStdinTest(unittest.TestCase):
    def test_require_and_top_level_await_rejected(self):
        command = "node <<'NODE'\nconst fs = require('fs'); await Promise.resolve();\nNODE"
        self.assertIsNotNone(problem(command))

    def test_registered_hook_rejects_the_same_error(self):
        command = "node <<'NODE'\nrequire('fs'); await Promise.resolve();\nNODE"
        result = write_guard.verdict({'tool_input': {'cmd': command}})
        self.assertEqual(result[0], 'node-ambiguous-stdin')

    def test_async_function_with_require_allowed(self):
        self.assertIsNone(problem("node <<'NODE'\nconst fs = require('fs'); (async () => { await Promise.resolve(); })();\nNODE"))

    def test_explicit_module_allowed(self):
        self.assertIsNone(problem("node --input-type=module <<'NODE'\nimport fs from 'node:fs'; await Promise.resolve();\nNODE"))

    def test_pure_auto_module_allowed(self):
        self.assertIsNone(problem("node <<'NODE'\nawait Promise.resolve();\nNODE"))

    def test_explicit_create_require_auto_module_allowed(self):
        self.assertIsNone(problem("node <<'NODE'\nimport { createRequire } from 'node:module'; const require = createRequire(import.meta.url); require('fs'); await Promise.resolve();\nNODE"))

    def test_file_write_and_unknown_shell_forms_allowed(self):
        for command in ("cat <<'NODE'\nrequire('fs'); await x;\nNODE", "node script.js", "node <<'NODE'\nrequire('fs'); await x;"):
            self.assertIsNone(problem(command))


if __name__ == '__main__':
    unittest.main()
