#!/usr/bin/env python3
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REQUIRED_ENV = (
    "B12_SUBMISSION_URL",
    "B12_SIGNING_SECRET",
    "B12_NAME",
    "B12_EMAIL",
    "B12_RESUME_LINK",
    "B12_REPOSITORY_LINK",
)


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def github_action_run_link():
    server_url = os.environ.get("GITHUB_SERVER_URL")
    repository = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")

    if server_url and repository and run_id:
        return f"{server_url.rstrip('/')}/{repository}/actions/runs/{run_id}"

    return None


def current_timestamp():
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_payload():
    for name in REQUIRED_ENV:
        require_env(name)

    action_run_link = os.environ.get("B12_ACTION_RUN_LINK") or github_action_run_link()
    if not action_run_link:
        raise RuntimeError(
            "missing B12_ACTION_RUN_LINK, or GitHub Actions variables "
            "GITHUB_SERVER_URL, GITHUB_REPOSITORY, and GITHUB_RUN_ID"
        )

    return {
        "timestamp": current_timestamp(),
        "name": require_env("B12_NAME"),
        "email": require_env("B12_EMAIL"),
        "resume_link": require_env("B12_RESUME_LINK"),
        "repository_link": require_env("B12_REPOSITORY_LINK"),
        "action_run_link": action_run_link,
    }


def canonical_json_bytes(payload):
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def signature_header(body, secret):
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def post_submission(url, body, signature):
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Signature-256": signature,
        },
    )

    with urlopen(request, timeout=30) as response:
        response_body = response.read().decode("utf-8")
        return response.status, json.loads(response_body)


def main():
    try:
        submission_url = require_env("B12_SUBMISSION_URL")
        signing_secret = require_env("B12_SIGNING_SECRET")
        payload = build_payload()
        body = canonical_json_bytes(payload)
        signature = signature_header(body, signing_secret)
        status, response = post_submission(submission_url, body, signature)
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        print(f"submission failed with HTTP {error.code}", file=sys.stderr)
        print(error_body, file=sys.stderr)
        return 1
    except (URLError, RuntimeError, json.JSONDecodeError) as error:
        print(f"submission failed: {error}", file=sys.stderr)
        return 1

    if status != 200 or response.get("success") is not True:
        print(f"submission failed: unexpected response {response}", file=sys.stderr)
        return 1

    receipt = response.get("receipt")
    if not receipt:
        print(f"submission failed: response did not include a receipt {response}", file=sys.stderr)
        return 1

    print(f"receipt: {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
