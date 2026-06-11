"""Sanitize a DOT file by replacing quoted node names with simple ids and keeping original names as labels.

Usage:
    python backend\scripts\sanitize_dot.py docs\code_map_deep_ast.dot docs\code_map_deep_ast_sanitized.dot

This is defensive: it maps every quoted string token to a node id and rewrites edges.
"""
import re
import sys
from pathlib import Path

if len(sys.argv) < 3:
    print('Usage: sanitize_dot.py input.dot output.dot')
    sys.exit(2)

inp = Path(sys.argv[1])
out = Path(sys.argv[2])
text = inp.read_text(encoding='utf-8')
# find all quoted strings
quoted = re.findall(r'"([^"]+)"', text)
# unique preserve order
seen = {}
order = []
for q in quoted:
    if q not in seen:
        seen[q] = len(seen)
        order.append(q)
# mapping
mapping = {q: f'node{idx}' for q, idx in zip(order, range(len(order)))}

# replace quoted occurrences with node ids
# but we must avoid replacing labels inside [label=...] so we'll parse edges/nodes
# simpler: for each unique quoted string, replace only occurrences of the exact quoted token with the id
san = text
for q, nid in mapping.items():
    san = san.replace(f'"{q}"', nid)

# build new header
lines = ['digraph G {', '  rankdir=LR;', '  node [shape=box,fontname="Courier"];']
# add nodes with labels
for q, nid in mapping.items():
    # escape quotes in label
    lbl = q.replace('"', '\\"')
    lines.append(f'  {nid} [label="{lbl}"];')
# append the rest of sanitized content but remove the original node declarations since we've added our own
# find the opening brace and then append everything after it except the node declarations we replaced
# we'll append the edges and other attributes from san but excluding our newly created nodes lines might duplicate; simply append original body after removing first line and final brace
body = san
# remove leading 'digraph' header if present
m = re.search(r'digraph\s+[^\{]*\{', body)
if m:
    body = body[m.end():]
# remove trailing '}'
if body.strip().endswith('}'):
    body = body.rstrip()[:-1]
# append body lines
lines.append(body.strip())
lines.append('}')
out.write_text('\n'.join(lines), encoding='utf-8')
print('Wrote', out)
