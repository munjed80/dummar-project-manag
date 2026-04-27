import type { UserRole } from '@/hooks/useAuth';

export const INTERNAL_ROLES: UserRole[] = [
  'project_director',
  'contracts_manager',
  'engineer_supervisor',
  'complaints_officer',
  'area_supervisor',
  'field_team',
  'contractor_user',
  'property_manager',
  'investment_manager',
];

export const REPORT_ROLES: UserRole[] = [
  'project_director',
  'contracts_manager',
  'engineer_supervisor',
  'complaints_officer',
  'area_supervisor',
];

export const CONTRACT_INTELLIGENCE_ROLES: UserRole[] = [
  'project_director',
  'contracts_manager',
];

export const INVESTMENT_PROPERTIES_ROLES: UserRole[] = [
  'project_director',
  'contracts_manager',
  'property_manager',
  'investment_manager',
];

export const INVESTMENT_CONTRACTS_ROLES: UserRole[] = [
  'project_director',
  'contracts_manager',
  'investment_manager',
  'property_manager',
];

export const MANUAL_CONTRACTS_ROLES: UserRole[] = [
  'project_director',
  'contracts_manager',
  'investment_manager',
  'property_manager',
  'engineer_supervisor',
  'complaints_officer',
  'area_supervisor',
];

export const OPERATIONAL_CONTRACT_ROLES: UserRole[] = [
  'project_director',
  'contracts_manager',
  'engineer_supervisor',
  'complaints_officer',
  'area_supervisor',
  'property_manager',
  'investment_manager',
];

export const NAV_ROLE_RULES = {
  dashboard: INTERNAL_ROLES,
  citizen: ['citizen'] as UserRole[],
  complaints: [
    'project_director',
    'contracts_manager',
    'engineer_supervisor',
    'complaints_officer',
    'area_supervisor',
    'field_team',
    'contractor_user',
  ] as UserRole[],
  tasks: [
    'project_director',
    'contracts_manager',
    'engineer_supervisor',
    'complaints_officer',
    'area_supervisor',
    'field_team',
    'contractor_user',
  ] as UserRole[],
  investmentContracts: INVESTMENT_CONTRACTS_ROLES,
  contractIntelligence: CONTRACT_INTELLIGENCE_ROLES,
  manualContracts: MANUAL_CONTRACTS_ROLES,
  investmentProperties: INVESTMENT_PROPERTIES_ROLES,
  teams: [
    'project_director',
    'contracts_manager',
    'engineer_supervisor',
    'complaints_officer',
    'area_supervisor',
    'field_team',
    'contractor_user',
  ] as UserRole[],
  projects: [
    'project_director',
    'contracts_manager',
    'engineer_supervisor',
    'complaints_officer',
    'area_supervisor',
    'field_team',
    'contractor_user',
  ] as UserRole[],
  complaintsMap: [
    'project_director',
    'contracts_manager',
    'engineer_supervisor',
    'complaints_officer',
    'area_supervisor',
    'field_team',
    'contractor_user',
  ] as UserRole[],
  users: ['project_director'] as UserRole[],
  reports: REPORT_ROLES,
};

export function roleDefaultRoute(role: UserRole | null): string {
  if (!role) return '/login';
  if (role === 'citizen') return '/citizen';
  if (role === 'property_manager') return '/investment-properties';
  if (role === 'investment_manager') return '/investment-contracts';
  return '/dashboard';
}
