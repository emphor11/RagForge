import { NavLink } from "react-router-dom";

const Sidebar = ({ currentDocId }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">🔮</div>
        <div className="sidebar-brand-text">
          RAGForge<span>v2.0</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `sidebar-item ${isActive ? "active" : ""}`
          }
        >
          <span className="sidebar-item-icon">🏠</span>
          Dashboard
        </NavLink>
        <NavLink
          to="/reports"
          className={({ isActive }) =>
            `sidebar-item ${isActive ? "active" : ""}`
          }
        >
          <span className="sidebar-item-icon">📊</span>
          Reports
        </NavLink>
        <NavLink
          to="/documents"
          className={({ isActive }) =>
            `sidebar-item ${isActive ? "active" : ""}`
          }
        >
          <span className="sidebar-item-icon">📁</span>
          Documents
        </NavLink>
        <NavLink
          to="/analytics"
          className={({ isActive }) =>
            `sidebar-item ${isActive ? "active" : ""}`
          }
        >
          <span className="sidebar-item-icon">📈</span>
          Analytics
        </NavLink>
        <button className="sidebar-item">
          <span className="sidebar-item-icon">⚙️</span>
          Settings
        </button>

        <div className="sidebar-section-title">Recent Documents</div>

        {currentDocId && (
          <NavLink
            to={`/documents/${encodeURIComponent(currentDocId)}`}
            className={({ isActive }) =>
              `sidebar-item ${isActive ? "active" : ""}`
            }
          >
            <span className="sidebar-item-icon">📄</span>
            {currentDocId.length > 20
              ? currentDocId.slice(0, 20) + "..."
              : currentDocId}
          </NavLink>
        )}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-upgrade">
          <div className="sidebar-upgrade-title">✨ Upgrade to Pro</div>
          <div className="sidebar-upgrade-desc">
            Unlock advanced features & unlimited uploads.
          </div>
          <button className="sidebar-upgrade-btn">Upgrade Now →</button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
