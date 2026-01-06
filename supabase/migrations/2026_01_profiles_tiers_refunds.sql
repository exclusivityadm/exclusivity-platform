-- =========================================================
-- EXCLUSIVITY — PROFILES + TIERS + REFUNDS (ENGINE)
-- EXCL-END2END-04
-- =========================================================

create extension if not exists "pgcrypto";

-- -----------------------------
-- MERCHANT TIERS (optional, merchant-defined)
-- -----------------------------
create table if not exists public.merchant_tiers (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  name text not null,
  min_spend numeric not null default 0,
  created_at timestamptz not null default now()
);

create unique index if not exists uniq_merchant_tiers
  on public.merchant_tiers (merchant_id, name);

create index if not exists idx_merchant_tiers_min_spend
  on public.merchant_tiers (merchant_id, min_spend);

comment on table public.merchant_tiers is
  'Merchant-defined tiers. If absent, backend uses defaults.';


-- -----------------------------
-- CUSTOMER PROFILES (lifetime spend + order count + tier)
-- -----------------------------
create table if not exists public.loyalty_customer_profiles (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  customer_id uuid not null,
  lifetime_spend numeric not null default 0,
  order_count int not null default 0,
  tier text,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create unique index if not exists uniq_customer_profile
  on public.loyalty_customer_profiles (merchant_id, customer_id);

comment on table public.loyalty_customer_profiles is
  'Derived per-customer metrics used by engine + AI. Customer-invisible.';


-- -----------------------------
-- ATOMIC PROFILE INCREMENT (RPC)
-- -----------------------------
create or replace function public.increment_customer_profile(
  p_merchant_id uuid,
  p_customer_id uuid,
  p_spend_delta numeric,
  p_order_delta int
)
returns table (
  merchant_id uuid,
  customer_id uuid,
  lifetime_spend numeric,
  order_count int
)
language plpgsql
as $$
begin
  insert into public.loyalty_customer_profiles
    (merchant_id, customer_id, lifetime_spend, order_count, updated_at)
  values
    (p_merchant_id, p_customer_id, 0, 0, now())
  on conflict (merchant_id, customer_id) do nothing;

  update public.loyalty_customer_profiles
  set lifetime_spend = greatest(0, lifetime_spend + p_spend_delta),
      order_count = greatest(0, order_count + p_order_delta),
      updated_at = now()
  where merchant_id = p_merchant_id
    and customer_id = p_customer_id
  returning
    public.loyalty_customer_profiles.merchant_id,
    public.loyalty_customer_profiles.customer_id,
    public.loyalty_customer_profiles.lifetime_spend,
    public.loyalty_customer_profiles.order_count
  into merchant_id, customer_id, lifetime_spend, order_count;

  return next;
end;
$$;

comment on function public.increment_customer_profile(uuid, uuid, numeric, int) is
  'Atomically increments lifetime_spend and order_count (clamped >= 0).';


-- -----------------------------
-- LEDGER IDEMPOTENCY FOR REFUNDS
-- -----------------------------
-- Assumes wallet_ledger has: merchant_id, source, source_ref, etc.
create unique index if not exists uniq_wallet_ledger_shopify_refund
on public.wallet_ledger (merchant_id, source, source_ref)
where source = 'shopify_refund' and source_ref is not null;

-- =========================================================
-- END MIGRATION
-- =========================================================
