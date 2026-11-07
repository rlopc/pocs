#!/usr/bin/env bash
# GitHub settings the Terraform provider (integrations/github 6.13) cannot manage yet,
# applied through the REST API with the GitHub CLI. Move each one to Terraform when the
# provider supports it:
# - Private vulnerability reporting: integrations/terraform-provider-github#2969.
# - CodeQL default setup: integrations/terraform-provider-github#3315.
#
# Usage: ./api-only.sh check   report drift, change nothing (exit 1 on drift)
#        ./api-only.sh apply   set the declared values
set -euo pipefail

repo="rlopc/pocs"
mode="${1:-check}"
drift=0

# compare <name> <actual> <expected>
compare() {
  if [[ "$2" == "$3" ]]; then
    echo "OK     $1: $2"
  else
    echo "DRIFT  $1: $2 (expected $3)"
    drift=1
  fi
}

# Private vulnerability reporting: the channel SECURITY.md points reporters to.
pvr=$(gh api "repos/$repo/private-vulnerability-reporting" --jq .enabled)
compare "private vulnerability reporting" "$pvr" "true"
if [[ "$mode" == "apply" && "$pvr" != "true" ]]; then
  gh api -X PUT "repos/$repo/private-vulnerability-reporting" --silent
fi

# CodeQL default setup for every language in the repository (Python and the
# workflows themselves). Its "Analyze (...)" checks are required by the ruleset.
codeql=$(gh api "repos/$repo/code-scanning/default-setup" \
  --jq '"\(.state) \(.languages | sort | join(",")) \(.query_suite)"')
compare "CodeQL default setup" "$codeql" "configured actions,python default"
if [[ "$mode" == "apply" && "$codeql" != "configured actions,python default" ]]; then
  gh api -X PATCH "repos/$repo/code-scanning/default-setup" --silent \
    -f state=configured -f query_suite=default -f 'languages[]=actions' -f 'languages[]=python'
fi

if [[ "$mode" == "check" ]]; then
  exit "$drift"
fi
