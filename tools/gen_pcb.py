"""design.py から KiCad 基板 (.kicad_pcb) を生成する。KiCad 同梱 Python (pcbnew) で実行する。

使い方: $KIPY gen_pcb.py <出力.kicad_pcb>
座標はすべて基板左上を原点とした mm（X 右、Y 下）。USB コネクタが上、1 番ピンが左上。
"""
import json
import os
import sys

import pcbnew

import design
from gen_sch import ROOT, uid

KIFP = os.environ["KIFP"]
OX, OY = 100.0, 50.0  # 図面上の基板原点
W, H = 21.0, 51.0
F, B, IN1, IN2 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu
mm = pcbnew.FromMM

# 部品配置: ref -> (x, y, 回転[deg])
PLACE = {
    "U1": (10.5, 25.1, 0), "J1": (10.5, 3.15, 180), "J2": (0, 0, 0), "J3": (10.5, 51.0, 0),
    "H1": (4.8, 49.0, 0), "H2": (16.2, 49.0, 0),
    # 左上: Flash / BOOTSEL / VBUS 検出 / VSYS 測定
    "U2": (7.9, 18.3, 0), "C20": (8.85, 16.45, 180), "SW1": (7.9, 13.6, 0), "R5": (5.9, 15.5, 90),
    "R12": (4.0, 2.3, 270), "R13": (4.0, 4.9, 270), "R14": (7.1, 9.55, 270), "R15": (7.1, 11.5, 270),
    "R4": (8.75, 9.2, 270), "R3": (12.2, 9.4, 270),
    # USB 直列抵抗
    "R1": (10.35, 10.6, 270), "R2": (11.35, 10.6, 270),
    # 右上: 3.3V 昇降圧電源
    "D1": (16.9, 2.65, 90), "R10": (18.0, 7.0, 270),
    "U3": (15.6, 13.2, 270), "L1": (15.6, 10.2, 0), "C1": (13.2, 11.1, 180), "C3": (17.3, 10.8, 90),
    # コア電源 (内蔵 SMPS)
    "C5": (12.5, 20.4, 0), "L2": (12.5, 18.5, 270), "C6": (14.1, 17.775, 0),
    "R7": (14.4, 19.3, 180), "C7": (14.4, 20.3, 0),
    # チップ周りのデカップリング
    "C8": (6.25, 21.35, 90), "C9": (5.1, 26.55, 180), "C14": (6.4, 28.75, 0), "C10": (5.9, 31.9, 0),
    "C11": (14.2, 28.9, 0), "C16": (15.98, 24.65, 0), "C13": (15.2, 21.65, 0),
    # ADC 基準
    "C18": (16.45, 22.0, 90), "R8": (16.5, 18.3, 270), "C19": (16.5, 20.3, 270),
    # LED (チップ右脇)
    "R9": (15.45, 25.6, 0), "D2": (17.1, 25.6, 180),
    # 水晶
    "Y1": (8.6, 33.8, 0), "R6": (10.0, 31.2, 90), "C21": (6.0, 34.65, 180), "C22": (11.25, 32.95, 0),
}


NC_NETS = {("J1", "A8"): "unconnected-(J1-SBU1-PadA8)", ("J1", "B8"): "unconnected-(J1-SBU2-PadB8)"}


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


class Gen:
    def __init__(self, path):
        self.path = path
        # プロジェクト設定（ネットクラス等）を読み込ませるため、空の基板を作ってから LoadBoard する
        with open(path, "w") as f:
            f.write('(kicad_pcb (version 20241229) (generator "pcbnew") (generator_version "9.0"))\n')
        self.b = pcbnew.LoadBoard(path)
        self.b.SetCopperLayerCount(4)
        self.nets = {}
        self.fps = {}
        self.libdir = os.path.join(os.path.dirname(path), "lib", "claude_pico.pretty")

    # ------------------------------------------------------------ ネット
    def net(self, name, raw=False):
        if name not in self.nets:
            # 回路図ではラベルのネットは "/名前"、電源シンボルのネットは名前そのまま
            full = name if raw or name in ("GND", "+3V3", "+1V1", "VBUS") else "/" + name
            ni = pcbnew.NETINFO_ITEM(self.b, full)
            self.b.Add(ni)
            self.nets[name] = ni
        return self.nets[name]

    # ------------------------------------------------------------ 独自フットプリント
    def _pad(self, fp, num, x, y, w, h, kind, drill=0.0, shape=pcbnew.PAD_SHAPE_CIRCLE, layer=F, castellated=False):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(num))
        if kind == "pth":
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad.SetLayerSet(pcbnew.PAD.PTHMask())
            pad.SetDrillSize(pcbnew.VECTOR2I(mm(drill), mm(drill)))
        else:
            pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            ls = pcbnew.LSET()
            ls.AddLayer(layer)
            ls.AddLayer(pcbnew.F_Mask if layer == F else pcbnew.B_Mask)
            pad.SetLayerSet(ls)
        pad.SetShape(F, shape)
        pad.SetSize(F, pcbnew.VECTOR2I(mm(w), mm(h)))
        if castellated:
            pad.SetProperty(pcbnew.PAD_PROP_CASTELLATED)
        pad.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.Add(pad)
        return pad

    def _edge_pin(self, fp, num, hx, hy, ex, ey):
        """Pico 風の端面スルーホール付きピン: スルーホール + 基板端の半穴 + 表裏の接続パッド"""
        self._pad(fp, num, hx, hy, 1.6, 1.6, "pth", drill=1.0)
        self._pad(fp, num, ex, ey, 1.6, 1.6, "pth", drill=0.9, shape=pcbnew.PAD_SHAPE_RECT, castellated=True)
        # 半穴パッド（端から 0.8mm）とスルーホールの間を表裏の角パッドでつなぐ
        k = 0.7 / 1.61
        cx, cy = (hx + ex + (hx - ex) * k) / 2, (hy + ey + (hy - ey) * k) / 2
        w, h = (abs(hx - ex) * (1 - k), 1.6) if hy == ey else (1.6, abs(hy - ey) * (1 - k))
        for layer in (F, B):
            self._pad(fp, num, cx, cy, w, h, "smd", shape=pcbnew.PAD_SHAPE_RECT, layer=layer)

    def make_custom_fps(self):
        os.makedirs(self.libdir, exist_ok=True)
        out = {}
        fp = pcbnew.FOOTPRINT(self.b)
        fp.SetFPID(pcbnew.LIB_ID("claude_pico", "PicoEdge_40"))
        for i in range(20):
            y = 1.37 + 2.54 * i
            self._edge_pin(fp, i + 1, 1.61, y, 0.0, y)
            self._edge_pin(fp, 40 - i, W - 1.61, y, W, y)
        out["PicoEdge_40"] = fp
        fp = pcbnew.FOOTPRINT(self.b)
        fp.SetFPID(pcbnew.LIB_ID("claude_pico", "PicoDebug_3"))
        for i in range(3):
            x = (i - 1) * 2.54
            self._edge_pin(fp, i + 1, x, -1.61, x, 0.0)
        out["PicoDebug_3"] = fp
        for name, fp in out.items():
            fp.SetAttributes(pcbnew.FP_THROUGH_HOLE | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
            fp.Reference().SetVisible(False)
            fp.Value().SetVisible(False)
            pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP).FootprintSave(self.libdir, fp)
        return out

    # ------------------------------------------------------------ 部品
    def place_parts(self):
        custom = self.make_custom_fps()
        for p in design.PARTS:
            ref = p["ref"]
            if ref.startswith("#"):
                continue
            lib, name = p["fp"].split(":")
            if lib == "claude_pico":
                fp = pcbnew.FootprintLoad(self.libdir, name)
            else:
                fp = pcbnew.FootprintLoad(os.path.join(KIFP, lib + ".pretty"), name)
            if fp is None:
                raise SystemExit("footprint not found: " + p["fp"])
            fp.SetFPID(pcbnew.LIB_ID(lib, name))
            fp.SetReference(ref)
            fp.SetValue(p["value"])
            fp.SetPath(pcbnew.KIID_PATH("/" + uid("sym", ref)))
            fp.SetSheetname("/")
            fp.SetSheetfile(design.PROJECT + ".kicad_sch")
            fp.Reference().SetVisible(False)
            fp.Value().SetVisible(False)
            x, y, rot = PLACE[ref]
            self.b.Add(fp)
            fp.SetPosition(P(x, y))
            fp.SetOrientationDegrees(rot)
            for pad in fp.Pads():
                num = pad.GetNumber()
                net = p["pins"].get(num)
                if net:
                    pad.SetNet(self.net(net))
                elif num in p["pins"]:  # 未接続ピンは回路図と同じ自動ネット名にする
                    pad.SetNet(self.net(NC_NETS[(ref, num)], raw=True))
                if ref == "J2" or (ref in ("J1", "U3", "R3") and net == "GND"):
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            self.fps[ref] = fp

    def pad(self, ref, num):
        """パッド中心 (x, y) を基板座標 mm で返す。同番号が複数ある場合は最初の 1 個。"""
        for pad in self.fps[ref].Pads():
            if pad.GetNumber() == str(num):
                pos = pad.GetPosition()
                return (round(pcbnew.ToMM(pos.x) - OX, 4), round(pcbnew.ToMM(pos.y) - OY, 4))
        raise KeyError((ref, num))

    # ------------------------------------------------------------ 配線プリミティブ
    def seg(self, net, a, b, w=0.15, layer=F):
        if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
            return
        t = pcbnew.PCB_TRACK(self.b)
        t.SetStart(P(*a))
        t.SetEnd(P(*b))
        t.SetWidth(mm(w))
        t.SetLayer(layer)
        t.SetNet(self.net(net))
        self.b.Add(t)

    def route(self, net, pts, w=0.15, layer=F):
        """折れ線を引く。pts の要素は (x, y) か、次の区間の曲げ方を指定する文字列:
        "sd" = 直線→斜め 45°（既定）, "ds" = 斜め→直線, "-" = そのまま直結"""
        mode = "sd"
        cur = None
        for p in pts:
            if isinstance(p, str):
                mode = p
                continue
            if cur is not None:
                dx, dy = p[0] - cur[0], p[1] - cur[1]
                adx, ady = abs(dx), abs(dy)
                if mode == "-" or adx < 1e-6 or ady < 1e-6 or abs(adx - ady) < 1e-6:
                    self.seg(net, cur, p, w, layer)
                else:
                    d = min(adx, ady)
                    sx, sy = (1 if dx > 0 else -1), (1 if dy > 0 else -1)
                    if mode == "ds":
                        mid = (cur[0] + sx * d, cur[1] + sy * d)
                    else:
                        mid = (p[0] - sx * d, p[1] - sy * d)
                    mid = (round(mid[0], 4), round(mid[1], 4))
                    self.seg(net, cur, mid, w, layer)
                    self.seg(net, mid, p, w, layer)
                mode = "sd"
            cur = p

    def via(self, net, x, y, d=0.55, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(P(x, y))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(F, B)
        v.SetWidth(F, mm(d))
        v.SetDrill(mm(drill))
        v.SetNet(self.net(net))
        self.b.Add(v)
        return (x, y)

    # ------------------------------------------------------------ 外形・ゾーン・シルク
    def outline(self, r=0.5):
        def line(a, b):
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(*a))
            s.SetEnd(P(*b))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.05))
            self.b.Add(s)

        def arc(c, start, mid, end):
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetArcGeometry(P(*start), P(*mid), P(*end))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.05))
            self.b.Add(s)

        k = r * (1 - 0.70710678)
        line((r, 0), (W - r, 0))
        line((W, r), (W, H - r))
        line((W - r, H), (r, H))
        line((0, H - r), (0, r))
        arc(None, (0, r), (k, k), (r, 0))
        arc(None, (W - r, 0), (W - k, k), (W, r))
        arc(None, (W, H - r), (W - k, H - k), (W - r, H))
        arc(None, (r, H), (k, H - k), (0, H - r))

    def zone(self, net, layer, pts, priority=0, clearance=0.15, solid=False, min_w=0.2):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(layer)
        z.SetNet(self.net(net))
        z.SetAssignedPriority(priority)
        z.SetMinThickness(mm(min_w))
        if clearance is not None:
            z.SetLocalClearance(mm(clearance))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.2))
        z.SetThermalReliefSpokeWidth(mm(0.3))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline()
        o.NewOutline()
        for x, y in pts:
            o.Append(mm(OX + x), mm(OY + y))
        self.b.Add(z)
        return z

    def text(self, s, x, y, size=0.8, layer=pcbnew.F_SilkS, rot=0, just=None, thick=None):
        t = pcbnew.PCB_TEXT(self.b)
        t.SetText(s)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(thick or size * 0.15))
        t.SetTextAngleDegrees(rot)
        if layer in (pcbnew.B_SilkS, pcbnew.B_Fab):
            t.SetMirrored(True)
        if just is not None:
            t.SetHorizJustify(just)
        self.b.Add(t)

    def fill(self):
        pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())

    def save(self):
        pcbnew.SaveBoard(self.path, self.b)


def main(path):
    import routes
    g = Gen(path)
    ds = g.b.GetDesignSettings()
    ds.SetBoardThickness(mm(1.0))  # 純正 Pico と同じ 1.0mm 厚
    g.outline()
    g.place_parts()
    full = [(0, 0), (W, 0), (W, H), (0, H)]
    g.zone("GND", IN1, full)
    g.zone("+3V3", IN2, full)
    routes.build(g)
    g.fill()
    g.save()
    print("saved", path, "tracks:", len(g.b.GetTracks()), "footprints:", len(g.b.GetFootprints()))


if __name__ == "__main__":
    main(sys.argv[1])
