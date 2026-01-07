/**
 * UI-04 Actions (frontend)
 * Uses backend AI action surfaces:
 *  - POST /ai/action/preview
 *  - POST /ai/action/execute
 */

import { apiPost, ApiResult } from "@/lib";

export type ActionIntent =
  | "pricing.apply_recommendation"
  | "blockchain.retry_failed_jobs"
  | "invoice.export_latest";

export type ActionPayload = {
  intent: ActionIntent;
  merchant_id: string;
  params?: Record<string, any>;
};

export type ActionPreviewResult = {
  ok: boolean;
  summary?: string;
  risk?: string;
  cost_estimate?: string;
  requires_plan?: string;
  action?: ActionPayload;
  message?: string;
};

export type ActionExecuteResult = {
  ok: boolean;
  message?: string;
  status_code?: number;
  details?: any;
};

export function previewAction(action: ActionPayload): Promise<ApiResult<ActionPreviewResult>> {
  return apiPost<ActionPreviewResult>("/ai/action/preview", {
    merchant_id: action.merchant_id,
    action,
  });
}

export function executeAction(action: ActionPayload): Promise<ApiResult<ActionExecuteResult>> {
  return apiPost<ActionExecuteResult>("/ai/action/execute", {
    merchant_id: action.merchant_id,
    action,
  });
}
