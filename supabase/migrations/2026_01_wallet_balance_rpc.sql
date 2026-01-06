-- =========================================================
-- EXCLUSIVITY — WALLET BALANCE ATOMIC INCREMENT (RPC)
-- EXCL-END2END-03
-- =========================================================

create extension if not exists "pgcrypto";

-- Ensure wallet_balances exists (safe if it already exists)
create table if not exists public.wallet_balances (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  customer_id uuid not null,
  balance int not null default 0,
  updated_at timestamptz not null default now()
);

create unique index if not exists uniq_wallet_balances_merchant_customer
  on public.wallet_balances (merchant_id, customer_id);

comment on table public.wallet_balances is
  'Current token/points balance per merchant + customer. Updated via atomic RPC to avoid race conditions.';

-- Atomic increment RPC
create or replace function public.increment_wallet_balance(
  p_merchant_id uuid,
  p_customer_id uuid,
  p_delta int
)
returns table (
  merchant_id uuid,
  customer_id uuid,
  balance int
)
language plpgsql
as $$
begin
  -- Upsert row if missing
  insert into public.wallet_balances (merchant_id, customer_id, balance, updated_at)
  values (p_merchant_id, p_customer_id, 0, now())
  on conflict (merchant_id, customer_id) do nothing;

  -- Atomic increment
  update public.wallet_balances
  set balance = balance + p_delta,
      updated_at = now()
  where merchant_id = p_merchant_id
    and customer_id = p_customer_id
  returning public.wallet_balances.merchant_id,
            public.wallet_balances.customer_id,
            public.wallet_balances.balance
  into merchant_id, customer_id, balance;

  return next;
end;
$$;

comment on function public.increment_wallet_balance(uuid, uuid, int) is
  'Atomically increments wallet_balances.balance for a merchant/customer pair.';

-- =========================================================
-- END MIGRATION
-- =========================================================
