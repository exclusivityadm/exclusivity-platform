-- ==========================================
-- EXCL: Install + Backfill + Onboarding (v1)
-- ==========================================

-- 1) Merchant integrations (authority bindings)
create table if not exists public.merchant_integrations (
  id uuid primary key default gen_random_uuid(),
  merchant_id text not null,
  provider text not null check (provider in ('shopify')),
  shop_domain text not null,
  access_token text not null,
  scopes text not null default '',
  installed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (provider, shop_domain),
  unique (merchant_id, provider)
);

create index if not exists idx_merchant_integrations_merchant on public.merchant_integrations (merchant_id);
create index if not exists idx_merchant_integrations_shop on public.merchant_integrations (shop_domain);

-- 2) Backfill runs (resumable + idempotent)
create table if not exists public.backfill_runs (
  id uuid primary key default gen_random_uuid(),
  merchant_id text not null,
  provider text not null check (provider in ('shopify')),
  shop_domain text not null,
  status text not null check (status in ('queued','running','completed','failed')),
  cursor text null,                      -- Shopify pagination cursor (page_info), stored as opaque
  last_order_id text null,               -- optional marker
  orders_processed int not null default 0,
  customers_seen int not null default 0,
  started_at timestamptz null,
  finished_at timestamptz null,
  error text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (merchant_id, provider)         -- one active run record per merchant/provider
);

create index if not exists idx_backfill_runs_status on public.backfill_runs (status);
create index if not exists idx_backfill_runs_merchant on public.backfill_runs (merchant_id);

-- 3) Merchant brand profile (theme + naming semantics)
create table if not exists public.merchant_brand (
  id uuid primary key default gen_random_uuid(),
  merchant_id text not null unique,
  shop_domain text null,
  brand_name text null,
  primary_color text null,
  secondary_color text null,
  font_family text null,
  tone_tags jsonb not null default '{}'::jsonb,

  -- naming semantics (no crypto language)
  program_name text not null default 'Loyalty Program',
  unit_name_singular text not null default 'Point',
  unit_name_plural text not null default 'Points',

  -- flags
  onboarding_completed boolean not null default false,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_merchant_brand_merchant on public.merchant_brand (merchant_id);

-- Updated_at trigger helper (assumes you already have set_updated_at())
-- If not present, you already created it earlier. This keeps consistency.
do $$
begin
  if exists (select 1 from pg_proc where proname = 'set_updated_at') then
    drop trigger if exists trg_merchant_integrations_updated_at on public.merchant_integrations;
    create trigger trg_merchant_integrations_updated_at
      before update on public.merchant_integrations
      for each row execute function public.set_updated_at();

    drop trigger if exists trg_backfill_runs_updated_at on public.backfill_runs;
    create trigger trg_backfill_runs_updated_at
      before update on public.backfill_runs
      for each row execute function public.set_updated_at();

    drop trigger if exists trg_merchant_brand_updated_at on public.merchant_brand;
    create trigger trg_merchant_brand_updated_at
      before update on public.merchant_brand
      for each row execute function public.set_updated_at();
  end if;
end $$;

-- RLS (Exclusivity backend uses service_role, but lock these down anyway)
alter table public.merchant_integrations enable row level security;
alter table public.backfill_runs enable row level security;
alter table public.merchant_brand enable row level security;

-- No public read policies by default.
-- Backend uses service_role; merchant-facing access later can be introduced via signed JWT + RLS policies.
