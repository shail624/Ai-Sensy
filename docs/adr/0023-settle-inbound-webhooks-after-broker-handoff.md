# ADR-0023 — Settle inbound webhooks after broker handoff

## Status

Accepted — 2026-09-24.

## Context

The persisted webhook event was marked `processed` before publishing its inbound task. If broker
publication failed or the worker died in that gap, task retry saw a settled event and skipped it.
The signed webhook was durable, but the customer message could still be absent from Live Chat.
This is a distinct local risk; it is not proven to explain a live message for which no webhook
request reached the edge.

## Decision

Publish the inbound task before committing `processed` for Meta messages and QR phone echoes.
Treat broker operational failures as transient. Retain the existing at-least-once queue and
idempotent message application rather than adding a parallel inbox model or migration. Emit a
privacy-safe warning for provider-to-ingress delay over 30 seconds.

## Consequences

Publication failure leaves the event retryable. A crash after publication may publish twice;
the existing provider-message deduplication makes that safe. The application still cannot recover
an inbound message Meta never sends to its callback URL; that requires provider-side diagnosis.
