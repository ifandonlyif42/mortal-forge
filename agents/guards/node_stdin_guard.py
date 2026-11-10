import re
import subprocess


def problem(text):
    if len(text) > 65536 or 'await' not in text or 'require' not in text:
        return None
    pattern = r'''(?m)^[ \t]*(?:/[^ \t\n]+/)?node[ \t]*([^<\n]*)<<[ \t]*(['"]?)([A-Za-z_]\w*)\2[ \t]*\n'''
    for match in re.finditer(pattern, text):
        if match[1].strip() not in ('', '-'):
            continue
        end = re.search(r'(?m)^' + re.escape(match[3]) + r'[ \t]*(?:\n|$)', text[match.end():])
        if not end:
            continue
        source = text[match.end():match.end() + end.start()]
        if not re.match(r'\s*(?:(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*)?require\s*\(', source):
            continue
        try:
            result = subprocess.run(['node', '--check', '--input-type=commonjs'], input=source, text=True, capture_output=True, timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode and 'await is only valid' in result.stderr:
            return 'Node標準輸入混用require與頂層await；請把await放進async函式，或明確用module並改用import。'
    return None
