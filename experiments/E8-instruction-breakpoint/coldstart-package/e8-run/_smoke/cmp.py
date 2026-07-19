import json
from pathlib import Path
smoke = Path.home()/"e8-run/_smoke"
serial = json.loads((smoke/"serial_gt.json").read_text())
merged = {}
for k in (0, 1):
    p = json.loads((smoke/("scored-shard-%d.json" % k)).read_text())
    print("shard %d families: %s" % (k, sorted(p["family_ids"])))
    for fam, per_item in p["scored"].items():
        merged[fam] = {int(i): {"a": list(map(bool, ac["a"])), "c": list(map(bool, ac["c"]))}
                       for i, ac in per_item.items()}
serial_n = {fam: {int(i): {"a": list(map(bool, ac["a"])), "c": list(map(bool, ac["c"]))}
                  for i, ac in items.items()} for fam, items in serial.items()}
print("serial families:", sorted(serial_n))
print("merged families:", sorted(merged))
assert sorted(serial_n) == sorted(merged), "FAMILY SET MISMATCH"
mismatches, total_items, total_bools = [], 0, 0
for fam in sorted(serial_n):
    si, mi = serial_n[fam], merged[fam]
    assert sorted(si) == sorted(mi), "item set mismatch %s" % fam
    for i in si:
        total_items += 1
        for key in ("a", "c"):
            total_bools += len(si[i][key])
            if si[i][key] != mi[i][key]:
                mismatches.append((fam, i, key, si[i][key], mi[i][key]))
print("compared %d families, %d items, %d booleans" % (len(serial_n), total_items, total_bools))
if mismatches:
    print("MISMATCHES:", mismatches)
    print("SMOKE_RESULT: FAIL")
else:
    print("SMOKE_RESULT: PASS (all per-item booleans IDENTICAL serial vs 2-worker)")
