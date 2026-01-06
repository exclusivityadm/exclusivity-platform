-- =========================================================
-- EXCLUSIVITY — BLOCKCHAIN ORCHESTRATION HARDENING
-- EXCL-END2END-07
-- =========================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------
-- Wallet provisioning (customer-level, abstracted)
-- ---------------------------------------------------------
create table if not exists public.customer_wallets (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  customer_id uuid not null,

  provider text not null default 'internal',  -- internal|custodial_provider|future
  wallet_ref text,                            -- provider reference id (not exposed to merchant)
  address text,                               -- optional if you decide to store public address
  status text not null default 'pending' check (status in ('pending','ready','failed')),
  error_last text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists uniq_customer_wallet
  on public.customer_wallets (merchant_id, customer_id);

comment on table public.customer_wallets is
  'Abstracted wallets created invisibly. Stores provider refs; merchant never sees crypto language.';


-- ---------------------------------------------------------
-- Mint queue (durable job system)
-- ---------------------------------------------------------
create table if not exists public.mint_jobs (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  customer_id uuid not null,

  job_type text not null default 'badge_issue',  -- badge_issue|badge_revoke|future
  source text not null default 'engine',          -- engine|admin|future
  source_ref text,                                -- e.g. ledger id, order id, campaign id

  payload jsonb not null default '{}'::jsonb,     -- abstract metadata for mint
  status text not null check (status in ('queued','running','retrying','completed','failed')),
  attempts int not null default 0,
  run_after timestamptz,
  locked_at timestamptz,
  locked_by text,
  error_last text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_mint_jobs_status_time
  on public.mint_jobs (status, created_at);

create index if not exists idx_mint_jobs_merchant_time
  on public.mint_jobs (merchant_id, created_at desc);

-- Prevent duplicate mint jobs for same logical source
create unique index if not exists uniq_mint_jobs_source
  on public.mint_jobs (merchant_id, job_type, source, source_ref)
  where source_ref is not null;

comment on table public.mint_jobs is
  'Durable queue for blockchain actions. Claimed atomically, retryable, auditable.';


-- ---------------------------------------------------------
-- Mint job events (audit trail)
-- ---------------------------------------------------------
create table if not exists public.mint_job_events (
  id uuid primary key default gen_random_uuid(),
  mint_job_id uuid not null,
  merchant_id uuid not null,
  event text not null,                 -- started|progress|completed|failed|retry_scheduled
  details text,
  created_at timestamptz not null default now()
);

create index if not exists idx_mint_job_events_job
  on public.mint_job_events (mint_job_id, created_at asc);

comment on table public.mint_job_events is
  'Append-only audit events for mint jobs.';


-- ---------------------------------------------------------
-- Atomic job claim RPC
-- ---------------------------------------------------------
create or replace function public.claim_mint_job(worker_id text)
returns table (
  id uuid,
  merchant_id uuid,
  customer_id uuid,
  job_type text,
  source text,
  source_ref text,
  payload jsonb,
  attempts int
)
language plpgsql
as $$
begin
  return query
  update public.mint_jobs
  set status = 'running',
      locked_at = now(),
      locked_by = worker_id,
      updated_at = now()
  where id = (
    select j.id
    from public.mint_jobs j
    where j.status in ('queued','retrying')
      and (j.run_after is null or j.run_after <= now())
    order by j.created_at asc
    limit 1
    for update skip locked
  )
  returning
    public.mint_jobs.id,
    public.mint_jobs.merchant_id,
    public.mint_jobs.customer_id,
    public.mint_jobs.job_type,
    public.mint_jobs.source,
    public.mint_jobs.source_ref,
    public.mint_jobs.payload,
    public.mint_jobs.attempts;
end;
$$;

comment on function public.claim_mint_job(text) is
  'Claims one eligible mint job atomically for a worker.';

-- =========================================================
-- END MIGRATION
-- =========================================================
