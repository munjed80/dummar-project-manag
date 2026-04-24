/**
 * Translate a list-page load failure into a clean Arabic message for the
 * operator and (in dev mode) log the underlying structured ApiError to the
 * browser console so the real status / detail is never silently swallowed.
 *
 * This intentionally distinguishes:
 *   - 401  → the session expired / token missing
 *   - 403  → the logged-in role is not allowed by the backend
 *   - 5xx  → backend runtime failure, surface the real `detail`
 *   - else → network / unknown error, still surface what we know
 *
 * Callers should pass `entityLabel` in Arabic (e.g. "الشكاوى", "المهام").
 */

import { ApiError } from '@/services/api';

export interface LoadErrorInfo {
  /** Arabic message safe to render directly in the UI. */
  message: string;
  /** HTTP status code if known, else null. */
  status: number | null;
  /** True if the backend explicitly refused due to auth/role (401/403). */
  isAuth: boolean;
}

export function describeLoadError(err: unknown, entityLabel: string): LoadErrorInfo {
  // Always log the raw error in dev so the operator sees the real cause.
  if (import.meta.env?.DEV) {
    // eslint-disable-next-line no-console
    console.error(`[load:${entityLabel}]`, err);
  }

  if (err instanceof ApiError) {
    const detail = err.detail ?? err.statusText ?? '';
    if (err.status === 401) {
      return {
        status: 401,
        isAuth: true,
        message: 'انتهت الجلسة أو الرمز غير صالح. يرجى تسجيل الدخول من جديد.',
      };
    }
    if (err.status === 403) {
      return {
        status: 403,
        isAuth: true,
        message: `ليس لديك صلاحية لعرض ${entityLabel} (HTTP ${err.status}${detail ? `: ${detail}` : ''}).`,
      };
    }
    if (err.status >= 500) {
      return {
        status: err.status,
        isAuth: false,
        message: `خطأ في الخادم أثناء تحميل ${entityLabel} (HTTP ${err.status}${detail ? `: ${detail}` : ''}).`,
      };
    }
    return {
      status: err.status,
      isAuth: false,
      message: `تعذّر تحميل ${entityLabel} (HTTP ${err.status}${detail ? `: ${detail}` : ''}).`,
    };
  }

  const msg = err instanceof Error ? err.message : String(err ?? 'unknown error');
  return {
    status: null,
    isAuth: false,
    message: `تعذّر الاتصال بالخادم لتحميل ${entityLabel} (${msg}).`,
  };
}
