# Security policy

## Supported versions

The project is pre-1.0. Only the latest release receives security fixes.

## Reporting

Do not attach transcripts, screenshots, prompts, tokens, or other sensitive
content to a public issue. Report the smallest synthetic reproducer possible to
the repository's private vulnerability-reporting channel. If private reporting
is unavailable, open a content-free issue asking the maintainers for a secure
contact method.

## Threat model

Agent histories may contain credentials, private source code, health data, or
other sensitive material. Sessionfold therefore makes no network calls,
does not display transcript content, refuses implicit deletion, uses explicit
paths for mutation, verifies reconstructed source hashes, and never overwrites
restore targets.

The local archive is not encrypted. Its permissions and backup policy are the
operator's responsibility. Content-addressed hashes can also reveal whether
two local archives contain identical payloads; do not share a store across
trust boundaries.
