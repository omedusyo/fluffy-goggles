#!/usr/bin/env python3
import hashlib
import hmac
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8000
PATH = "/apply/submission"
SIGNING_SECRET = b"hello-there-from-b12"
REQUIRED_KEYS = {
    "action_run_link",
    "email",
    "name",
    "repository_link",
    "resume_link",
    "timestamp",
}


def log_section(title, value):
    print(f"\n{title}")
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def json_response(handler, status, payload):
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def is_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_iso8601_timestamp(value):
    if not isinstance(value, str):
        return False

    normalized = value
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False

    return parsed.tzinfo is not None


def validate_submission(raw_body, headers):
    errors = []
    parsed = None

    try:
        text_body = raw_body.decode("utf-8")
    except UnicodeDecodeError as error:
        return None, [f"body is not valid UTF-8: {error}"]

    try:
        parsed = json.loads(text_body)
    except json.JSONDecodeError as error:
        return None, [f"body is not valid JSON: {error}"]

    if not isinstance(parsed, dict):
        errors.append("body must be a JSON object")
        return parsed, errors

    actual_keys = set(parsed)
    missing_keys = sorted(REQUIRED_KEYS - actual_keys)
    unexpected_keys = sorted(actual_keys - REQUIRED_KEYS)

    if missing_keys:
        errors.append(f"missing required keys: {missing_keys}")
    if unexpected_keys:
        errors.append(f"unexpected keys: {unexpected_keys}")

    canonical_body = json.dumps(
        parsed,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if raw_body != canonical_body:
        errors.append("body is not canonical JSON: expected compact UTF-8 JSON with sorted keys")

    for key in REQUIRED_KEYS:
        value = parsed.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{key} must be a non-empty string")

    if "timestamp" in parsed and not is_iso8601_timestamp(parsed["timestamp"]):
        errors.append("timestamp must be a timezone-aware ISO 8601 timestamp")

    for key in ("action_run_link", "repository_link", "resume_link"):
        if key in parsed and isinstance(parsed[key], str) and not is_url(parsed[key]):
            errors.append(f"{key} must be an http(s) URL")

    signature = headers.get("X-Signature-256")
    expected_digest = hmac.new(SIGNING_SECRET, raw_body, hashlib.sha256).hexdigest()
    expected_signature = f"sha256={expected_digest}"

    if not signature:
        errors.append("missing X-Signature-256 header")
    elif not hmac.compare_digest(signature, expected_signature):
        errors.append("X-Signature-256 does not match the raw request body")

    return parsed, errors


class B12MockHandler(BaseHTTPRequestHandler):
    server_version = "B12Mock/1.0"

    def do_POST(self):
        if self.path != PATH:
            json_response(self, 404, {"success": False, "errors": ["unknown endpoint"]})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            json_response(self, 400, {"success": False, "errors": ["invalid Content-Length"]})
            return

        raw_body = self.rfile.read(content_length)
        parsed, errors = validate_submission(raw_body, self.headers)

        print("\n--- Request received ---")
        print(f"Path: {self.path}")
        print(f"Body bytes: {len(raw_body)}")
        print(f"Signature: {self.headers.get('X-Signature-256')}")

        if parsed is not None:
            log_section("Parsed submission", parsed)

        if errors:
            log_section("Validation errors", errors)
            json_response(self, 400, {"success": False, "errors": errors})
            return

        receipt = "local-test-receipt"
        log_section("Validation result", {"correct": True, "receipt": receipt})
        log_section("Stored submission", {"receipt": receipt, "submission": parsed})
        json_response(self, 200, {"success": True, "receipt": receipt})

    def do_GET(self):
        json_response(self, 404, {"success": False, "errors": ["use POST /apply/submission"]})

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


def main():
    server = HTTPServer((HOST, PORT), B12MockHandler)
    print(f"Listening on http://{HOST}:{PORT}{PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
