#!/bin/zsh
# usage: setup-trial.sh WORKDIR BRIEF MAP   (BRIEF and MAP are file paths; MAP is copied to map.md)
# Isolated author workspace for Quiet Hours: good APK, logging maestro wrapper, reset (clock pinned
# to Wed 18 Nov 2026 08:00 IST), flow checker, map checker, the map and the brief. No bug builds.
set -e
W=$1; BRIEF=$2; MAP=$3; REPO=${0:A:h:h:h}
mkdir -p $W; cd $W
cp $REPO/.scratch/proofloop/apks/good-e4ba3eb.apk good.apk
REAL=$(which maestro)
cat > maestro <<EOS
#!/bin/zsh
echo "\$(date +%s) \$*" >> ${W}/maestro.log
exec $REAL "\$@"
EOS
cat > reset.sh <<EOS
#!/bin/zsh
# Resets the app (the good build is installed once by the experimenter) to a fresh install, grants notifications, pins the clock.
cd $REPO && python3 -c "
from datetime import datetime
from proofloop.device import AdbDevice
d = AdbDevice('emulator-5556'); d.free_automation_lock()
d.reset('com.sam.quiethours', ['android.permission.POST_NOTIFICATIONS'], False)
d.pin_clock(datetime(2026, 11, 18, 8, 0), 'Asia/Kolkata')"
EOS
cat > check.sh <<EOS
#!/bin/zsh
# Flow checker (same rules as 'proofloop check'); waits on screen anchors listed in map.md are allowed.
cd $REPO && python3 -c "
import sys, os
from proofloop.flow import parse_flow, check_flow
from proofloop.appmap import load
m = '$W/map.md'
anchors = frozenset(a for s in load(m).screens.values() for a in s.anchors) if os.path.exists(m) else frozenset()
r = check_flow(parse_flow(sys.argv[1]), 'com.sam.quiethours', anchors)
print('\\\\n'.join('ERROR ' + e for e in r.errors) or 'ok')
sys.exit(0 if r.ok else 1)" "\$(cd $W && pwd)/\$1"
EOS
cat > map-check.sh <<EOS
#!/bin/zsh
# Checks a map file's format: ./map-check.sh map-out.md
cd $REPO && python3 -m proofloop.cli map "\$(cd $W && pwd)/\$1"
EOS
chmod +x maestro reset.sh check.sh map-check.sh
cp $BRIEF brief.md; cp $MAP map.md
sed -n '/^## Format/,$p' $REPO/skills/app-map/SKILL.md > map-format.md
: > maestro.log
echo "$W ready"
