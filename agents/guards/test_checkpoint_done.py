import unittest

import write_guard


class CheckpointDoneTest(unittest.TestCase):
    def test_unrun_or_failed_checks_block_done(self):
        for state in ('not_run', 'fail'):
            for style in ('--step-state DONE --check x=', '--step-state=DONE --check=x='):
                command = '~/tools/cash-rule-checkpoint x.checkpoints.jsonl ' + style + state
                self.assertEqual(write_guard.verdict({'tool_input': {'cmd': command}})[0], 'checkpoint-done-checks')

    def test_unverified_scope_is_preserved(self):
        for state in ('pass', 'not_applicable'):
            command = '~/tools/cash-rule-checkpoint x.checkpoints.jsonl --step-state DONE --check x=' + state + ' --not-proven "真LINE未驗"'
            self.assertIsNone(write_guard.verdict({'tool_input': {'cmd': command}})[0])

    def test_running_unrun_check_is_allowed(self):
        command = '~/tools/cash-rule-checkpoint x.checkpoints.jsonl --step-state VALIDATING --check x=not_run'
        self.assertIsNone(write_guard.verdict({'tool_input': {'cmd': command}})[0])

    def test_unrelated_command_is_allowed(self):
        command = 'echo "cash-rule-checkpoint --step-state DONE --check x=not_run"'
        self.assertIsNone(write_guard.verdict({'tool_input': {'cmd': command}})[0])

    def test_env_and_python_entry(self):
        command = 'env EXAMPLE=1 python3 ~/tools/cash_rule_checkpoint.py x.checkpoints.jsonl --step-state DONE --check x=not_run'
        self.assertEqual(write_guard.verdict({'tool_input': {'cmd': command}})[0], 'checkpoint-done-checks')

    def test_separate_commands_do_not_mix_options(self):
        command = '~/tools/cash-rule-checkpoint x.checkpoints.jsonl --step-state DONE --check x=pass; echo --check x=not_run'
        self.assertIsNone(write_guard.verdict({'tool_input': {'cmd': command}})[0])


if __name__ == '__main__':
    unittest.main()
