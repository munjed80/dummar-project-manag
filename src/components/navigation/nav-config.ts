import type { ElementType } from 'react';
import type { UserRole } from '@/hooks/useAuth';
import {
  Briefcase,
  Buildings,
  Brain,
  ChartBar,
  ChatCircleDots,
  ChatsCircle,
  ClipboardText,
  FileText,
  FolderOpen,
  GearSix,
  Gavel,
  House,
  IdentificationCard,
  ListChecks,
  MapTrifold,
  PaperPlaneTilt,
  Rows,
  ShieldCheck,
  SquaresFour,
  UserCircle,
  Users,
  UsersThree,
} from '@phosphor-icons/react';

/**
 * A single clickable leaf entry inside a sidebar group, or a top-level
 * single entry (e.g. Dashboard).
 */
export interface NavItem {
  path: string;
  icon: ElementType;
  label: string;
  /** Roles allowed to see this entry. Empty/undefined = visible to all. */
  roles?: UserRole[];
  /** Optional badge identifier; resolved at render time. */
  badge?: 'ai' | 'messages';
}

/**
 * A collapsible sidebar group.  Groups are the second navigation level
 * (the first level is the small list of single entries like Dashboard).
 */
export interface NavGroup {
  id: string;
  label: string;
  icon: ElementType;
  items: NavItem[];
}

/**
 * Top-level navigation entry: either a single direct link (Dashboard,
 * Citizen home) or a collapsible group of related items.
 */
export type NavEntry =
  | ({ kind: 'single' } & NavItem)
  | ({ kind: 'group' } & NavGroup);

/** All internal staff roles — used as the default roles list for shared items. */
const INTERNAL_ROLES: UserRole[] = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user',
  'property_manager', 'investment_manager',
];

const FIELD_ROLES: UserRole[] = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user',
];

const CONTRACTS_ROLES: UserRole[] = [
  'project_director', 'contracts_manager', 'investment_manager', 'property_manager',
];

const OPERATIONAL_CONTRACT_ROLES: UserRole[] = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor', 'investment_manager', 'property_manager',
];

const INSPECTION_ROLES: UserRole[] = FIELD_ROLES;

const REPORT_ROLES: UserRole[] = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor',
];

/**
 * Grouped sidebar navigation.  This is the primary configuration consumed
 * by the new <Sidebar /> component.  Routes are intentionally NOT renamed
 * here — only the visible labels and grouping have changed.
 */
export const NAV_ENTRIES: NavEntry[] = [
  {
    kind: 'single',
    path: '/dashboard',
    icon: House,
    label: 'لوحة القيادة',
    roles: INTERNAL_ROLES,
  },
  {
    kind: 'single',
    path: '/executive-briefing',
    icon: PaperPlaneTilt,
    label: 'موجز المحافظ',
    roles: INTERNAL_ROLES,
  },
  {
    kind: 'single',
    path: '/citizen',
    icon: UserCircle,
    label: 'شكاواي',
    roles: ['citizen'],
  },
  {
    kind: 'group',
    id: 'field-operations',
    label: 'العمليات الميدانية',
    icon: Briefcase,
    items: [
      { path: '/complaints', icon: ChatCircleDots, label: 'الشكاوى', roles: FIELD_ROLES },
      { path: '/tasks', icon: ListChecks, label: 'المهام', roles: FIELD_ROLES },
      { path: '/teams', icon: UsersThree, label: 'الفرق التنفيذية', roles: FIELD_ROLES },
      { path: '/projects', icon: FolderOpen, label: 'المشاريع', roles: FIELD_ROLES },
    ],
  },
  {
    kind: 'group',
    id: 'contracts-assets',
    label: 'العقود والأصول',
    icon: FileText,
    items: [
      { path: '/manual-contracts', icon: Rows, label: 'العقود التشغيلية', roles: OPERATIONAL_CONTRACT_ROLES },
      { path: '/investment-contracts', icon: ClipboardText, label: 'العقود الاستثمارية', roles: CONTRACTS_ROLES },
      { path: '/contract-intelligence', icon: Brain, label: 'مركز ذكاء العقود', roles: ['project_director', 'contracts_manager'], badge: 'ai' },
      // Note: route preserved as /investment-properties — labelled الأصول.
      { path: '/investment-properties', icon: Buildings, label: 'الأصول', roles: CONTRACTS_ROLES },
    ],
  },
  {
    kind: 'group',
    id: 'oversight-licensing',
    label: 'الرقابة والتراخيص',
    icon: ShieldCheck,
    items: [
      { path: '/licenses', icon: IdentificationCard, label: 'التراخيص', roles: OPERATIONAL_CONTRACT_ROLES },
      { path: '/violations', icon: Gavel, label: 'المخالفات', roles: FIELD_ROLES },
      { path: '/inspection-teams', icon: Users, label: 'فرق التفتيش', roles: INSPECTION_ROLES },
    ],
  },
  {
    kind: 'group',
    id: 'admin-control',
    label: 'الإدارة والتحكم',
    icon: SquaresFour,
    items: [
      { path: '/users', icon: UsersThree, label: 'المستخدمون', roles: ['project_director'] },
      { path: '/reports', icon: ChartBar, label: 'التقارير', roles: REPORT_ROLES },
      // Note: route preserved as /complaints-map — labelled خريطة العمليات.
      { path: '/complaints-map', icon: MapTrifold, label: 'خريطة العمليات', roles: FIELD_ROLES },
      { path: '/messages', icon: ChatsCircle, label: 'الرسائل الداخلية', roles: INTERNAL_ROLES, badge: 'messages' },
      { path: '/settings', icon: GearSix, label: 'الإعدادات' },
    ],
  },
];

/**
 * Filter a flat list of items by the current role.  Items without a
 * `roles` array are visible to every authenticated user.
 */
export function filterNavByRole<T extends { roles?: UserRole[] }>(items: T[], role: UserRole | null): T[] {
  return items.filter((item) => {
    if (!item.roles || item.roles.length === 0) return true;
    return role ? item.roles.includes(role) : false;
  });
}

/**
 * Filter the grouped navigation tree for the current role.  Empty groups
 * (where the user can see none of the items) are dropped from the result.
 */
export function filterEntriesByRole(entries: NavEntry[], role: UserRole | null): NavEntry[] {
  const result: NavEntry[] = [];
  for (const entry of entries) {
    if (entry.kind === 'single') {
      if (!entry.roles || entry.roles.length === 0 || (role && entry.roles.includes(role))) {
        result.push(entry);
      }
      continue;
    }
    const visibleItems = filterNavByRole(entry.items, role);
    if (visibleItems.length > 0) {
      result.push({ ...entry, items: visibleItems });
    }
  }
  return result;
}

export function formatRoleLabel(role: UserRole | null | undefined): string {
  if (!role) return 'مستخدم';
  const roleMap: Record<UserRole, string> = {
    project_director: 'مدير المشروع',
    contracts_manager: 'مدير العقود',
    engineer_supervisor: 'مشرف هندسي',
    complaints_officer: 'مسؤول الشكاوى',
    area_supervisor: 'مشرف منطقة',
    field_team: 'فريق ميداني',
    contractor_user: 'مستخدم متعهد',
    citizen: 'مواطن',
    property_manager: 'مدير الأصول',
    investment_manager: 'مدير الاستثمار',
  };
  return roleMap[role] ?? role;
}
