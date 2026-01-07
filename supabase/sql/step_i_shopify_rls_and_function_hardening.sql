-- supabase/sql/step_i_shopify_rls_and_function_hardening.sql
-- ==========================================================
-- Exclusivity — Step I
-- Lock down Shopify tables and harden claim_shopify_backfill_job
--
-- Fixes:
-- 1) "Table public.shopify_* is public, but RLS has not been enabled."
-- 2) "shopify_tokens exposed without RLS + access_token sensitive"
-- 3) "Function public.claim_shopify_backfill_job has a role mutable search_path"
-- 4) "function name ... is not unique" (multiple overloads) — handled safely by iterating overloads
--
-- Notes:
-- - This enables RLS and makes access "service_role only".
-- - Your backend uses the Supabase SERVICE ROLE key for admin operations.
-- ==========================================================

begin;

-- ----------------------------------------------------------
-- A) TABLE PRIVILEGES: revoke from anon/authenticated
-- ----------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array[
    'public.shopify_orders',
    'public.shopify_products',
    'public.shopify_customers',
    'public.shopify_tokens',
    'public.shopify_backfill_jobs'
  ]
  loop
    execute format('revoke all on table %s from anon;', t);
    execute format('revoke all on table %s from authenticated;', t);

    -- keep service_role access
    execute format('grant all on table %s to service_role;', t);
  end loop;
end $$;

-- ----------------------------------------------------------
-- B) ENABLE RLS + "service_role only" policies
-- ----------------------------------------------------------
do $$
declare
  t text;
  pol text;
begin
  foreach t in array array[
    'public.shopify_orders',
    'public.shopify_products',
    'public.shopify_customers',
    'public.shopify_tokens',
    'public.shopify_backfill_jobs'
  ]
  loop
    -- Enable RLS
    execute format('alter table %s enable row level security;', t);

    -- Drop any prior policies we created with the same names (idempotent)
    pol := replace(t, 'public.', '') || '_service_role_only_select';
    execute format('drop policy if exists %I on %s;', pol, t);
    pol := replace(t, 'public.', '') || '_service_role_only_insert';
    execute format('drop policy if exists %I on %s;', pol, t);
    pol := replace(t, 'public.', '') || '_service_role_only_update';
    execute format('drop policy if exists %I on %s;', pol, t);
    pol := replace(t, 'public.', '') || '_service_role_only_delete';
    execute format('drop policy if exists %I on %s;', pol, t);

    -- Create "service_role only" policies for all actions.
    -- In Supabase, service role requests carry role=service_role.
    execute format(
      'create policy %I on %s for select using (auth.role() = ''service_role'');',
      replace(t, 'public.', '') || '_service_role_only_select',
      t
    );
    execute format(
      'create policy %I on %s for insert with check (auth.role() = ''service_role'');',
      replace(t, 'public.', '') || '_service_role_only_insert',
      t
    );
    execute format(
      'create policy %I on %s for update using (auth.role() = ''service_role'') with check (auth.role() = ''service_role'');',
      replace(t, 'public.', '') || '_service_role_only_update',
      t
    );
    execute format(
      'create policy %I on %s for delete using (auth.role() = ''service_role'');',
      replace(t, 'public.', '') || '_service_role_only_delete',
      t
    );
  end loop;
end $$;

-- ----------------------------------------------------------
-- C) FUNCTION HARDENING: fix role-mutable search_path on ALL overloads
-- ----------------------------------------------------------
-- This handles the "function is not unique" situation safely:
-- It finds every overload of public.claim_shopify_backfill_job(...)
-- and applies: SECURITY DEFINER + SET search_path = public, pg_temp
do $$
declare
  r record;
  fn_ident text;
begin
  for r in
    select
      n.nspname as schema_name,
      p.proname as func_name,
      pg_get_function_identity_arguments(p.oid) as args
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'claim_shopify_backfill_job'
  loop
    fn_ident := format('%I.%I(%s)', r.schema_name, r.func_name, r.args);

    -- Set stable search_path (removes "role mutable search_path" warning)
    execute format('alter function %s set search_path = public, pg_temp;', fn_ident);

    -- Ensure SECURITY DEFINER (common requirement for safe queue-claim funcs)
    execute format('alter function %s security definer;', fn_ident);
  end loop;
end $$;

commit;
