#!/bin/zsh
# usage: score-trial.sh WORKDIR   (run after the author is done; uses the device)
# Proves the authored flow: flow check, 3 clean runs on the good build, the proof bug must fail at C1.
set -e
W=$1; REPO=${0:A:h:h:h}; A=$REPO/.scratch/proofloop/apks
mkdir -p $W/score; cp $W/flow.yaml $W/score/flow.yaml
cat > $W/score/task.json <<EOT
{"name": "map-effect/$(basename $W)",
 "criterion": "Adding two different plants to the garden lists both of them on the My garden tab.",
 "app_id": "com.google.samples.apps.sunflower",
 "approved_by": "experiment brief (experiments/map-effect/brief.md)",
 "good": "$A/sunflower-good.apk",
 "bugs": [{"name": "garden-wrong-column", "apk": "$A/sunflower-bug-garden-wrong-column.apk", "role": "proof", "expect": "C1"}],
 "good_runs": 3, "budget_minutes": 30, "steps": [{"flow": "flow.yaml"}]}
EOT
cd $REPO
# Standing approval for scoring: the experimenter approved the brief, which fixes the checkpoint the bug must
# fail at; the plan is the author's own checkpoint markers. Labelled as such in approved_by, never as a review.
grep -E '^# *checkpoint:' $W/score/flow.yaml | sed -E 's/^# *checkpoint: */- /' > $W/score/plan.md
python3 -m proofloop.cli approve $W/score/task.json --by "standing approval, experiments/map-effect brief: the proof bug must fail at C1; plan from author markers" >/dev/null
python3 -m proofloop.cli check $W/score/task.json | tail -4
python3 -m proofloop.cli prove $W/score/task.json --runs 3 --out $W/score/out | grep -iE 'verdict|good build|proof|C1|failed' | head -8
echo "maestro calls: hierarchy=$(grep -c hierarchy $W/maestro.log) test=$(grep -c ' test' $W/maestro.log) all=$(wc -l < $W/maestro.log | tr -d ' ')"
