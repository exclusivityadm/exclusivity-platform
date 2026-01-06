-- =========================================================
-- EXCLUSIVITY — SHOPIFY WEBHOOK REGISTRY (OPTIONAL)
-- =========================================================

create extension if not exists "pgcrypto";

create table if not exists public.shopify_webhook_registry (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null unique,
  shop_domain text not null,
  orders_paid_webhook_id bigint,
  orders_refunded_webhook_id bigint,
  updated_at timestamptz not null default now()
);

comment on table public.shopify_webhook_registry is
  'Stores Shopify webhook ids for maintenance / debugging. Not required for engine correctness.';

-- =========================================================
-- END MIGRATION
-- =========================================================
