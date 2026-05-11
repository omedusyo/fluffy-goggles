#!/usr/bin/env bash
set -euo pipefail

base_url="${1:-http://localhost:8000}"
base_url="${base_url%/}"
endpoint="${base_url}/apply/submission"

body='{"action_run_link":"https://link-to-github-or-another-forge.example.com/your/repository/actions/runs/run_id","email":"you@example.com","name":"Your name","repository_link":"https://link-to-github-or-other-forge.example.com/your/repository","resume_link":"https://pdf-or-html-or-linkedin.example.com","timestamp":"2026-01-06T16:59:37.571Z"}'
signature="$(
  printf '%s' "$body" |
    openssl dgst -sha256 -hmac 'hello-there-from-b12' -hex |
    awk '{print "sha256="$2}'
)"

curl \
  --request POST \
  --header 'Content-Type: application/json; charset=utf-8' \
  --header "X-Signature-256: ${signature}" \
  --data-binary "$body" \
  "$endpoint"
