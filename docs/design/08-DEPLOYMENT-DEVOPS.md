# Deployment & DevOps Architecture
### Self-Hosted WhatsApp Business Platform — Production Blueprint

| | |
|---|---|
| **Document** | 8 — Deployment & DevOps Architecture (production infrastructure blueprint) |
| **Version** | 1.2 — **FROZEN** (final additive pass: §56 Platform Portability Appendix) |
| **Date** | 2026-07-15 |
| **Status** | ✅ Frozen — record changes in `CHANGELOG.md`. §1–§41 = v1.0; §42–§55 added in the enhancement pass (v1.0 → v1.1). |
| **Owner / sole user** | Internal — **Vi Reactivation Team** (single-tenant, self-hosted, not SaaS) |
| **Preceded by** | Docs 1–7 (frozen; referenced only) |

> This is an **infrastructure and operational architecture blueprint** — **no code, no shell scripts, no
> docker-compose, no YAML, no Kubernetes manifests, no configuration files**. It describes *how the platform
> is deployed, operated, secured, monitored, backed up, recovered, scaled, and upgraded* for years of
> continuous operation with minimal downtime — and how it grows to multiple servers **without redesign**. It
> extends the frozen documents additively and references them for anything already specified (schema Doc 3,
> API Doc 4, UI Doc 5, async fabric Doc 6, channels Doc 7).
>
> **Reading convention:** every architectural section carries the standard block — **Purpose · Scope ·
> Architecture · Design Decisions · Alternatives Considered · Trade-offs · Failure Handling · Performance ·
> Scalability · Security · Future Extensibility · Cross References.** Deployment decisions are recorded as
> **DD1–DD32** (§37).

**Existing stack (context):** Ubuntu LTS · Docker · Docker Compose · Nginx · Redis · MySQL 8 · FastAPI ·
React · Celery · Prometheus · Grafana · Loki · Cloudflare · Meta Cloud API · Support Connector · Object
Storage.

---

## 1. Purpose & Objective

**Purpose.** Define the complete production deployment architecture for the platform so a small engineering
team can run it reliably, securely, and cost-effectively for the Vi Reactivation Team — and scale it later
without re-architecting.

**Scope.** Physical/logical topology, networking, containerization, edge (Cloudflare/Nginx/TLS), data tier
(MySQL/Redis/object storage), the async fabric (Celery, Doc 6) and Support Connector services (Doc 7) as
*deployed units*, monitoring/logging, secrets, backup, disaster recovery, high-availability readiness,
deployment/upgrade strategy, performance, hardening, capacity/cost planning, maintenance, governance, and the
decision records — **architecture only**.

**Architecture (objective shape).** Start as a **single well-provisioned Ubuntu LTS host** running the full
stack in Docker behind Cloudflare + Nginx, with **all state externalized** to MySQL, Redis, and object storage
so that services are **stateless and horizontally scalable**. Every component is chosen and configured so that
moving to **multiple servers** (dedicated data node, worker nodes, a load balancer) is an **additive** step,
not a redesign (§23 HA readiness; Doc 6 §16/§23).

**Design decisions:** single-node-first, multi-node-ready (DD1). **Alternatives considered:** day-one
Kubernetes cluster; managed cloud PaaS. **Trade-offs:** simplicity/cost now vs. building HA later (mitigated by
statelessness + externalized state). **Failure handling:** the whole document (esp. §22 DR). **Performance:**
§25. **Scalability:** §23/§27; Doc 6 §16. **Security:** §26. **Future extensibility:** the topology upgrades to
multi-server/K8s without app changes. **Cross-refs:** Docs 1–7.

---

## 2. Scope & Guiding Principles

**Purpose.** Fix the principles every later section obeys, so the blueprint is coherent.

| Principle | Meaning |
|---|---|
| **Self-hosted, single-tenant** | One deployment for the Vi Reactivation Team; no multi-tenancy, no public sign-up. |
| **Stateless services, externalized state** | App/workers/connector services hold no durable state; truth lives in MySQL, Redis, object storage — enabling scale-out and safe restarts (Doc 6 §16). |
| **Containerized everything** | Every service runs in Docker with pinned images, resource limits, health checks, and restart policies. |
| **Edge-protected origin** | The origin is never exposed directly; Cloudflare + Nginx front everything (§5/§9). |
| **Security by default** | Least privilege, secrets encrypted, firewalled zones, hardened host (§26). |
| **Observable & recoverable** | Full metrics/logs/alerts (§18/§19) and tested backup/restore (§21/§22). |
| **Zero-/low-downtime operations** | Rolling/blue-green deploys, graceful drains, health-gated cutovers (§24/§30). |
| **Scale without redesign** | Single-node → multi-node is additive; the async fabric and channel abstraction already support it (Doc 6, Doc 7). |
| **Cost-conscious** | Right-sized to actual number/connector count; capacity + cost planning drive provisioning (§27/§28). |

**Design decisions / alternatives / trade-offs / failure / performance / scalability / security / future /
cross-refs:** these principles are themselves DD-backed (§37); alternatives and trade-offs are captured per
section; they collectively reference Docs 1–7.

---

## 3. Infrastructure Overview

**Purpose.** Present the complete production topology — what runs where and how traffic and data flow.

**Scope.** The single-node production baseline (with the multi-node evolution shown in §23).

**Architecture.**
```mermaid
flowchart TB
  USER["Vi Reactivation Team (agents/admins, browser)"] -->|HTTPS| CF[Cloudflare: DNS · WAF · DDoS · TLS edge · cache]
  META[[Meta Cloud API]] -->|webhooks HTTPS| CF
  CF -->|HTTPS origin cert| NGINX[Nginx reverse proxy · TLS termination · static · SSE/WS · uploads]

  subgraph HOST["Ubuntu LTS host (Docker)"]
    NGINX --> FE[React static assets]
    NGINX --> API[FastAPI/uvicorn app containers]
    NGINX --> SSEGW[SSE/WebSocket gateway]
    API --> REDIS[(Redis: broker · cache · locks · rate)]
    API --> MYSQL[(MySQL 8: durable truth)]
    API --> OBJ[(Object storage: media · exports · backups)]
    subgraph WORKERS["Celery worker pools + Beat"]
      WSEND[send/campaign]
      WHOOK[webhook/inbound]
      WSUPP[Support Connector]
      WAI[AI]
      WJOBS[import/export/media]
      WMAINT[maint/cleanup/notif]
      BEAT[Beat scheduler]
    end
    REDIS <--> WORKERS
    WORKERS --> MYSQL
    WORKERS --> OBJ
    subgraph CONN["Support Connector services (Doc 7)"]
      CMGR[Connector Manager · Session · QR · Health]
      WSUPP <--> CMGR
    end
    WSEND -->|send| META
    CMGR <-->|per-connector session| EXTCH[[External channel via connector]]
    subgraph OBSV["Observability"]
      PROM[Prometheus] --> GRAF[Grafana]
      LOKI[Loki] --> GRAF
      ALERT[Alertmanager]
      PROM --> ALERT
    end
    WORKERS -. metrics/logs .-> OBSV
    API -. metrics/logs .-> OBSV
  end

  OBJ -. off-host backup .-> BKP[(Off-site backup target)]
  MYSQL -. dumps .-> BKP
```

**Design decisions.** A single Ubuntu host runs the whole stack in Docker behind Cloudflare+Nginx; all state is
externalized (DD1/DD2). **Alternatives considered:** managed cloud, K8s from day one, bare-metal without
containers. **Trade-offs:** one host is a single point of failure now — mitigated by tested DR (§22) and the
multi-node path (§23). **Failure handling:** §22. **Performance:** edge cache + local low-latency services
(§25). **Scalability:** externalized state → add worker nodes/data node/LB (§23; Doc 6 §16). **Security:**
edge-protected, firewalled, hardened (§5/§26). **Future extensibility:** topology evolves to multi-node/K8s
additively. **Cross-refs:** Doc 6 §16/§23, Doc 7 §6/§27.

---

## 4. Complete Server Layout & Component Inventory

**Purpose.** Enumerate every deployed component, its role, statefulness, and scaling unit — the "what runs
here" reference.

**Scope.** All containers/services on the production host (single-node baseline).

**Architecture (component inventory).**
| Component | Role | State | Scaling unit | Notes |
|---|---|---|---|---|
| **Cloudflare** (external) | DNS, WAF, DDoS, TLS edge, cache | — | managed | §9 |
| **Nginx** | Reverse proxy, TLS termination, static serving, SSE/WS, uploads | stateless | replicas behind LB (future) | §7 |
| **Frontend (React)** | Static SPA build served by Nginx | stateless | CDN/edge cacheable | §16 |
| **Backend (FastAPI)** | API app servers (ASGI) | stateless | container replicas | §15 |
| **SSE/WebSocket gateway** | Real-time push (Doc 4 §24) | ephemeral conn state | replicas (sticky/pub-sub) | §7 |
| **Celery workers** | Async fabric pools (Doc 6 §22) | stateless | per-pool replicas | §12 |
| **Celery Beat** | Scheduler (Doc 6 §10) | singleton (leader) | 1 + standby | §12 |
| **Support Connector services** | Connector Manager/Session/QR/Health (Doc 7) | session-affine | per-connector pool | §13 |
| **Redis** | Broker, cache, locks, rate, pub/sub | durable-ish (AOF) | role-split → cluster | §11 |
| **MySQL 8** | Durable truth (Doc 3) | **stateful** | primary + replicas | §10 |
| **Object storage** | Media, attachments, AI files, exports, backups | **stateful** | scale/managed | §14 |
| **Prometheus** | Metrics TSDB | stateful (local) | HA pair (future) | §18 |
| **Grafana** | Dashboards | config state | replicas | §18 |
| **Loki** | Log aggregation | stateful | scale storage | §19 |
| **Alertmanager** | Alert routing | config state | HA pair (future) | §18 |
| **Exporters** | node/mysql/redis/nginx exporters | stateless | per-target | §18 |
| **Backup agent** | Scheduled backups + verification (Doc 6 §41) | job state | 1 | §21 |
| **AI services** | AI worker pool + provider client (Doc 7 §17-context) | stateless | replicas, rate-bound | §17 |

**Statefulness classification (critical for scaling).** *Stateful:* MySQL, object storage, Redis (semi),
Prometheus/Loki storage. *Stateless (scale freely):* Nginx, FastAPI, all Celery worker pools, AI services,
Support Connector *compute* (session material is externalized to the encrypted store, Doc 7 §9). This split is
what makes horizontal scaling additive (§23).

**Design decisions.** Explicit stateful/stateless classification (DD3). **Alternatives considered:** co-locating
state in app containers. **Trade-offs:** externalized state adds I/O hops vs. scalability + safe restarts.
**Failure handling:** stateless components are cattle (restart/replace); stateful get backup+HA (§21/§22/§23).
**Performance:** local networking between containers is fast (§25). **Scalability:** each row's "scaling unit"
is independent (§23/§27). **Security:** each component isolated in Docker networks (§6/§26). **Future
extensibility:** components lift to dedicated nodes without change. **Cross-refs:** Doc 3, Doc 6 §22, Doc 7
§6/§9.

---

## 5. Network Architecture

**Purpose.** Define trust zones, traffic paths, and isolation so the origin is never directly exposed and
services communicate only as permitted.

**Scope.** External ingress/egress, DMZ vs private network, firewall zones, internal service networking, DNS,
and the Cloudflare/Nginx edge.

**Architecture.**
```mermaid
flowchart LR
  subgraph INET["Internet"]
    U[Agents/Admins]
    M[[Meta Cloud API]]
  end
  U -->|443| CF[Cloudflare edge]
  M -->|443 webhooks| CF
  CF -->|443 origin-cert, allowlisted| FW[Host firewall: only 443 from Cloudflare IPs]
  subgraph HOST["Ubuntu host"]
    subgraph DMZ["DMZ (edge net)"]
      NGINX[Nginx]
    end
    subgraph PRIV["Private app net (no ingress)"]
      API[FastAPI] 
      WORKERS[Celery pools]
      CONN[Connector services]
      AISVC[AI services]
    end
    subgraph DATA["Data net (most restricted)"]
      REDIS[(Redis)]
      MYSQL[(MySQL)]
      OBJ[(Object storage)]
    end
    subgraph OBS["Obs net"]
      PROM[Prometheus]; LOKI[Loki]; GRAF[Grafana]; ALERT[Alertmanager]
    end
    NGINX --> API
    NGINX --> GRAF
    API --> REDIS & MYSQL & OBJ
    WORKERS --> REDIS & MYSQL & OBJ
    CONN --> REDIS & MYSQL & OBJ
    AISVC --> REDIS & MYSQL
    WORKERS -->|egress 443| M
    CONN -->|egress via connector| EXT[[External channel]]
  end
```

- **Firewall zones (DD4):** the host firewall exposes **only 443**, and only from **Cloudflare IP ranges**
  (origin allowlisting). SSH is restricted (§26). Docker networks segment traffic into **DMZ** (Nginx),
  **private app** (API/workers/connector/AI — no inbound from internet), **data** (Redis/MySQL/object storage —
  reachable only from app/worker networks), and **observability**.
- **Internal communication:** service-to-service over Docker networks by name; the data net accepts connections
  only from the app net. No database/Redis port is published to the host's public interface.
- **External communication:** *inbound* only via Cloudflare→Nginx (443); *outbound* egress from workers to Meta
  (443) and from connector services via their adapters. Egress can be restricted to required destinations.
- **DNS:** managed at Cloudflare; the origin's real IP is hidden behind Cloudflare (origin protection, §9).

**Design decisions.** Zero direct origin exposure + zoned Docker networks (DD4). **Alternatives considered:**
flat network; VPN-only admin. **Trade-offs:** more network config vs. strong isolation. **Failure handling:**
if Cloudflare is unavailable, origin remains firewalled (§22 F: Cloudflare failure). **Performance:** local
Docker networking is low-latency. **Scalability:** the same zones map onto multi-node (data node, worker
nodes) via a private network/VPC. **Security:** least-exposure, origin allowlisting, segmented zones (§26).
**Future extensibility:** Zero-Trust/service-mesh ready (§9.6). **Cross-refs:** §9 Cloudflare, §26 hardening.

---

## 6. Docker Architecture

**Purpose.** Standardize how every service is containerized, isolated, networked, resourced, versioned, and
updated.

**Scope.** Containers, isolation, networking, volumes, restart policies, resource limits, image versioning,
rolling updates.

**Architecture.**
```mermaid
flowchart TB
  subgraph EDGE[edge-net]
    C_NGINX[nginx]
  end
  subgraph APP[app-net]
    C_API[api xN]; C_WSEND[worker-send xN]; C_WHOOK[worker-webhook xN]
    C_WSUPP[worker-support xN]; C_WAI[worker-ai xN]; C_WJOBS[worker-jobs xN]
    C_WMAINT[worker-maint]; C_BEAT[beat]; C_CONN[connector-mgr]; C_AISVC[ai-svc]
  end
  subgraph DATANET[data-net]
    C_REDIS[redis]; C_MYSQL[mysql]; C_OBJ[object-storage]
  end
  subgraph OBSNET[obs-net]
    C_PROM[prometheus]; C_LOKI[loki]; C_GRAF[grafana]; C_ALERT[alertmanager]
  end
  C_NGINX --- APP
  APP --- DATANET
  APP -. metrics/logs .- OBSNET
  V1[(named vol: mysql-data)] --- C_MYSQL
  V2[(named vol: redis-data)] --- C_REDIS
  V3[(named vol: object-data)] --- C_OBJ
  V4[(named vol: prometheus/loki)] --- OBSNET
```

| Concern | Design |
|---|---|
| **Containers** | One responsibility per container; the same **backend image** runs as API and as each worker pool (role by launch parameters), so API and workers are version-identical (DD5). |
| **Isolation** | Segmented Docker networks (§5); no container has more access than it needs; non-root container users; read-only root filesystems where possible. |
| **Networking** | Internal DNS by service name; only Nginx is reachable from the edge; data services never publish to the public host interface. |
| **Volumes** | **Named volumes** for all durable data (MySQL, Redis AOF, object storage, Prometheus/Loki); application containers are ephemeral (no local durable data). |
| **Restart policies** | `unless-stopped`/`on-failure` semantics so crashed containers auto-restart; combined with health checks. |
| **Resource limits** | CPU/memory limits per container (cgroups) — mapping Doc 6 §25's worker resource protection to deployment; prevents any container starving the host. |
| **Health checks** | Liveness/readiness per container (`/health`,`/ready`, Doc 4 §22) gate traffic and restarts. |
| **Image versioning** | Immutable, **pinned image tags** (semantic + build id); a deploy = new tag; `latest` never used in production (DD6). |
| **Rolling updates** | New container versions start, pass health checks, then old ones drain (graceful, Doc 6 §3.5) — no in-place mutation. |

**Design decisions.** Single backend image for API+workers (DD5); pinned immutable images (DD6). **Alternatives
considered:** separate images per worker type; mutable containers. **Trade-offs:** a slightly larger shared
image vs. guaranteed version parity + simpler ops. **Failure handling:** restart policies + health checks +
`acks_late` (Doc 6). **Performance:** resource limits protect neighbors; local networking. **Scalability:**
replicas per service; the model lifts to K8s unchanged (§23). **Security:** non-root, read-only FS, isolation,
minimal base images, image scanning (§26). **Future extensibility:** the same containers run under Compose now
and an orchestrator later. **Cross-refs:** Doc 6 §3.5/§25, §23/§24.

---

## 7. Nginx Architecture

**Purpose.** Define the reverse proxy/edge-on-host that terminates TLS, serves the SPA, proxies the API, and
handles real-time and uploads.

**Scope.** Reverse proxy, compression, caching, rate limiting, headers, WebSocket, SSE, large uploads, security
headers.

**Architecture / responsibilities.**
| Function | Design |
|---|---|
| **Reverse proxy** | Routes `/` → React static; `/api/*` → FastAPI; `/api/v1/events/stream` → SSE gateway; `/api/v1/ws` → WebSocket; `/webhooks/*` → API webhook endpoints. |
| **TLS termination** | Terminates the Cloudflare **origin certificate** (§8); HTTP→HTTPS redirect; modern TLS only. |
| **Compression** | gzip/brotli for text/JSON/JS/CSS above a threshold (Doc 4 §34). |
| **Caching** | Long-cache immutable static assets (hashed filenames); never cache API/auth responses; honor `Cache-Control` from the API. |
| **Rate limiting** | Coarse edge rate limits (per IP) as a first layer, complementing app-level limits (Doc 4 §9) and Cloudflare WAF (§9). |
| **Security headers** | HSTS, CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` (Doc 1 NFR-SEC-03). |
| **WebSocket / SSE** | Upgrade handling for WS; long-lived, unbuffered streaming for SSE (Doc 4 §24.1) with appropriate timeouts + keep-alive/HTTP-2. |
| **Large uploads** | Bounded body sizes for media/imports (Doc 4 §34) streamed to the API/object storage; upload timeouts tuned. |
| **Static SPA serving** | Serves the React build with SPA fallback routing. |

**Design decisions.** Nginx as the single on-host ingress + static server (DD7). **Alternatives considered:**
Traefik/Caddy; serving the SPA from a CDN only. **Trade-offs:** manual config vs. ubiquity/control; SPA served
locally now, CDN-cacheable later. **Failure handling:** Nginx health-checked and auto-restarted; a bad config
is caught pre-reload. **Performance:** compression, static caching, HTTP/2, keep-alive (§25). **Scalability:**
stateless — replicate behind a load balancer (§23). **Security:** headers, TLS, request limits, only-from-
Cloudflare (§5/§26). **Future extensibility:** the same role runs as an ingress controller under K8s.
**Cross-refs:** Doc 4 §9/§24.1/§34, Doc 1 NFR-SEC, §8/§9/§25.

---

## 8. SSL / TLS Architecture

**Purpose.** Ensure end-to-end encryption with a managed certificate lifecycle and strong TLS policy.

**Scope.** Certificate lifecycle, renewal, rotation, HSTS, TLS policy.

**Architecture.**
- **Two TLS legs (DD8):** **client→Cloudflare** uses a Cloudflare-managed edge certificate (auto-renewed);
  **Cloudflare→origin** uses a **Cloudflare Origin CA certificate** (long-lived) on Nginx, with **Full
  (strict)** origin validation so the edge trusts only our origin cert. This gives HTTPS everywhere without the
  origin managing public ACME.
- **Renewal:** edge certs auto-renew at Cloudflare; the origin cert is long-lived and rotated on a schedule
  (§ below).
- **Rotation:** origin cert rotation is a planned maintenance step (§29) — issue new origin cert, install,
  reload Nginx, retire old; no downtime.
- **HSTS:** enabled with a long max-age + preload (after validation) so browsers force HTTPS.
- **TLS policy:** TLS 1.2+ only (prefer 1.3), modern cipher suites, OCSP stapling, no legacy protocols.

**Design decisions.** Cloudflare edge cert + Origin CA cert with strict validation (DD8). **Alternatives
considered:** Let's Encrypt/ACME directly on the origin; self-signed origin with "Full" (non-strict).
**Trade-offs:** dependence on Cloudflare for edge certs vs. zero public ACME on a firewalled origin. **Failure
handling:** if Cloudflare edge cert lapses (rare/managed), origin still serves valid TLS; monitoring alerts on
cert expiry (§18). **Performance:** TLS 1.3 + session resumption + OCSP stapling. **Scalability:** certs are
host/edge concerns, independent of app scale. **Security:** strong policy, HSTS, strict origin validation
(§26). **Future extensibility:** mTLS between edge and origin (Cloudflare Authenticated Origin Pulls) as a
hardening upgrade. **Cross-refs:** §5/§9/§26, Doc 1 NFR-SEC-03.

---

## 9. Cloudflare Architecture

**Purpose.** Use Cloudflare as the security + performance edge — hiding the origin, filtering malicious traffic,
absorbing DDoS, and caching static content.

**Scope.** DNS, WAF, DDoS protection, caching strategy, origin protection, Zero-Trust readiness.

**Architecture.**
| Function | Design |
|---|---|
| **DNS** | Authoritative DNS at Cloudflare; proxied (orange-cloud) records so the origin IP is never exposed. |
| **WAF** | Managed rulesets + custom rules (block bad patterns, geo/rate rules); complements Nginx + app rate limits (Doc 4 §9). |
| **DDoS protection** | L3/L4/L7 mitigation at the edge, absorbing volumetric attacks before they reach the origin. |
| **Caching strategy** | Cache immutable static assets (hashed SPA files) at the edge; **bypass cache** for `/api/*`, auth, SSE, and webhooks (dynamic/real-time). |
| **Origin protection** | Origin firewall allows **only Cloudflare IP ranges** on 443 (§5); optional **Authenticated Origin Pulls** (mTLS) so the origin accepts only Cloudflare (DD9). |
| **Webhook ingress** | Meta webhooks traverse Cloudflare→Nginx→API; WAF tuned to allow Meta's callbacks while filtering abuse. |
| **Zero-Trust readiness** | Admin surfaces (Grafana, ops) can be placed behind **Cloudflare Access** (identity-gated) without app changes. |

**Design decisions.** Cloudflare as edge + origin allowlisting + optional mTLS (DD9). **Alternatives
considered:** self-managed WAF/DDoS; exposing the origin directly. **Trade-offs:** dependence on Cloudflare vs.
strong, low-effort protection. **Failure handling:** if Cloudflare is degraded, the origin stays firewalled
(fails closed) — availability trades against exposure; a documented break-glass path (temporarily allow direct)
exists for emergencies (§22). **Performance:** edge caching + global anycast reduce origin load/latency.
**Scalability:** the edge absorbs spikes independent of origin size. **Security:** origin hidden, WAF, DDoS,
Access-ready (§26). **Future extensibility:** full Zero-Trust, Cloudflare Tunnel (no inbound origin ports) as a
later hardening. **Cross-refs:** §5, §7, §8, §26; Doc 4 §9.

---

## 10. MySQL Architecture (deployment)

**Purpose.** Deploy MySQL 8 as the durable source of truth (Doc 3) with pooling, replication readiness, and a
tested backup/restore + partition/migration operational model.

**Scope.** Connection pooling, replication readiness, backup, restore, partition maintenance, migration.

**Architecture.**
| Concern | Design |
|---|---|
| **Engine/config** | MySQL 8 InnoDB, `utf8mb4` (Doc 3), tuned buffer pool (sized to RAM, §27), slow-query log on, binary logging on (for PITR + replication). |
| **Connection pooling** | App/worker pools per Doc 4 §34 (API 10–20/proc, Celery 5–10/proc), bounded ≤ MySQL `max_connections` with margin; a proxy (e.g., a connection multiplexer) can be added at scale. |
| **Replication ready** | Binlog + GTID enabled from day one so a **read replica** (analytics/reads) and failover standby can be added **without redesign** (DD10). |
| **Backup strategy** | Nightly logical/physical backups + **binlog** for point-in-time recovery; off-host copies; verified (§21). |
| **Restore strategy** | Documented cold/warm restore + PITR (§22); test-restores prove backups (Doc 6 §41/NFR-DR-04). |
| **Partition maintenance** | Scheduled jobs pre-create/drop monthly partitions on the high-volume tables (Doc 3 §14) via the maintenance queue (Doc 6 §10/§30). |
| **Migration strategy** | **Alembic** migrations (Doc 3), applied in a controlled order during deploys (§24.6): additive/backward-compatible first, expand→migrate→contract for breaking changes, zero-downtime. |

**Design decisions.** Replication-ready single primary now; binlog/GTID from day one (DD10). **Alternatives
considered:** managed DB; day-one primary/replica HA; PostgreSQL. **Trade-offs:** single primary is a SPOF now
vs. simplicity; mitigated by backups/DR and the ready replica path. **Failure handling:** §22 (DB failure →
restore/failover). **Performance:** buffer pool, indexes/partitioning (Doc 3), read replica offload (§25).
**Scalability:** replica(s), then sharding by org/time (Doc 3 §16). **Security:** least-privilege DB users,
network-restricted (data-net), encrypted backups, secrets-managed credentials (§20/§26). **Future
extensibility:** promote replica → HA cluster (§23). **Cross-refs:** Doc 3 §14/§16, Doc 6 §10/§41, §21/§22/§24.

---

## 11. Redis Architecture (deployment)

**Purpose.** Deploy Redis as the fast, rebuildable layer (broker/cache/locks/rate/pub-sub) per Doc 6 §12, with
the right persistence, memory policy, and recovery.

**Scope.** Persistence, memory policy, namespaces, monitoring, recovery, replication readiness.

**Architecture.**
| Concern | Design |
|---|---|
| **Role separation** | Logical separation now (broker vs cache vs rate/locks via DBs/prefixes, Doc 6 §12/§17); **physical split** into separate instances at scale, then Cluster (§23). |
| **Persistence** | **AOF** (append-only) for the broker/rate/lock instance so queued tasks + limiter state survive a restart; the cache instance may run RDB/none (rebuildable) (DD11). |
| **Memory policy** | Cache instance: `allkeys-lru` (evictable); broker/rate/lock instance: `noeviction` with headroom + alerts (Doc 6 §12.5). |
| **Namespaces** | Prefixed keys with TTLs per Doc 6 §12.3/§12.4. |
| **Monitoring** | Redis exporter → Prometheus: memory, hit rate, evictions, latency, connections (§18; Doc 6 §13). |
| **Recovery** | On loss, cache rebuilds from MySQL; broker/rate reload from AOF; pending work reconciled from durable checkpoints (Doc 6 §8.4/§41) — **no data loss** (Doc 6 NFR-DR-06). |
| **Replication ready** | Redis replica/Sentinel can be added for failover; the lock design supports a Redlock/cluster variant (Doc 6 §9.2) (DD12). |

**Design decisions.** AOF on the must-not-lose instance; eviction only on cache; replication-ready (DD11/DD12).
**Alternatives considered:** single Redis for everything; managed Redis; RabbitMQ broker (Doc 6 §45).
**Trade-offs:** more instances vs. blast-radius isolation. **Failure handling:** §22 (Redis failure → rebuild +
reconcile). **Performance:** in-memory O(1) hot paths (Doc 6 §14). **Scalability:** split → Cluster at ~50
numbers (Doc 6 §32). **Security:** network-restricted (data-net), auth/ACL, no public exposure (§26). **Future
extensibility:** Sentinel/Cluster; RabbitMQ swap (Doc 6 §16.4/§45). **Cross-refs:** Doc 6 §8/§9/§12/§13/§32/§41.

---

## 12. Celery Deployment

**Purpose.** Deploy the async fabric (Doc 6) as isolated, independently-scalable worker pools + the Beat
scheduler.

**Scope.** Worker pools, autoscaling, queue isolation, priority workers, Support Connector workers, campaign
workers, webhook workers, AI workers, Beat.

**Architecture (queue deployment).**
```mermaid
flowchart TB
  REDIS[(Redis broker - AOF)]
  BEAT[Beat scheduler - singleton + standby]
  subgraph POOLS["Worker pools (containers, per Doc 6 §22)"]
    P1[send-priority pool]:::p1
    P2[send-bulk pool]:::p2
    P3[webhook pool]:::p1
    P4[support-connector pool - session-affine]:::p1
    P5[ai pool]:::p3
    P6[jobs pool: import/export/media]:::p3
    P7[maint pool: cleanup/analytics/notif]:::p4
  end
  REDIS <--> P1 & P2 & P3 & P4 & P5 & P6 & P7
  BEAT --> REDIS
  P1 & P2 -->|443| META[[Meta Cloud API]]
  P4 <-->|session| EXT[[External channel via connector]]
  classDef p1 fill:#dbeafe; classDef p2 fill:#e0e7ff; classDef p3 fill:#ede9fe; classDef p4 fill:#f3f4f6;
```

| Aspect | Design |
|---|---|
| **Worker pools** | One container set per pool (Doc 6 §22); the shared backend image launched with the pool's queue set. |
| **Queue isolation** | Each pool consumes only its queues (Doc 6 §2) — no cross-starvation. |
| **Priority workers** | `send-priority` (agent/transactional) always outranks `send-bulk` (Doc 6 §3/§24). |
| **Support Connector workers** | **Session-affine** pool (one worker per connector session, lock-guarded) (Doc 7 §6/§9). |
| **Campaign workers** | `send-bulk`/control pool, rate-gated to Meta tiers (Doc 6 §5). |
| **Webhook workers** | Ingest/process pool, scales on lag (Doc 6 §11). |
| **AI workers** | Isolated, provider-rate-bound pool (Doc 6 §2 `ai`). |
| **Autoscaling** | Per-pool replicas scaled on **queue depth + age + throughput** signals (Doc 6 §30), limit-aware for sends; min replicas keep latency-sensitive pools warm. |
| **Beat scheduler** | Singleton with a **leader lock + standby** (Doc 6 §10.7) so schedules aren't double-fired and survive failover. |
| **Resource limits** | Per-pool cgroup limits + worker recycling (Doc 6 §25). |

**Design decisions.** Deploy Doc 6's logical pools as isolated containers (DD13); single Beat with standby
(DD14). **Alternatives considered:** one big worker; embedding Beat in a worker. **Trade-offs:** more containers
vs. isolation + independent scaling. **Failure handling:** `acks_late` redelivery, session re-pin, poison→DLQ
(Doc 6 §3/§7/§22). **Performance:** I/O-concurrency for sends, process-concurrency for parsing (Doc 6 §3.2).
**Scalability:** scale hot pools independently, across nodes (§23; Doc 6 §16/§32). **Security:** workers on the
private net; egress to Meta only where needed (§5). **Future extensibility:** new pools (new channels) deploy
identically (Doc 7 §29). **Cross-refs:** Doc 6 §2/§3/§5/§22/§25/§30, Doc 7 §6.

---

## 13. Support Connector Deployment

**Purpose.** Deploy the Support Connector services (Doc 7) as isolated, session-affine, independently-scalable
units that host unlimited connector instances.

**Scope.** Connector Manager service, Session Manager, QR Manager, Health Monitor, Connector Dashboard service,
connector scaling, isolation, session persistence, multi-number support.

**Architecture (connector services).**
```mermaid
flowchart TB
  subgraph CMGR["Connector Manager service (app-net)"]
    REG[Registry]; SESSMGR[Session Manager]; QRM[QR Manager]; HM[Health Monitor]
  end
  DASH[Connector Dashboard service - API/SSE]
  POOL[Support Connector worker pool - session-affine]
  SSTORE[(Encrypted session store - MySQL, Doc 7 §9)]
  REDIS[(Redis: locks · heartbeat · presence)]
  CMGR --> SSTORE
  CMGR --> REDIS
  POOL --> REDIS
  POOL <-->|per-connector session| EXT1[[Connector #1 · 9999999991]]
  POOL <-->|per-connector session| EXT2[[Connector #2 · 9999999992]]
  POOL <-->|per-connector session| EXT3[[Connector #3 · 9999999993]]
  DASH --> CMGR
  HM -. metrics .-> PROM[Prometheus]
```

| Service | Deployment design |
|---|---|
| **Connector Manager** | Stateless service holding the registry + orchestration; state in MySQL/Redis (Doc 7 §6). |
| **Session Manager** | Owns encrypted session lifecycle; sessions persisted in the encrypted store (Doc 7 §9), not in container memory beyond the active holder. |
| **QR Manager** | Orchestrates QR issuance/refresh; QR payloads are opaque + TTL'd, streamed to the dashboard via SSE (Doc 7 §8). |
| **Health Monitor** | Scores connector health, drives auto-recovery, emits metrics (Doc 7 §11). |
| **Connector Dashboard service** | Serves the per-connector operational view (Doc 7 §13.3) over the API/SSE. |
| **Support Connector worker pool** | **Session-affine** compute (one worker per connector session, lock-guarded, Doc 6 §22/§9); scales with connector count. |
| **Session persistence** | Encrypted at rest (Doc 7 §9); survives restarts/failover; re-pinned on worker/node loss (Doc 6 §23). |
| **Isolation** | Each connector is an independent lane; one connector's fault never affects others or Channel 1 (Doc 6 §21; Doc 7 §24). |
| **Multi-number** | Unlimited connectors, each its own session/QR/health/stream (Doc 7 §6.2). |

**Design decisions.** Deploy connector services as stateless orchestration + session-affine workers + encrypted
external session store (DD15). **Alternatives considered:** one connector process for all numbers; sessions in
container memory. **Trade-offs:** session affinity/coordination vs. isolation + no split-brain. **Failure
handling:** re-pin + auto-recovery (Doc 7 §10). **Performance:** per-connector streams; no cross-connector
contention. **Scalability:** scale the pool with connector count; distribute across nodes (Doc 6 §23; Doc 7
§27). **Security:** encrypted sessions, opaque QR, governed ops, private-net only (Doc 7 §27/§28; §26). **Future
extensibility:** new connector *types* or channels deploy identically (Doc 7 §29). **Cross-refs:** Doc 7
§6–§13/§27, Doc 6 §9/§21/§22/§23.

---

## 14. Object Storage

**Purpose.** Deploy durable object storage for all binary/large data — media, attachments, AI files, exports —
and as a backup target, keeping such data out of MySQL (Doc 3 §2).

**Scope.** Media, attachments, AI files, exports, retention, lifecycle policies.

**Architecture (media flow).**
```mermaid
flowchart LR
  IN[Inbound media - both channels] --> WMEDIA[media worker: fetch+validate+hash]
  WMEDIA --> DEDUP{SHA-256 exists?}
  DEDUP -->|no| PUT[(store bytes → object storage)]
  DEDUP -->|yes| SKIP[reuse existing key]
  PUT --> META[(metadata → MySQL media_assets)]
  SKIP --> META
  UI[Agent/UI] -->|signed URL| GET[(object storage read)]
  EXP[export/backup jobs] --> PUTX[(store artifacts)]
```

| Concern | Design |
|---|---|
| **Backend** | S3-compatible object storage — **self-hosted (e.g., MinIO)** on the data-net by default, or an external S3-compatible service (pluggable, Doc 3 FR-MED-06) (DD16). |
| **Content** | Media/attachments (Doc 7 §16), AI-generated/knowledge files, exports, and **backup artifacts** (§21). |
| **Access** | Only via **signed, expiring URLs** (Doc 4 §16); no public bucket; app/worker access via scoped credentials (§20). |
| **Dedup** | SHA-256 content addressing (Doc 3 §7.2/§3.11) avoids re-storage. |
| **Retention / lifecycle** | Lifecycle rules per data class (Doc 3 §15): exports expire (7–30d), inbound media retained per policy, backups per DR policy; orphaned media cleaned by the cleanup queue (Doc 6 §10). |
| **Durability** | Replicated/redundant storage; backups copied off-host (§21). |

**Design decisions.** S3-compatible, pluggable local/external, signed access, lifecycle-managed (DD16).
**Alternatives considered:** blobs in MySQL (rejected, Doc 3 §2); host filesystem only. **Trade-offs:** an extra
service vs. scalable, lifecycle-managed binary storage. **Failure handling:** redundancy + off-host backups
(§21/§22); media fetch retried (Doc 6 media queue). **Performance:** offloads bytes from DB; CDN-cacheable via
signed URLs; thumbnails/lazy-load (Doc 5). **Scalability:** scales independently; external S3 for very large
volumes. **Security:** private, signed access, encrypted at rest, scoped creds (§20/§26). **Future
extensibility:** swap local↔external without app change (Doc 3 FR-MED-06). **Cross-refs:** Doc 3 §2/§7.2/§15,
Doc 4 §16, Doc 7 §16, §21.

---

## 15. Backend (FastAPI) Deployment

**Purpose.** Deploy the API application tier as stateless, health-checked, horizontally-scalable ASGI servers.

**Scope.** App servers, process model, health, scaling, config.

**Architecture.**
- **Process model:** FastAPI served by an ASGI server (uvicorn workers under a supervisor/gunicorn) in
  containers; **stateless** (all state in MySQL/Redis/object storage).
- **Replicas:** multiple API containers behind Nginx; scale by adding replicas (§23).
- **Health:** `/health` (liveness) + `/ready` (dependency checks) gate traffic and restarts (Doc 4 §22).
- **Config:** environment-driven (§20/§31); no secrets in images; the **same image** runs as API and workers
  (§6, DD5).
- **Concurrency:** async endpoints; DB/Redis pools bounded (Doc 4 §34); long work offloaded to Celery (Doc 6).

**Design decisions.** Stateless ASGI replicas behind Nginx (DD17). **Alternatives considered:** a monolith with
in-process background threads (rejected — Doc 6 async fabric). **Trade-offs:** more containers vs. clean scaling.
**Failure handling:** health-gated restarts; a crashed replica is replaced; requests retried by clients.
**Performance:** async I/O, connection pooling, cache-first reads (§25). **Scalability:** add replicas; sits
behind an LB in multi-node (§23). **Security:** private-net, non-root, secrets via env/secret store (§20/§26).
**Future extensibility:** replicas lift to K8s pods unchanged. **Cross-refs:** Doc 4 §22/§34, Doc 6, §6/§23.

---

## 16. Frontend (React) Deployment

**Purpose.** Deploy the React SPA as static, versioned, cache-optimized assets.

**Scope.** Build artifacts, serving, caching, versioning.

**Architecture.**
- **Build:** the React/Vite app is built to **static assets** (hashed filenames) at release time; no runtime
  server needed.
- **Serving:** Nginx serves the SPA with fallback routing (§7); Cloudflare caches immutable assets at the edge
  (§9).
- **Caching/versioning:** content-hashed filenames enable **long-cache immutable** assets + instant cache-bust
  on deploy; `index.html` is short-cached so new builds are picked up.
- **Runtime config:** the SPA reads capabilities from `GET /api` (Doc 4 §33) so a build works against additive
  API changes.

**Design decisions.** Static, edge-cacheable, hash-versioned SPA (DD18). **Alternatives considered:** SSR/Next
server (unnecessary for an internal tool). **Trade-offs:** no SSR vs. simplicity + cacheability. **Failure
handling:** static assets are trivially redeployable/rollback-able (§24). **Performance:** edge cache,
compression, code-splitting (Doc 5 F15). **Scalability:** static scales infinitely via cache. **Security:** CSP
+ security headers (§7; Doc 1 NFR-SEC), no secrets in the bundle. **Future extensibility:** a CDN or a mobile
app consume the same API (Doc 4). **Cross-refs:** Doc 4 §33, Doc 5 F15, §7/§9.

---

## 17. AI Services Deployment

**Purpose.** Deploy the AI capability tier (Doc 5 B8, Doc 7 references) as an isolated, provider-abstracted,
rate/cost-bounded set of workers.

**Scope.** AI worker pool, provider integration, isolation, cost/rate control, human-approval enforcement.

**Architecture (AI services).**
```mermaid
flowchart LR
  API[API] -->|enqueue ai task| REDIS[(Redis broker)]
  REDIS --> WAI[AI worker pool - isolated, rate-bound]
  WAI -->|provider-abstracted| PROV[[AI provider - default Claude]]
  WAI --> DB[(MySQL: ai_conversations, usage)]
  WAI -->|draft requires human approval| API
  WAI -. tokens/cost metrics .-> PROM[Prometheus]
```

| Concern | Design |
|---|---|
| **Isolation** | Dedicated `ai` pool (Doc 6 §2/§22) so AI latency/cost never blocks sends. |
| **Provider abstraction** | Provider-agnostic client (default **latest Claude models**), swappable via config (Doc 1 NFR-EXT-04). |
| **Rate/cost control** | Per-org rate + token budgets; usage tracked (Doc 4 §32) and cost-analyzed (Doc 6 §37). |
| **Human approval** | AI never sends to customers autonomously; drafts return for human approval (Doc 1 FR-AI-10; Doc 5 F8). |
| **Data** | AI interactions/usage in MySQL (Doc 3 §10); KB files/embeddings via object storage + DB. |

**Design decisions.** Isolated, provider-abstracted AI pool with strict human-approval + budgets (DD19).
**Alternatives considered:** inline AI in the API (blocks requests); hard provider coupling. **Trade-offs:** an
extra pool vs. isolation + swappability. **Failure handling:** provider errors retry/bounded; guardrail refusals
surfaced; AI outage never affects messaging. **Performance:** streamed responses; off the hot path (§25).
**Scalability:** scale within provider limits + budget. **Security:** provider keys in the secret store (§20);
no PII beyond need; outputs audited. **Future extensibility:** new providers/models + the automation engine
(Doc 9) reuse this tier. **Cross-refs:** Doc 1 FR-AI-10/NFR-EXT-04, Doc 3 §10, Doc 4 §32, Doc 5 B8/F8, Doc 6
§37.

---

## 18. Monitoring Architecture

**Purpose.** Deploy full-stack monitoring so every layer is observable and alertable, realizing Doc 6 §13/§35's
observability design.

**Scope.** Prometheus, Grafana, Loki, Alertmanager, and the dashboard set.

**Architecture (monitoring).**
```mermaid
flowchart TB
  subgraph TARGETS["Exporters / instrumented services"]
    NODEEXP[node-exporter]; MYSQLEXP[mysql-exporter]; REDISEXP[redis-exporter]
    NGINXEXP[nginx-exporter]; APPM[app+worker /metrics]; CONNM[connector metrics]
  end
  PROM[Prometheus - scrape + TSDB] --> ALERT[Alertmanager - routing]
  TARGETS --> PROM
  LOKI[Loki - logs] --> GRAF[Grafana - dashboards]
  PROM --> GRAF
  ALERT --> NOTIFY[Email / webhook / in-app notifications]
```

| Component | Role |
|---|---|
| **Prometheus** | Scrapes exporters + app/worker `/metrics`; stores time-series; evaluates alert rules. |
| **Grafana** | Dashboards over Prometheus + Loki (single pane). |
| **Loki** | Aggregates structured logs (§19) for search + correlation with metrics. |
| **Alertmanager** | Deduplicates/groups/routes alerts to email/webhook/in-app (Doc 5 DS-16; Doc 6 §13.4). |
| **Dashboards** | **Health**, **Connector** (Doc 7 §13.3), **Queue** (Doc 6 §13), **Campaign**, **API** (latency/error), **Database**, **Redis** — plus SLA-compliance (Doc 6 §42). |

**Design decisions.** Prometheus/Grafana/Loki/Alertmanager as the self-hosted observability stack (DD20),
dual-sinked with the in-app monitor (Doc 6 §13.3). **Alternatives considered:** hosted APM (Datadog); ELK.
**Trade-offs:** self-hosting effort vs. no vendor lock-in/cost. **Failure handling:** monitoring loss never
affects processing; a monitoring-down alert is itself watched (dead-man's switch). **Performance:** scrape
intervals + recording rules keep it light. **Scalability:** Prometheus/Loki scale storage; HA pairs later.
**Security:** dashboards behind auth/Cloudflare Access (§9/§26). **Future extensibility:** remote-write/Thanos,
tracing (OpenTelemetry) additive. **Cross-refs:** Doc 6 §13/§35/§42, Doc 5 B11.8/B11.9/DS-16, Doc 7 §25.

---

## 19. Logging Strategy

**Purpose.** Standardize structured logging across all services with correlation, retention, and rotation —
feeding both Loki and the in-app system/audit surfaces (Doc 3 §11).

**Scope.** Application, queue, connector, audit, security, access, and error logs; retention; rotation.

**Architecture (logging).**
```mermaid
flowchart LR
  APP[API + workers] -->|structured JSON + request_id| STDOUT[container stdout]
  CONN[connector services] --> STDOUT
  NGINX[nginx access/error] --> STDOUT
  STDOUT --> SHIP[log shipper] --> LOKI[Loki]
  LOKI --> GRAF[Grafana search]
  APP -->|audit/system events| MYSQL[(MySQL: audit_logs/system_logs - Doc 3)]
```

| Log type | Source / destination | Notes |
|---|---|---|
| **Application logs** | API/workers → stdout → Loki | structured JSON + `request_id` correlation (Doc 6 §13.3) |
| **Queue logs** | worker task lifecycle → Loki + `job_metadata` | per-task trace |
| **Connector logs** | connector services → Loki | session/health events (no secrets) |
| **Audit logs** | → **MySQL `audit_logs`** (immutable, hash-chained, Doc 3 §11.2) | queryable in-app (Doc 5 B11.10) |
| **Security logs** | auth failures, WAF, fail2ban, SSH → Loki + alerts | §26 |
| **Access logs** | Nginx/Cloudflare → Loki | request-level |
| **Error logs** | exceptions → `error_logs` (Doc 3 §11.3) + Loki | fingerprinted (Doc 6 §35) |
| **Retention** | per class (Doc 3 §15; e.g., app/access 30–90d, audit 24–84mo) | |
| **Rotation** | container/Loki-managed size/time rotation; MySQL log tables partitioned/pruned (Doc 3 §14) | |

**Design decisions.** Structured JSON to stdout → Loki, with **durable audit/system logs in MySQL** (DD21).
**Alternatives considered:** files on host; ELK. **Trade-offs:** two sinks (ops logs vs. durable audit) — by
design (compliance). **Failure handling:** log-shipping loss never affects processing; audit writes are
alerted if they fail (Doc 6 §44). **Performance:** async, sampled where noisy. **Scalability:** Loki scales
storage; log tables partitioned. **Security:** **no secrets/PII in logs** (§20/§26); audit immutable.
**Future extensibility:** tracing correlation, log-based alerts. **Cross-refs:** Doc 3 §11/§14/§15, Doc 6
§13/§35/§44, Doc 5 B11.10.

---

## 20. Secrets Management

**Purpose.** Protect every secret the platform holds — with encryption at rest, least-privilege access, and
rotation.

**Scope.** API keys, Meta tokens, connector sessions, encryption keys, environment variables, key rotation.

**Architecture.**
| Secret | Handling |
|---|---|
| **Meta tokens** (system-user) | Encrypted at rest in MySQL (Doc 3 WABA `access_token_enc`); never returned by the API (Doc 4 §13.2); decrypted only in-memory when sending. |
| **Connector sessions** | Encrypted at rest (Doc 7 §9 `credentials_enc`); single-holder; rotated on replace. |
| **API keys** (platform's own) | Hashed at rest (Doc 3 `api_keys`); shown once (Doc 4 §11 B11.4). |
| **Encryption keys** | A master key (from a secret store / host KMS / env-injected at start) protects field-level encryption; never stored beside the data it protects. |
| **Provider keys** (AI, SMTP) | In the secret store / injected as env at container start; not in images. |
| **Environment variables** | Config via env; secret env values sourced from a secret store or an encrypted `.env` mounted at runtime (never committed). |
| **Key rotation** | Scheduled rotation for encryption keys, tokens, and API keys (§29); envelope encryption enables re-wrapping without mass re-encryption. |

**Design decisions.** Field-level encryption + hashed keys + externally-injected master key + rotation (DD22).
**Alternatives considered:** plaintext env; secrets in images (rejected). **Trade-offs:** key-management
overhead vs. strong protection. **Failure handling:** a lost master key is a recovery event (documented, §22);
rotation is zero-downtime (envelope). **Performance:** field crypto is cheap. **Scalability:** integrates with
a dedicated secret manager (Vault) later without app change. **Security:** least privilege, never-logged,
rotated, encrypted at rest (Doc 1 NFR-SEC-08). **Future extensibility:** Vault/cloud KMS drop-in. **Cross-refs:**
Doc 1 NFR-SEC-08, Doc 3 (encrypted fields), Doc 4 §11/§13, Doc 7 §9/§28.

---

## 21. Backup Strategy

**Purpose.** Guarantee recoverability of all durable data with scheduled, verified, off-host backups.

**Scope.** Database, Redis, object storage, configurations, connector sessions, recovery testing, retention,
verification.

**Architecture (backup).**
```mermaid
flowchart TB
  subgraph SRC["Sources"]
    MYSQL[(MySQL + binlog)]; REDIS[(Redis AOF/RDB)]; OBJ[(Object storage)]; CFG[Config + secrets metadata]; SESS[(Encrypted connector sessions)]
  end
  MYSQL -->|nightly full + binlog PITR| B[(Backup store - off-host/off-site)]
  REDIS -->|periodic snapshot| B
  OBJ -->|replicate/versioned| B
  CFG -->|versioned| B
  SESS -->|encrypted export| B
  B --> VERIFY[Test-restore + integrity check - Doc 6 §41]
  VERIFY -->|fail| ALERT[Alert]
  VERIFY -->|pass| OK[Backup marked verified - Doc 3 backups]
```

| Target | Method | Frequency |
|---|---|---|
| **Database** | Logical/physical dump + **binlog** for PITR | nightly full; binlog continuous |
| **Redis** | AOF + periodic RDB snapshot | periodic (broker/rate instance) |
| **Object storage** | Versioning + replication/copy off-host | continuous/versioned |
| **Configurations** | Versioned infra config/state (encrypted where sensitive) | on change |
| **Connector sessions** | Encrypted export (so a connector can be restored without full re-QR where valid) | with DB backup |
| **Recovery testing** | Periodic **test-restore** to a scratch instance + integrity check (Doc 6 §41/NFR-DR-04) | scheduled |
| **Retention** | Tiered (e.g., daily 14–30d, weekly 8–12w, monthly 12mo) | policy-driven (Doc 3 §15) |
| **Verification** | A backup is "good" only after a proven restore (recorded in Doc 3 `backups`) | every cycle |

**Design decisions.** Verified, off-host, PITR-capable backups across all durable stores (DD23). **Alternatives
considered:** DB-only backups; unverified backups (rejected — "untested backup = no backup"). **Trade-offs:**
storage + test-restore compute vs. guaranteed recoverability. **Failure handling:** failed backup/verify →
critical alert (§18). **Performance:** backups run off-peak via the maintenance queue (Doc 6 §10). **Scalability:**
backup store scales with data; incremental strategies at scale. **Security:** backups **encrypted at rest**,
access-controlled, off-site (§26). **Future extensibility:** cross-region replication. **Cross-refs:** Doc 1
NFR-DR, Doc 3 §15/`backups`, Doc 6 §10/§41, §22.

---

## 22. Disaster Recovery

**Purpose.** Define recovery objectives and procedures for every catastrophic failure, so the platform returns
to a known-correct state within target time with no data loss.

**Scope.** RTO/RPO, cold/warm restore, and node/disk/database/Redis/connector/Cloudflare/internet/power
failures.

**Architecture (DR workflow).**
```mermaid
flowchart TB
  D[Disaster detected] --> CLASSIFY{Failure class}
  CLASSIFY --> RESTOREDB[Restore MySQL from verified backup + PITR]
  RESTOREDB --> RECON[Reconcile counters + validate checkpoints - Doc 6 §41]
  RECON --> REDIS[Rebuild Redis + re-enqueue pending]
  REDIS --> CONN[Re-auth/re-pin connectors as needed - Doc 7 §10]
  CONN --> WH[Replay webhooks/DLQ idempotently - Doc 6 §7/§11]
  WH --> VERIFY[Integrity + audit verification]
  VERIFY --> RESUME[Resume production from checkpoints]
```

**Objectives.** **RPO ≈ 0** for accepted messages/durable state (nothing accepted is lost); **RTO ≤ 1h** for
the single-node baseline (faster with warm standby, §23). (Doc 1 NFR-DR; Doc 6 §41.)

| Failure | Behavior | Recovery |
|---|---|---|
| **Node failure (whole host)** | Outage of the single node | Restore stack on a replacement host from backups (**cold restore**); or promote a **warm standby** (§23) for near-zero RTO |
| **Disk failure** | Data volume loss | Restore volumes from backup; RAID/redundant storage reduces risk |
| **Database failure/corruption** | MySQL down/corrupt | Restore latest **verified** backup + PITR via binlog; reconcile (Doc 6 §41) |
| **Redis failure** | Broker/cache/rate loss | Rebuild from AOF + reconcile pending from checkpoints (Doc 6 §8.4) — no message loss |
| **Connector failure** | Session lost/invalid | Auto-reconnect or QR re-login; other connectors unaffected (Doc 7 §10) |
| **Cloudflare failure** | Edge degraded | Origin stays firewalled (fails closed); documented **break-glass** to temporarily allow direct/alt-edge access |
| **Internet failure** | No egress/ingress | Sends pause + queue; inbound (Meta) retried by Meta for 7 days; auto-resume on restore |
| **Power failure** | Host down | UPS + auto-restart on power return; `acks_late` + checkpoints resume cleanly |
| **Cold restore** | Rebuild from zero | Provision host → deploy pinned images → restore data → verify → resume |
| **Warm restore** | Standby ready | Promote standby (data replicated) → cut over → verify |

**Design decisions.** Verified-backup-driven DR with a documented, tested workflow + warm-standby path (DD24).
**Alternatives considered:** no DR plan; relying on host snapshots only. **Trade-offs:** backup/standby cost vs.
recoverability. **Failure handling:** *this section is the failure handling.* **Performance:** PITR + parallel
restore reduce RTO. **Scalability:** multi-node reduces single-host risk (§23). **Security:** encrypted backups,
governed recovery (Doc 6 §43). **Future extensibility:** cross-region DR. **Cross-refs:** Doc 1 NFR-DR, Doc 6
§8/§15/§41, Doc 7 §10, §21/§23.

---

## 23. High Availability Strategy (multi-server readiness)

**Purpose.** Show how the single-node baseline evolves to a highly-available multi-server deployment **without
redesign**.

**Scope.** Future multi-server topology, load-balancer readiness, stateless services, shared storage, leader
election, worker redistribution.

**Architecture (HA target).**
```mermaid
flowchart TB
  CF[Cloudflare] --> LB[Load Balancer]
  LB --> N1[App node 1: nginx+api+SSE]
  LB --> N2[App node 2: nginx+api+SSE]
  subgraph WN["Worker nodes (scale-out pools)"]
    W1[node: send/webhook]; W2[node: support-connector]; W3[node: ai/jobs]
  end
  subgraph DATA["Data tier (HA)"]
    MYSQLP[(MySQL primary)] --> MYSQLR[(replica/standby)]
    REDISP[(Redis primary)] --> REDISR[(replica/Sentinel)]
    OBJHA[(Object storage - redundant)]
  end
  N1 & N2 --> DATA
  WN --> DATA
  BEAT[Beat leader + standby]
```

| Element | Readiness (already true today) |
|---|---|
| **Stateless services** | API/workers/connector-compute hold no durable state (§4) → add replicas/nodes freely. |
| **Load balancer** | API/Nginx are stateless behind an LB; **SSE** uses a shared pub/sub bus (Doc 4 §24) so any node can serve any client (sticky or shared). |
| **Shared storage** | MySQL/Redis/object storage are already external, shared services (§10/§11/§14). |
| **Leader election** | Beat + singleton tasks use **leader locks** (Doc 6 §9/§10.7) → run a standby safely. |
| **Worker redistribution** | Broker distributes tasks to any node; node loss → `acks_late` redelivery + connector re-pin (Doc 6 §22/§23). |
| **Data-tier HA** | MySQL primary+replica/standby (§10), Redis replica/Sentinel (§11), redundant object storage (§14). |

**Design decisions.** Statelessness + externalized state + leader locks make HA **additive** (DD25). **Alternatives
considered:** building HA on day one; active-active DB (complex). **Trade-offs:** single-node cost/simplicity
now vs. deferred HA (bridged by DR §22). **Failure handling:** node loss tolerated once multi-node; until then,
DR covers it. **Performance:** horizontal scale-out (Doc 6 §16). **Scalability:** the core objective — grows to
100+ numbers (Doc 6 §32; §27). **Security:** private inter-node network/VPC (§5/§26). **Future extensibility:**
lift to **Kubernetes** (the container model already fits) for orchestration/autoscaling. **Cross-refs:** Doc 4
§24, Doc 6 §9/§16/§22/§23/§32, §4/§22.

---

## 24. Deployment Strategy

**Purpose.** Ship changes with minimal/zero downtime and safe rollback, including correct database-migration
ordering.

**Scope.** Blue-green, rolling update, canary readiness, rollback, health verification, migration order.

**Architecture (deployment).**
```mermaid
flowchart LR
  BUILD[Build + pin image tag + scan] --> MIGRATE[DB migrate: expand - backward-compatible]
  MIGRATE --> ROLL[Rolling/blue-green: start new, health-check, drain old - Doc 6 §3.5/§39]
  ROLL --> VERIFY[Health + smoke verification /ready]
  VERIFY -->|ok| CONTRACT[DB contract: remove old columns later release]
  VERIFY -->|fail| ROLLBACK[Rollback to previous pinned image]
```

| Aspect | Design |
|---|---|
| **Rolling update** | New containers start, pass `/ready`, then old ones drain gracefully (Doc 6 §3.5) — no downtime. |
| **Blue-green** | Two environments; cut traffic (via Nginx/LB) to the new (green) after verification; instant rollback to blue. |
| **Canary ready** | Route a fraction of traffic to a new version first (LB/Nginx) before full cutover — supported by statelessness. |
| **Rollback** | Redeploy the previous **pinned image** (§6); DB changes are backward-compatible so rollback is safe. |
| **Health verification** | `/health`+`/ready` gate cutover; smoke checks on key flows post-deploy. |
| **DB migration order (DD26)** | **Expand → migrate → contract**: additive/backward-compatible schema first (old code still works), deploy new code, backfill, then remove old columns in a later release — so app and DB are never incompatible. Task-payload versioning (Doc 6 §39) covers in-flight jobs. |

**Design decisions.** Rolling/blue-green + expand-migrate-contract (DD26). **Alternatives considered:** stop-the-
world deploys; in-place migrations. **Trade-offs:** multi-step migrations vs. zero downtime. **Failure
handling:** health-gated cutover + instant rollback. **Performance:** no downtime, no dip (warm replicas).
**Scalability:** same process across nodes (§23). **Security:** image scanning, signed/pinned images (§6/§26).
**Future extensibility:** CI/CD pipeline + canary automation. **Cross-refs:** Doc 3 (Alembic), Doc 6 §3.5/§39,
§6/§30.

---

## 25. Performance Optimization

**Purpose.** Meet the platform's performance targets (Doc 1 §5.1, Doc 5 F15, Doc 6 §14) at the infrastructure
layer.

**Scope.** Compression, caching, virtualization, connection pooling, HTTP/2, SSE optimization, media, database,
Redis.

**Architecture (levers).**
| Lever | Design |
|---|---|
| **Compression** | gzip/brotli at Nginx + Cloudflare for text/JSON/assets (§7/§9). |
| **Caching** | Edge cache for static; app cache (Redis) for dashboards/aggregates (stale-while-revalidate, Doc 5); ETag/304 (Doc 4 §34). |
| **Virtualization** | UI list/thread virtualization (Doc 5 F15) — infra ensures fast API + SSE to feed it. |
| **Connection pooling** | Bounded DB/Redis pools (§10/§11; Doc 4 §34). |
| **HTTP/2** | Nginx/Cloudflare HTTP/2 (multiplexing) for the SPA + SSE. |
| **SSE optimization** | Unbuffered, keep-alive, per-user connection caps, shared pub/sub bus (Doc 4 §24.1). |
| **Media optimization** | Dedup, thumbnails, lazy-load, signed URLs, CDN-cacheable (§14; Doc 5). |
| **Database optimization** | Indexes/partitioning (Doc 3), read replica offload (§10), query monitoring (§18). |
| **Redis optimization** | O(1) hot paths, role-split, memory policy (§11; Doc 6 §12). |

**Design decisions.** Optimize at every tier to hit frozen targets (DD27). **Alternatives considered:** premature
micro-optimization; ignoring edge caching. **Trade-offs:** cache freshness vs. speed (bounded TTLs). **Failure
handling:** caches are rebuildable; degrade to origin. **Performance:** *this is the section.* **Scalability:**
optimizations compound with scale-out. **Security:** never cache sensitive/auth responses (§7/§9). **Future
extensibility:** CDN, read replicas, tracing-guided tuning. **Cross-refs:** Doc 1 §5.1, Doc 4 §24.1/§34, Doc 5
F15, Doc 6 §12/§14.

---

## 26. Security Hardening

**Purpose.** Harden the host, containers, and network to a defensible production posture (Doc 1 §5.4/§7).

**Scope.** Linux, Docker, firewall, fail2ban, SSH, least privilege, container isolation, secrets, audit.

**Architecture (controls).**
| Layer | Hardening |
|---|---|
| **Linux (Ubuntu LTS)** | Minimal packages, automatic security updates, kernel hardening, disabled unused services, time sync, integrity monitoring. |
| **SSH** | Key-only auth (no passwords), non-default/limited access, restricted source IPs, no root login; ideally via bastion/Cloudflare Access. |
| **Firewall** | Default-deny; only 443 from Cloudflare IPs; internal ports never public (§5). |
| **fail2ban** | Ban brute-force sources (SSH, auth endpoints) — complements app rate limits + Cloudflare WAF. |
| **Docker** | Non-root containers, read-only root FS where possible, dropped capabilities, no `--privileged`, seccomp/AppArmor profiles, image scanning, pinned base images. |
| **Container isolation** | Segmented networks (§5); least inter-service access; resource limits (§6). |
| **Least privilege** | Scoped DB/Redis/storage credentials; RBAC in-app (Doc 1); governed ops (Doc 6 §43). |
| **Secrets** | Encrypted, injected, rotated, never logged (§20). |
| **Audit** | Immutable, hash-chained audit of privileged/ops actions (Doc 6 §44; Doc 3 §11.2). |
| **Edge** | WAF, DDoS, origin allowlisting, HSTS/CSP/headers (§7/§8/§9). |

**Design decisions.** Defense-in-depth across host/container/network/edge (DD28). **Alternatives considered:**
perimeter-only security. **Trade-offs:** hardening effort/ops friction vs. strong posture. **Failure handling:**
compromised component is isolated (network + least privilege); audit enables forensics. **Performance:** minimal
overhead. **Scalability:** the same baseline applies per node (image/config as code). **Security:** *this is the
section* — target Doc 1 OWASP ASVS L2. **Future extensibility:** CIS benchmarks, Zero-Trust, secret manager,
SIEM. **Cross-refs:** Doc 1 §5.4/§7, Doc 6 §43/§44, §5/§20.

---

## 27. Capacity Planning

**Purpose.** Provide **deployment sizing** for common scales, extending Doc 6 §32 with host-level resource
estimates. **Guidance only** — validate with load tests (Doc 10).

**Scope.** CPU, RAM, disk, network, Redis, MySQL, workers, storage — at 1/5/10/25/50/100 numbers (Channel 1)
plus Support Connectors (Channel 2 adds human-support-rate load, not bulk).

**Architecture (sizing).**
| Numbers | Deployment | vCPU | RAM | Disk (hot) | Network | Redis | MySQL | Workers (procs) | Object storage |
|---|---|---|---|---|---|---|---|---|---|
| **1** | Single node | 4–8 | 8–16 GB | 100–250 GB SSD | modest | 1 GB | single | 6–8 | small |
| **5** | Single node | 8–16 | 16–32 GB | 250–500 GB SSD | moderate | 2 GB | single | 10–12 | moderate |
| **10** | Single (start replica) | 16–24 | 32–48 GB | 0.5–1 TB SSD | moderate | 4 GB | + read replica | 14–18 | growing |
| **25** | 2–4 nodes | 24–48 | 48–96 GB | 1–2 TB SSD | high | 8 GB (split) | primary+replica | 24–32 | 100s GB |
| **50** | 5–8 nodes | 48–96 | 96–192 GB | 2–4 TB SSD | high | 16 GB (split/cluster) | primary+replicas | 40–56 | 100s GB–TB |
| **100** | 10–16 nodes (K8s) | 96–200+ | 192–384 GB | 4 TB+ SSD | very high | Redis Cluster | primary + replicas (+shard path) | 80–120 | TB+ |

- **Support Connectors:** each connector adds a **session-affine worker slot** + modest CPU/RAM/network for its
  stream; unlimited connectors scale the support pool (Doc 7 §27). Plan ~1 support worker slot per active
  connector plus headroom.
- **Disk** is dominated by the message ledger + status history + media; time-partitioning + retention keep the
  **hot** set bounded (Doc 3 §14/§15).

**Design decisions.** Host-level sizing derived from Doc 6 §32 workload sizing (DD29). **Alternatives
considered:** guesswork provisioning; fixed one-size host. **Trade-offs:** estimates vs. exact metering
(validate via load tests). **Failure handling:** headroom (60–80% target utilization) absorbs spikes.
**Performance:** right-sized buffer pool/Redis/workers (§10/§11/§12). **Scalability:** the table *is* the
scale path; single-node → multi-node/K8s. **Security:** unchanged by scale. **Future extensibility:** predictive
capacity (Doc 6 §36) refines these over time. **Cross-refs:** Doc 6 §32/§36, Doc 7 §27, Doc 3 §14/§15.

---

## 28. Cost Planning

**Purpose.** Give an architecture-level view of running costs so the deployment stays economical.

**Scope.** Monthly/yearly cost categories: Cloudflare, domain, server(s), storage, monitoring, backup, and
future scaling. (Meta **messaging** cost is separate and tracked by Doc 6 §37's cost engine — no reseller
markup.)

**Architecture (cost categories).**
| Category | Driver | Notes |
|---|---|---|
| **Server(s)** | vCPU/RAM/disk per §27 | dominant infra cost; grows stepwise with numbers/connectors |
| **Object storage** | media/exports/backups volume | grows with message/media volume + retention |
| **Cloudflare** | plan tier (WAF/Access features) | modest; free/Pro sufficient at small scale |
| **Domain / DNS** | annual domain | minimal |
| **Monitoring** | self-hosted (Prometheus/Grafana/Loki) → **compute/disk only** | no license cost |
| **Backup** | off-host/off-site backup storage | scales with retention |
| **Egress/network** | bandwidth (media, sends) | usually modest for internal use |
| **AI provider** | token usage (Doc 6 §37) | usage-based; budgeted/alertable |
| **Future scaling** | added nodes / managed data tier | stepwise as numbers grow (§27) |

**Design decisions.** Self-hosted stack keeps recurring cost to **infrastructure + Meta messaging only** — no
per-seat/per-message SaaS markup (DD30; Doc 2 advantage). **Alternatives considered:** SaaS BSP (recurring
subscription + markup). **Trade-offs:** self-hosting ops effort vs. far lower recurring cost + data ownership.
**Failure handling:** budget alerts (Doc 6 §37). **Performance:** cost-per-throughput improves with right-
sizing. **Scalability:** costs step with §27 tiers. **Security:** n/a. **Future extensibility:** cost forecasts
(Doc 6 §36/§37). **Cross-refs:** Doc 2, Doc 6 §36/§37, §27.

---

## 29. Maintenance Procedures

**Purpose.** Define the operational cadence that keeps the platform healthy.

**Scope.** Daily, weekly, monthly, quarterly, yearly procedures.

**Architecture (cadence).**
| Cadence | Procedures |
|---|---|
| **Daily** | Review health/alerts + connector health; verify backups ran; check queue backlog/DLQ; watch quality ratings (Doc 6 §28) + connector sessions. |
| **Weekly** | Review capacity/utilization + cost trends (Doc 6 §35/§37); audit-log spot check; dependency/security advisories; test one DLQ replay/runbook. |
| **Monthly** | **Test-restore** a backup (§21); partition maintenance verification (Doc 3 §14); rotate short-lived secrets; review performance vs SLOs (§33); patch OS/images. |
| **Quarterly** | Full DR drill (§22); origin cert rotation (§8); access review (RBAC/keys); capacity re-forecast (Doc 6 §36); load test if scale changed (Doc 10). |
| **Yearly** | Major version upgrades (§30); encryption-key rotation (§20); architecture review vs. roadmap; retention policy review (Doc 3 §15). |

**Design decisions.** A fixed, documented cadence (DD31) — reliability is a habit. **Alternatives considered:**
ad-hoc maintenance. **Trade-offs:** operator time vs. avoided incidents. **Failure handling:** each procedure
surfaces issues early; runbooks (Doc 11) guide remediation. **Performance:** partition/cleanup keep the DB
fast. **Scalability:** cadence unchanged with scale; automated where possible. **Security:** rotation, patching,
access reviews. **Future extensibility:** automate procedures into scheduled jobs (Doc 6 §10). **Cross-refs:**
Doc 3 §14/§15, Doc 6 §10/§28/§35/§36/§37, Doc 10, Doc 11, §8/§20/§21/§22.

---

## 30. Upgrade Strategy

**Purpose.** Upgrade every component safely with zero/low downtime and clean rollback.

**Scope.** Application, database, Redis, workers, Support Connector; zero-downtime; rollback.

**Architecture.**
| Component | Upgrade approach |
|---|---|
| **Application (API/frontend)** | Rolling/blue-green with pinned images (§24); health-gated; instant rollback. |
| **Database** | Expand→migrate→contract migrations (§24.6); online schema change tools for large tables; replica-first validation. |
| **Redis** | Rolling with replica/Sentinel promotion (§11); AOF preserves broker state. |
| **Workers** | Rolling with graceful drain (Doc 6 §3.5) + task-payload versioning (Doc 6 §39) → mixed versions coexist. |
| **Support Connector** | Rolling with **session re-pin** (Doc 6 §22/§23; Doc 7 §10); connectors stay connected or auto-recover; per-connector maintenance possible (Doc 6 §40). |
| **Zero downtime** | Achieved via statelessness, health-gated cutover, backward-compatible migrations, and `acks_late`. |
| **Rollback** | Previous pinned image + backward-compatible schema = safe revert (§24). |

**Design decisions.** Component-specific, zero-downtime upgrade playbooks reusing the deploy strategy (DD32).
**Alternatives considered:** big-bang upgrades. **Trade-offs:** staged upgrades vs. availability. **Failure
handling:** rollback + maintenance mode (Doc 6 §40) if needed. **Performance:** no dip (warm replicas).
**Scalability:** same across nodes. **Security:** patch cadence (§29). **Future extensibility:** CI/CD +
automated canary. **Cross-refs:** Doc 6 §3.5/§39/§40, Doc 7 §10, §24/§29.

---

## 31. Infrastructure Governance

**Purpose.** Standardize how infrastructure is versioned, named, allocated, and owned so it stays consistent and
maintainable for years.

**Scope.** Versioning, environment strategy, naming standards, ports, resource allocation, ownership.

**Architecture.**
| Aspect | Standard |
|---|---|
| **Versioning** | Immutable pinned image tags (semver + build id); infra config/state versioned in git; documents versioned per CHANGELOG policy. |
| **Naming standards** | Consistent service/container/network/volume names (`svc-role`, `net-zone`, `vol-purpose`); environment prefixes. |
| **Ports** | A fixed internal port map per service (documented); only 443 public; no ad-hoc port exposure. |
| **Resource allocation** | Documented CPU/RAM limits per service (§6/§27); changes reviewed. |
| **Ownership** | Clear ownership per subsystem (data, workers, connectors, edge, observability) mapped to on-call (§34). |
| **Change control** | Infra changes reviewed + audited; secrets governed (§20); ops actions governed (Doc 6 §43). |

**Design decisions.** Governance-as-standards (naming/ports/versioning/ownership). **Alternatives considered:**
ad-hoc conventions. **Trade-offs:** upfront discipline vs. long-term maintainability. **Failure handling:**
consistent naming/ownership speeds incident response. **Performance:** n/a. **Scalability:** standards scale to
many nodes. **Security:** change control + audit. **Future extensibility:** Infrastructure-as-Code (the
architecture is IaC-ready). **Cross-refs:** Doc 6 §43, §6/§20/§34, CHANGELOG policy.

---

## 32. Environment Strategy

**Purpose.** Define separated environments for safe development, validation, and production.

**Scope.** Development, staging, production; parity; data handling.

**Architecture.**
- **Environments:** **Development** (local/compose), **Staging** (prod-like, for migration/deploy/DR
  rehearsals and load tests), **Production** (the live single-tenant deployment).
- **Parity:** staging mirrors production topology (scaled down) so deploys/migrations/DR are validated before
  production (§24/§22).
- **Data handling:** production data is **never** copied to lower environments in raw form; staging uses
  synthetic/anonymized data (privacy, Doc 1 CMP-09).
- **Promotion:** the same pinned image promotes dev→staging→prod; config differs by environment (§20/§31).

**Design decisions.** Three-tier environments with prod-like staging + anonymized data. **Alternatives
considered:** prod-only. **Trade-offs:** extra environment cost vs. safe change validation. **Failure handling:**
staging catches issues pre-prod. **Performance:** staging load-tests validate capacity (§27; Doc 10).
**Scalability:** staging validates scale changes. **Security:** no raw prod data downstream. **Future
extensibility:** ephemeral preview environments. **Cross-refs:** Doc 1 CMP-09, Doc 10, §20/§22/§24/§31.

---

## 33. Observability, SLOs & Alerting Operations

**Purpose.** Operationalize the SLA/SLO objectives (Doc 6 §42) at the deployment layer — turning metrics into
alerts, on-call signals, and error budgets.

**Scope.** SLOs, alert routing, error budgets, dashboards-to-action.

**Architecture.**
- **SLOs:** per-queue/service objectives from Doc 6 §42 (availability/latency/RTO/RPO) are the alert thresholds
  (§18).
- **Alert routing:** Alertmanager groups/dedupes and routes by severity/owner to email/webhook/in-app (Doc 5
  DS-16); critical → on-call (§34).
- **Error budgets:** SLO breaches consume an error budget; sustained burn triggers a change freeze / reliability
  focus.
- **Golden signals:** latency, traffic, errors, saturation tracked per service; connector/queue/campaign/API/DB
  dashboards (§18).

**Design decisions.** SLO-driven alerting with error budgets. **Alternatives considered:** threshold-only
alerts without SLOs. **Trade-offs:** SLO upkeep vs. fair, actionable alerting. **Failure handling:** every SLO
breach has an owner + escalation (Doc 6 §42; §34). **Performance:** recording rules keep evaluation cheap.
**Scalability:** SLOs per new service/channel. **Security:** access-gated dashboards. **Future extensibility:**
tracing, anomaly detection. **Cross-refs:** Doc 6 §13/§42, Doc 5 DS-16, §18/§34.

---

## 34. Incident Management & On-Call

**Purpose.** Define how incidents are detected, responded to, and learned from (the ops complement to runbooks,
Doc 11).

**Scope.** Detection, severity, response, escalation, postmortems.

**Architecture.**
- **Detection:** alerts (§18/§33) + connector/queue health + user reports.
- **Severity & ownership:** severity tiers map to owners/escalation (Doc 6 §42); break-glass ops are governed +
  audited (Doc 6 §43/§44).
- **Response:** follow **runbooks** (Doc 11) — DLQ replay (Doc 6 §7), connector recovery (Doc 7 §10), DR (§22),
  maintenance mode (Doc 6 §40).
- **Communication:** internal status updates to the Vi Reactivation Team; maintenance banners (Doc 6 §40).
- **Postmortems:** blameless reviews; action items feed maintenance/upgrades (§29/§30).

**Design decisions.** Alert-driven incident process tied to governance/runbooks. **Alternatives considered:**
ad-hoc firefighting. **Trade-offs:** process overhead vs. faster, safer recovery. **Failure handling:** *this is
the section.* **Performance:** faster MTTR. **Scalability:** process scales with team. **Security:** governed +
audited actions (Doc 6 §43/§44). **Future extensibility:** on-call rotation tooling. **Cross-refs:** Doc 6
§40/§42/§43/§44, Doc 7 §10, Doc 11, §18/§22/§33.

---

## 35. Compliance & Data Residency

**Purpose.** Ensure the deployment upholds Meta policy and data-protection obligations for a single-tenant
internal platform.

**Scope.** Meta policy, opt-in/window (Channel 1), connector adapter compliance (Channel 2), data protection,
residency.

**Architecture.**
- **Meta compliance (Channel 1):** opt-in, 24-hour window, template categories, messaging limits, quality —
  enforced in the app/queue (Doc 1 §7; Doc 6 §5/§28) and never bypassed by deployment.
- **Connector compliance (Channel 2):** per Doc 7 §5.5/§28.3, each concrete adapter must comply with the terms
  of the channel it integrates; the platform depends only on the abstraction and can replace an adapter (e.g.,
  with an official Meta solution) as a local change. **This document specifies deployment of the abstraction,
  not any specific connector implementation.**
- **Data protection:** encryption at rest (secrets/sessions/backups), least privilege, audit, contact
  export/erasure + retention (Doc 1 CMP-09; Doc 3 §15).
- **Residency:** self-hosted on infrastructure the team controls; data location is a provisioning choice
  (region of the host + object storage); no third-party BSP holds the data.

**Design decisions.** Compliance enforced in-platform, deployment stays adapter-neutral. **Alternatives
considered:** relying on a BSP (loses data ownership). **Trade-offs:** self-hosting responsibility vs. control +
compliance. **Failure handling:** quality/limit protection (Doc 6 §28); governed ops. **Performance:** n/a.
**Scalability:** compliance model unchanged by scale. **Security:** §26/§20. **Future extensibility:** official
connector adapters; regional deployments. **Cross-refs:** Doc 1 §7/CMP, Doc 3 §15, Doc 6 §5/§28, Doc 7
§5.5/§28.

---

## 36. Data Lifecycle & Retention (operations)

**Purpose.** Operate the data-lifecycle policies (Doc 3 §15, Doc 1 FR-DL) at the deployment layer.

**Scope.** Archival, retention enforcement, cleanup, purge, privacy erasure — as scheduled operations.

**Architecture.**
- **Retention enforcement:** scheduled cleanup/maintenance jobs (Doc 6 §10) archive/purge per policy with a
  **dry-run** mode + audit (Doc 1 FR-DL-06).
- **Partitioning:** monthly partition drop prunes aged high-volume data cheaply (Doc 3 §14).
- **Media/exports:** object-storage lifecycle rules expire exports and orphaned media (§14).
- **Privacy erasure:** contact-level erasure on request, preserving anonymized aggregates (Doc 1 FR-DL-08).
- **Aggregates first:** analytics rollups computed **before** raw partitions are pruned (Doc 6 §35) so history
  survives.

**Design decisions.** Policy-driven, audited, aggregate-preserving lifecycle. **Alternatives considered:** keep
everything forever (cost/risk) or ad-hoc deletion. **Trade-offs:** retention cost vs. compliance/performance.
**Failure handling:** dry-run + audit prevent accidental loss. **Performance:** pruning keeps the hot set small.
**Scalability:** partition drop is O(1) regardless of volume. **Security:** governed + audited; erasure
supported. **Future extensibility:** tiered/cold storage. **Cross-refs:** Doc 1 FR-DL, Doc 3 §14/§15, Doc 6
§10/§35, §14.

---

## 37. Deployment Decision Records (DD1–DD32)

Each: **Decision · Why · Alternative · Why rejected · Benefits · Trade-offs · Migration strategy.**

| ID | Decision | Why | Alternative (rejected) | Benefits | Trade-offs | Migration |
|---|---|---|---|---|---|---|
| **DD1** | Single-node first, multi-node ready | Simplicity/cost now; internal scale | Day-one K8s/HA | fast to run, low cost | single SPOF now | add nodes/LB (§23) |
| **DD2** | Externalized state, stateless services | Enables scale-out + safe restarts | in-app state | horizontal scaling | extra I/O hops | already done |
| **DD3** | Explicit stateful/stateless classification | Drives scaling + backup | implicit | clear scale/DR plan | discipline | — |
| **DD4** | Zoned Docker nets + origin allowlisting | Least exposure | flat network | strong isolation | net config | VPC/mesh later |
| **DD5** | One backend image for API+workers | Version parity, simpler ops | image per worker | consistency | larger image | — |
| **DD6** | Pinned immutable image tags | Reproducible deploys/rollback | `latest`/mutable | safe rollback | tag hygiene | — |
| **DD7** | Nginx single on-host ingress + static | Ubiquity, control | Traefik/Caddy; CDN-only | one edge on host | manual config | ingress controller (K8s) |
| **DD8** | CF edge cert + Origin CA (strict) | HTTPS everywhere, no origin ACME | ACME on origin | managed certs | CF dependency | mTLS origin pulls |
| **DD9** | Cloudflare edge + origin allowlist (+mTLS) | Hide/protect origin | expose origin | WAF/DDoS/cache | CF dependency | Zero-Trust/Tunnel |
| **DD10** | Replication-ready MySQL (binlog/GTID day one) | Add replica/HA w/o redesign | plain single DB | PITR + replica path | binlog overhead | promote replica |
| **DD11** | Redis AOF on must-not-lose; LRU only on cache | No task/rate loss | one Redis, one policy | safe memory mgmt | more instances | split→cluster |
| **DD12** | Redis replication-ready | Failover path | single Redis | HA path | complexity later | Sentinel/Cluster |
| **DD13** | Deploy Doc 6 pools as isolated containers | Isolation + independent scale | one big worker | tail-latency safety | more containers | K8s pods |
| **DD14** | Single Beat + standby (leader lock) | No double-fire, survives failover | Beat in a worker | reliable scheduling | standby infra | — |
| **DD15** | Connector: stateless orchestration + session-affine workers + encrypted external sessions | Isolation + no split-brain | one shared client; in-memory sessions | per-connector isolation | affinity coordination | re-pin across nodes |
| **DD16** | S3-compatible storage, pluggable, signed access | Scalable binary storage | blobs in MySQL; host FS | lifecycle + dedup | extra service | local↔external swap |
| **DD17** | Stateless ASGI API replicas behind Nginx | Clean scaling | in-process background | scale-out | more containers | LB/K8s |
| **DD18** | Static hash-versioned SPA, edge-cached | Simplicity + cacheability | SSR server | infinite static scale | no SSR | CDN/mobile reuse |
| **DD19** | Isolated provider-abstracted AI pool + human approval + budgets | Safety + no blocking | inline AI; hard coupling | isolation, swappable | extra pool | new providers |
| **DD20** | Self-hosted Prometheus/Grafana/Loki/Alertmanager | No lock-in/cost | hosted APM; ELK | full control | self-host effort | remote-write/Thanos |
| **DD21** | JSON logs→Loki + durable audit in MySQL | Ops search + immutable compliance | files; ELK-only | correlation + audit | two sinks | tracing |
| **DD22** | Field encryption + hashed keys + external master key + rotation | Strong secret protection | plaintext env; secrets in images | encrypted at rest | key mgmt | Vault/KMS |
| **DD23** | Verified off-host PITR backups (all stores) | Real recoverability | DB-only/unverified | proven restore | storage/compute | cross-region |
| **DD24** | Verified-backup DR workflow + warm-standby path | Known-correct recovery | no DR plan | RPO≈0, bounded RTO | backup/standby cost | cross-region DR |
| **DD25** | Stateless + externalized state + leader locks → additive HA | Grow without redesign | day-one HA | deferred cost | HA later | LB + data-tier HA |
| **DD26** | Expand→migrate→contract; rolling/blue-green | Zero downtime, safe rollback | stop-the-world | no downtime | multi-step migrations | CI/CD canary |
| **DD27** | Optimize every tier to frozen targets | Meet SLOs | ignore edge/cache | fast UX | cache freshness | CDN/replicas |
| **DD28** | Defense-in-depth hardening | Defensible posture | perimeter-only | strong security | ops friction | CIS/SIEM/Zero-Trust |
| **DD29** | Host sizing derived from Doc 6 §32 | Right-size provisioning | guesswork | predictable cost | estimates | predictive capacity |
| **DD30** | Self-hosted → infra + Meta cost only | No SaaS markup, data ownership | BSP subscription | low recurring cost | ops responsibility | managed data tier |
| **DD31** | Fixed maintenance cadence | Reliability as habit | ad-hoc | fewer incidents | operator time | automate jobs |
| **DD32** | Component-specific zero-downtime upgrades | Safe evolution | big-bang upgrades | availability | staged effort | CI/CD |

---

## 38. Diagram Index

| Diagram | Location |
|---|---|
| Infrastructure topology | §3 |
| Network / trust zones | §5 |
| Docker container/network layout | §6 |
| Queue deployment | §12 |
| Support Connector services | §13 |
| Media flow | §14 |
| AI services | §17 |
| Monitoring | §18 |
| Logging | §19 |
| Backup | §21 |
| Disaster Recovery | §22 |
| High Availability (target) | §23 |
| Deployment (rolling/blue-green + migration) | §24 |

---

## 39. Cross References

| Document | Referenced for (not duplicated) |
|---|---|
| **Doc 1 — SRS** (frozen) | NFRs (performance/DR/security), compliance (§7/CMP), RBAC, data-lifecycle requirements |
| **Doc 2 — Feature Matrix** (frozen) | Self-hosted/no-markup cost advantage (§28) |
| **Doc 3 — Database Design** (frozen) | Schema, partitioning/retention (§14/§15), encrypted fields, `backups`, media model |
| **Doc 4 — API Design** (frozen) | Health/ready, SSE (§24.1), rate limits, operational recommendations (§34), media (§16) |
| **Doc 5 — UI/UX** (frozen) | Performance budgets (F15), notifications (DS-16), monitor/health/connector screens |
| **Doc 6 — Queue & Scheduler** (frozen v1.1) | Worker pools/affinity (§22), resource protection (§25), autoscaling (§30), observability (§13/§35), SLA matrix (§42), governance/audit (§43/§44), disaster replay (§41), broker choice (§45), capacity (§32), maintenance mode (§40) |
| **Doc 7 — Integrations & Channel Architecture** (frozen) | Support Connector services/sessions/health (§6–§13), unified media (§16), channel isolation (§21/§24), scaling (§27), compliance stance (§5.5/§28) |
| **Doc 9 — AI & Automation** (planned) | AI/automation services on this infra |
| **Doc 10 — Testing & QA** (planned) | Load/chaos/DR validation of this blueprint |
| **Doc 11 — Operations Runbook** (planned) | Step-by-step procedures for §22/§29/§30/§34 |

---

## 40. Glossary

| Term | Definition |
|---|---|
| **Origin** | The Ubuntu host running the stack behind Cloudflare; never exposed directly. |
| **DMZ / data-net / app-net / obs-net** | Segmented Docker networks by trust zone (§5). |
| **Origin allowlisting** | Firewall accepts 443 only from Cloudflare IPs (§5/§9). |
| **Origin CA cert** | Cloudflare-issued cert on Nginx for edge→origin TLS (§8). |
| **Pinned image** | An immutable, version-tagged container image (§6). |
| **Expand→migrate→contract** | Zero-downtime DB migration pattern (§24.6). |
| **Warm standby** | A near-ready replica environment for fast DR promotion (§22/§23). |
| **Session-affine worker** | A worker pinned to one connector session (§13; Doc 6 §22). |
| **PITR** | Point-in-time recovery via MySQL binlog (§10/§21). |
| **Error budget** | Allowed SLO breach before a reliability freeze (§33). |
| **Break-glass** | An emergency, governed, audited override procedure (§22; Doc 6 §43). |

---

## 41. Self-Review

Reviewed as **Enterprise Architect, DevOps Architect, Cloud Architect, Linux Administrator, Database
Administrator, Security Engineer, Backend Engineer, SRE Engineer, Performance Engineer, Compliance Reviewer**;
gaps closed before presenting:

- **Completeness (Enterprise/DevOps Architect):** 40 major sections cover the full mandated list — infra,
  server layout, network, Docker, Nginx, SSL, Cloudflare, MySQL, Redis, Celery, Support Connector, object
  storage, backend, frontend, AI, monitoring, logging, secrets, backup, DR, HA, deployment, performance,
  hardening, capacity, cost, maintenance, upgrades, governance, environments, SLOs, incidents, compliance,
  lifecycle — plus 32 DDs, 13 diagrams, cross-refs, glossary. ✔
- **Frozen-document integrity:** Docs 1–7 are only **referenced**, never modified or duplicated; new material is
  deployment-only and additive. ✔
- **Reliability/DR (SRE):** RPO≈0 for accepted data, bounded RTO, every failure class has a recovery path
  (§22), tested backups (§21), and a multi-node HA path (§23). ✔
- **Scalability (Cloud Architect):** stateless services + externalized state + leader locks make single→multi-
  node/K8s **additive**; host sizing for 1–100 numbers (§27) ties to Doc 6 §32. ✔
- **Security (Security Engineer):** edge-protected origin, zoned networks, hardened host/containers, encrypted
  secrets/sessions/backups, governed+audited ops, TLS everywhere — Doc 1 ASVS-L2 posture (§5/§8/§9/§20/§26). ✔
- **Data tier (DBA):** replication-ready MySQL with binlog/PITR, partition maintenance, expand-migrate-contract
  migrations, read-replica offload (§10/§24). ✔
- **Linux/host (Linux Admin):** minimal hardened Ubuntu, firewall/fail2ban/SSH policy, auto-updates, UPS/power
  handling (§26/§22). ✔
- **Performance (Performance Engineer):** compression/caching/HTTP-2/SSE/pooling/media/DB/Redis levers meet
  frozen targets (§25; Doc 1 §5.1, Doc 5 F15, Doc 6 §14). ✔
- **Operability (Backend/SRE):** zero-downtime deploys/upgrades, maintenance mode, monitoring/logging, SLOs +
  incident process + runbook references (§24/§30/§18/§19/§33/§34). ✔
- **Compliance (Compliance Reviewer):** Meta policy enforced in-platform (Channel 1); connector adapter
  compliance kept adapter-neutral (Channel 2, Doc 7); data protection, residency, retention, erasure (§35/§36;
  Doc 1 CMP/FR-DL). ✔
- **Architecture-only discipline:** no code/scripts/compose/YAML/manifests/config — topology, flows, diagrams,
  decisions, and operations only, matching the frozen documents' style and depth. ✔

**No architectural gaps identified.**

---

## 42. Environment Strategy (complete lifecycle)

**Purpose.** Define the full environment lifecycle that supports safe development, validation, and operation —
expanding the three-tier summary of §32 into the complete enterprise set.

**Scope.** Local Development, Shared Development, QA, UAT, Staging, Production, Hotfix, Sandbox, AI Testing, and
a Disaster-Recovery environment.

**Architecture.**
| Environment | Why it exists |
|---|---|
| **Local Development** | Each engineer runs the stack locally (Compose) for fast iteration; disposable data. |
| **Shared Development** | An integrated dev environment where feature branches meet; catches integration issues early. |
| **QA** | Dedicated functional testing (manual + automated, Doc 10) against a stable build; isolated data. |
| **UAT** | Business acceptance by the Vi Reactivation Team before release; prod-like, anonymized data. |
| **Staging** | Prod-mirror (scaled down) for deploy/migration/DR rehearsals + load tests (§24/§22/§27). |
| **Production** | The live single-tenant deployment. |
| **Hotfix** | An isolated fast-track lane to build/validate an emergency fix off the production release line (§46). |
| **Sandbox** | A throwaway environment for experiments/spikes and connector/QR trials without risk. |
| **AI Testing** | Isolated environment to evaluate AI prompts/models/costs (Doc 5 B8) without touching prod data or budgets. |
| **DR Environment** | The warm-standby/restore target used in DR drills and real recovery (§22/§23). |

**Deployment flow & promotion.**
```mermaid
flowchart LR
  LD[Local Dev] --> SD[Shared Dev] --> QA[QA] --> UAT[UAT] --> STG[Staging] --> PROD[Production]
  HF[Hotfix] --> STG
  HF -. emergency .-> PROD
  SBX[Sandbox] -. experiments .-> LD
  AIT[AI Testing] -. validated prompts .-> SD
  PROD -. replicate .-> DR[DR Environment]
```
- **Promotion rules (DD33):** the **same pinned image** promotes forward (dev→…→prod); nothing is rebuilt per
  environment. Each gate requires green tests + sign-off (QA → UAT → release approval, §43/§46). Hotfixes
  fast-track through Staging with mandatory post-hoc back-merge.
- **Configuration isolation:** environment-specific config via env/secret store (§20/§45); no shared config
  files across environments.
- **Database isolation:** each environment has its **own database**; production data is **never** copied raw to
  lower environments (anonymized/synthetic only — Doc 1 CMP-09).
- **Secrets isolation:** separate secret sets per environment; production secrets exist only in production
  (§20).

**Design decisions.** Full lifecycle with image-promotion + strict data/secret isolation (DD33). **Alternatives
considered:** fewer environments (prod+staging only). **Trade-offs:** more environments to run vs. safe,
staged validation. **Failure handling:** lower environments catch defects pre-prod. **Performance:** staging
load-tests validate capacity (§27). **Scalability:** environments scale down from prod topology. **Security:**
no raw prod data downstream; isolated secrets. **Future extensibility:** ephemeral preview environments per
PR. **Cross-refs:** §20/§22/§24/§27/§32/§43/§45/§46; Doc 1 CMP-09, Doc 10.

---

## 43. CI/CD Architecture

**Purpose.** Define the automated path from commit to production — building, scanning, testing, promoting, and
(if needed) rolling back — **architecture only, no pipeline YAML**.

**Scope.** Git flow, branch strategy, PR policy, build pipeline, static analysis, security/dependency/image
scans, unit/integration tests, artifact repository, release promotion, production approval, rollback trigger.

**Architecture (pipeline).**
```mermaid
flowchart LR
  DEVB[Feature branch] -->|PR + review| MAIN[main - protected]
  MAIN --> BUILD[Build backend+frontend images]
  BUILD --> SAST[Static analysis / lint / type-check]
  SAST --> DEPSCAN[Dependency scan]
  DEPSCAN --> IMGSCAN[Docker image scan]
  IMGSCAN --> UT[Unit tests]
  UT --> IT[Integration tests]
  IT --> ART[(Artifact repo - pinned image tags)]
  ART --> STG[Deploy to Staging]
  STG --> VER[Smoke + health verification]
  VER -->|manual approval| PROD[Promote to Production]
  VER -->|fail| STOP[Block release]
  PROD -->|health fail| RB[Rollback trigger → previous pinned image]
```

| Stage | Design |
|---|---|
| **Git flow / branch strategy** | Trunk-based with short-lived feature branches off a protected `main`; release tags cut from `main` (§46); `hotfix/*` branches for emergencies. |
| **PR policy** | Mandatory review + green checks + no direct pushes to `main`; conventional commits; linked to a work item. |
| **Build pipeline** | Reproducible builds → **pinned image tags** (§6/DD6); frontend static build (§16). |
| **Static analysis** | Lint + type-check (TS/Python) + code-quality gates. |
| **Security scan (SAST)** | Static app security testing on the codebase. |
| **Dependency scan** | Known-vulnerability scan of dependencies (§49). |
| **Docker image scan** | Vulnerability scan of built images before promotion (§26). |
| **Unit tests / Integration tests** | Gate promotion (Doc 10); coverage thresholds. |
| **Artifact repository** | Immutable image registry (versioned, retained); source of deploys. |
| **Release promotion** | Same artifact promoted dev→staging→prod (§42); no rebuilds. |
| **Production approval** | **Manual approval gate** before prod (governed, Doc 6 §43). |
| **Rollback trigger** | Health/smoke failure post-deploy → automatic/one-click rollback to the previous pinned image (§24). |

**Design decisions.** Scan-and-test-gated, artifact-promotion CI/CD with a manual prod gate + rollback (DD34).
**Alternatives considered:** manual builds/deploys; auto-deploy to prod without approval. **Trade-offs:**
pipeline maintenance vs. safe, repeatable releases. **Failure handling:** any red gate blocks; rollback path
defined. **Performance:** caching + parallel stages keep pipelines fast. **Scalability:** the same pipeline
serves multi-node/K8s deploys. **Security:** SAST + dependency + image scans + protected branches + approval.
**Future extensibility:** canary automation, GitOps. **Cross-refs:** §6/§16/§24/§42/§46/§49; Doc 6 §43, Doc 10.

---

## 44. Infrastructure Inventory

**Purpose.** Provide a complete, authoritative inventory of what exists in the deployment — the operational
"single source of truth" reference (values are illustrative/logical; real values live in the secret store and
config, never in this document).

**Scope.** Servers, containers, ports, volumes, networks, certificates, domains, DNS, storage, secrets,
scheduled jobs, monitoring components.

**Architecture (inventories).**

**Servers / nodes (single-node baseline; multi-node per §23)**
| Node | Role | Sizing ref |
|---|---|---|
| `host-prod-1` | Full stack (edge, app, workers, data, obs) | §27 |
| (future) `data-1`, `worker-N`, `lb-1` | Split tiers | §23 |

**Containers**
| Container | Role | Net |
|---|---|---|
| `nginx` | reverse proxy/TLS/static | edge |
| `api` (×N) | FastAPI | app |
| `worker-send/webhook/support/ai/jobs/maint` | Celery pools (Doc 6 §22) | app |
| `beat` | scheduler | app |
| `connector-mgr` | Connector Manager (Doc 7) | app |
| `ai-svc` | AI services | app |
| `redis` | broker/cache/locks | data |
| `mysql` | database | data |
| `object-storage` | S3-compatible | data |
| `prometheus/grafana/loki/alertmanager` | observability | obs |
| `*-exporter` | metrics exporters | obs |

**Ports (logical; only 443 public)**
| Service | Internal port | Public? |
|---|---|---|
| Nginx | 80→443 | **yes (via Cloudflare)** |
| API (ASGI) | app-only | no |
| Redis | 6379 | no |
| MySQL | 3306 | no |
| Object storage | 9000/9001 | no |
| Prometheus/Grafana/Loki/Alertmanager | 9090/3000/3100/9093 | no (admin via Access) |
| Exporters | 9100/9104/9121/9113 | no |

**Volumes** — `vol-mysql-data`, `vol-redis-data`, `vol-object-data`, `vol-prometheus`, `vol-loki`,
`vol-grafana` (named, backed up per §21).
**Networks** — `net-edge`, `net-app`, `net-data`, `net-obs` (§5/§6).
**Certificates** — Cloudflare edge cert (managed), Cloudflare **Origin CA** cert on Nginx (§8), internal TLS
(future mesh).
**Domains / DNS** — primary app domain + webhook host, DNS at Cloudflare (proxied), origin IP hidden (§9).
**Storage** — object storage buckets: `media`, `exports`, `ai`, `backups` (lifecycle-managed, §14).
**Secrets (types only)** — Meta token, connector session keys, master encryption key, API-key hashes, AI
provider key, SMTP creds, DB/Redis creds, object-storage creds, Origin CA key (§20).
**Scheduled jobs (Beat, Doc 6 §10)** — partition maintenance, backups+verify, analytics/cost rollups, retention
cleanup, template sync, number/connector health refresh, DLQ-age alerts, counter reconciliation, recurring-
campaign scan.
**Monitoring components** — Prometheus, Grafana, Loki, Alertmanager, node/mysql/redis/nginx exporters, app
`/metrics`, uptime/blackbox probe (§18).

**Design decisions.** A living inventory as the ops source of truth (values externalized). **Alternatives
considered:** tribal knowledge. **Trade-offs:** upkeep vs. clarity. **Failure handling:** inventory speeds
incident response (§34). **Performance:** n/a. **Scalability:** rows added per node/service. **Security:**
secrets listed by **type only**, never value (§20). **Future extensibility:** generated from IaC.
**Cross-refs:** §5/§6/§8/§9/§14/§18/§20/§21/§23/§27; Doc 6 §10/§22, Doc 7.

## 45. Configuration Management

**Purpose.** Define a clear configuration hierarchy so behavior is predictable, environment-isolated, and
changeable without code.

**Scope.** Configuration hierarchy, environment variables, feature flags, runtime configuration, tenant
configuration (future, disabled), connector configuration, AI configuration, backup configuration, logging
configuration, versioning.

**Architecture (configuration hierarchy — highest precedence last).**
1. **Build-time defaults** (safe defaults baked into the image).
2. **Environment variables** (per environment; secrets injected from the secret store, §20).
3. **Runtime configuration** (DB-backed `settings`, Doc 3 §11.5) — changeable without redeploy.
4. **Feature flags** (`feature_flags`, Doc 3 §11.8) — enable/disable/rollout capabilities dark.
5. **Per-scope overrides** (org/user settings, Doc 3) — highest precedence.

| Config domain | Where | Notes |
|---|---|---|
| **Environment variables** | env/secret store | connection strings, keys, mode |
| **Feature flags** | DB (`feature_flags`) | ship dark, progressive rollout (Doc 5 F10 uses this) |
| **Runtime configuration** | DB (`settings`) | org/security/notification/retention config (Doc 5 B11.11) |
| **Tenant configuration (future, disabled)** | `organization_id` scoping (Doc 3) | single-tenant now; multi-workspace-ready, **flag OFF** |
| **Connector configuration** | Connector registry (Doc 7 §6) | per-connector settings/assignment/pacing |
| **AI configuration** | settings + provider config | model/provider/budgets (Doc 6 §37; §17) |
| **Backup configuration** | settings | schedule/retention/targets (§21) |
| **Logging configuration** | env + settings | levels, retention (§19) |
| **Versioning** | config versioned in git; DB settings audited | changes tracked (Doc 6 §44) |

**Design decisions.** Layered precedence with **DB-backed runtime config + feature flags** so most changes need
no redeploy (DD35). **Alternatives considered:** all-static config files (redeploy for every change).
**Trade-offs:** a config surface to govern vs. operational agility. **Failure handling:** invalid config
rejected/validated; safe defaults. **Performance:** config cached (Redis). **Scalability:** per-scope overrides
scale to future multi-workspace. **Security:** secrets never in flags/settings; sensitive settings encrypted
(§20). **Future extensibility:** tenant config activates by flipping the flag — no redesign. **Cross-refs:**
Doc 3 §11.5/§11.8, Doc 5 F10/B11.11, Doc 6 §37/§44, §17/§19/§20/§21.

---

## 46. Release Management

**Purpose.** Define the release lifecycle and versioning so changes ship predictably with clear compatibility
guarantees.

**Scope.** Development → Testing → Release Candidate → Production → Emergency Hotfix → Rollback → Patch → LTS;
version numbering; compatibility rules.

**Architecture (release lifecycle).**
```mermaid
flowchart LR
  DEV[Development] --> TEST[Testing/QA] --> RC[Release Candidate - UAT/Staging] --> PROD[Production]
  PROD --> PATCH[Patch]
  PROD --> HF[Emergency Hotfix]
  HF --> PROD
  PROD -. issue .-> RB[Rollback]
  PROD --> LTS[LTS line - long-term support]
```
| Stage | Meaning |
|---|---|
| **Development** | Feature work merged to `main`. |
| **Testing/QA** | Automated + manual validation (Doc 10). |
| **Release Candidate** | Frozen build in UAT/Staging awaiting sign-off. |
| **Production** | Promoted RC (manual approval, §43). |
| **Emergency Hotfix** | Fast-track fix off the release line (§42 hotfix env). |
| **Rollback** | Revert to previous pinned image (§24). |
| **Patch** | Backward-compatible fix release. |
| **LTS** | A designated stable line receiving security/critical patches for an extended window. |

- **Version numbering (DD36):** **SemVer** `MAJOR.MINOR.PATCH` for the application; the API has its own URI
  version (`/api/v1`, Doc 4 §26); task payloads are versioned (Doc 6 §39); design docs version per CHANGELOG.
- **Compatibility rules:** minor/patch are backward-compatible; API breaking changes → new major API version
  (parallel-run, Doc 4 §26); DB via expand→migrate→contract (§24.6); mixed worker versions tolerated (Doc 6
  §39).

**Design decisions.** SemVer + LTS + compatibility guarantees aligned with API/task versioning (DD36).
**Alternatives considered:** ad-hoc versioning. **Trade-offs:** release discipline vs. predictability.
**Failure handling:** rollback + hotfix lanes. **Performance:** n/a. **Scalability:** unchanged. **Security:**
LTS security patching. **Future extensibility:** automated release notes/changelog. **Cross-refs:** Doc 4 §26,
Doc 6 §39, Doc 10, §24/§42/§43, CHANGELOG policy.

---

## 47. Business Continuity Planning

**Purpose.** Keep the business operating through outages — defining degraded/manual modes and recovery
priorities so the Vi Reactivation Team can continue working when a dependency fails.

**Scope.** Continuity strategy, operational continuity, manual mode, Meta outage, Support Connector outage,
internet/Cloudflare/power outages, human error, recovery priority.

**Architecture (continuity modes).**
| Scenario | Continuity behavior |
|---|---|
| **Meta (Channel 1) outage** | Campaigns/sends **pause + queue** (breaker, Doc 6 §15 F4); **Channel 2 (Support Connector) keeps working** for live support — dual-channel is itself a continuity feature. |
| **Support Connector outage** | Affected connector's lane pauses; **other connectors + Channel 1 unaffected** (Doc 7 §24); auto-recovery (Doc 7 §10). |
| **Internet outage** | Inbound retried by Meta (7 days) + connectors reconnect on restore; outbound queued; **manual mode** notice to agents. |
| **Cloudflare outage** | Origin firewalled (fails closed); documented **break-glass** alt-access (§22). |
| **Power outage** | UPS + auto-restart; `acks_late` + checkpoints resume; no data loss. |
| **Human error** (bad deploy/config/delete) | Rollback (§24), config revert (§45), soft-delete/restore (Doc 3 §DL), DR restore (§22); governed + audited (Doc 6 §43/§44). |
| **Manual mode** | Read-only/maintenance mode (Doc 6 §40) keeps the inbox and history viewable while writes/sends are deferred. |

- **Operational continuity:** the **two independent channels** mean a single-channel outage never halts all
  customer contact — a core continuity advantage of the dual-channel architecture (Doc 7).
- **Recovery priority (DD37):** **(1)** data integrity → **(2)** inbound capture (webhooks/connector) → **(3)**
  agent inbox/support (Channel 2) → **(4)** outbound sends/campaigns (Channel 1) → **(5)** analytics/reporting.

**Design decisions.** Explicit degraded/manual modes + priority order + dual-channel continuity (DD37).
**Alternatives considered:** no continuity plan. **Trade-offs:** planning effort vs. resilience. **Failure
handling:** *this is the section* (complements §22 DR). **Performance:** graceful degradation preserves live
paths (Doc 6 §29). **Scalability:** unchanged. **Security:** governed break-glass, audited. **Future
extensibility:** more channels = more continuity redundancy. **Cross-refs:** Doc 6 §15/§29/§40/§43/§44, Doc 7
§10/§24, §22/§24/§45.

---

## 48. Compliance Architecture

**Purpose.** Architect the deployment so it can meet data-protection and audit obligations (GDPR-style and
India's DPDP Act) for a self-hosted internal platform.

**Scope.** GDPR readiness, Indian **DPDP Act** readiness, audit requirements, consent management, data
retention, data deletion, evidence collection, export requests, legal hold.

**Architecture.**
| Requirement | How the architecture supports it |
|---|---|
| **GDPR / DPDP readiness** | Self-hosted (data stays with the team, §35); lawful-basis via **opt-in/consent** (Doc 1 CMP-02); purpose limitation; data-subject rights below. |
| **Consent management** | Opt-in/opt-out tracked per contact (Doc 3 §6.1); auto opt-out on STOP (Doc 1 CMP-03); consent state auditable. |
| **Audit requirements** | Immutable, hash-chained audit of all mutations/ops (Doc 3 §11.2; Doc 6 §44). |
| **Data retention** | Configurable per-class retention + auto-cleanup (Doc 3 §15; §36). |
| **Data deletion / erasure** | Contact-level **privacy erasure** preserving anonymized aggregates (Doc 1 FR-DL-08; §36). |
| **Export requests (data portability)** | Per-contact/data export (CSV/Excel/JSON, Doc 4; Doc 1 CMP-09). |
| **Evidence collection** | Audit logs + delivery/status ledger + consent history provide defensible evidence. |
| **Legal hold** | A hold flag can **suspend retention/erasure** for specified data during litigation/investigation (additive setting; overrides cleanup, governed + audited). |
| **Data residency** | Host + object storage region is a provisioning choice; no third-party BSP holds the data (§35). |

**Design decisions.** Compliance-by-architecture: consent + immutable audit + retention/erasure + legal hold,
self-hosted for residency (DD38). **Alternatives considered:** bolt-on compliance later; BSP (loses control).
**Trade-offs:** governance overhead vs. defensible compliance + data ownership. **Failure handling:** audit
integrity verification (Doc 6 §41); erasure is governed to avoid accidental loss. **Performance:** n/a.
**Scalability:** unchanged by scale. **Security:** encryption, least privilege, audit (§20/§26). **Future
extensibility:** DPA/consent-record modules; regional deployments; the (disabled) multi-tenant scoping isolates
data if ever enabled. **Cross-refs:** Doc 1 CMP/FR-DL, Doc 3 §6/§11/§15, Doc 4 (export), Doc 6 §41/§44, §35/§36.

## 49. License & Third-Party Dependency Governance

**Purpose.** Keep the dependency surface known, secure, legally compatible, and current over the platform's
multi-year life.

**Scope.** Dependency inventory, version policy, upgrade policy, security review, license compatibility,
deprecation monitoring.

**Architecture.**
| Practice | Design |
|---|---|
| **Inventory (SBOM)** | Maintain a software bill of materials for backend, frontend, and container base images (generated in CI, §43). |
| **Version policy** | **Pin** versions (lockfiles + pinned base images, §6); no floating `latest`; reproducible builds. |
| **Upgrade policy** | Regular, scheduled dependency updates (§29); security patches expedited; validated in staging before prod. |
| **Security review** | CI dependency + image scans (§43) gate releases; CVEs triaged by severity; expedited patch path (§46 hotfix). |
| **License compatibility** | Track licenses; ensure compatibility with an internal, non-distributed deployment; avoid copyleft conflicts where relevant; **the icon set and other assets are used under permissive licenses** (Doc 5 DS-7). |
| **Deprecation monitoring** | Watch upstream EOL/deprecation (frameworks, DB, Redis, base OS LTS) and plan upgrades ahead of end-of-support (§30). |

**Design decisions.** SBOM + pinned versions + scanned/scheduled upgrades + license tracking (DD39).
**Alternatives considered:** unpinned deps, ad-hoc upgrades. **Trade-offs:** governance effort vs. security +
legal safety + stability. **Failure handling:** a vulnerable/EOL dependency is flagged and patched via the
release process. **Performance:** n/a. **Scalability:** governance scales with automation (CI). **Security:**
continuous vulnerability management (§26). **Future extensibility:** automated dependency PRs. **Cross-refs:**
§6/§26/§29/§30/§43/§46; Doc 5 DS-7.

---

## 50. Infrastructure Cost Optimization

**Purpose.** Keep infrastructure spend efficient without compromising reliability or performance.

**Scope.** CPU, RAM, storage, Redis, database, Cloudflare, object-storage lifecycle, worker autoscaling, idle
reduction, and a future Kubernetes cost comparison.

**Architecture (levers).**
| Lever | Optimization |
|---|---|
| **CPU** | Right-size per §27; I/O-bound send/webhook pools use concurrency not cores (Doc 6 §3.2); cap limits (§6). |
| **RAM** | Bounded worker memory + recycling (Doc 6 §25); tuned MySQL buffer pool / Redis maxmemory (§10/§11). |
| **Storage** | Time-partition + prune hot data (Doc 3 §14/§15); dedup media (§14); compress backups. |
| **Redis** | Role-split so cache is evictable; keep only small/TTL'd values; no large blobs (Doc 6 §12). |
| **Database** | Indexes/partitioning avoid over-provisioning; read replica offloads analytics (§10). |
| **Cloudflare** | Edge caching offloads origin bandwidth/CPU; right-size the plan to needed features (§9/§28). |
| **Object-storage lifecycle** | Expire exports/orphans; tier cold data (§14/§36). |
| **Worker autoscaling** | Scale pools on demand; scale **in** during idle to a small floor (Doc 6 §30) — pay for load, not peak. |
| **Idle reduction** | Consolidate on one node at low scale; power/resource-efficient off-peak; suspend non-prod environments when unused (§42). |
| **Future K8s cost comparison** | K8s adds control-plane + operational overhead — justified at ~≥25–50 numbers (autoscaling/HA value), not at 1–10 numbers where Compose is cheaper (§53). |

**Design decisions.** Demand-based sizing + autoscale-in + lifecycle pruning + edge offload (DD40). **Alternatives
considered:** over-provision for peak; never scale in. **Trade-offs:** scale-in latency vs. cost; mitigated by
warm floors for latency-sensitive pools. **Failure handling:** headroom + autoscale absorb spikes. **Performance:**
optimization respects SLOs (§33). **Scalability:** cost scales stepwise (§27/§28). **Security:** unaffected.
**Future extensibility:** K8s HPA + spot/preemptible for batch pools. **Cross-refs:** §6/§9/§10/§11/§14/§27/§28/
§36/§53; Doc 3 §14/§15, Doc 6 §3.2/§12/§25/§30.

---

## 51. Production Readiness Checklist

**Purpose.** A gate that must be fully satisfied before go-live — the definitive "are we ready?" list.

**Scope.** Infrastructure, security, database, Redis, queues, Support Connector, AI, monitoring, logging,
backups, DR, documentation, operations, go-live.

**Architecture (checklist).**
| Area | Ready when |
|---|---|
| **Infrastructure** | Host hardened; Docker networks zoned; resource limits set; Nginx/Cloudflare configured; origin allowlisted (§5/§6/§7/§9/§26). |
| **Security** | TLS + HSTS; secrets encrypted/rotated; SSH/firewall/fail2ban; image scans clean; RBAC seeded (§8/§20/§26; Doc 1). |
| **Database** | Migrations applied; binlog/PITR on; partitions provisioned; pools tuned; replica plan ready (§10). |
| **Redis** | AOF on broker instance; memory policy set; monitored (§11). |
| **Queues** | All pools deployed; Beat + standby; DLQ + replay verified; SLA thresholds set (§12; Doc 6). |
| **Support Connector** | Connectors registered; QR/session flow tested; health + auto-recovery verified; isolation confirmed (§13; Doc 7). |
| **AI** | Provider configured; budgets/limits set; human-approval enforced (§17; Doc 1 FR-AI-10). |
| **Monitoring** | Dashboards live; alerts routed; dead-man's switch; SLOs defined (§18/§33). |
| **Logging** | Structured logs → Loki; audit → MySQL; retention/rotation set; no secrets in logs (§19/§20). |
| **Backups** | Scheduled + off-host + **verified by test-restore** (§21). |
| **Disaster Recovery** | DR runbook + drill passed; RTO/RPO validated (§22). |
| **Documentation** | Docs 1–8 current; runbooks (Doc 11) available; inventory (§44) current. |
| **Operations** | On-call + escalation defined; maintenance cadence scheduled; governance/audit on (§29/§31/§34). |
| **Go-Live** | UAT sign-off; rollback rehearsed; comms plan; capacity validated (§27); load test passed (Doc 10). |

**Design decisions.** A hard, all-areas readiness gate before go-live. **Alternatives considered:** launch and
fix later. **Trade-offs:** slower launch vs. a stable, supportable production. **Failure handling:** any unmet
item blocks go-live. **Performance:** capacity validated pre-launch. **Scalability:** re-run at each scale step.
**Security:** security items are gating. **Future extensibility:** automated readiness checks in CI/CD.
**Cross-refs:** §5–§34; Doc 1, Doc 6, Doc 7, Doc 10, Doc 11.

---

## 52. Enterprise Operational KPIs

**Purpose.** Define the infrastructure/operational KPIs that quantify platform health and improvement over
time — the numbers leadership and on-call track.

**Scope.** Availability, latency, resource, queue, connector, API, recovery, backup, deployment, and MTTD/MTTR
KPIs.

**Architecture (KPI targets).**
| KPI | Target | Source |
|---|---|---|
| **Platform availability** | ≥ 99.9% (single-node best-effort; higher with HA §23) | uptime probe (§18) |
| **API uptime** | ≥ 99.9% | §18/§33 |
| **Connector uptime** (per connector) | ≥ 99.9% session availability | Doc 7 §11; §18 |
| **API latency (p95)** | < 300 ms reads (Doc 1 §5.1) | §18 |
| **Queue latency (p95, hot)** | < 1 s (Doc 6 §14) | §18 |
| **CPU utilization** | 60–80% steady (headroom) | node exporter |
| **RAM utilization** | < 80% steady | node exporter |
| **Storage utilization** | < 75%; growth forecast (Doc 6 §36) | node/DB exporter |
| **Backup success rate** | 100% (verified) | §21 (`backups`) |
| **Deployment success rate** | ≥ 99% (rollback on fail) | CI/CD (§43) |
| **MTTD** (mean time to detect) | minutes (alert-driven) | §18/§33 |
| **MTTR** (mean time to recover) | ≤ target RTO per SLA (Doc 6 §42) | §22/§34 |
| **Recovery time (RTO)** | ≤ 1 h baseline (§22) | DR drills |
| **RPO** | ≈ 0 for accepted data | §21/§22 |
| **SLA compliance** | per Doc 6 §42 matrix | §35 (Doc 6) |

**Design decisions.** A concrete KPI set tied to SLOs (Doc 6 §42) and monitored continuously. **Alternatives
considered:** vibes-based ops. **Trade-offs:** measurement upkeep vs. objective health. **Failure handling:**
KPI breaches trigger alerts/escalation (§33/§34). **Performance:** KPIs *are* the performance contract.
**Scalability:** KPIs per node/service/channel. **Security:** includes patch/scan compliance (via §29/§43).
**Future extensibility:** SLO dashboards, error-budget reports. **Cross-refs:** Doc 1 §5.1, Doc 6 §14/§36/§42,
Doc 7 §11, §18/§21/§22/§33/§34/§43.

## 53. Infrastructure Decision Appendix — Orchestrator Comparison

**Purpose.** Justify **Docker Compose today** against the major orchestration/runtime alternatives, with a clear
migration path — extending the DD series with **DD41**.

**Scope.** Docker Compose, Nomad, Kubernetes, Docker Swarm, systemd, Bare Metal, Google Cloud Run, Azure
Container Apps, AWS ECS.

**Context & criteria.** Single-tenant, self-hosted, small team, ≤100 numbers, cost-sensitive, must run for
years and scale later. Criteria: operational simplicity, self-hostability, HA/autoscaling capability, learning
curve, cost, and a clean upgrade path.

**Chosen today: Docker Compose.** *Advantages:* simplest multi-container orchestration on a single host; low
learning curve; matches the stack; fast to operate. *Disadvantages:* single-host, no built-in autoscaling/
multi-node scheduling. *Fit:* ideal at 1–25 numbers.

Each alternative: **Advantages · Disadvantages · Why (not) selected · Migration path.**

- **Kubernetes** — *Adv:* autoscaling, self-healing, multi-node, huge ecosystem, rolling deploys. *Dis:*
  significant operational complexity + control-plane overhead. *Why not now:* over-engineered/costly at small
  scale for a small team. *Migration:* the **target** at ~≥25–50 numbers/HA; the containerized, stateless design
  ports directly (§23) — Compose services → Deployments/StatefulSets. **(DD41: Compose now, K8s later.)**
- **Docker Swarm** — *Adv:* simple multi-node clustering, close to Compose syntax. *Dis:* declining ecosystem/
  momentum. *Why not:* limited future-proofing vs. K8s. *Migration:* possible interim step; likelier to jump
  straight to K8s.
- **HashiCorp Nomad** — *Adv:* lightweight scheduler, simpler than K8s, multi-workload. *Dis:* smaller
  ecosystem; another control plane to run. *Why not:* K8s is the more standard long-term target. *Migration:*
  feasible alternative to K8s if simplicity is prioritized.
- **systemd (containers/services)** — *Adv:* no extra tooling on the host. *Dis:* manual orchestration,
  networking, scaling. *Why not:* Compose is more ergonomic for multi-container apps. *Migration:* n/a.
- **Bare metal (no containers)** — *Adv:* max performance, no container overhead. *Dis:* no isolation/
  reproducibility; painful ops. *Why not:* loses containerization benefits (parity, rollback, isolation).
  *Migration:* n/a.
- **Google Cloud Run** — *Adv:* fully managed, scale-to-zero, simple. *Dis:* cloud lock-in; not ideal for
  stateful/long-lived connector sessions or self-hosting. *Why not:* self-hosting requirement + session-affine
  workers. *Migration:* stateless API could run there on GCP later; workers/connectors would not fit well.
- **Azure Container Apps** — *Adv:* managed, KEDA autoscaling. *Dis:* cloud lock-in; self-hosting conflict.
  *Why not:* same as Cloud Run. *Migration:* possible on Azure for stateless tiers.
- **AWS ECS (Fargate/EC2)** — *Adv:* managed containers, integrates with AWS. *Dis:* cloud lock-in; ties to AWS.
  *Why not:* self-hosting requirement. *Migration:* viable if the deployment moves to AWS; images run unchanged.

**Summary (DD41).** Docker Compose is the right **today** choice for a self-hosted, small-team, cost-sensitive
deployment; because everything is containerized and stateless with externalized state (§4/§23), the migration to
**Kubernetes** (the long-term HA/autoscaling target) — or to a managed cloud runtime if ever desired — is
**additive and low-risk**, not a redesign. *Long-term maintainability:* high (standard tooling); *operational
complexity:* lowest now, deliberately deferred. **Cross-refs:** §4/§6/§23/§27/§50; Doc 6 §16/§45.

---

## 54. Cross-Document Traceability

**Purpose.** Trace every major deployment component back to its **origin requirement** and forward to the
frozen documents it depends on — proving the blueprint implements the specified system with nothing orphaned.

**Scope.** Deployment component → origin requirement (Doc 1) · database (Doc 3) · API (Doc 4) · queue (Doc 6) ·
UI (Doc 5) · connector (Doc 7).

**Architecture (traceability matrix).**
| Deployment component (Doc 8) | Origin requirement (Doc 1) | Database (Doc 3) | API (Doc 4) | Queue (Doc 6) | UI (Doc 5) | Connector (Doc 7) |
|---|---|---|---|---|---|---|
| Backend/API (§15) | FR-* / NFR-* | all tables | §1–§28 | enqueues | consumes API | via abstraction |
| Frontend (§16) | FR-UX-* | — | consumes | — | Doc 5 | inbox markers |
| Nginx/Cloudflare/TLS (§7/§8/§9) | NFR-SEC-01..03 | — | §9/§34 | — | — | — |
| MySQL (§10) | NFR-PERF/DR | §1–§20 | data source | durable truth | — | connector tables (§23·D7) |
| Redis (§11) | NFR-DR-06 | §2 | rate/cache | §12 broker | — | locks/heartbeat |
| Celery workers (§12) | FR-CAM/FR-WA | recipients/ledger | send/webhook | §2/§22 | progress | support pool |
| Support Connector (§13) | Doc 7 reqs | connector/session/lead | connector endpoints | §22 support | B7/dashboard | **Doc 7 §6–§13** |
| Object storage (§14) | FR-MED-* | `media_assets` | §16 | media queue | B6 media | connector media |
| AI services (§17) | FR-AI-*/NFR-EXT-04 | §10 AI tables | §19/§32 | `ai` queue | B8/F8 | cross-channel AI |
| Monitoring/Logging (§18/§19) | FR-MON-*/NFR-SEC-07 | metrics/audit/system logs | §22 | §13/§35 | B11.8/9 | connector health |
| Secrets (§20) | NFR-SEC-08 | encrypted fields | §11/§13 | — | — | session keys (§9·D7) |
| Backup/DR (§21/§22) | NFR-DR-* | `backups` | — | §10/§41 | B11.9 | session restore |
| Deployment/Upgrade (§24/§30) | maintainability | Alembic | §26 | §3.5/§39 | — | §10 re-pin |
| Compliance (§35/§48) | CMP-*/FR-DL-* | §6/§11/§15 | export | §41/§44 | B11.10 audit | §5.5/§28 stance |

**Design decisions.** Explicit forward+backward traceability. **Alternatives considered:** implicit mapping.
**Trade-offs:** matrix upkeep vs. verifiable coverage. **Failure handling:** gaps in the matrix reveal missing
design. **Performance:** n/a. **Scalability:** rows added per component. **Security:** confirms security
requirements are deployed. **Future extensibility:** extend for Docs 9–11. **Cross-refs:** Docs 1–7 (as mapped).

---

## 55. Final Self-Review

Reviewed as **Enterprise Architect, DevOps Architect, SRE, Platform Engineer, Linux Administrator, Cloud
Architect, DBA, Security Engineer, Compliance Officer, QA Lead, Performance Engineer, Operations Engineer**:

- **Enterprise Architect:** the blueprint is complete (55 sections), internally consistent, and traceable to
  Docs 1–7 (§54); single-node-now / multi-node-ready without redesign. ✔
- **DevOps Architect:** full environment lifecycle (§42), CI/CD with scans + approval + rollback (§43), release
  management + SemVer/LTS (§46), zero-downtime deploy/upgrade (§24/§30). ✔
- **SRE:** SLOs/KPIs (§52), DR (§22), business continuity + manual/degraded modes + recovery priority (§47),
  incident process (§34), MTTD/MTTR targets. ✔
- **Platform Engineer:** inventory (§44), configuration hierarchy + flags (§45), governance/naming/ports (§31),
  orchestrator choice + K8s migration path (§53). ✔
- **Linux Administrator:** hardened Ubuntu, firewall/fail2ban/SSH, updates, power/UPS (§26/§22). ✔
- **Cloud Architect:** externalized state, HA readiness, Cloudflare edge, managed-cloud migration options (§9/
  §23/§53). ✔
- **DBA:** replication/PITR, partition maintenance, expand-migrate-contract migrations, pooling, replica offload
  (§10/§24). ✔
- **Security Engineer:** defense-in-depth, encrypted secrets/sessions/backups, image/dependency scanning, TLS,
  audit, least privilege (§20/§26/§43/§49). ✔
- **Compliance Officer:** GDPR/DPDP readiness, consent, retention, erasure, evidence, export, legal hold,
  residency; adapter-neutral Channel-2 stance (§48/§35). ✔
- **QA Lead:** production readiness checklist (§51), test gates in CI (§43), staging/UAT validation (§42), load
  tests referenced (Doc 10). ✔
- **Performance Engineer:** optimization levers + cost optimization meet frozen targets (§25/§50; Doc 1 §5.1,
  Doc 5 F15, Doc 6 §14). ✔
- **Operations Engineer:** maintenance cadence, runbook references, KPIs, inventory, on-call — operable for
  years (§29/§34/§44/§52; Doc 11). ✔

**Confirmations:** No placeholders · No TODOs · No code · Architecture only · Production-ready · Cross
references verified (§54) · **Ready for implementation.**

**No architectural gaps identified. Document 8 frozen as Version 1.1.**




---

## §56 — Platform Portability Appendix (additive, v1.2)

> **Scope.** This is an *architecture guarantee*, not a build item. It states that the platform's data and
> configuration are **portable and owner-owned**, so the Vi Reactivation Team is never locked in. It is
> deliberately **lightweight**: it defines guarantees, formats and verification — it is **not** a migration
> engine, ETL product, data warehouse, or MDM (those are explicitly out of scope per the final governance
> ruling). It builds on existing capabilities: backups (§9), object storage (§10), the export APIs (Doc 4 §20),
> the business-event ledger (Doc 3 §21) and the audit log (Doc 3).

### §56.1 Full Data Export Guarantee
The platform can export **100% of tenant-owned data** — contacts/leads, conversations & messages, templates,
campaigns, unified CRM records across **all channels** (Meta + every Support Connector), the **business-event
ledger** (Doc 3 §21), audit logs, users/roles, and settings — with **no field withheld** behind the product.
Exports are produced by the existing async export APIs (Doc 4 §20) plus the database backups (§9).

### §56.2 Data Ownership
All data and content are **owned by the tenant** (the Vi Reactivation Team / operating org), not by the
platform or any connector vendor. Self-hosting (Doc 1) means data resides in the owner's MySQL + object storage;
no third party holds an exclusive copy. Support-Connector data is normalized into the owner's CRM and is exported
on identical terms to Meta-channel data (channel neutrality — Doc 7).

### §56.3 Vendor Independence
- **No connector lock-in.** The channel layer is an abstraction (Doc 7); replacing/removing any connector does
  **not** touch the data model or exports.
- **Open infrastructure.** MySQL, Redis, S3-compatible storage, OCI containers (§4–§10) — all replaceable with
  standards-compliant equivalents; no proprietary datastore.
- **No proprietary encoding.** Exports use open formats (below), not an opaque platform-only format.

### §56.4 Platform Exit Strategy
A documented, self-serve exit path — no vendor assistance required:
1. Trigger a **full export** (§56.1) via the export APIs and take a **database backup** (§9).
2. Retrieve media/attachments from object storage (§10) — export manifests reference object keys.
3. **Validate & verify integrity** (§56.6–§56.8) against the manifest.
4. The bundle (open formats + backup + media + manifest + checksums) is sufficient to stand the data up
   elsewhere. *(Operational drill: Doc 11 Runbook.)*

### §56.5 Export Formats
| Data | Format |
|---|---|
| Structured records (contacts, messages, campaigns, CRM, users/roles) | **CSV** and/or **JSON (NDJSON for large sets)** |
| Business-event ledger & audit logs | **NDJSON** (append-only, one event per line — Doc 3 §21) |
| Full database | native **MySQL logical/physical backup** (§9) |
| Media/attachments | original binaries in **object storage** (§10) + manifest of keys |
| Report exports | **PDF / Excel** (Doc 5 Part G, Doc 4 §20) |

All open, non-proprietary, documented by schema (Doc 3).

### §56.6 Export Validation
Each export ships a **manifest**: dataset inventory, per-dataset **row counts**, schema version (Doc 3), time
range, channel coverage, and generation timestamp — so completeness is checkable (expected vs actual counts).

### §56.7 Export Audit
Every export is an **audited, business-ledger event** (Doc 3 §21 — e.g. `data.exported`): who, when, scope,
row counts, destination. Exports of finance/PII data are additionally gated by RBAC (Doc 4 §4.3) and captured in
the audit log — export is a governed action (Doc 12).

### §56.8 Integrity Verification
Exports include **checksums** (per-file SHA-256) plus the manifest counts (§56.6); the ledger/audit NDJSON is
independently **replayable/verifiable** (Doc 3 §21, Doc 6 §47) — a receiver can confirm nothing was altered or
dropped in transit.

### §56.9 Backup Compatibility
Portability reuses the **existing backup system** (§9): standard MySQL backups (restorable on any conforming
MySQL 8), object-storage sync (§10), documented restore drills (Doc 11). No portability-specific backup format.

### §56.10 Future Migration Readiness
The platform is **structured to make a future migration feasible** without committing to build one now:
stable open export formats (§56.5), documented schema + schema-version stamping (Doc 3), an append-only replayable
ledger (Doc 3 §21), and channel-neutral CRM (Doc 7). **Explicitly out of scope** (final governance ruling): a
migration/ETL engine, data warehouse, MDM, or plugin marketplace. This appendix guarantees *readiness*, not a tool.

### §56 — self-review
- **Additive integrity:** §1–§55 unchanged; §56 appended; reuses backups (§9), storage (§10), export APIs
  (Doc 4 §20), ledger (Doc 3 §21) — no new subsystem. ✔
- **In-scope only:** guarantees + formats + verification; **no** migration engine / warehouse / MDM / marketplace
  (respects the final ruling). ✔
- **Dual-channel & governed:** covers Meta + all connectors equally; exports are RBAC-gated and audited as ledger
  events. ✔

---

*End of Document 8 — Deployment & DevOps Architecture (Version 1.2, FROZEN). §1–§41 = v1.0 baseline;
§42–§55 added in the enhancement pass (environment lifecycle, CI/CD, inventory, configuration, release,
business continuity, compliance, dependency governance, cost optimization, readiness checklist, KPIs,
orchestrator decision appendix, traceability, final review).*







