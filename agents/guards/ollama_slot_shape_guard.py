import ast
from pathlib import Path
import shlex
import textwrap


def problem(tool_input):
    patch = str(tool_input.get('patch') or '')
    target = str(tool_input.get('file_path') or tool_input.get('path') or '')
    if 'client_local_cancel.py' not in target + patch:
        return None
    source = str(tool_input.get('new_string') or tool_input.get('new_str') or tool_input.get('content') or '')
    if patch:
        source = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != 'get':
            continue
        for inner in ast.walk(node.func.value):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr == 'get' and inner.args and isinstance(inner.args[0], ast.Constant) and inner.args[0].value == 'next_token':
                return '模型的next_token可能是陣列；請先核對並拆開格式，再讀取生成計數。'
    return None


def runtime_problem(text, base):
    if len(text) > 65536 or '--check-local' not in text or '--check-cancel' not in text:
        return None
    try:
        words = shlex.split(text)
    except ValueError:
        return None
    for word in words:
        if word.endswith('/verify-client-identity.py') or word == 'verify-client-identity.py':
            script = Path(word)
            if not script.is_absolute():
                script = Path(base) / script
            helper = script.with_name('client_local_cancel.py')
            try:
                if helper.stat().st_size > 65536:
                    return None
                return problem({'file_path': str(helper), 'content': helper.read_text()})
            except OSError:
                return None
    return None
