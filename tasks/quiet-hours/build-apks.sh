#!/bin/zsh
# Build the Quiet Hours good APK and one APK per seeded bug from a base commit, without committing anything.
# Usage: build-apks.sh [APP_REPO] [BASE] [OUT_DIR]
# The app repo must have no uncommitted changes to tracked files under app/ (other edits are stashed and restored).
set -e
REPO=${1:-~/Desktop/quiet-hours}; BASE=${2:-e4ba3eb}; OUT=${3:-${0:A:h}/../../.scratch/proofloop/apks}
BUGS=${0:A:h}/bugs; mkdir -p $OUT
export JAVA_HOME=${JAVA_HOME_21:-/opt/homebrew/Cellar/openjdk@21/21.0.9/libexec/openjdk.jdk/Contents/Home}
cd $REPO; branch=$(git branch --show-current); stashed=0
[[ -n "$(git status --porcelain --untracked-files=no)" ]] && { git stash push -q -m proofloop-build; stashed=1; }
restore() { git checkout -q -- app 2>/dev/null; git switch -q $branch; (( stashed )) && git stash pop -q; }
trap restore EXIT
git switch -q --detach $BASE
build() { ./gradlew -q assembleDebug >/dev/null 2>&1 && cp app/build/outputs/apk/debug/app-debug.apk $OUT/$1.apk && echo "built $1 from $BASE"; }
build good-$BASE
for p in $BUGS/*.patch; do n=${p:t:r}; git apply $p && build $n-$BASE; git checkout -q -- app; done
