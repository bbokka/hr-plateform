import { NavLink } from 'react-router-dom';
import logoUrl from '../../assets/Logo_Talentini.svg';
import { useAuth } from '../../context/AuthContext';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
}

function DashboardIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  );
}

function BriefcaseIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function PowerIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
    </svg>
  );
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: <DashboardIcon /> },
  { to: '/jobs', label: 'Jobs', icon: <BriefcaseIcon /> },
  { to: '/candidates', label: 'Candidates', icon: <UsersIcon /> },
];

export default function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-full w-60 bg-primary-dark flex flex-col z-40">
      {/* Logo area */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/10">
        <img
          src={logoUrl}
          alt="TalentiniHR"
          className="h-8 w-auto"
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
        />
        <span className="text-white font-semibold text-base tracking-tight">TalentiniHR</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1" aria-label="Main navigation">
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              [
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                isActive
                  ? 'bg-gradient-to-r from-primary-start to-primary-end text-white shadow-sm'
                  : 'text-white/60 hover:text-white hover:bg-white/8',
              ].join(' ')
            }
          >
            {icon}
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User / Logout footer */}
      <div className="px-4 py-4 border-t border-white/10">
        {user && (
          <p className="text-xs text-white/40 font-medium truncate mb-2 px-1" title={user.email}>
            {user.email}
          </p>
        )}
        <button
          id="sidebar-logout-btn"
          onClick={() => void logout()}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium text-white/60
            hover:text-white hover:bg-white/8 transition-all duration-150"
        >
          <PowerIcon />
          Sign out
        </button>
      </div>
    </aside>
  );
}

