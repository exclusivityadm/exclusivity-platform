-- =========================================================
-- EXCLUSIVITY — UNINSTALL + CANCELLED (ENGINE)
-- EXCL-END2END-05
-- =========================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------
-- MERCHANT STATUS FIELDS (best-effort; safe if already exist)
-- ---------------------------------------------------------
alter table public.merchants
  add column if not exists is_active boolean not null default true;

alter table public.merchants
  add column if not exists uninstalled_at timestamptz;

comment on column public.merchants.is_active is
  'If false, engine ignores incoming Shopify events.';

comment on column public.merchants.uninstalled_at is
  'Timestamp of Shopify app uninstall webhook.';

-- ---------------------------------------------------------
-- LEDGER IDEMPOTENCY FOR CANCELLED
-- ---------------------------------------------------------
create unique index if not exists uniq_wallet_ledger_shopify_cancelled
on public.wallet_ledger (merchant_id, source, source_ref)
where source = 'shopify_cancelled' and source_ref is not null;

-- =========================================================
-- END MIGRATION
-- =========================================================
