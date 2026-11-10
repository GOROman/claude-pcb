#!/bin/sh
# ローカルのリポジトリを mac-studio に同期し、KiCad 同梱 Python / kicad-cli でコマンドを実行して結果を取り込む。
# 使い方: tools/remote.sh '<mac-studio 上でリポジトリ直下から実行するコマンド>'
set -e
HOST=${PCB_HOST:-mac-studio.local}
RDIR=work/github.com/GOROman/claude-pcb
cd "$(dirname "$0")/.."
rsync -a --delete --exclude .git ./ "$HOST:$RDIR/"
ssh -o BatchMode=yes "$HOST" "cd $RDIR && export KICAD=/Applications/KiCad/KiCad.app/Contents && export KIPY=\$KICAD/Frameworks/Python.framework/Versions/Current/bin/python3 && export KICLI=\$KICAD/MacOS/kicad-cli && export KISYM=\$KICAD/SharedSupport/symbols && export KIFP=\$KICAD/SharedSupport/footprints && $1"
rsync -a --exclude .git "$HOST:$RDIR/" ./
