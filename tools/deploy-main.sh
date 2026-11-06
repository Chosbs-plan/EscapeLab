#!/usr/bin/env bash
# 빌드 결과(dist/)를 main 브랜치 루트에 올린다. main = 웹에 바로 올릴 수 있는 실행 파일만 있는 브랜치.
# 사용: bash tools/deploy-main.sh   (개발 브랜치에서 실행)
set -euo pipefail
cd "$(dirname "$0")/.."
SRC_REF=$(git rev-parse --short HEAD)
SRC_BRANCH=$(git rev-parse --abbrev-ref HEAD)
npx vite build
WT=$(mktemp -d)
if git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
  git fetch -q origin main
  git worktree add -q -B main "$WT" origin/main
else
  git worktree add -q --orphan -b main "$WT"
fi
find "$WT" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -r dist/. "$WT"/
touch "$WT/.nojekyll"
cat > "$WT/README.md" <<MD
# EscapeLab 웹 그레이박스 — 실행 빌드

이 브랜치는 빌드 결과만 담는다. 직접 고치지 말 것.
소스: \`$SRC_BRANCH\` @ \`$SRC_REF\` → \`bash tools/deploy-main.sh\` 로 갱신.

정적 호스팅(GitHub Pages 등)에서 브랜치 \`main\`, 폴더 \`/ (root)\` 로 열면 \`index.html\` 이 실행된다.
MD
git -C "$WT" add -A
git -C "$WT" commit -q -m "Build from $SRC_BRANCH@$SRC_REF" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01VMSJGDopAqBJFmAE9puLai" || echo "no changes"
git -C "$WT" push -u origin main
git worktree remove --force "$WT"
