-- DROP B: Shadow Wallet Engine (internal-only)
-- Assumes you already have a "merchants" table with "id" (uuid)

create extension if not exists "pgcrypto";

-- 1) Customer wallets (one per merchant + customer_ref)
create table if not exists public.customer_wallets (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references public.merchants(id) on delete cascade,
  customer_ref text not null, -- Shopify customer id/email/whatever reference you choose
  created_at timestamptz not null default now()
);

create unique index if not exists customer_wallets_unique
  on public.customer_wallets (merchant_id, customer_ref);

create index if not exists customer_wallets_merchant_idx
  on public.customer_wallets (merchant_id);

-- 2) Ledger (append-only)
create table if not exists public.wallet_ledger (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references public.merchants(id) on delete cascade,
  wallet_id uuid not null references public.customer_wallets(id) on delete cascade,

  -- Idempotency key: must be unique per merchant
  event_id text not null,

  -- Points delta: positive=credit, negative=debit
  delta integer not null check (delta <> 0),

  reason text,
  source text default 'api',
  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now()
);

create unique index if not exists wallet_ledger_event_unique
  on public.wallet_ledger (merchant_id, event_id);

create index if not exists wallet_ledger_wallet_idx
  on public.wallet_ledger (wallet_id, created_at desc);

-- 3) Cached balances (maintained by trigger)
create table if not exists public.wallet_balances (
  wallet_id uuid primary key references public.customer_wallets(id) on delete cascade,
  merchant_id uuid not null references public.merchants(id) on delete cascade,
  balance integer not null default 0,
  updated_at timestamptz not null default now()
);

create index if not exists wallet_balances_merchant_idx
  on public.wallet_balances (merchant_id);

-- 4) Trigger to upsert/update balance whenever a ledger row is inserted
create or replace function public.apply_wallet_ledger_to_balance()
returns trigger
language plpgsql
as $$
begin
  insert into public.wallet_balances (wallet_id, merchant_id, balance, updated_at)
  values (new.wallet_id, new.merchant_id, new.delta, now())
  on conflict (wallet_id)
  do update set
    balance = public.wallet_balances.balance + excluded.balance,
    updated_at = now();

  return new;
end;
$$;

drop trigger if exists trg_apply_wallet_ledger_to_balance on public.wallet_ledger;

create trigger trg_apply_wallet_ledger_to_balance
after insert on public.wallet_ledger
for each row
execute function public.apply_wallet_ledger_to_balance();

-- NOTE: For private beta, keep RLS simple or off for these tables
-- because the backend uses service-role access.
