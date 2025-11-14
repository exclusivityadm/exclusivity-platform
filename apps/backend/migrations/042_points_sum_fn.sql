-- FULL FILE — run as a migration
create or replace function sum_points(m uuid, c text)
returns table(sum bigint)
language sql
as $$
  select coalesce(sum(delta),0) from points_ledger
   where merchant_id=m and customer_id=c
$$;
