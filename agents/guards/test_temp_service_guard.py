import json
import subprocess
import sys
import unittest
from pathlib import Path

GUARD = str(Path(__file__).with_name('temp_service_guard.py'))


def run(command):
    payload = json.dumps({'tool_input': {'command': command}})
    return subprocess.run([sys.executable, GUARD], input=payload, capture_output=True, text=True).returncode


class TempServiceGuardTest(unittest.TestCase):
    def test_blocked(self):
        for command in [
            'pnpm --filter @crossec/api dev',
            'pnpm dev',
            'cd apps/web && pnpm run dev',
            'npm run dev:api',
            'pnpm exec tsx watch src/index.ts',
            'nohup next dev -p 3002 &',
            'python3 -m http.server 8000',
            'vite --host 127.0.0.1',
            'FOO=1 pnpm start',
        ]:
            self.assertEqual(run(command), 2, command)

    def test_allowed(self):
        for command in [
            'pnpm exec vitest run a.test.ts',
            'pnpm install',
            'pnpm test',
            'next build',
            'vite build',
            'pnpm exec tsc --noEmit',
            'tsx scripts/seed.ts',
            'node script.js',
            'python3 -m pytest',
            'python3 ~/tools/temp-service.py start --name a --ttl 1h -- pnpm dev',
            'git commit -m "pnpm dev"',
        ]:
            self.assertEqual(run(command), 0, command)


if __name__ == '__main__':
    unittest.main()
