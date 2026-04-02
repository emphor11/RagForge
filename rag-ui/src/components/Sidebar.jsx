import { NavLink } from "react-router-dom";
import { useState, useEffect } from "react";

const Sidebar = ({ currentDocId }) => {
  const [recentDocs, setRecentDocs] = useState([]);

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem("recentDocs") || "[]");
      let newDocs = [...stored];
      if (currentDocId) {
        newDocs = newDocs.filter(d => d !== currentDocId);
        newDocs.unshift(currentDocId);
        newDocs = newDocs.slice(0, 5);
        localStorage.setItem("recentDocs", JSON.stringify(newDocs));
      }
      setRecentDocs(newDocs);
    } catch {
      setRecentDocs(currentDocId ? [currentDocId] : []);
    }
  }, [currentDocId]);

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

        {recentDocs.length > 0 ? (
          recentDocs.map((docId) => (
            <NavLink
              key={docId}
              to={`/documents/${encodeURIComponent(docId)}`}
              className={({ isActive }) =>
                `sidebar-item ${isActive ? "active" : ""}`
              }
            >
              <span className="sidebar-item-icon">📄</span>
              {docId.length > 20
                ? docId.slice(0, 20) + "..."
                : docId}
            </NavLink>
          ))
        ) : (
          <div className="sidebar-item" style={{opacity: 0.5, pointerEvents: 'none'}}>No recent docs</div>
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
