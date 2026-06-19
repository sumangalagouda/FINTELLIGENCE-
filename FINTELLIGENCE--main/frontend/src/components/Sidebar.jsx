import { LogOut } from 'lucide-react';
import '../App.css';
import Brand from './Brand';

export default function Sidebar({ activeView, setActiveView, user, onLogout, navItems }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Brand />
      </div>
      <nav>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={activeView === item.id ? 'nav-item active' : 'nav-item'}
              key={item.id}
              onClick={() => setActiveView(item.id)}
              type="button"
            >
              <Icon size={17} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="signed-in">
        <span>Signed in</span>
        <strong>{user?.name || 'Lead Analyst'}</strong>
        <button onClick={onLogout} type="button">
          <LogOut size={14} /> Sign out
        </button>
      </div>
    </aside>
  );
}
