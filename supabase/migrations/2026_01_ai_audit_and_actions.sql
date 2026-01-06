-- =========================================================
-- EXCLUSIVITY — AI UTILITY LAYER (AUDIT + ACTION GATING)
-- EXCL-END2END-09
-- =========================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------
-- AI action requests (audit + idempotency)
-- ---------------------------------------------------------
create table if not exists public.ai_action_requests (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,

  mode text not null check (mode in ('preview','execute')),
  action_type text not null,              -- e.g. pricing_apply, mint_issue, marketing_blast, etc.
  source text not null default 'api',      -- api|system|future
  source_ref text,                         -- idempotency key

  request jsonb not null default '{}'::jsonb,
  status text not null default 'received' check (status in ('received','blocked','completed','failed')),
  decision text,                           -- allow|deny with reason
  result jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists uniq_ai_action_requests_source_ref
  on public.ai_action_requests (merchant_id, mode, action_type, source, source_ref)
  where source_ref is not null;

create index if not exists idx_ai_action_requests_merchant_time
  on public.ai_action_requests (merchant_id, created_at desc);

comment on table public.ai_action_requests is
  'Audit trail and idempotency for AI actions. Enforces Preview vs Execute policies.';

-- =========================================================
-- END MIGRATION
-- =========================================================
