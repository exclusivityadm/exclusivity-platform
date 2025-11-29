-- ============================================
-- FIX ALL RLS POLICIES IN ONE SAFE SCRIPT
-- Converts auth.*() → (select auth.*())
-- ============================================

-- ai_logs
drop policy if exists "Server access only" on public.ai_logs;
create policy "Server access only" on public.ai_logs
for all
using ((select auth.role()) = 'service_role');

-- analytics
drop policy if exists "Server access only" on public.analytics;
create policy "Server access only" on public.analytics
for all
using ((select auth.role()) = 'service_role');

-- customers
drop policy if exists "Server access only" on public.customers;
create policy "Server access only" on public.customers
for all
using ((select auth.role()) = 'service_role');

-- nfts
drop policy if exists "Server access only" on public.nfts;
create policy "Server access only" on public.nfts
for all
using ((select auth.role()) = 'service_role');

-- settings
drop policy if exists "Server access only" on public.settings;
create policy "Server access only" on public.settings
for all
using ((select auth.role()) = 'service_role');

-- tiers
drop policy if exists "Server access only" on public.tiers;
create policy "Server access only" on public.tiers
for all
using ((select auth.role()) = 'service_role');

-- tokens
drop policy if exists "Server access only" on public.tokens;
create policy "Server access only" on public.tokens
for all
using ((select auth.role()) = 'service_role');

-- transactions
drop policy if exists "Server access only" on public.transactions;
create policy "Server access only" on public.transactions
for all
using ((select auth.role()) = 'service_role');
