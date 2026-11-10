#!/bin/sh
# 基板の指定レイヤーを PNG にする (mac-studio 上で実行): view.sh <名前> <レイヤー> [x0 y0 x1 y1 (基板座標mm)] [px/mm]
set -e
export PATH=/opt/homebrew/bin:$PATH
NAME=$1; LAYERS=$2; PPM=${7:-40}
cd "$(dirname "$0")/.."
mkdir -p build
$KICLI pcb export svg --layers "$LAYERS" --mode-single --page-size-mode 2 --exclude-drawing-sheet -o build/$NAME.svg hardware/claude-pico2.kicad_pcb >/dev/null
rsvg-convert -z $(echo "$PPM / 3.7795" | bc -l) -b white build/$NAME.svg -o build/$NAME.png
if [ -n "$6" ]; then
  X=$(echo "$3 * $PPM" | bc); Y=$(echo "$4 * $PPM" | bc); CW=$(echo "($5 - $3) * $PPM" | bc); CH=$(echo "($6 - $4) * $PPM" | bc)
  magick build/$NAME.png -crop ${CW%.*}x${CH%.*}+${X%.*}+${Y%.*} +repage build/$NAME.png
fi
