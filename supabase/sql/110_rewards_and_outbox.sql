begin;

-- =====================================================
-- Reward catalog (per merchant)
-- =====================================================
create table if not exists public.reward_catalog (
  reward_id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,

  reward_code text not null,                  -- stable identifier e.g. "WELCOME10"
  reward_name text not null,
  reward_type text not null default 'discount', -- discount | perk | gift | other
  required_tier_rank integer,                 -- optional gate
  required_points integer not null default 0, -- optional gate

  payload jsonb not null default '{}',        -- freeform (amount, message, etc.)
  is_active boolean not null default true,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists ux_reward_catalog_unique
on public.reward_catalog (merchant_id, reward_code);

create index if not exists ix_reward_catalog_merchant
on public.reward_catalog (merchant_id, is_active);


-- =====================================================
-- Reward events (earned/issued)
-- =====================================================
create table if not exists public.reward_events (
  event_id uuid primary key default gen_random_uuid(),

  merchant_id uuid not null,
  customer_ref text not null,                 -- email preferred

  event_type text not null,                   -- reward_issued | tier_up | points_awarded | etc.
  reward_code text,                           -- optional link to reward_catalog.reward_code
  points_snapshot integer,
  tier_rank_snapshot integer,
  tier_name_snapshot text,

  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists ix_reward_events_merchant
on public.reward_events (merchant_id, created_at desc);

create index if not exists ix_reward_events_customer
on public.reward_events (merchant_id, customer_ref, created_at desc);


-- =====================================================
-- Reward redemptions (claimed/used)
-- =====================================================
create table if not exists public.reward_redemptions (
  redemption_id uuid primary key default gen_random_uuid(),

  merchant_id uuid not null,
  customer_ref text not null,

  reward_code text not null,
  status text not null default 'claimed',      -- claimed | used | void
  external_ref text,                           -- e.g. Shopify discount id, order id, etc.

  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ix_reward_redemptions_merchant
on public.reward_redemptions (merchant_id, created_at desc);

create index if not exists ix_reward_redemptions_customer
on public.reward_redemptions (merchant_id, customer_ref, created_at desc);


-- =====================================================
-- Notification outbox (queue)
-- =====================================================
create table if not exists public.notification_outbox (
  outbox_id uuid primary key default gen_random_uuid(),

  merchant_id uuid not null,
  customer_ref text,                          -- optional (may notify merchant admin)
  channel text not null,                      -- email | sms | push | internal
  template_key text not null,                 -- e.g. "tier_up", "reward_issued"
  payload jsonb not null default '{}',

  status text not null default 'queued',      -- queued | sent | failed | skipped
  last_error text,
  attempts integer not null default 0,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ix_notification_outbox_status
on public.notification_outbox (status, created_at asc);

create index if not exists ix_notification_outbox_merchant
on public.notification_outbox (merchant_id, status, created_at asc);


-- =====================================================
-- RLS (service_role only for now)
-- =====================================================
alter table public.reward_catalog enable row level security;
alter table public.reward_events enable row level security;
alter table public.reward_redemptions enable row level security;
alter table public.notification_outbox enable row level security;

revoke all on table public.reward_catalog from anon, authenticated;
revoke all on table public.reward_events from anon, authenticated;
revoke all on table public.reward_redemptions from anon, authenticated;
revoke all on table public.notification_outbox from anon, authenticated;

drop policy if exists "service_role_all_reward_catalog" on public.reward_catalog;
create policy "service_role_all_reward_catalog"
on public.reward_catalog
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service_role_all_reward_events" on public.reward_events;
create policy "service_role_all_reward_events"
on public.reward_events
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service_role_all_reward_redemptions" on public.reward_redemptions;
create policy "service_role_all_reward_redemptions"
on public.reward_redemptions
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service_role_all_notification_outbox" on public.notification_outbox;
create policy "service_role_all_notification_outbox"
on public.notification_outbox
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

commit;
