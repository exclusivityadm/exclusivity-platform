-- FULL FILE — run as a migration
create table if not exists shopify_install (
  merchant_id uuid primary key,
  shop_domain text not null unique,
  access_token text not null,
  scope text,
  installed_at timestamptz default now()
);

create table if not exists shopify_webhook_log (
  id bigserial primary key,
  topic text not null,
  shop_domain text not null,
  payload jsonb not null,
  received_at timestamptz default now()
);
