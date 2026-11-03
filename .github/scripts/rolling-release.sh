#!/usr/bin/env bash
# Update a rolling prerelease (`latest`, `dev-core`): force-move its tag to
# $GITHUB_SHA and make its assets exactly the files given.
#
#   rolling-release.sh TAG TITLE NOTES_FILE FILE...
#
# Needs `contents: write`, a checkout with credentials, and GH_TOKEN set.
# Callers serialise runs with a concurrency group. manifest.json, if given,
# is uploaded last, so nobody sees a new manifest next to old wheels.
set -euo pipefail

tag=$1 title=$2 notes=$3
shift 3

git tag -f "$tag" "$GITHUB_SHA"
git push --force origin "refs/tags/$tag"

wheels=() manifest=()
for f in "$@"; do
  if [ "$(basename "$f")" = manifest.json ]; then manifest+=("$f"); else wheels+=("$f"); fi
done

if gh release view "$tag" >/dev/null 2>&1; then
  gh release edit "$tag" --prerelease --title "$title" --notes-file "$notes"
  gh release upload "$tag" "${wheels[@]}" --clobber
else
  gh release create "$tag" "${wheels[@]}" --verify-tag --prerelease \
    --title "$title" --notes-file "$notes"
fi
if [ "${#manifest[@]}" -gt 0 ]; then
  gh release upload "$tag" "${manifest[@]}" --clobber
fi

# Drop assets that are no longer part of the set (old versions, old names).
keep=$(for f in "$@"; do basename "$f"; done)
gh release view "$tag" --json assets --jq '.assets[].name' | while read -r name; do
  if ! grep -qxF -- "$name" <<<"$keep"; then
    gh release delete-asset "$tag" "$name" --yes
  fi
done
