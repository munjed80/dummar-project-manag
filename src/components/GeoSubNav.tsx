import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { MapTrifold, MapPin, Globe } from '@phosphor-icons/react';

/**
 * Sub-navigation strip for the consolidated geographic section.
 *
 * The main top-level nav exposes a single entry — "خريطة العمليات" — and the
 * previously-separate "المواقع المرجعية" (Locations) and "التحليلات الجغرافية" (Geo
 * Dashboard) menu items now live as tabs inside that section. The pages
 * themselves are still individually routable so old bookmarks keep working.
 *
 * Tabs are role-gated to match the existing route guards in App.tsx:
 *   /complaints-map         → all internal staff
 *   /locations              → all internal staff
 *   /locations/geo-dashboard→ project_director, contracts_manager,
 *                              engineer_supervisor, complaints_officer,
 *                              area_supervisor (REPORT_ROLES)
 */
export type GeoSubNavTab = 'map' | 'locations' | 'geo';

const REPORT_ROLES = new Set([
  'project_director',
  'contracts_manager',
  'engineer_supervisor',
  'complaints_officer',
  'area_supervisor',
]);

const INTERNAL_ROLES = new Set([
  'project_director',
  'contracts_manager',
  'engineer_supervisor',
  'complaints_officer',
  'area_supervisor',
  'field_team',
  'contractor_user',
]);

export function GeoSubNav({ active }: { active: GeoSubNavTab }) {
  const { role } = useAuth();
  const tabs: { key: GeoSubNavTab; to: string; label: string; icon: React.ElementType; visible: boolean }[] = [
    {
      key: 'map',
      to: '/complaints-map',
      label: 'الخريطة',
      icon: MapTrifold,
      visible: !!role && INTERNAL_ROLES.has(role),
    },
    {
      key: 'locations',
      to: '/locations',
      label: 'المواقع المرجعية',
      icon: MapPin,
      visible: !!role && INTERNAL_ROLES.has(role),
    },
    {
      key: 'geo',
      to: '/locations/geo-dashboard',
      label: 'التحليلات الجغرافية',
      icon: Globe,
      visible: !!role && REPORT_ROLES.has(role),
    },
  ];

  return (
    <nav className="flex flex-wrap gap-1 border-b border-border" aria-label="القسم الجغرافي">
      {tabs
        .filter((t) => t.visible)
        .map(({ key, to, label, icon: Icon }) => (
          <Link
            key={key}
            to={to}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              active === key
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            }`}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
    </nav>
  );
}
