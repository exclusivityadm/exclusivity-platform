begin;

-- ------------------------------------------------------------
-- Drop ALL existing versions of the function (unambiguous)
-- ------------------------------------------------------------

drop function if exists public.claim_shopify_backfill_job();
drop function if exists public.claim_shopify_backfill_job(uuid);
drop function if exists public.claim_shopify_backfill_job(text);
drop function if exists public.claim_shopify_backfill_job(uuid, text);

-- ------------------------------------------------------------
-- Recreate canonical function (SECURE)
-- ------------------------------------------------------------

create function public.claim_shopify_backfill_job(
  p_merchant_id uuid
)
returns table (
  job_id uuid,
  merchant_id uuid,
  status text,
  created_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  update public.shopify_backfill_jobs
     set status = 'processing'
   where id = (
     select id
       from public.shopify_backfill_jobs
      where merchant_id = p_merchant_id
        and status = 'pending'
      order by created_at asc
      limit 1
      for update skip locked
   )
  returning
    id,
    merchant_id,
    status,
    created_at;
end;
$$;

-- ------------------------------------------------------------
-- Lock execution rights
-- ------------------------------------------------------------

revoke all on function public.claim_shopify_backfill_job(uuid) from public;
grant execute on function public.claim_shopify_backfill_job(uuid) to service_role;

commit;
