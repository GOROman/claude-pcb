#!/bin/sh
# DRC を実行して要約を表示する (mac-studio 上で実行)。違反位置は基板座標 mm に直して出す。
cd "$(dirname "$0")/.."
mkdir -p build
$KICLI pcb drc --format json --severity-all --schematic-parity --units mm -o build/drc.json hardware/claude-pico2.kicad_pcb >/dev/null 2>&1
python3 - "$@" <<'PY'
import json, sys, collections
d = json.load(open("build/drc.json"))
OX, OY = 100.0, 50.0
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
skip = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set()
for key in ("violations", "unconnected_items", "schematic_parity"):
    items = d.get(key, [])
    c = collections.Counter(i["type"] for i in items)
    print("== %s: %d %s" % (key, len(items), dict(c)))
    n = 0
    for i in items:
        if i["type"] in skip:
            continue
        n += 1
        if n > limit:
            break
        its = "; ".join("%s@(%.2f,%.2f)" % (x["description"][:48], x["pos"]["x"] - OX, x["pos"]["y"] - OY) for x in i.get("items", []))
        print("  [%s] %s | %s" % (i["type"], i["description"][:70], its))
PY
