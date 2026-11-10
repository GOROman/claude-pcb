"""フットプリントのパッド/コートヤード寸法を表示する: dump_fp.py Lib:Name ... (KiCad 同梱 Python で実行)"""
import os
import sys
import pcbnew

FP = os.environ["KIFP"]
mm = pcbnew.ToMM
for spec in sys.argv[1:]:
    lib, name = spec.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(FP, lib + ".pretty"), name)
    if fp is None:
        print("== NOT FOUND", spec)
        continue
    cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    print("== %s  courtyard x[%.2f,%.2f] y[%.2f,%.2f]" % (spec, mm(cy.GetLeft()), mm(cy.GetRight()), mm(cy.GetTop()), mm(cy.GetBottom())))
    seen = {}
    for p in fp.Pads():
        pos, size, dr = p.GetPosition(), p.GetSize(pcbnew.F_Cu), p.GetDrillSize()
        line = "  pad %-4s (%7.3f,%7.3f) %5.3fx%5.3f drill %.2fx%.2f %s" % (
            p.GetNumber(), mm(pos.x), mm(pos.y), mm(size.x), mm(size.y), mm(dr.x), mm(dr.y),
            "SMD" if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD else ("NPTH" if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else "THT"))
        seen.setdefault(p.GetNumber(), []).append(line)
    for num, lines in seen.items():
        if len(lines) > 4:
            print(lines[0] + "   ... x%d" % len(lines))
        else:
            print("\n".join(lines))
