import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { CaretLeft } from '@phosphor-icons/react';
import { cn } from '@/lib/utils';
import type { NavEntry, NavItem } from '@/components/navigation/nav-config';

export interface SidebarBadges {
  /** Number of unread internal-message threads (0 = no badge). */
  messages?: number;
}

interface SidebarProps {
  entries: NavEntry[];
  pathname: string;
  badges?: SidebarBadges;
  /** Called when a link is activated — used to close the mobile drawer. */
  onNavigate?: () => void;
  /** Compact = mobile drawer (no surrounding panel chrome). */
  compact?: boolean;
}

function isActive(pathname: string, path: string): boolean {
  return pathname === path || pathname.startsWith(`${path}/`);
}

function groupHasActive(entry: Extract<NavEntry, { kind: 'group' }>, pathname: string): boolean {
  return entry.items.some((it) => isActive(pathname, it.path));
}

/**
 * Storage key for which groups are open.  Persists across reloads so the
 * admin's chosen view is remembered, just like WordPress / Xtream Codes.
 */
const OPEN_GROUPS_KEY = 'sidebar.openGroups.v1';

function loadOpenGroups(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(OPEN_GROUPS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return typeof parsed === 'object' && parsed ? parsed : {};
  } catch {
    return {};
  }
}

function NavBadge({ kind, messages }: { kind: NavItem['badge']; messages?: number }) {
  if (kind === 'ai') {
    return (
      <span className="ml-auto inline-flex items-center rounded-md bg-gradient-to-r from-indigo-500/30 to-fuchsia-500/30 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-100 ring-1 ring-inset ring-indigo-300/30">
        AI
      </span>
    );
  }
  if (kind === 'messages' && messages && messages > 0) {
    return (
      <span className="ml-auto inline-flex min-w-[20px] items-center justify-center rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
        {messages > 99 ? '99+' : messages}
      </span>
    );
  }
  return null;
}

function LeafLink({
  item,
  pathname,
  onNavigate,
  badges,
  indented,
}: {
  item: NavItem;
  pathname: string;
  onNavigate?: () => void;
  badges?: SidebarBadges;
  indented: boolean;
}) {
  const active = isActive(pathname, item.path);
  const Icon = item.icon;
  return (
    <Link
      to={item.path}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
        indented && 'mr-2 ps-9 pe-3',
        active
          ? 'bg-sky-500/15 text-white shadow-[inset_0_0_0_1px_rgba(125,211,252,0.25)]'
          : 'text-slate-300 hover:bg-white/5 hover:text-white',
      )}
    >
      {active && (
        <span
          aria-hidden
          className="absolute inset-y-1 right-0 w-[3px] rounded-l-full bg-[#C8A24A]"
        />
      )}
      <Icon
        size={18}
        weight={active ? 'fill' : 'regular'}
        className={active ? 'text-sky-300' : 'text-slate-400 group-hover:text-slate-200'}
      />
      <span className="truncate">{item.label}</span>
      <NavBadge kind={item.badge} messages={badges?.messages} />
    </Link>
  );
}

function SidebarGroup({
  entry,
  pathname,
  badges,
  onNavigate,
  initiallyOpen,
  onToggle,
}: {
  entry: Extract<NavEntry, { kind: 'group' }>;
  pathname: string;
  badges?: SidebarBadges;
  onNavigate?: () => void;
  initiallyOpen: boolean;
  onToggle: (open: boolean) => void;
}) {
  const [open, setOpen] = useState<boolean>(initiallyOpen);
  const Icon = entry.icon;
  const hasActive = groupHasActive(entry, pathname);

  // If the user navigates via deep link into this group while it's
  // collapsed, auto-expand so the active item is visible.
  useEffect(() => {
    if (hasActive && !open) {
      setOpen(true);
      onToggle(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasActive]);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    onToggle(next);
  };

  return (
    <li>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-controls={`nav-group-${entry.id}`}
        className={cn(
          'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition-colors',
          hasActive
            ? 'text-white'
            : 'text-slate-200 hover:bg-white/5 hover:text-white',
        )}
      >
        <Icon
          size={18}
          weight={hasActive ? 'fill' : 'regular'}
          className={hasActive ? 'text-sky-300' : 'text-slate-400'}
        />
        <span className="truncate">{entry.label}</span>
        <CaretLeft
          size={14}
          className={cn(
            'ml-auto text-slate-500 transition-transform duration-200',
            open ? '-rotate-90' : 'rotate-0',
          )}
        />
      </button>
      <div
        id={`nav-group-${entry.id}`}
        hidden={!open}
        className={cn('mt-1 overflow-hidden', open ? 'block' : 'hidden')}
      >
        <ul className="space-y-0.5 border-r border-white/5 pr-2">
          {entry.items.map((item) => (
            <li key={item.path}>
              <LeafLink
                item={item}
                pathname={pathname}
                onNavigate={onNavigate}
                badges={badges}
                indented
              />
            </li>
          ))}
        </ul>
      </div>
    </li>
  );
}

export function SidebarNav({ entries, pathname, badges, onNavigate, compact }: SidebarProps) {
  const [openMap, setOpenMap] = useState<Record<string, boolean>>(() => loadOpenGroups());

  // Persist open-group state.
  useEffect(() => {
    try {
      localStorage.setItem(OPEN_GROUPS_KEY, JSON.stringify(openMap));
    } catch {
      // Ignore quota / privacy errors.
    }
  }, [openMap]);

  const initialOpenFor = useMemo(() => {
    return (entry: Extract<NavEntry, { kind: 'group' }>): boolean => {
      // Active group is always opened by default.
      if (groupHasActive(entry, pathname)) return true;
      // Otherwise honour the persisted state, defaulting to open on first
      // visit so the user discovers the structure.
      const stored = openMap[entry.id];
      return stored === undefined ? true : stored;
    };
  }, [pathname, openMap]);

  return (
    <nav
      aria-label="القائمة الرئيسية"
      className={cn(
        'flex h-full flex-col text-slate-100',
        compact ? '' : 'bg-[#123B63]',
      )}
    >
      <div className="flex-1 overflow-y-auto px-3 py-4 [scrollbar-width:thin]">
        <ul className="space-y-1">
          {entries.map((entry) => {
            if (entry.kind === 'single') {
              return (
                <li key={entry.path}>
                  <LeafLink
                    item={entry}
                    pathname={pathname}
                    onNavigate={onNavigate}
                    badges={badges}
                    indented={false}
                  />
                </li>
              );
            }
            return (
              <SidebarGroup
                key={entry.id}
                entry={entry}
                pathname={pathname}
                badges={badges}
                onNavigate={onNavigate}
                initiallyOpen={initialOpenFor(entry)}
                onToggle={(open) =>
                  setOpenMap((prev) => ({ ...prev, [entry.id]: open }))
                }
              />
            );
          })}
        </ul>
      </div>
    </nav>
  );
}

export default SidebarNav;
