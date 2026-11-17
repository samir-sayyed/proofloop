#!/bin/zsh
# usage: setup-trial.sh WORKDIR control|map
# Builds an isolated author workspace: good APK, a logging maestro wrapper, a reset script, the brief
# (and the app map for the map arm). No bug builds, no existing flows, no task files.
set -e
W=$1; ARM=$2; REPO=${0:A:h:h:h}
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
cp $REPO/experiments/map-effect/brief.md brief.md
[ $ARM = map ] && cp $REPO/tasks/sunflower/app-map.md map.md
: > maestro.log
echo "$W ready ($ARM)"
