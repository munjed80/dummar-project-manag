import type { ElementType } from 'react';
import type { UserRole } from '@/hooks/useAuth';
import { Buildings, Brain, ChartBar, ChatCircleDots, FileText, FolderOpen, GearSix, House, IdentificationCard, ListChecks, MapTrifold, Rows, UserCircle, Users, UsersThree, WarningCircle } from '@phosphor-icons/react';

export interface NavItem {
  path: string;
  icon: ElementType;
  label: string;
  section: 'home' | 'work' | 'contracts' | 'assets' | 'admin';
  mobileSection: 'home' | 'work' | 'contracts' | 'assets' | 'admin';
  roles?: UserRole[];
}

export const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard', icon: House, label: 'لوحة التحكم', section: 'home', mobileSection: 'home', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user', 'property_manager', 'investment_manager'] },
  { path: '/citizen', icon: UserCircle, label: 'شكاواي', section: 'home', mobileSection: 'home', roles: ['citizen'] },
  { path: '/complaints', icon: ChatCircleDots, label: 'الشكاوى', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
  { path: '/violations', icon: WarningCircle, label: 'المخالفات', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
  { path: '/tasks', icon: ListChecks, label: 'المهام', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
  { path: '/teams', icon: UsersThree, label: 'الفرق التنفيذية', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
  { path: '/inspection-teams', icon: Users, label: 'فرق التفتيش', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
  { path: '/projects', icon: FolderOpen, label: 'المشاريع', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
  { path: '/complaints-map', icon: MapTrifold, label: 'خريطة العمليات', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
  { path: '/messages', icon: ChatCircleDots, label: 'الرسائل الداخلية', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user', 'property_manager', 'investment_manager'] },
  { path: '/internal-bot', icon: Brain, label: 'المساعد الذكي', section: 'work', mobileSection: 'work', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user', 'property_manager', 'investment_manager'] },
  { path: '/investment-contracts', icon: FileText, label: 'العقود الاستثمارية', section: 'contracts', mobileSection: 'contracts', roles: ['project_director', 'contracts_manager', 'investment_manager', 'property_manager'] },
  { path: '/contract-intelligence', icon: Brain, label: 'تحليل عقود الاستثمار', section: 'contracts', mobileSection: 'contracts', roles: ['project_director', 'contracts_manager'] },
  { path: '/manual-contracts', icon: Rows, label: 'العقود التشغيلية', section: 'contracts', mobileSection: 'contracts', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'investment_manager', 'property_manager'] },
  { path: '/licenses', icon: IdentificationCard, label: 'التراخيص', section: 'contracts', mobileSection: 'contracts', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'investment_manager', 'property_manager'] },
  { path: '/investment-properties', icon: Buildings, label: 'الأصول', section: 'assets', mobileSection: 'assets', roles: ['project_director', 'contracts_manager', 'property_manager', 'investment_manager'] },
  { path: '/users', icon: UsersThree, label: 'المستخدمون', section: 'admin', mobileSection: 'admin', roles: ['project_director'] },
  { path: '/reports', icon: ChartBar, label: 'التقارير', section: 'admin', mobileSection: 'admin', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor'] },
  { path: '/settings', icon: GearSix, label: 'الإعدادات', section: 'admin', mobileSection: 'admin' },
];

export const DESKTOP_GROUP_LABELS: Record<NavItem['section'], string> = {
  home: 'الرئيسية',
  work: 'الطلبات والعمل',
  contracts: 'العقود',
  assets: 'الأصول',
  admin: 'الإدارة',
};

export const MOBILE_GROUP_LABELS: Record<NavItem['mobileSection'], string> = {
  home: 'الرئيسية',
  work: 'الطلبات والعمل',
  contracts: 'العقود',
  assets: 'الأصول',
  admin: 'الإدارة',
};

export function filterNavByRole(items: NavItem[], role: UserRole | null) {
  return items.filter((item) => {
    if (!item.roles || item.roles.length === 0) return true;
    return role ? item.roles.includes(role) : false;
  });
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
