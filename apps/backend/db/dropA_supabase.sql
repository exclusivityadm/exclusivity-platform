create table if not exists public.merchants (
  id uuid primary key,
  shop_domain text unique not null,
  shopify_access_token text not null,
  plan text default 'beta',
  created_at timestamptz default now()
);

create table if not exists public.merchant_onboarding (
  merchant_id uuid primary key references public.merchants(id) on delete cascade,
  status text not null default 'installed',
  updated_at timestamptz default now()
);

create table if not exists public.loyalty_config (
  merchant_id uuid primary key references public.merchants(id) on delete cascade,
  points_label text not null default 'Points',
  earn_rate numeric not null default 1.0,
  currency text not null default 'USD',
  enabled boolean not null default true,
  updated_at timestamptz default now()
);

create table if not exists public.loyalty_tiers (
  merchant_id uuid references public.merchants(id) on delete cascade,
  tier text not null,
  threshold integer not null default 0,
  primary key (merchant_id, tier)
);

-- RLS: backend uses service role; keep tables protected
alter table public.merchants enable row level security;
alter table public.merchant_onboarding enable row level security;
alter table public.loyalty_config enable row level security;
alter table public.loyalty_tiers enable row level security;

-- Minimal policies (service role bypasses RLS; these are defensive defaults)
do $$ begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='merchants') then
    create policy "No direct public access" on public.merchants for all using (false) with check (false);
  end if;
end $$;

do $$ begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='merchant_onboarding') then
    create policy "No direct public access" on public.merchant_onboarding for all using (false) with check (false);
  end if;
end $$;

do $$ begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='loyalty_config') then
    create policy "No direct public access" on public.loyalty_config for all using (false) with check (false);
  end if;
end $$;

do $$ begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='loyalty_tiers') then
    create policy "No direct public access" on public.loyalty_tiers for all using (false) with check (false);
  end if;
end $$;
