"""Generate a deep code map with AST-based call mapping and heuristic explanations.

This fixed variant avoids using f-strings that embed triple-backticks and builds the
markdown safely to prevent parsing errors.

Outputs:
- docs/code_map_deep.md
- docs/code_map_deep.dot

Run: python backend\scripts\generate_code_map_deep_fixed.py
"""
from __future__ import annotations
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / 'docs'
DOCS.mkdir(parents=True, exist_ok=True)

EXCLUDE_PARTS = {'.git', '.venv', 'venv', '__pycache__'}

PY_FILES = [p for p in REPO_ROOT.rglob('*.py') if not any(part in EXCLUDE_PARTS for part in p.parts)]

def read_text(p: Path) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return p.read_text(encoding=enc)
        except Exception:
            continue
    return p.read_text(errors='replace')

def func_sig_from_node(node: ast.FunctionDef) -> str:
    args = node.args
    def fmt(a):
        if hasattr(a, 'arg'):
            name = a.arg
            if getattr(a, 'annotation', None) is not None:
                try:
                    ann = ast.unparse(a.annotation)
                except Exception:
                    ann = '?'
                return f"{name}: {ann}"
            return name
        return str(a)
    pos = [fmt(a) for a in args.args]
    if args.vararg:
        pos.append('*' + args.vararg.arg)
    kw = [fmt(a) for a in args.kwonlyargs]
    if args.kwarg:
        kw.append('**' + args.kwarg.arg)
    return '(' + ', '.join(pos + kw) + ')'

FuncDefs: Dict[str, Dict[str, dict]] = {}
AllCalls: List[Tuple[str, int, str, str]] = []

for p in PY_FILES:
    rel = str(p.relative_to(REPO_ROOT))
    src = read_text(p)
    try:
        tree = ast.parse(src)
    except Exception:
        continue
    FuncDefs.setdefault(rel, {})
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            name = node.name
            lineno = node.lineno
            end = getattr(node, 'end_lineno', None) or lineno
            sig = func_sig_from_node(node)
            doc = ast.get_docstring(node) or ''
            src_seg = '\n'.join(src.splitlines()[lineno-1:end])
            FuncDefs[rel][name] = {'lineno': lineno, 'end_lineno': end, 'sig': sig, 'doc': doc, 'src': src_seg}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            lineno = getattr(node, 'lineno', 0)
            enclosing = None
            for fname, info in FuncDefs[rel].items():
                if info['lineno'] <= lineno <= info['end_lineno']:
                    enclosing = fname
                    break
            callee = None
            f = node.func
            if isinstance(f, ast.Name):
                callee = f.id
            elif isinstance(f, ast.Attribute):
                parts = []
                cur = f
                while isinstance(cur, ast.Attribute):
                    parts.insert(0, cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    parts.insert(0, cur.id)
                callee = '.'.join(parts)
            else:
                try:
                    callee = ast.unparse(f)
                except Exception:
                    callee = '<call>'
            AllCalls.append((rel, lineno, enclosing or '<module>', callee))

Callers: Dict[str, List[Tuple[str, int, str]]] = {}
for file, lineno, caller_func, callee in AllCalls:
    Callers.setdefault(callee, []).append((file, lineno, caller_func))

KEYWORDS_PURPOSE = [
    ('db', ['db', 'psql', 'postgres', 'query', 'select', 'insert', 'update', 'delete', 'pg']),
    ('ssh', ['ssh', 'sftp', 'paramiko', 'connect', 'exec_command', 'stream_command']),
    ('logs', ['log', 'grep', 'tail', 'catalina', 'logfile', 'parser', 'parse_log']),
    ('llm', ['llm', 'gpt', 'openai', 'generation', 'prompt']),
    ('rca', ['rca', 'root', 'cause', 'hypothesis']),
    ('pipeline', ['pipeline', 'ingest', 'index', 'qdrant', 'vector']),
    ('http', ['curl', 'requests', 'http', 'wsdl', 'soap', 'requests']),
]

def infer_purpose(name: str, doc: str, src: str) -> str:
    tokens = (name + ' ' + doc + ' ' + src).lower()
    reasons = []
    for label, kws in KEYWORDS_PURPOSE:
        if any(k in tokens for k in kws):
            reasons.append(label)
    expl = []
    if doc:
        expl.append(doc.strip().split('\n')[0])
    if reasons:
        expl.append('Inferred roles: ' + ', '.join(reasons))
    else:
        expl.append('Role: utility/helper or business logic (unspecified)')
    return ' '.join(expl)

FuncCallMap: Dict[Tuple[str, str], Dict[str, List[Tuple[str, int, str]]]] = {}
for ffile, funcs in FuncDefs.items():
    for fname, info in funcs.items():
        key = (ffile, fname)
        FuncCallMap[key] = {'callees': [], 'callers': []}

for file, lineno, enclosing, callee in AllCalls:
    key = (file, enclosing)
    simple = callee.split('.')[-1]
    targets = []
    for ffile, funcs in FuncDefs.items():
        if simple in funcs:
            targets.append((ffile, simple))
    if key in FuncCallMap:
        for t in targets:
            FuncCallMap[key]['callees'].append((t[0], t[1], callee, lineno))
        FuncCallMap[key].setdefault('raw_callees', []).append((callee, lineno))

for callee_name, callers in Callers.items():
    simple = callee_name.split('.')[-1]
    for ffile, funcs in FuncDefs.items():
        if simple in funcs:
            for caller in callers:
                FuncCallMap.setdefault((ffile, simple), {}).setdefault('callers', [])
                FuncCallMap[(ffile, simple)]['callers'].append(caller)

out_md = DOCS / 'code_map_deep.md'
lines: List[str] = ["# Deep Code Map\n", "Generated by backend/scripts/generate_code_map_deep_fixed.py\n\n"]
for ffile in sorted(FuncDefs.keys()):
    lines.append(f"## File: {ffile}\n\n")
    funcs = FuncDefs[ffile]
    if not funcs:
        lines.append("(no top-level functions)\n\n")
        continue
    for fname, info in sorted(funcs.items(), key=lambda x: x[1]['lineno']):
        lines.append(f"### Function: {fname} {info['sig']}\n")
        lines.append(f"- Defined at: {ffile}:{info['lineno']}-{info['end_lineno']}\n")
        doc = info['doc'].strip() if info['doc'] else ''
        if doc:
            lines.append("- Docstring:\n\n``\n")
            lines.append(doc + "\n")
            lines.append("```\n")
        else:
            lines.append("- Docstring: *(none)*\n")
        lines.append("- Source snippet:\n\n``\n")
        src_lines = info['src'].splitlines()
        for sl in src_lines[:30]:
            lines.append(sl + '\n')
        lines.append("```\n")
        key = (ffile, fname)
        cmap = FuncCallMap.get(key, {})
        callers = cmap.get('callers', []) if cmap else []
        callees = cmap.get('callees', []) if cmap else []
        raw_callees = cmap.get('raw_callees', []) if cmap else []
        lines.append(f"- Callers ({len(callers)}):\n")
        if callers:
            for cf, ln, caller_func in callers[:50]:
                lines.append(f"  - {cf}:{ln} inside {caller_func}\n")
        else:
            lines.append("  - *(no callers detected by AST)*\n")
        lines.append(f"- Callees ({len(callees)} matched defs, {len(raw_callees)} raw):\n")
        if callees:
            for tf, tfname, raw, ln in callees[:50]:
                lines.append(f"  - calls {tf}::{tfname} (raw: {raw}) at line {ln}\n")
        if raw_callees and not callees:
            for raw, ln in raw_callees[:50]:
                lines.append(f"  - raw call: {raw} at line {ln}\n")
        lines.append('\n')
        explanation = infer_purpose(fname, doc, info['src'])
        lines.append("- Heuristic explanation:\n\n")
        lines.append(explanation + "\n\n")
    lines.append('\n')

out_md.write_text('\n'.join(lines), encoding='utf-8')
print('Wrote', out_md)

out_dot = DOCS / 'code_map_deep.dot'
lines_dot: List[str] = ['digraph G {', '  rankdir=LR;', '  node [shape=box,fontname="Courier"];']
nodes: Set[str] = set()
for (ffile, fname), cmap in FuncCallMap.items():
    node = f"{ffile}::{fname}"
    nodes.add(node)
for node in sorted(nodes):
    lines_dot.append(f'  "{node}";')
for (ffile, fname), cmap in FuncCallMap.items():
    src_node = f"{ffile}::{fname}"
    for tf in cmap.get('callees', []):
        tf_file, tf_name, raw, ln = tf
        dst_node = f"{tf_file}::{tf_name}"
        lines_dot.append(f'  "{src_node}" -> "{dst_node}" [label="{raw} @ {ln}"];')
lines_dot.append('}')
out_dot.write_text('\n'.join(lines_dot), encoding='utf-8')
print('Wrote', out_dot)

print('Deep code map generation complete.')
