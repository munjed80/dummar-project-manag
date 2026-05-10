/**
 * Canonical Arabic labels for each backend UserRole.
 *
 * Single source of truth — every page that renders a role badge or selector
 * MUST import from here so a label change propagates everywhere instead of
 * drifting per-page (e.g. "مسؤول الشكاوى" vs "رئيس القسم الفني" before
 * centralization).
 */
export const ROLE_LABELS: Record<string, string> = {
  project_director: 'مدير المشروع',
  contracts_manager: 'مدير العقود',
  engineer_supervisor: 'مشرف هندسي',
  // Renamed per spec: was "مسؤول الشكاوى"
  complaints_officer: 'رئيس القسم الفني',
  area_supervisor: 'مشرف منطقة',
  field_team: 'فريق تنفيذي',
  contractor_user: 'مقاول',
  citizen: 'مواطن',
  property_manager: 'مسؤول الأصول',
  // Display label per spec — internal enum value stays "investment_manager"
  investment_manager: 'مكتب الاستثمار',
};

/** Lookup a role label, falling back to the raw role string when unknown. */
export function getRoleLabel(role: string | null | undefined): string {
  if (!role) return 'مستخدم';
  return ROLE_LABELS[role] ?? role;
}
