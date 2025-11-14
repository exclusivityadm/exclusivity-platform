-- FULL FILE — run as a migration
create table if not exists loyalty_tier (
  id bigserial primary key,
  merchant_id uuid not null,
  name text not null,
  threshold_points int not null default 0
);

create table if not exists loyalty_badge (
  id bigserial primary key,
  merchant_id uuid not null,
  code text not null unique,
  name text not null,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists wallet_map (
  merchant_id uuid not null,
  customer_id text not null,
  wallet_address text not null,
  primary key (merchant_id, customer_id)
);

create table if not exists points_ledger (
  id bigserial primary key,
  merchant_id uuid not null,
  customer_id text not null,
  delta int not null,
  reason text not null,
  ref jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);
