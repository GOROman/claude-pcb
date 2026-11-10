#!/bin/sh
# ローカルのリポジトリを mac-studio に同期し、KiCad 同梱 Python / kicad-cli でコマンドを実行して結果を取り込む。
# 使い方: tools/remote.sh '<mac-studio 上でリポジトリ直下から実行するコマンド>'
# リモートの出力は build/remote.log に書かせてから表示する（ssh が出力待ちで戻らなくなるのを避けるため）。
set -e
HOST=${PCB_HOST:-mac-studio.local}
RDIR=work/github.com/GOROman/claude-pcb
SSH="ssh -n -o BatchMode=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=4"
cd "$(dirname "$0")/.."
rsync -a --delete --exclude .git --exclude build ./ "$HOST:$RDIR/"
RC=0
$SSH "$HOST" "cd $RDIR && mkdir -p build && export PATH=/opt/homebrew/bin:\$PATH && export KICAD=/Applications/KiCad/KiCad.app/Contents && export KIPY=\$KICAD/Frameworks/Python.framework/Versions/Current/bin/python3 && export KICLI=\$KICAD/MacOS/kicad-cli && export KISYM=\$KICAD/SharedSupport/symbols && export KIFP=\$KICAD/SharedSupport/footprints && ( $1 ) > build/remote.log 2>&1 < /dev/null" || RC=$?
rsync -a --exclude .git "$HOST:$RDIR/" ./
cat build/remote.log
exit $RC
