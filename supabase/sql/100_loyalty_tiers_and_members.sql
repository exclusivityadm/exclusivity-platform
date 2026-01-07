begin;

-- =====================================================
-- Loyalty tiers (per merchant)
-- =====================================================
create table if not exists public.loyalty_tiers (
  tier_id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,

  tier_name text not null,
  tier_rank integer not null,                -- 1..N (ascending)
  threshold_points integer not null default 0,

  benefits jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists ux_loyalty_tiers_unique
on public.loyalty_tiers (merchant_id, tier_rank);

create index if not exists ix_loyalty_tiers_merchant
on public.loyalty_tiers (merchant_id, tier_rank);


-- =====================================================
-- Loyalty members (current state per customer_ref)
-- =====================================================
create table if not exists public.loyalty_members (
  member_id uuid primary key default gen_random_uuid(),

  merchant_id uuid not null,
  customer_ref text not null,                -- email preferred

  points_total integer not null default 0,
  tier_rank integer not null default 1,
  tier_name text not null default 'Tier 1',

  last_source text,                          -- e.g. 'ledger_rollup'
  last_evaluated_at timestamptz,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists ux_loyalty_members_unique
on public.loyalty_members (merchant_id, customer_ref);

create index if not exists ix_loyalty_members_merchant
on public.loyalty_members (merchant_id, tier_rank);


-- =====================================================
-- RLS (service_role only for now)
-- =====================================================
alter table public.loyalty_tiers enable row level security;
alter table public.loyalty_members enable row level security;

revoke all on table public.loyalty_tiers from anon, authenticated;
revoke all on table public.loyalty_members from anon, authenticated;

drop policy if exists "service_role_all_loyalty_tiers" on public.loyalty_tiers;
create policy "service_role_all_loyalty_tiers"
on public.loyalty_tiers
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service_role_all_loyalty_members" on public.loyalty_members;
create policy "service_role_all_loyalty_members"
on public.loyalty_members
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

commit;
