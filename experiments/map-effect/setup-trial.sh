#!/bin/zsh
# usage: setup-trial.sh WORKDIR control|map [v2]   (v2: brief-v2.md and a check.sh flow checker)
# Builds an isolated author workspace: good APK, a logging maestro wrapper, a reset script, the brief
# (and the app map for the map arm). No bug builds, no existing flows, no task files.
set -e
W=$1; ARM=$2; VER=${3:-v1}; REPO=${0:A:h:h:h}
mkdir -p $W; cd $W
cp $REPO/.scratch/proofloop/apks/sunflower-good.apk good.apk
REAL=$(which maestro)
cat > maestro <<EOS
#!/bin/zsh
echo "\$(date +%s) \$*" >> ${W}/maestro.log
exec $REAL "\$@"
EOS
cat > reset.sh <<EOS
#!/bin/zsh
# Installs the good build and resets the app to a fresh install state (clears data, waits for the old task).
cd $REPO && python3 -c "
from proofloop.device import AdbDevice
d = AdbDevice(None); d.free_automation_lock(); d.install('$W/good.apk')
d.reset('com.google.samples.apps.sunflower', [], False)"
EOS
chmod +x maestro reset.sh
[ $ARM = map ] && cp $REPO/tasks/sunflower/app-map.md map.md
if [ $VER = v2 ]; then
  cp $REPO/experiments/map-effect/brief-v2.md brief.md
  cat > check.sh <<EOS
#!/bin/zsh
# Flow checker (same rules as 'proofloop check'). Uses map.md anchors if the map is in this directory.
cd $REPO && python3 -c "
import sys, os
from proofloop.flow import parse_flow, check_flow
from proofloop.appmap import load
m = '$W/map.md'
anchors = frozenset(a for s in load(m).screens.values() for a in s.anchors) if os.path.exists(m) else frozenset()
r = check_flow(parse_flow(sys.argv[1]), 'com.google.samples.apps.sunflower', anchors)
print('\\n'.join('ERROR ' + e for e in r.errors) or 'ok')
sys.exit(0 if r.ok else 1)" "\$(cd $W && pwd)/\$1"
EOS
  chmod +x check.sh
else
  cp $REPO/experiments/map-effect/brief.md brief.md
fi
: > maestro.log
echo "$W ready ($ARM)"
