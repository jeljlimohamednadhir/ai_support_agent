"""Simplify labels in a sanitized DOT file by replacing long labels with short safe labels.

Usage:
    python backend\scripts\simplify_dot_labels.py docs\code_map_deep_ast_sanitized.dot docs\code_map_deep_ast_simplified.dot docs\code_map_label_map.csv
"""
import re
import sys
from pathlib import Path

if len(sys.argv) < 4:
    print('Usage: simplify_dot_labels.py in.dot out.dot labels.csv')
    sys.exit(2)

inp = Path(sys.argv[1])
out = Path(sys.argv[2])
labels_csv = Path(sys.argv[3])
text = inp.read_text(encoding='utf-8')
# find node label declarations like: node123 [label="..."];
pattern = re.compile(r"(node\d+)\s*\[label=\"([^\"]*)\"\]\s*;")
labels = []
repl = text
mapping = {}
for m in pattern.finditer(text):
    nid = m.group(1)
    orig = m.group(2)
    mapping[nid] = orig

# produce simplified: replace label value with short label "N{index}"
for i, (nid, orig) in enumerate(mapping.items(), start=1):
    short = f"N{i}"
    repl = repl.replace(f'{nid} [label="{orig}"];', f'{nid} [label="{short}"];')

out.write_text(repl, encoding='utf-8')
# write mapping CSV
lines = ['node_id,short,label']
for i, (nid, orig) in enumerate(mapping.items(), start=1):
    lines.append(f'{nid},N{i},"{orig.replace("\"","\"\"")}"')
labels_csv.write_text('\n'.join(lines), encoding='utf-8')
print('Wrote', out, 'and', labels_csv)
