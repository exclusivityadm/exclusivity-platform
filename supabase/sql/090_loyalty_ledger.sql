begin;

-- =====================================================
-- Loyalty Ledger (Canonical, Idempotent)
-- =====================================================

create table if not exists public.loyalty_ledger (
    ledger_id uuid primary key default gen_random_uuid(),

    merchant_id uuid not null,
    source_type text not null,              -- 'shopify_order'
    source_id text not null,                -- order_id (string)
    
    customer_ref text,                      -- email or customer_id
    points_awarded integer not null default 0,

    metadata jsonb not null default '{}',

    created_at timestamptz not null default now()
);

-- -----------------------------------------------------
-- Idempotency: ONE ledger row per merchant + source
-- -----------------------------------------------------
create unique index if not exists ux_loyalty_idempotent
on public.loyalty_ledger (merchant_id, source_type, source_id);

-- -----------------------------------------------------
-- Query helpers
-- -----------------------------------------------------
create index if not exists ix_loyalty_merchant
on public.loyalty_ledger (merchant_id, created_at desc);

-- -----------------------------------------------------
-- Security
-- -----------------------------------------------------
alter table public.loyalty_ledger enable row level security;

revoke all on table public.loyalty_ledger from anon, authenticated;

drop policy if exists "service_role_all_loyalty_ledger" on public.loyalty_ledger;
create policy "service_role_all_loyalty_ledger"
on public.loyalty_ledger
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

commit;
