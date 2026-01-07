// apps/backend/shared/apiResult.ts
// Canonical API envelope used by ALL backend routes.

export type ApiOk<T> = {
  ok: true;
  data: T;
};

export type ApiErr = {
  ok: false;
  error: string;
  details?: any;
};

export type ApiResult<T> = ApiOk<T> | ApiErr;

export function ok<T>(data: T): ApiOk<T> {
  return { ok: true, data };
}

export function err(message: string, details?: any): ApiErr {
  return { ok: false, error: message, details };
}

// Optional: helper for unexpected exceptions
export function fromException(message: string, e: unknown): ApiErr {
  const details =
    e instanceof Error
      ? { name: e.name, message: e.message, stack: e.stack }
      : { value: e };
  return err(message, details);
}
