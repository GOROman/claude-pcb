"""ライブラリシンボルのピン一覧を表示する: dump_pins.py <lib.kicad_sym> <symbol>..."""
import sys
from sexpr import parse, find, first

lib = parse(open(sys.argv[1]).read())
syms = {s[1]: s for s in find(lib, "symbol")}
for name in sys.argv[2:]:
    s = syms[name]
    ext = first(s, "extends")
    base = syms[ext[1]] if ext else s
    print("==", name, "extends", ext[1] if ext else None)
    for p in find(s, "property"):
        if p[1] in ("Footprint", "Value", "Reference"):
            print("  ", p[1], "=", p[2])
    for u in find(base, "symbol"):
        for p in find(u, "pin"):
            at = first(p, "at")
            print("  %-4s %-16s %-14s at %s len %s unit %s" % (first(p, "number")[1], first(p, "name")[1], p[1], at[1:], first(p, "length")[1], u[1]))
