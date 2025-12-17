/*
========================================================
 Loyalty Schema (Canonical)
========================================================

Design goals:
- Deterministic
- Auditable
- Idempotent
- Non-punitive
- Server-authoritative

All money values are NUMERIC to avoid float drift.
All policy is stored as JSONB but enforced by application logic.
*/

-- -----------------------------
-- Loyalty Policies
-- -----------------------------
create table if not exists public.loyalty_policies (
    merchant_id text primary key,
    policy jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_loyalty_policies_updated
    on public.loyalty_policies (updated_at);


-- -----------------------------
-- Loyalty Members
-- -----------------------------
create table if not exists public.loyalty_members (
    merchant_id text not null,
    member_ref text not null, -- email or canonical customer ref
    lifetime_spend numeric(14,2) not null default 0.00,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (merchant_id, member_ref)
);

create index if not exists idx_loyalty_members_spend
    on public.loyalty_members (merchant_id, lifetime_spend desc);


-- -----------------------------
-- Loyalty Ledger Events
-- -----------------------------
create table if not exists public.loyalty_ledger_events (
    merchant_id text not null,
    event_id text not null,
    member_ref text not null,

    event_type text not null
        check (event_type in (
            'earn',
            'refund',
            'correction',
            'admin_grant',
            'admin_revoke'
        )),

    points_delta integer not null,
    idempotency_key text null,

    related_ref text null,       -- order_id, refund_id, etc
    related_line_ref text null,  -- order_line_id

    reason text null,
    meta jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),

    primary key (event_id)
);

-- Idempotency enforcement
create unique index if not exists uq_loyalty_ledger_idempotency
    on public.loyalty_ledger_events (idempotency_key)
    where idempotency_key is not null;

-- Query performance
create index if not exists idx_loyalty_ledger_member
    on public.loyalty_ledger_events (merchant_id, member_ref, created_at);

create index if not exists idx_loyalty_ledger_related
    on public.loyalty_ledger_events (merchant_id, related_ref);

create index if not exists idx_loyalty_ledger_type
    on public.loyalty_ledger_events (event_type);


-- -----------------------------
-- Updated-at trigger helper
-- -----------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_loyalty_policies_updated on public.loyalty_policies;
create trigger trg_loyalty_policies_updated
before update on public.loyalty_policies
for each row
execute function public.set_updated_at();

drop trigger if exists trg_loyalty_members_updated on public.loyalty_members;
create trigger trg_loyalty_members_updated
before update on public.loyalty_members
for each row
execute function public.set_updated_at();
