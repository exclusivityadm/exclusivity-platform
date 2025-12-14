/*
========================================================
 Loyalty RLS Policies (Canonical)
========================================================

Security model:
- Server-authoritative
- No direct client writes
- Service role only for mutations
- Read access allowed only through server routes

This aligns with:
- Non-public loyalty program
- Email → wallet abstraction
- No customer-facing ledger access
*/

-- Enable RLS
alter table public.loyalty_policies enable row level security;
alter table public.loyalty_members enable row level security;
alter table public.loyalty_ledger_events enable row level security;


-- -----------------------------------------------------
-- Policies: loyalty_policies
-- -----------------------------------------------------
drop policy if exists "Server access only" on public.loyalty_policies;

create policy "Server access only"
on public.loyalty_policies
for all
using (
    auth.role() = 'service_role'
)
with check (
    auth.role() = 'service_role'
);


-- -----------------------------------------------------
-- Policies: loyalty_members
-- -----------------------------------------------------
drop policy if exists "Server access only" on public.loyalty_members;

create policy "Server access only"
on public.loyalty_members
for all
using (
    auth.role() = 'service_role'
)
with check (
    auth.role() = 'service_role'
);


-- -----------------------------------------------------
-- Policies: loyalty_ledger_events
-- -----------------------------------------------------
drop policy if exists "Server access only" on public.loyalty_ledger_events;

create policy "Server access only"
on public.loyalty_ledger_events
for all
using (
    auth.role() = 'service_role'
)
with check (
    auth.role() = 'service_role'
);
