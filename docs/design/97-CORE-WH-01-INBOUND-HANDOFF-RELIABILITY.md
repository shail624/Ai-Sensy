# CORE-WH-01 — Inbound webhook handoff reliability

## Scope and observed incident

The owner reported a WhatsApp text that showed delivered on the sending phone but never reached
the app. The same official API number later received an image and a fresh text. In the live test,
the fresh text reached the public webhook at 07:54:43 UTC and the inbound task applied it within
0.1 seconds. The earlier missing text had no matching ingress request in the available edge logs.
This evidence does **not** establish why Meta did not deliver that earlier request. An application
cannot reconstruct a message whose webhook it never received.

## Handoff invariant

For a signed, persisted Meta or QR inbound event, the webhook processing task must not mark the
event processed until the inbound-lane task has been accepted by the broker. A broker publish
failure leaves the event in `received`, with its attempt recorded, so retry can publish it. A
worker crash after publish can cause a second enqueue; the existing provider-message identity
and message-ledger checks make application idempotent. Broker operational errors are transient
processing failures, not poison data. Unknown/invalid events still go to the existing dead-letter
path. No schema, endpoint, queue topology or consent behaviour changes.

## Visibility and limits

For signed inbound messages with a provider timestamp at least 30 seconds older than ingress,
write a structured warning containing only rounded delay and connector type—never the sender,
message content, media or credentials. This distinguishes provider-to-ingress delay from local
queue processing. It is a diagnostic signal, not a guarantee of delivery or a synthetic message.
No automatic backfill is claimed for a webhook that the provider never posts.

## Acceptance evidence

- Inject a broker publish failure for a Meta message and a QR phone echo: both stay `received`.
- Retry each event: exactly one successful dispatch in the test, then `processed`.
- Existing webhook, idempotency, tenant-routing and full backend tests remain green.
- Public webhook signature check and the frontend contract remain unchanged.
