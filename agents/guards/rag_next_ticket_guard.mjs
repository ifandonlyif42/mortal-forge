import fs from 'node:fs';
import path from 'node:path';

let raw = '';
for await (const chunk of process.stdin) raw += chunk;
let result = {reason: null};
try {
  const input = JSON.parse(raw);
  const argv = input.argv;
  const get = flag => { const i = argv.indexOf(flag); return i < 0 ? null : argv[i + 1]; };
  const state = get('--step-state');
  const file = argv.find(s => s.endsWith('.checkpoints.jsonl'));
  if (file && ['READY', 'DONE'].includes(state)) {
    const location = path.resolve(input.cwd, file);
    const tickets = JSON.parse(fs.readFileSync(path.join(path.dirname(location), 'tickets.json'), 'utf8'));
    if (tickets.schema_version === 3 && tickets.selection_rule?.includes('最早必備票')) {
      const step = get('--step');
      const states = new Map(tickets.tickets.map(t => [t.id, state === 'DONE' && t.id === step ? 'DONE' : t.state]));
      const relationship = ['evaluating', 'adopted'].includes(tickets.relationship_decision?.state);
      const eligible = tickets.tickets.filter(t => !t.optional && ['PENDING', 'READY'].includes(states.get(t.id)) && [...t.dependencies, ...(relationship ? t.conditional_dependencies?.relationship_evaluating_or_adopted ?? [] : [])].every(id => states.get(id) === 'DONE'));
      const expected = eligible[0]?.id;
      result.expected_ticket = expected ?? null;
      if (expected && state === 'READY' && step !== expected) result.reason = '票表最早可開工票是' + expected + '，不能先開始' + step + '；請先核依賴與排序。';
      const next = get('--next')?.match(/下一[^。；\n]{0,20}?票\s*([A-Z][0-9]+)(?=$|[^A-Z0-9])/u)?.[1];
      if (expected && state === 'DONE' && next && next !== expected) result.reason = '票表最早可開工票是' + expected + '，下一票卻寫' + next + '；請由票表計算下一票。';
    }
  }
} catch {}
process.stdout.write(JSON.stringify(result));
