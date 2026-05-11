# Local B12 Submission Test Server

This server provides a local stand-in for:

```text
POST https://b12.io/apply/submission
```

It exposes:

```text
POST /apply/submission
```

The endpoint accepts a B12 application submission payload and validates that the request matches the exercise requirements:

- required JSON fields are present
- request body is valid UTF-8 JSON
- JSON body is compact and alphabetically sorted by key
- timestamp is a valid ISO 8601 timestamp
- `X-Signature-256` is present and matches the raw request body

For a valid request, the server prints the accepted submission and returns a success response with a local receipt.

For an invalid request, the server prints validation details and returns an error response explaining what failed.

