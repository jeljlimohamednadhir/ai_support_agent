import json, re
from pathlib import Path

BACKEND   = Path(__file__).parent
FR_RAW    = BACKEND / "FR"
FR_STRUCT = BACKEND / "data" / "fr_structured"

# Extraire le numéro FR depuis un nom de fichier
def extract_num(name: str) -> str:
    m = re.search(r'FR[\s\-_]?(\d{1,4}[Bb]?)', name, re.IGNORECASE)
    return m.group(1).upper() if m else ""

# FRs brutes
raw_files = sorted(FR_RAW.glob("*.json")) if FR_RAW.exists() else []
raw_nums  = {extract_num(f.stem): f for f in raw_files}

# FRs structurées : lire l'id et le source_file
struct_files = sorted(FR_STRUCT.glob("*.json"))
struct_nums  = set()
struct_ids   = set()
for sf in struct_files:
    try:
        rec = json.loads(sf.read_text(encoding="utf-8"))
        struct_ids.add(rec.get("id",""))
        num = extract_num(sf.stem) or extract_num(rec.get("id","")) or extract_num(rec.get("_source_file",""))
        if num:
            struct_nums.add(num)
    except Exception:
        pass

print(f"FRs brutes   : {len(raw_files)} fichiers dans data/FR/")
print(f"FRs struct.  : {len(struct_files)} fichiers dans data/fr_structured/")
print()

# FRs brutes sans correspondance structurée
missing = []
for num, path in sorted(raw_nums.items(), key=lambda x: x[0].zfill(5)):
    if num not in struct_nums:
        missing.append((num, path))

print(f"=== FRs NON STRUCTUREES ({len(missing)}) ===")
for num, path in missing:
    print(f"  FR {num:<8}  {path.name}")

print()
# FRs structurées sans FR brute correspondante
orphan = struct_nums - set(raw_nums.keys())
if orphan:
    print(f"=== FRs structurées sans source brute ({len(orphan)}) ===")
    for n in sorted(orphan):
        print(f"  FR {n}")
