-- =========================================================
-- EXCL: Brand + Catalog + Pricing Intelligence (v1)
-- =========================================================

-- Catalog snapshots (so pricing engine has stable data to reason on)
create table if not exists public.merchant_catalog_snapshots (
  id uuid primary key default gen_random_uuid(),
  merchant_id text not null,
  shop_domain text not null,
  captured_at timestamptz not null default now(),
  payload jsonb not null default '{}'::jsonb
);

create index if not exists idx_catalog_snapshots_merchant on public.merchant_catalog_snapshots (merchant_id);
create index if not exists idx_catalog_snapshots_captured on public.merchant_catalog_snapshots (captured_at desc);

-- Pricing recommendations (the “buffer” logic lives here, merchant-facing naming only)
create table if not exists public.merchant_pricing_recommendations (
  id uuid primary key default gen_random_uuid(),
  merchant_id text not null,
  shop_domain text not null,
  captured_at timestamptz not null default now(),
  strategy text not null default 'flat_buffer',   -- future: margin_aware, tier_aware, etc.
  buffer_cents int not null default 0,
  notes text null,
  payload jsonb not null default '{}'::jsonb
);

create index if not exists idx_pricing_recs_merchant on public.merchant_pricing_recommendations (merchant_id);
create index if not exists idx_pricing_recs_captured on public.merchant_pricing_recommendations (captured_at desc);

-- RLS (service_role uses bypass; still lock public access)
alter table public.merchant_catalog_snapshots enable row level security;
alter table public.merchant_pricing_recommendations enable row level security;

-- Updated_at triggers (only if your set_updated_at exists)
do $$
begin
  if exists (select 1 from pg_proc where proname = 'set_updated_at') then
    -- these tables don’t currently have updated_at columns by design (append-only).
    -- leave as-is.
    null;
  end if;
end $$;
