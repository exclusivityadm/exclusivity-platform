begin;

-- ------------------------------------------------------------
-- Remove all overloaded versions so name is unique again
-- ------------------------------------------------------------
do $$
declare r record;
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

-- ------------------------------------------------------------
-- Recreate canonical function with locked search_path
-- NOTE: update the table/column names below ONLY if yours differ
-- ------------------------------------------------------------
create function public.claim_shopify_backfill_job(p_merchant_id uuid)
returns table (
  job_id uuid,
  merchant_id uuid,
  job_type text,
  status text,
  payload jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  with cte as (
    select *
    from public.shopify_backfill_jobs
    where merchant_id = p_merchant_id
      and status in ('queued','retry')
    order by created_at asc
    limit 1
    for update skip locked
  ),
  upd as (
    update public.shopify_backfill_jobs b
      set status = 'claimed',
          updated_at = now()
    from cte
    where b.job_id = cte.job_id
    returning b.*
  )
  select
    upd.job_id,
    upd.merchant_id,
    upd.job_type,
    upd.status,
    upd.payload,
    upd.created_at,
    upd.updated_at
  from upd;
end;
$$;

revoke all on function public.claim_shopify_backfill_job(uuid) from public;
grant execute on function public.claim_shopify_backfill_job(uuid) to service_role;

commit;
