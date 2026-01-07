-- =====================================================
-- Step L — Shopify tables hardening + function fix
-- =====================================================

-- 1) Enable RLS on Shopify tables (removes "public but no RLS" warnings)
alter table if exists public.shopify_orders enable row level security;
alter table if exists public.shopify_products enable row level security;
alter table if exists public.shopify_customers enable row level security;
alter table if exists public.shopify_tokens enable row level security;
alter table if exists public.shopify_backfill_jobs enable row level security;

-- 2) Lock down table privileges for anon/authenticated (service_role still works)
revoke all on table public.shopify_orders from anon, authenticated;
revoke all on table public.shopify_products from anon, authenticated;
revoke all on table public.shopify_customers from anon, authenticated;
revoke all on table public.shopify_tokens from anon, authenticated;
revoke all on table public.shopify_backfill_jobs from anon, authenticated;

-- NOTE: We intentionally do NOT add permissive RLS policies.
-- That means anon/authenticated cannot read/write.
-- Your backend uses service_role and is not blocked by RLS.

-- 3) Fix: claim_shopify_backfill_job "not unique" + lock search_path
-- Drop any overloads safely, then recreate ONE canonical function.

do $$
declare
  r record;
begin
  for r in
    select p.oid::regprocedure as sig
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'claim_shopify_backfill_job'
  loop
    execute format('drop function if exists %s;', r.sig);
  end loop;
end $$;

create or replace function public.claim_shopify_backfill_job(dry_run boolean default false)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_job record;
begin
  -- Claim the oldest queued job
  select *
    into v_job
  from public.shopify_backfill_jobs
  where status = 'queued'
  order by created_at asc
  limit 1
  for update skip locked;

  if not found then
    return null;
  end if;

  if dry_run then
    return to_jsonb(v_job);
  end if;

  update public.shopify_backfill_jobs
    set status = 'claimed',
        claimed_at = now(),
        updated_at = now()
  where id = v_job.id;

  select *
    into v_job
  from public.shopify_backfill_jobs
  where id = v_job.id;

  return to_jsonb(v_job);
end;
$$;
