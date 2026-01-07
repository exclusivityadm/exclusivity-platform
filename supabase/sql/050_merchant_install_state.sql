-- supabase/sql/050_merchant_install_state.sql
-- =========================================================
-- Exclusivity: Merchant Install State Machine (Canonical)
--
-- States:
--   created
--   oauth_complete
--   backfill_pending
--   backfill_running
--   ready
--   error
--
-- Goals:
-- 1) Backend is the source of truth for install readiness.
-- 2) Frontend can gate onboarding/dashboard without guessing.
-- 3) Works even if older rows only had `installed` boolean.
-- =========================================================

begin;

-- 1) Enum for install state (safe-create)
do $$
begin
  if not exists (select 1 from pg_type where typname = 'merchant_install_state') then
    create type public.merchant_install_state as enum (
      'created',
      'oauth_complete',
      'backfill_pending',
      'backfill_running',
      'ready',
      'error'
    );
  end if;
end $$;

-- 2) Columns on merchants
alter table public.merchants
  add column if not exists install_state public.merchant_install_state,
  add column if not exists install_error text,
  add column if not exists oauth_completed_at timestamptz,
  add column if not exists ready_at timestamptz;

-- 3) Backfill existing merchants:
-- If an older row was marked installed=true, set ready.
-- Otherwise set created.
update public.merchants
set install_state = case
  when install_state is not null then install_state
  when installed is true then 'ready'::public.merchant_install_state
  else 'created'::public.merchant_install_state
end
where install_state is null;

-- 4) Ensure install_state is never null going forward
alter table public.merchants
  alter column install_state set not null;

-- 5) Optional: add a lightweight index for common lookups
-- shop_domain is heavily used by onboarding
create index if not exists idx_merchants_shop_domain on public.merchants (shop_domain);

-- 6) Optional: install_state index for dashboards/admin
create index if not exists idx_merchants_install_state on public.merchants (install_state);

-- 7) Optional: helper function to update install state (service-only)
-- NOTE: This does NOT enable RLS. It's just a controlled write surface.
create or replace function public.set_merchant_install_state(
  p_merchant_id uuid,
  p_state public.merchant_install_state,
  p_error text default null
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
  v_now timestamptz := now();
begin
  update public.merchants m
  set
    install_state = p_state,
    install_error = case when p_state = 'error' then coalesce(p_error, m.install_error) else null end,
    oauth_completed_at = case when p_state in ('oauth_complete','backfill_pending','backfill_running','ready') then coalesce(m.oauth_completed_at, v_now) else m.oauth_completed_at end,
    ready_at = case when p_state = 'ready' then coalesce(m.ready_at, v_now) else m.ready_at end,
    updated_at = v_now
  where m.merchant_id = p_merchant_id;

  if not found then
    return jsonb_build_object('ok', false, 'error', 'merchant_not_found');
  end if;

  return jsonb_build_object('ok', true, 'merchant_id', p_merchant_id, 'state', p_state::text);
end;
$$;

-- Lock down function execution: only postgres/service_role should execute
revoke all on function public.set_merchant_install_state(uuid, public.merchant_install_state, text) from public;
revoke all on function public.set_merchant_install_state(uuid, public.merchant_install_state, text) from anon;
revoke all on function public.set_merchant_install_state(uuid, public.merchant_install_state, text) from authenticated;

commit;
