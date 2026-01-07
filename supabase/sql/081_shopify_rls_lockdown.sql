begin;

-- ============================
-- Enable RLS everywhere
-- ============================
alter table if exists public.shopify_orders enable row level security;
alter table if exists public.shopify_products enable row level security;
alter table if exists public.shopify_customers enable row level security;
alter table if exists public.shopify_tokens enable row level security;
alter table if exists public.shopify_backfill_jobs enable row level security;

-- ============================
-- Drop overly permissive grants
-- (Supabase API exposure is through PostgREST; RLS is the real gate,
--  but we still keep grants tight.)
-- ============================
revoke all on table public.shopify_orders from anon, authenticated;
revoke all on table public.shopify_products from anon, authenticated;
revoke all on table public.shopify_customers from anon, authenticated;
revoke all on table public.shopify_tokens from anon, authenticated;
revoke all on table public.shopify_backfill_jobs from anon, authenticated;

-- ============================
-- Policies: allow ONLY service_role
-- ============================
drop policy if exists "service_role_all_shopify_orders" on public.shopify_orders;
create policy "service_role_all_shopify_orders"
on public.shopify_orders
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service_role_all_shopify_products" on public.shopify_products;
create policy "service_role_all_shopify_products"
on public.shopify_products
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service_role_all_shopify_customers" on public.shopify_customers;
create policy "service_role_all_shopify_customers"
on public.shopify_customers
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service_role_all_shopify_tokens" on public.shopify_tokens;
create policy "service_role_all_shopify_tokens"
on public.shopify_tokens
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service_role_all_shopify_backfill_jobs" on public.shopify_backfill_jobs;
create policy "service_role_all_shopify_backfill_jobs"
on public.shopify_backfill_jobs
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

commit;
