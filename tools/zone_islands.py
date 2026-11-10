"""ベタの塗り島を一覧する（分断の調査用）: $KIPY zone_islands.py <pcb> <ネット名>"""
import sys
import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
for z in b.Zones():
    if z.GetNetname() != sys.argv[2]:
        continue
    for layer in z.GetLayerSet().Seq():
        poly = z.GetFilledPolysList(layer)
        for i in range(poly.OutlineCount()):
            bb = poly.Outline(i).BBox()
            print("%s %s island %d: x[%.2f,%.2f] y[%.2f,%.2f] area=%.2fmm2" % (
                z.GetNetname(), b.GetLayerName(layer), i, mm(bb.GetLeft()) - 100, mm(bb.GetRight()) - 100,
                mm(bb.GetTop()) - 50, mm(bb.GetBottom()) - 50, poly.Outline(i).Area() / 1e12))
