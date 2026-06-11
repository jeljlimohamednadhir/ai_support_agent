"""Generate an AST-accurate code map resolving imports, aliases, classes, and methods.

Outputs:
- docs/code_map_deep_ast.md
- docs/code_map_deep_ast.dot

This is a heuristic static analyzer (no imports executed). It builds per-module symbol
maps, resolves simple imports and attribute chains, and records callers/callees with
best-effort resolution.

Run:
    python backend\scripts\generate_code_map_ast.py
"""
from __future__ import annotations
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / 'docs'
DOCS.mkdir(parents=True, exist_ok=True)

EXCLUDE_PARTS = {'.git', '.venv', 'venv', '__pycache__'}
PY_FILES = [p for p in REPO_ROOT.rglob('*.py') if not any(part in EXCLUDE_PARTS for part in p.parts)]

# Read safely
def read_text(p: Path) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return p.read_text(encoding=enc)
        except Exception:
            continue
    return p.read_text(errors='replace')

# Data structures
# module -> {name -> ('func'|'class'|'var', node)}
ModuleSymbols: Dict[str, Dict[str, Tuple[str, ast.AST]]] = {}
# Function/Method defs keyed by qualified name file::qualname
Defs: Dict[str, Dict[str, dict]] = {}
# Calls: (file, lineno, caller_qualname, callee_expr_str)
Calls: List[Tuple[str, int, str, str]] = []

# Helper to get module path from file path
def module_name_from_path(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT)).replace('\\', '/').rstrip('.py')
    except Exception:
        return str(p)

# First pass: collect symbols
for p in PY_FILES:
    mod = module_name_from_path(p)
    src = read_text(p)
    try:
        tree = ast.parse(src)
    except Exception:
        continue
    ModuleSymbols.setdefault(mod, {})
    Defs.setdefault(mod, {})
    # visit top-level defs and classes
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            name = node.name
            ModuleSymbols[mod][name] = ('func', node)
            Defs[mod][name] = {'node': node, 'lineno': node.lineno, 'end_lineno': getattr(node, 'end_lineno', node.lineno), 'sig': None, 'doc': ast.get_docstring(node) or '', 'type': 'function'}
        elif isinstance(node, ast.ClassDef):
            cls_name = node.name
            ModuleSymbols[mod][cls_name] = ('class', node)
            # record methods
            for cnode in node.body:
                if isinstance(cnode, ast.FunctionDef):
                    mname = cnode.name
                    qname = f"{cls_name}.{mname}"
                    Defs[mod][qname] = {'node': cnode, 'lineno': cnode.lineno, 'end_lineno': getattr(cnode, 'end_lineno', cnode.lineno), 'sig': None, 'doc': ast.get_docstring(cnode) or '', 'type': 'method', 'class': cls_name}

# Second pass: build import maps and find calls
# For each module, create a map of local names to origin module (imports)
ImportMaps: Dict[str, Dict[str, str]] = {}  # mod -> local name -> origin module
for p in PY_FILES:
    mod = module_name_from_path(p)
    src = read_text(p)
    try:
        tree = ast.parse(src)
    except Exception:
        continue
    ImportMaps.setdefault(mod, {})
    # record imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                asname = alias.asname or alias.name
                ImportMaps[mod][asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                asname = alias.asname or alias.name
                full = f"{module}.{alias.name}" if module else alias.name
                ImportMaps[mod][asname] = full
    # find calls and enclosing function/method
    # build list of ranges for defs in this module
    ranges = []  # (start,end,qualname)
    for name, info in Defs[mod].items():
        ranges.append((info['lineno'], info['end_lineno'], name))
    # walk calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            lineno = getattr(node, 'lineno', 0)
            # determine enclosing qualname
            enclosing = '<module>'
            for start, end, q in ranges:
                if start <= lineno <= end:
                    enclosing = q
                    break
            # stringify callee expression
            try:
                callee_src = ast.unparse(node.func)
            except Exception:
                callee_src = '<call>'
            Calls.append((mod, lineno, enclosing, callee_src))

# Resolver functions

def resolve_callee(mod: str, callee_expr: str, enclosing: str) -> List[Tuple[str, str]]:
    """Try to resolve a callee expression (like "foo", "mod.func", "self.bar") to list of (module, qualname)
    Returns possible targets (module, qualname)
    """
    targets = []
    # simple name
    if '.' not in callee_expr:
        name = callee_expr
        # local defs in same module
        if name in Defs.get(mod, {}):
            targets.append((mod, name))
        # imported name -> origin module
        origin = ImportMaps.get(mod, {}).get(name)
        if origin:
            # if origin points to module.func or module
            parts = origin.split('.')
            if len(parts) > 1:
                origin_mod = '.'.join(parts[:-1])
                origin_name = parts[-1]
                if origin_name in Defs.get(origin_mod, {}):
                    targets.append((origin_mod, origin_name))
            else:
                # origin is module; check module's defs
                origin_mod = origin
                if name in Defs.get(origin_mod, {}):
                    targets.append((origin_mod, name))
        # global search for functions with this name
        for omod, defs in Defs.items():
            if name in defs:
                targets.append((omod, name))
        return targets
    # dotted name e.g. module.func or pkg.module.func or self.method
    parts = callee_expr.split('.')
    if parts[0] == 'self' or parts[0] == 'cls':
        # method on same class if enclosing is class.method
        if '.' in enclosing:
            cls = enclosing.split('.')[0]
            q = f"{cls}.{parts[1]}"
            if q in Defs.get(mod, {}):
                targets.append((mod, q))
        return targets
    # check if first part is an import alias
    first = parts[0]
    origin = ImportMaps.get(mod, {}).get(first)
    if origin:
        # map rest to possible name
        rest = parts[1:]
        # if origin is full like package.module
        origin_mod = origin
        # try combine origin_mod + rest as module or attribute
        candidate_mod = origin_mod
        candidate_name = '.'.join(rest)
        # direct function in origin_mod
        if candidate_name in Defs.get(candidate_mod, {}):
            targets.append((candidate_mod, candidate_name))
        # if rest length 1 and that name is defined in origin_mod
        if len(rest) == 1 and rest[0] in Defs.get(origin_mod, {}):
            targets.append((origin_mod, rest[0]))
        # fallback: try resolve as module path where last is function name
        # e.g. origin is package.module, rest ['func'] => package.module.func
        full_mod = origin_mod
        if len(rest) >= 1:
            func_name = rest[-1]
            if func_name in Defs.get(full_mod, {}):
                targets.append((full_mod, func_name))
    else:
        # try treat first part as module path
        # try decreasing prefixes
        for i in range(len(parts)-1, 0, -1):
            mod_try = '.'.join(parts[:i])
            name_try = '.'.join(parts[i:])
            if name_try in Defs.get(mod_try, {}):
                targets.append((mod_try, name_try))
    return targets

# Build callers/callees maps
FuncCallMap: Dict[Tuple[str, str], Dict[str, List[Tuple[str, int, str]]]] = {}
# initialize
for mod, defs in Defs.items():
    for name in defs.keys():
        FuncCallMap[(mod, name)] = {'callees': [], 'callers': []}
# populate
for mod, lineno, enclosing, callee_src in Calls:
    caller_key = (mod, enclosing)
    resolved = resolve_callee(mod, callee_src, enclosing)
    # record raw
    if caller_key in FuncCallMap:
        FuncCallMap[caller_key].setdefault('raw_callees', []).append((callee_src, lineno))
    # for each resolved target, add to callees and callers
    for tmod, tname in resolved:
        if caller_key in FuncCallMap:
            FuncCallMap[caller_key]['callees'].append((tmod, tname, callee_src, lineno))
        FuncCallMap.setdefault((tmod, tname), {}).setdefault('callers', []).append((mod, lineno, enclosing))

# Write outputs
out_md = DOCS / 'code_map_deep_ast.md'
md_lines: List[str] = ["# Deep AST Code Map\n", "Generated by backend/scripts/generate_code_map_ast.py\n\n"]
for mod in sorted(Defs.keys()):
    md_lines.append(f"## Module: {mod}\n\n")
    defs = Defs[mod]
    if not defs:
        md_lines.append('(no top-level defs)\n\n')
        continue
    for name, info in sorted(defs.items(), key=lambda x: x[1]['lineno']):
        md_lines.append(f"### {name} ({info.get('type','')})\n")
        md_lines.append(f"- Location: {mod}:{info['lineno']}-{info['end_lineno']}\n")
        doc = info.get('doc','').strip()
        if doc:
            md_lines.append("- Docstring:\n\n``\n")
            md_lines.append(doc + "\n")
            md_lines.append("```\n")
        else:
            md_lines.append("- Docstring: *(none)*\n")
        # source snippet
        snippet = ''
        try:
            src = read_text(REPO_ROOT / mod)
        except Exception:
            src = ''
        if src:
            lines_src = src.splitlines()
            start = max(info['lineno']-1, 0)
            end = min(info['end_lineno'], len(lines_src))
            snippet = '\n'.join(lines_src[start:end])
        if snippet:
            md_lines.append("- Source snippet:\n\n``\n")
            md_lines.append(snippet + "\n")
            md_lines.append("```\n")
        # callers
        callers = FuncCallMap.get((mod, name), {}).get('callers', [])
        md_lines.append(f"- Callers ({len(callers)}):\n")
        if callers:
            for cf, ln, caller in callers[:200]:
                md_lines.append(f"  - {cf}:{ln} inside {caller}\n")
        else:
            md_lines.append("  - *(no callers detected)*\n")
        # callees
        callees = FuncCallMap.get((mod, name), {}).get('callees', [])
        raw_callees = FuncCallMap.get((mod, name), {}).get('raw_callees', [])
        md_lines.append(f"- Callees ({len(callees)} resolved, {len(raw_callees)} raw):\n")
        if callees:
            for tm, tn, raw, ln in callees[:200]:
                md_lines.append(f"  - {tm}::{tn} (raw: {raw}) at {ln}\n")
        if raw_callees and not callees:
            for raw, ln in raw_callees[:200]:
                md_lines.append(f"  - raw: {raw} at {ln}\n")
        # heuristic
        heuristic = ''
        if doc:
            heuristic = doc.split('\n',1)[0]
        md_lines.append(f"- Heuristic: {heuristic}\n\n")
    md_lines.append('\n')

out_md.write_text('\n'.join(md_lines), encoding='utf-8')
print('Wrote', out_md)

out_dot = DOCS / 'code_map_deep_ast.dot'
dot_lines: List[str] = ['digraph G {', '  rankdir=LR;', '  node [shape=box,fontname="Courier"];']
nodes: Set[str] = set()
for (mod, name), cmap in FuncCallMap.items():
    nodes.add(f"{mod}::{name}")
for n in sorted(nodes):
    dot_lines.append(f'  "{n}";')
for (mod, name), cmap in FuncCallMap.items():
    src = f"{mod}::{name}"
    for tm, tn, raw, ln in cmap.get('callees', []):
        dst = f"{tm}::{tn}"
        label = raw.replace('"', '\\"')[:60]
        dot_lines.append(f'  "{src}" -> "{dst}" [label="{label} @ {ln}"];')

dot_lines.append('}')
out_dot.write_text('\n'.join(dot_lines), encoding='utf-8')
print('Wrote', out_dot)

print('AST code map generation complete.')
