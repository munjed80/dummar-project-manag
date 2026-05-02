/**
 * Translate a list-page load failure into a clean Arabic message for the
 * operator and (in dev mode) log the underlying structured ApiError to the
 * browser console so the real status / detail is never silently swallowed.
 *
 * This intentionally distinguishes:
 *   - 401         → the session expired / token missing
 *   - 403         → the logged-in role is not allowed by the backend
 *   - 502/503/504 → transient gateway error; show a clean retry-friendly
 *                   Arabic message and DO NOT leak any HTML body
 *   - other 5xx   → backend runtime failure, surface the JSON `detail`
 *   - else        → network / unknown error, still surface what we know
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
  /** True if this is a transient infrastructure error (502/503/504, network)
   *  for which the UI should suggest a retry. */
  isTransient: boolean;
}

const TRANSIENT_GATEWAY_STATUSES = new Set([502, 503, 504]);

export function describeLoadError(err: unknown, entityLabel: string): LoadErrorInfo {
  // Always log the raw error in dev so the operator sees the real cause.
  if (import.meta.env?.DEV) {
    // eslint-disable-next-line no-console
    console.error(`[load:${entityLabel}]`, err);
  }

  if (err instanceof ApiError) {
    // Use detail only when it's a real backend message (never raw HTML — the
    // api.ts readErrorBody helper already discards HTML bodies, but we still
    // guard here in case a future caller passes through unsanitized text).
    const detailRaw = err.detail ?? '';
    const detail = /^\s*<(!doctype|html|\?xml)/i.test(detailRaw) ? '' : detailRaw;

    if (err.status === 401) {
      return {
        status: 401,
        isAuth: true,
        isTransient: false,
        message: 'انتهت الجلسة أو الرمز غير صالح. يرجى تسجيل الدخول من جديد.',
      };
    }
    if (err.status === 403) {
      return {
        status: 403,
        isAuth: true,
        isTransient: false,
        message: `ليس لديك صلاحية لعرض ${entityLabel} (HTTP ${err.status}${detail ? `: ${detail}` : ''}).`,
      };
    }
    if (TRANSIENT_GATEWAY_STATUSES.has(err.status)) {
      // Gateway error — typically nginx returning its default text/html 502
      // page when the backend was momentarily unreachable. NEVER include the
      // body here. Show a clean retry-friendly Arabic message that does NOT
      // leak the raw HTTP code into the user-facing UI; the structured
      // diagnostic logged above still preserves status/url/content-type for
      // developers.
      return {
        status: err.status,
        isAuth: false,
        isTransient: true,
        message: 'تعذر تحميل البيانات حالياً. قد تكون الخدمة مشغولة مؤقتاً. يرجى إعادة المحاولة.',
      };
    }
    if (err.status >= 500) {
      return {
        status: err.status,
        isAuth: false,
        isTransient: false,
        message: `خطأ في الخادم أثناء تحميل ${entityLabel} (HTTP ${err.status}${detail ? `: ${detail}` : ''}).`,
      };
    }
    return {
      status: err.status,
      isAuth: false,
      isTransient: false,
      message: `تعذّر تحميل ${entityLabel} (HTTP ${err.status}${detail ? `: ${detail}` : ''}).`,
    };
  }

  // Non-ApiError: typically a TypeError from fetch (network down, CORS, DNS).
  // These are also transient from the user's perspective. Keep the user-
  // facing copy clean — the underlying message is logged above for devs.
  return {
    status: null,
    isAuth: false,
    isTransient: true,
    message: 'تعذر تحميل البيانات حالياً. تحقق من الاتصال بالشبكة ثم أعد المحاولة.',
  };
}
