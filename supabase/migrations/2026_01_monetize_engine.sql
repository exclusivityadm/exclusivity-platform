-- =========================================================
-- EXCLUSIVITY — MONETIZE ENGINE (USAGE LEDGER + INVOICING)
-- EXCL-END2END-08
-- =========================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------
-- Merchant subscription plan (what tier they pay for)
-- ---------------------------------------------------------
create table if not exists public.merchant_subscription (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null unique,

  plan text not null default 'preview',        -- preview|paid_tier_1|paid_tier_2|enterprise
  subscription_status text not null default 'active',  -- active|past_due|paused|cancelled
  period_anchor_day int not null default 1,    -- billing anchor day of month

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.merchant_subscription is
  'Merchant subscription tracking. Separate from usage charges.';


-- ---------------------------------------------------------
-- Usage ledger (append-only; billable events)
-- ---------------------------------------------------------
create table if not exists public.usage_ledger (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,

  category text not null,          -- email|sms|ai_execute|other
  item text not null,              -- e.g. postmark_send, twilio_send, ai_action_execute
  quantity int not null default 1,

  unit_cost_cents int not null default 0,  -- cost basis (optional)
  unit_price_cents int not null default 0, -- what merchant is billed per unit
  total_cents int not null default 0,      -- quantity * unit_price_cents

  source text not null default 'engine',   -- engine|admin|system
  source_ref text,                         -- idempotency key
  occurred_at timestamptz not null default now(),

  created_at timestamptz not null default now()
);

create index if not exists idx_usage_ledger_merchant_time
  on public.usage_ledger (merchant_id, occurred_at desc);

-- Idempotency: prevent duplicates for same logical external event
create unique index if not exists uniq_usage_ledger_source_ref
  on public.usage_ledger (merchant_id, category, item, source, source_ref)
  where source_ref is not null;

comment on table public.usage_ledger is
  'Append-only usage events for metered billing (email/sms/ai execution/etc).';


-- ---------------------------------------------------------
-- Invoice drafts + final invoices
-- ---------------------------------------------------------
create table if not exists public.invoices (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,

  period_start date not null,
  period_end date not null,

  status text not null default 'draft', -- draft|final|paid|void
  currency text not null default 'USD',

  subscription_cents int not null default 0,
  usage_cents int not null default 0,
  total_cents int not null default 0,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists uniq_invoices_period
  on public.invoices (merchant_id, period_start, period_end);

create index if not exists idx_invoices_merchant_time
  on public.invoices (merchant_id, created_at desc);

comment on table public.invoices is
  'Invoices for subscription + usage. Drafted via RPC.';


create table if not exists public.invoice_line_items (
  id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null,
  merchant_id uuid not null,

  line_type text not null,     -- subscription|usage
  description text not null,
  quantity int not null default 1,
  unit_price_cents int not null default 0,
  amount_cents int not null default 0,

  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_invoice_lines_invoice
  on public.invoice_line_items (invoice_id, created_at asc);

comment on table public.invoice_line_items is
  'Line items for invoices. Usage lines can be aggregated per category/item.';


-- ---------------------------------------------------------
-- RPC: draft invoice for a given period (idempotent)
-- ---------------------------------------------------------
create or replace function public.draft_invoice_for_period(
  p_merchant_id uuid,
  p_period_start date,
  p_period_end date
)
returns table (
  invoice_id uuid,
  subscription_cents int,
  usage_cents int,
  total_cents int
)
language plpgsql
as $$
declare
  inv_id uuid;
  sub_cents int := 0;
  use_cents int := 0;
begin
  -- Create invoice draft if missing
  insert into public.invoices (merchant_id, period_start, period_end, status)
  values (p_merchant_id, p_period_start, p_period_end, 'draft')
  on conflict (merchant_id, period_start, period_end) do nothing;

  select i.id into inv_id
  from public.invoices i
  where i.merchant_id = p_merchant_id
    and i.period_start = p_period_start
    and i.period_end = p_period_end
  limit 1;

  -- Clear existing draft line items (re-draft is deterministic)
  delete from public.invoice_line_items
  where invoice_id = inv_id;

  -- Subscription: placeho
