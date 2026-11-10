#!/bin/sh
# 回路図・基板を生成し、検証と製造データ出力まで行う (mac-studio 上で実行)。
set -e
cd "$(dirname "$0")/.."
HW=hardware; NAME=claude-pico2; OUT=hardware/production; DOC=docs
mkdir -p build $OUT/gerber $DOC/img
(cd tools && python3 gen_sch.py ../$HW/$NAME.kicad_sch && $KIPY gen_pcb.py ../$HW/$NAME.kicad_pcb 2>&1 | grep -v traits)

echo "--- ERC"
$KICLI sch erc --severity-all --format report -o build/erc.rpt $HW/$NAME.kicad_sch >/dev/null
N=$(grep "^\[" build/erc.rpt | grep -c -v -E "lib_symbol_issues|footprint_link_issues" || true)
echo "  電気的な指摘: $N 件 (ライブラリ表が無いことによる警告は除外)"
grep "^\[" build/erc.rpt | grep -v -E "lib_symbol_issues|footprint_link_issues" | sort | uniq -c || true
echo "--- DRC"
tools/drc.sh 20 courtyards_overlap

echo "--- 出力"
rm -f $OUT/gerber/*
$KICLI pcb export gerbers --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" \
  --no-protel-ext --subtract-soldermask -o $OUT/gerber/ $HW/$NAME.kicad_pcb >/dev/null
$KICLI pcb export drill --format excellon --excellon-separate-th --excellon-units mm --generate-map --map-format gerberx2 \
  -o $OUT/gerber/ $HW/$NAME.kicad_pcb >/dev/null
(cd $OUT && rm -f $NAME-gerber.zip && zip -q -j $NAME-gerber.zip gerber/*)
$KICLI pcb export pos --format csv --units mm --side front --exclude-dnp -o $OUT/$NAME-pos.csv $HW/$NAME.kicad_pcb >/dev/null
$KICLI sch export bom --fields 'Reference,Value,Footprint,MPN,${QUANTITY}' --labels 'Reference,Value,Footprint,MPN,Qty' \
  --group-by 'Value,Footprint,MPN' --ref-range-delimiter '' -o $OUT/$NAME-bom.csv $HW/$NAME.kicad_sch >/dev/null
$KICLI sch export pdf -o $DOC/schematic.pdf $HW/$NAME.kicad_sch >/dev/null
sips -s format png -Z 2400 $DOC/schematic.pdf --out $DOC/img/schematic.png >/dev/null 2>&1
$KICLI pcb render --side top --width 1200 --height 2400 --zoom 0.9 --quality high --background opaque -o $DOC/img/render-top.png $HW/$NAME.kicad_pcb >/dev/null
$KICLI pcb render --side bottom --width 1200 --height 2400 --zoom 0.9 --quality high --background opaque -o $DOC/img/render-bottom.png $HW/$NAME.kicad_pcb >/dev/null
$KICLI pcb render --rotate '-50,0,25' --perspective --width 2000 --height 1400 --zoom 0.8 --quality high --background opaque -o $DOC/img/render-iso.png $HW/$NAME.kicad_pcb >/dev/null
for l in F.Cu In1.Cu In2.Cu B.Cu; do
  n=$(echo $l | tr -d '.')
  tools/view.sh layer-$n "$l,Edge.Cuts" && cp build/layer-$n.png $DOC/img/
done
ls $OUT $OUT/gerber $DOC/img
