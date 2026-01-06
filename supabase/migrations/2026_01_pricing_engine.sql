-- =========================================================
-- EXCLUSIVITY — PRICING ENGINE (GAS BAKED-IN)
-- EXCL-END2END-06
-- =========================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------
-- Merchant pricing policy (gas/mint buffer strategy)
-- ---------------------------------------------------------
create table if not exists public.merchant_pricing_policy (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null unique,
  points_per_dollar numeric not null default 1.0,

  -- Buffer strategy:
  -- recommended_uplift_percent is the default uplift applied to base prices
  -- min_buffer_cents is a hard floor to cover gas/mint variability
  recommended_uplift_percent numeric not null default 3.0,
  min_buffer_cents int not null default 50,

  -- Optional estimated per-mint cost in cents (gas abstraction)
  est_mint_cost_cents int not null default 25,

  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

comment on table public.merchant_pricing_policy is
  'Per-merchant pricing policy: uplift + buffer to abstract gas/mint costs. Merchant-invisible.';


-- ---------------------------------------------------------
-- Catalog snapshots (normalized “what the merchant sells”)
-- ---------------------------------------------------------
create table if not exists public.pricing_catalog_snapshots (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  source text not null default 'manual', -- shopify|manual|brand_ingest
  captured_at timestamptz not null default now(),
  item_count int not null default 0,
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_pricing_catalog_snapshots_merchant_time
  on public.pricing_catalog_snapshots (merchant_id, captured_at desc);

comment on table public.pricing_catalog_snapshots is
  'Point-in-time snapshots of a merchant catalog used for pricing recommendations.';


-- ---------------------------------------------------------
-- Snapshot items (variants/SKUs)
-- ---------------------------------------------------------
create table if not exists public.pricing_catalog_items (
  id uuid primary key default gen_random_uuid(),
  snapshot_id uuid not null,
  merchant_id uuid not null,

  product_ref text,         -- Shopify product id or internal ref
  variant_ref text,         -- Shopify variant id or internal ref
  sku text,
  title text,

  currency text not null default 'USD',
  base_price_cents int not null,
  compare_at_cents int,
  cost_cents int,           -- optional; if known
  taxable boolean not null default true,
  active boolean not null default true,

  created_at timestamptz not null default now()
);

create index if not exists idx_pricing_catalog_items_snapshot
  on public.pricing_catalog_items (snapshot_id);

create index if not exists idx_pricing_catalog_items_merchant
  on public.pricing_catalog_items (merchant_id);

comment on table public.pricing_catalog_items is
  'Catalog items (variants) associated to a catalog snapshot. Prices stored in cents.';


-- ---------------------------------------------------------
-- Pricing recommendations (top-level)
-- ---------------------------------------------------------
create table if not exists public.pricing_recommendations (
  id uuid primary key defaul
