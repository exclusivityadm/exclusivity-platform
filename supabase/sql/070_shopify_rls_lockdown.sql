begin;

-- ------------------------------------------------------------
-- Enable RLS on Shopify system tables
-- ------------------------------------------------------------

alter table public.shopify_tokens enable row level security;
alter table public.shopify_orders enable row level security;
alter table public.shopify_products enable row level security;
alter table public.shopify_customers enable row level security;
alter table public.shopify_backfill_jobs enable row level security;

-- ------------------------------------------------------------
-- Revoke public access (defensive)
-- ------------------------------------------------------------

revoke all on public.shopify_tokens from anon, authenticated;
revoke all on public.shopify_orders from anon, authenticated;
revoke all on public.shopify_products from anon, authenticated;
revoke all on public.shopify_customers from anon, authenticated;
revoke all on public.shopify_backfill_jobs from anon, authenticated;

-- ------------------------------------------------------------
-- Service role full access (internal workers only)
-- ------------------------------------------------------------

grant all on public.shopify_tokens to service_role;
grant all on public.shopify_orders to service_role;
grant all on public.shopify_products to service_role;
grant all on public.shopify_customers to service_role;
grant all on public.shopify_backfill_jobs to service_role;

-- ------------------------------------------------------------
-- Explicit deny-all policies (future proof)
-- ------------------------------------------------------------

create policy "deny_all_tokens"
  on public.shopify_tokens
  for all
  using (false);

create policy "deny_all_orders"
  on public.shopify_orders
  for all
  using (false);

create policy "deny_all_products"
  on public.shopify_products
  for all
  using (false);

create policy "deny_all_customers"
  on public.shopify_customers
  for all
  using (false);

create policy "deny_all_backfill_jobs"
  on public.shopify_backfill_jobs
  for all
  using (false);

commit;
