import unittest
import tempfile
from pathlib import Path

import write_guard
from ollama_slot_shape_guard import problem


class OllamaSlotShapeTest(unittest.TestCase):
    def test_actual_cli_launch_checks_helper(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            (path / 'verify-client-identity.py').write_text('pass')
            (path / 'client_local_cancel.py').write_text("def slots(row):\n    if not isinstance(row, dict):\n        raise ValueError()\n    return row.get('next_token', {}).get('n_decoded')")
            command = f'python3 {path}/verify-client-identity.py --check-local --check-cancel'
            self.assertEqual(write_guard.verdict({'tool_input': {'cmd': command, 'workdir': root}})[0], 'ollama-slot-shape')

    def test_correct_helper_cli_allowed(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            (path / 'verify-client-identity.py').write_text('pass')
            (path / 'client_local_cancel.py').write_text("def slots(row):\n    token = row.get('next_token')\n    if isinstance(token, list):\n        token = token[0]\n    return token.get('n_decoded')")
            command = f'python3 {path}/verify-client-identity.py --check-local --check-cancel'
            self.assertIsNone(write_guard.verdict({'tool_input': {'cmd': command, 'workdir': root}})[0])

    def test_direct_and_empty_fallback_chains_rejected(self):
        for expression in ("row.get('next_token', {}).get('n_decoded', 0)", "(row.get('next_token') or {}).get('n_decoded', 0)"):
            payload = {'file_path': '/tmp/client_local_cancel.py', 'new_string': 'return ' + expression}
            self.assertIsNotNone(problem(payload))
            self.assertEqual(write_guard.verdict({'tool_input': payload})[0], 'ollama-slot-shape')

    def test_registered_patch_rejected(self):
        patch = "*** Update File: /tmp/client_local_cancel.py\n@@\n+    return row.get('next_token', {}).get('n_decoded', 0)\n"
        self.assertEqual(write_guard.verdict({'tool_input': {'patch': patch}})[0], 'ollama-slot-shape')

    def test_explicit_type_handling_allowed(self):
        source = "token = row.get('next_token') or {}\nif isinstance(token, list):\n    token = token[0]\nreturn token.get('n_decoded', 0)"
        self.assertIsNone(problem({'file_path': '/tmp/client_local_cancel.py', 'new_string': source}))

    def test_other_files_and_unknown_fragments_allowed(self):
        self.assertIsNone(problem({'file_path': '/tmp/other.py', 'new_string': "return row.get('next_token', {}).get('n_decoded')"}))
        self.assertIsNone(problem({'file_path': '/tmp/client_local_cancel.py', 'new_string': 'elif unknown:'}))


if __name__ == '__main__':
    unittest.main()
