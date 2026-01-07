/**
 * UI-03 API surface (frontend)
 * Read-only, engine-first
 */

import { ApiResult, apiGet } from "@/lib";

export type PricingRecommendation = {
  id?: string;
  uplift_percent?: number;
  buffer_cents?: number;
  created_at?: string;
};

export type MintJob = {
  id?: string;
  status?: "queued" | "processing" | "retrying" | "failed" | "completed";
  attempts?: number;
  error_last?: string | null;
  created_at?: string;
};

export type Invoice = {
  id?: string;
  period_start?: string;
  period_end?: string;
  total_cents?: number;
  status?: string;
  created_at?: string;
};

export const getLatestPricing = (merchant_id: string) =>
  apiGet<PricingRecommendation>(
    `/pricing/recommendations/latest?merchant_id=${encodeURIComponent(merchant_id)}`
  );

export const getMintJobs = (merchant_id: string) =>
  apiGet<MintJob[]>(
    `/blockchain/jobs?merchant_id=${encodeURIComponent(merchant_id)}`
  );

export const getLatestInvoice = (merchant_id: string) =>
  apiGet<Invoice>(
    `/monetize/invoices/latest?merchant_id=${encodeURIComponent(merchant_id)}`
  );
