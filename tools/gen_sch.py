"""design.py から KiCad 回路図 (.kicad_sch) を生成する。

接続はすべてネットラベル（電源は電源シンボル）で表す。各ピンから短い配線を引き出し、その先にラベルを置く。
使い方: python3 gen_sch.py <出力.kicad_sch>   (環境変数 KISYM = KiCad シンボルライブラリのディレクトリ)
"""
import copy
import os
import sys
import uuid

import design
from sexpr import QStr, dump, find, first, parse

KISYM = os.environ["KISYM"]
NS = uuid.UUID("6f0b1d4e-52a0-4c6e-9b7a-2350a0c0ffee")
STUB = 2.54
POWER_SYMS = {"GND": "power:GND", "+3V3": "power:+3V3", "+1V1": "power:+1V1", "VBUS": "power:VBUS"}


def uid(*key):
    return str(uuid.uuid5(NS, "/".join(key)))


ROOT = uid("root")
_libs = {}
_flat = {}


def load_lib(lib):
    if lib not in _libs:
        tree = parse(open(os.path.join(KISYM, lib + ".kicad_sym")).read())
        _libs[lib] = {s[1]: s for s in find(tree, "symbol")}
    return _libs[lib]


def get_symbol(lib_id):
    """ライブラリシンボルを取り出す。extends（派生）は親を複製して平坦化する。"""
    if lib_id in _flat:
        return _flat[lib_id]
    lib, name = lib_id.split(":")
    src = load_lib(lib)[name]
    ext = first(src, "extends")
    if ext:
        base = load_lib(lib)[ext[1]]
        props = {p[1]: p for p in find(src, "property")}
        sym = ["symbol", QStr(lib_id)]
        used = set()
        for c in base[2:]:
            if isinstance(c, list) and c[0] == "property":
                sym.append(copy.deepcopy(props.get(c[1], c)))
                used.add(c[1])
            elif isinstance(c, list) and c[0] == "symbol":
                for k, p in props.items():
                    if k not in used:
                        sym.append(copy.deepcopy(p))
                        used.add(k)
                u = copy.deepcopy(c)
                u[1] = QStr(name + u[1][len(ext[1]):])
                sym.append(u)
            else:
                sym.append(copy.deepcopy(c))
    else:
        sym = copy.deepcopy(src)
        sym[1] = QStr(lib_id)
    _flat[lib_id] = sym
    return sym


def sym_pins(sym):
    """[(number, x, y, angle)] シンボル座標 (Y 上向き)"""
    out = []
    for u in find(sym, "symbol"):
        for p in find(u, "pin"):
            at = first(p, "at")
            out.append((first(p, "number")[1], float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0))
    return out


def r(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


FONT = ["effects", ["font", ["size", "1.27", "1.27"]]]
items = []
_pwr = [0]


def wire(x1, y1, x2, y2):
    items.append(["wire", ["pts", ["xy", r(x1), r(y1)], ["xy", r(x2), r(y2)]], ["stroke", ["width", "0"], ["type", "default"]],
                  ["uuid", QStr(uid("wire", r(x1), r(y1), r(x2), r(y2)))]])


def label(net, x, y, dx, dy):
    ang, just = {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, -1): (90, "left"), (0, 1): (270, "right")}[(dx, dy)]
    items.append(["label", QStr(net), ["at", r(x), r(y), str(ang)],
                  ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", just, "bottom"]],
                  ["uuid", QStr(uid("label", net, r(x), r(y)))]])


def instance(lib_id, ref, value, fp, x, y, extra_props=(), pins=None, in_bom=True, on_board=True):
    sym = get_symbol(lib_id)
    node = ["symbol", ["lib_id", QStr(lib_id)], ["at", r(x), r(y), "0"], ["unit", "1"],
            ["exclude_from_sim", "no"], ["in_bom", "yes" if in_bom else "no"], ["on_board", "yes" if on_board else "no"],
            ["dnp", "no"], ["uuid", QStr(uid("sym", ref))]]
    values = {"Reference": ref, "Value": value, "Footprint": fp}
    for p in find(sym, "property"):
        q = copy.deepcopy(p)
        if q[1] in values:
            q[2] = QStr(values[q[1]])
        at = first(q, "at")
        at[1], at[2] = r(x + float(at[1])), r(y - float(at[2]))
        node.append(q)
    for k, v in extra_props:
        node.append(["property", QStr(k), QStr(v), ["at", r(x), r(y), "0"], ["hide", "yes"], copy.deepcopy(FONT)])
    for num in sorted(set(p[0] for p in sym_pins(sym))):
        node.append(["pin", QStr(num), ["uuid", QStr(uid("pin", ref, num))]])
    node.append(["instances", ["project", QStr(design.PROJECT), ["path", QStr("/" + ROOT), ["reference", QStr(ref)], ["unit", "1"]]]])
    items.append(node)


def power(net, x, y):
    _pwr[0] += 1
    instance(POWER_SYMS[net], "#PWR%03d" % _pwr[0], net, "", x, y, in_bom=False)


def build():
    for p in design.PARTS:
        x, y = p["at"]
        sym = get_symbol(p["lib"])
        extra = [("MPN", p["extra"]["mpn"])] if p["extra"].get("mpn") else []
        is_flag = p["ref"].startswith("#")
        instance(p["lib"], p["ref"], p["value"], p["fp"], x, y, extra, in_bom=not is_flag, on_board=not is_flag)
        done = {}
        for num, px, py, ang in sym_pins(sym):
            if num not in p["pins"]:
                raise SystemExit("%s: ピン %s のネットが未定義" % (p["ref"], num))
            net = p["pins"][num]
            sx, sy = x + px, y - py
            key = (r(sx), r(sy))
            if key in done:
                if done[key] != net:
                    raise SystemExit("%s: 重なったピン %s が別ネット (%s / %s)" % (p["ref"], num, done[key], net))
                continue
            done[key] = net
            if net is None:
                items.append(["no_connect", ["at", r(sx), r(sy)], ["uuid", QStr(uid("nc", p["ref"], num))]])
                continue
            dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[ang]  # ピンの外向き（紙面座標）
            ex, ey = sx + dx * STUB, sy + dy * STUB
            wire(sx, sy, ex, ey)
            if net in POWER_SYMS and not p["extra"].get("labels_only"):
                gnd = net == "GND"
                if (gnd and dy == -1) or (not gnd and dy == 1):
                    label(net, ex, ey, dx, dy)  # 向きが合わない場合はラベルにする
                else:
                    if dy == 0:  # 横向きの引き出しは少し伸ばしてからシンボルを置く
                        wire(ex, ey, ex + dx * STUB, ey)
                        ex += dx * STUB
                    power(net, ex, ey)
            else:
                label(net, ex, ey, dx, dy)
        missing = set(p["pins"]) - set(n for n, _, _, _ in sym_pins(sym))
        if missing:
            raise SystemExit("%s: シンボルに無いピン %s" % (p["ref"], sorted(missing)))
    for x, y, text in design.NOTES:
        items.append(["text", QStr(text), ["exclude_from_sim", "no"], ["at", r(x), r(y), "0"],
                      ["effects", ["font", ["size", "2.54", "2.54"], ["bold", "yes"]], ["justify", "left", "bottom"]],
                      ["uuid", QStr(uid("text", text))]])


def main(out):
    build()
    used = sorted(_flat)
    doc = ["kicad_sch", ["version", "20251024"], ["generator", QStr("eeschema")], ["generator_version", QStr("10.0")],
           ["uuid", QStr(ROOT)], ["paper", QStr("A3")],
           ["title_block", ["title", QStr(design.TITLE)], ["rev", QStr(design.REV)], ["company", QStr("GOROman / designed by Claude")]],
           ["lib_symbols"] + [_flat[k] for k in used]]
    doc += items
    doc.append(["sheet_instances", ["path", QStr("/"), ["page", QStr("1")]]])
    doc.append(["embedded_fonts", "no"])
    with open(out, "w") as f:
        f.write(dump(doc) + "\n")
    print("wrote", out, "symbols:", len([p for p in design.PARTS]), "items:", len(items))


if __name__ == "__main__":
    main(sys.argv[1])
