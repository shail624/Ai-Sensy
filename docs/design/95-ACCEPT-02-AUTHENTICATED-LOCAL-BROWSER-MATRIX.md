# ACCEPT-02 — Authenticated Local Browser Matrix

Date: 2026-09-21  
Status: accepted

## Scope

Validate the built product through an authenticated browser session against local MySQL and Redis,
using only repository-owned development fixtures. This is acceptance evidence, not a feature or
visual redesign milestone.

## Environment and data

- Disposable development database at migration head.
- Local MySQL 8 and Redis services.
- Local FastAPI and Vite processes.
- One fictional Owner plus the governed fixture set: 2 agents, 1 WhatsApp account, 2 phone
  numbers, 4 tags, 31 contacts, 30 conversations and 191 messages.

No real customer, provider or production credential was used.

## Route matrix

Authenticated checks covered Dashboard, Live Chat, Chat History, Contacts, Campaigns, Analytics,
Download Center, Automation, Tags and Developer Hub. Live Chat and Chat History also covered
selection from a populated list into the message-detail workspace.

Desktop checks used a 1440×900 viewport. Responsive checks used 390×844. Every checked mobile
route reported document width equal to viewport width. Contacts changed from a table into cards;
Live Chat and Chat History changed from split panes into list/detail drill-in; primary navigation
moved to the compact bottom rail.

Campaigns, Download Center and Developer Hub had no corresponding fixture records and displayed
their designed empty states with the correct next action. This is accepted as truthful state
coverage, not evidence of populated-row rendering.

## Findings

- No blocking authentication, routing, API-loading or responsive-layout defect was found.
- Direct reference-style guesses `/history` and `/developer` are not product routes. The real
  governed routes are `/chat-history` and `/operations/api`, and the visible navigation resolves
  correctly to them.
- The browser recorded a Vite hot-reload WebSocket warning in the local development transport.
  No application or API console error was observed; production build validation is independently
  green under ACCEPT-01.

## Decision

Accept the local authenticated browser matrix without product-code changes. Do not create aliases
for guessed routes and do not seed fake campaigns, export artifacts or API credentials merely to
make empty states look populated.

## Remaining external gates

- Deploy to the approved target host.
- Configure real WhatsApp/provider credentials and approved real data sources.
- Validate production monitoring, backup/restore and operational runbooks on that host.
- Complete owner-led UAT and launch approval.
