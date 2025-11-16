-- ===============================
-- Exclusivity Platform — Schema
-- Loyalty core + Shopify install
-- ===============================

-- ===== Merchants & Settings =====
create table if not exists merchants (
  merchant_id uuid primary key default gen_random_uuid(),
  email text unique,
  name text,
  created_at timestamptz default now()
);

create table if not exists brand_settings (
  merchant_id uuid references merchants(merchant_id) on delete cascade,
  domain_allowlist text[] default '{}',
  token_name text default 'LUX',
  tier_unit text default 'points',
  primary_color text default '#111111',
  secondary_color text default '#999999',
  settings jsonb default '{}',
  updated_at timestamptz default now(),
  primary key (merchant_id)
);

-- ===== Tiers =====
create table if not exists tiers (
  merchant_id uuid references merchants(merchant_id) on delete cascade,
  code text,
  name text,
  min_points bigint default 0,
  benefits jsonb default '{}',
  sort_order int default 0,
  primary key (merchant_id, code)
);

-- ===== Customers & Balances =====
create table if not exists customers (
  merchant_id uuid references merchants(merchant_id) on delete cascade,
  customer_id text,
  email text,
  wallet text,
  created_at timestamptz default now(),
  primary key (merchant_id, customer_id)
);

create table if not exists points_balances (
  merchant_id uuid,
  customer_id text,
  points bigint default 0,
  updated_at timestamptz default now(),
  primary key (merchant_id, customer_id),
  foreign key (merchant_id, customer_id)
    references customers (merchant_id, customer_id)
    on delete cascade
);

-- ===== Points Ledger =====
create table if not exists points_ledger (
  id bigserial primary key,
  merchant_id uuid not null,
  customer_id text not null,
  delta bigint not null,
  reason text,
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

-- ===== Shopify Installed Shops =====
create table if not exists shopify_shops (
  shop text primary key,                -- e.g. mybrand.myshopify.com
  access_token text not null,
  scope text,
  merchant_id uuid,                     -- optional link to merchants
  installed_at timestamptz default now()
);

-- ===== Enable RLS (tighten later) =====
alter table merchants          enable row level security;
alter table brand_settings     enable row level security;
alter table tiers              enable row level security;
alter table customers          enable row level security;
alter table points_balances    enable row level security;
alter table points_ledger      enable row level security;
alter table shopify_shops      enable row level security;

-- ===== Service role can do all (backend uses service_role key) =====
create policy "service_all_merchants"         on merchants         for all using (true) with check (true);
create policy "service_all_brand_settings"    on brand_settings    for all using (true) with check (true);
create policy "service_all_tiers"             on tiers             for all using (true) with check (true);
create policy "service_all_customers"         on customers         for all using (true) with check (true);
create policy "service_all_points_balances"   on points_balances   for all using (true) with check (true);
create policy "service_all_points_ledger"     on points_ledger     for all using (true) with check (true);
create policy "service_all_shopify_shops"     on shopify_shops     for all using (true) with check (true);
