# ADR 001 — Exclusivity provider-neutral core, Circa Haus first

Status: **Foundation proposed on an isolated Git branch; not wired, deployed, released or billed.**  
Date: 2026-11-11

## Product decision
Exclusivity remains an independent, industry-agnostic merchant loyalty and customer-relationship product. **Circa Haus is its first native integration, not its core implementation or owning platform.** The existing Shopify integration remains a distribution channel; future independent retail and services can use separate adapters. Ether remains paused and is not required for an initial integration.

## Architecture
1. **Exclusivity core:** Merchant-scoped customer identity, program policy, recognition, status, eligibility, rewards, append-only loyalty event ledger, balance computation and business controls. Each merchant owns its program rules and permitted customer data.
2. **Provider adapters:** Circa Haus, Shopify, and later external/standalone systems translate validated, authorized source events to one normalized contract. No provider-specific assumptions in the core's policy or ledger code.
3. **Source of truth:** Circa Haus owns its orders and financial ledger; Shopify owns its commerce orders; Exclusivity owns only its **derived loyalty** ledger and recognition rules. No duplicated payment settlement authority.
4. **Fault isolation:** Exclusivity outage must not prevent Circa Haus checkout, fulfillment, member access, or application release. External delivery is asynchronous with durable retries, authorization, signature verification, and a dead-letter/reconciliation path. No credentials or secret tokens in clients or event bodies.
5. **Privacy:** Merchant-scoped opaque customer references; no automatic merging of identities across merchants, providers or Circa Haus creator accounts. Cross-platform linking is explicit, consented and revocable. No raw customer email in adapter event keys, logs, URLs, or shared program metrics.
6. **Commerce integrity:** Only settled/eligible events should award points; refunds reverse the original award without deleting the original event. One replay identity per unique original provider event, merchant and event type. Points valuation, tier thresholds, reserve liability, currency exponent and refunds must be governed by the merchant's **versioned** policy, not fixed in provider adapters.

## What the repository already has
- Existing pure domain components: `apps/backend/routes/services/loyalty/loyalty_policy.py`, `points_ledger.py`, and `rewards_allocator.py`. Retain and reconcile, do **not** fork competing policy engines.
- Existing persistence contract: `apps/backend/routes/repositories/loyalty_repository.py` and `supabase/migrations/supabase_schema_loyalty.sql`.
- Older code paths: `apps/backend/services/loyalty_service.py`, `apps/backend/routes/loyalty.py`, `apps/backend/services/shopify_backfill.py`, and other wallet schemas. Their overlapping ledger/policy implementations are **not** automatically equivalent. Map all calls and authoritative migrations before changing persistence.
- Provider-neutral adapter validation starts in `apps/backend/routes/services/integrations/normalized_events.py` and uses standard-library-only tests. This is intentionally NOT connected to live API routes.

## Known correctness and launch blockers
- `apps/backend/services/loyalty_service.py` catches any ledger insert error and silently continues as though a duplicate was replayed. Distinguish an explicit unique-key conflict from network, schema, authorization and transaction failures.
- `apps/backend/services/shopify_backfill.py` deletes and rewrites earlier `backfill_credit` ledger records and uses currency floats. Replace with immutable, idempotent, currency-exact historical events before running any production backfill.
- Legacy `loyalty_service.py` computes tier from points thresholds; newer `loyalty_policy.py` specifies tiers by lifetime spend. Reconcile against the **previously authorized Exclusivity rules**, with no silent policy or customer-balance migrations.
- Shopify OAuth/backfill includes token handling that needs authorization, secret-storage and data-scope review before public distribution.
- Existing repository schemas and actual deployed database state have **not** been reconciled. Never assume migration text indicates production tables or working RLS.
- Some `PointsLedger` reducer behavior clamps negative totals at presentation time: verify refund/adjustment sequence effects and exact non-punitive policy before relying on it as financial liability accounting.

## Controlled implementation sequence
1. **Foundation (this branch):** Define immutable, provider-neutral validated commerce fact and replay key. Add offline unit tests. No HTTP/database writes.
2. **Audit and unify:** Map every loyalty route/schema to one canonical policy and ledger. Add checks for unique idempotency, partial refunds, race conditions, strong tenant authorization, and reserve funding.
3. **Circa Haus adapter:** Server-side, permission-checked event delivery from completed eligible orders, refunds and merchant opt-in. Keep Circa Haus order state authoritative; opt in/feature flag. Never block checkout on Exclusivity failure.
4. **Shopify adapter:** Preserve existing OAuth/merchant integration and repair historical backfill, token storage, webhook validation and immutable event mapping.
5. **Independent API:** Expose the same permissions/contract to non-Shopify merchants; prove cross-provider isolation. Do not claim a live multi-industry product until tested.
6. **Controlled acceptance:** Offline tests first. Then separately owner-approved staging, identity/consent checks, reconciliation, chargeback/refund tests, failure injection, data export/deletion and costs. No additional paid accounts, resumed infrastructure, CI, migrations, live checkout or stores in this change.

## Release and cost boundaries
- Circa Haus release qualification and existing app-store blockers remain highest priority; do not introduce unfinished Exclusivity screens or make this a Circa Haus launch dependency.
- **Both Exclusivity and Ether remain operationally paused.** Do not reactivate Render, Supabase, automation jobs, hosting or paid providers; no CI dispatch for this foundation.
- Maintain recoverability and ownership isolation. Any future live run requires explicit account-level spending approval.

## 2026-11-11 implementation checkpoint
- **Created on branch `design/provider-neutral-core-20261111`:** normalized immutable commerce event contract; merchant+provider+source-account+event-scoped replay identity; currency-safe integer minor units; strict input contract; offline tests.
- **Fixed (branch, not deployed):** older `loyalty_service.append_ledger` no longer silently treats every failed database insert as success; a confirmed unique-key replay must be verified against the same customer, event type and point delta.
- **Blocked unsafe legacy operations (branch only):** Shopify backfill no longer deletes/reinserts historical loyalty records or uses floats; legacy backfill pump/status are inaccessible until rebuilt with merchant authorization. Legacy Shopify OAuth callback deliberately returns 503 instead of accepting an unsigned merchant ID and automatically initiating historical writes. Existing implementation retained in Git history.
- **Remaining:** reconcile multiple loyalty schemas and lifetime-spend-versus-points tier definitions; one canonical ledger and exact replay semantics; rebuild Shopify OAuth with signed state, secret management and verified tenant binding; build an authenticated immutable historical importer; add Circa Haus adapter, consent, idempotency and fallback; complete local/offline tests and separately authorized staging proof. **No active integration or production readiness claim.**
- **Validation:** repository files fetched back and inspected. Unit tests are committed but have **not been executed**; no GitHub Actions minutes used.
- **Operational posture:** Exclusivity and Ether remain paused; this development branch is not a request to restart services.
