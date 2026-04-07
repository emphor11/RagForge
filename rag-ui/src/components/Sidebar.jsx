import { NavLink } from "react-router-dom";
import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  BarChart3,
  FolderOpen,
  TrendingUp,
  FileText,
  Scale,
} from "lucide-react";

const Sidebar = ({ currentDocId }) => {
  const [recentDocs, setRecentDocs] = useState([]);

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem("recentDocs") || "[]");
      let newDocs = [...stored];
      if (currentDocId) {
        newDocs = newDocs.filter((d) => d !== currentDocId);
        newDocs.unshift(currentDocId);
        newDocs = newDocs.slice(0, 5);
        localStorage.setItem("recentDocs", JSON.stringify(newDocs));
      }
      setRecentDocs(newDocs);
    } catch {
      setRecentDocs(currentDocId ? [currentDocId] : []);
    }
  }, [currentDocId]);

  const guessDocType = (name) => {
    const n = (name || "").toLowerCase();
    if (n.includes("nda") || n.includes("non-disclosure")) return "NDA";
    if (n.includes("msa") || n.includes("master service")) return "MSA";
    if (n.includes("sow") || n.includes("statement of work")) return "SOW";
    if (n.includes("employ")) return "EMP";
    return "DOC";
  };

  const navItems = [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/reports", icon: BarChart3, label: "Reports" },
    { to: "/documents", icon: FolderOpen, label: "Documents" },
    { to: "/analytics", icon: TrendingUp, label: "Analytics" },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Scale />
        </div>
        <div className="sidebar-brand-text">
          RAGForge<span>v2</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `sidebar-item ${isActive ? "active" : ""}`
            }
          >
            <span className="sidebar-item-icon">
              <Icon />
            </span>
            {label}
          </NavLink>
        ))}

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
              <span className="sidebar-item-icon">
                <FileText />
              </span>
              <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {docId.length > 18 ? docId.slice(0, 18) + "…" : docId}
              </span>
              <span className="sidebar-doc-badge">{guessDocType(docId)}</span>
            </NavLink>
          ))
        ) : (
          <div
            className="sidebar-item"
            style={{ opacity: 0.35, pointerEvents: "none", fontSize: '13px' }}
          >
            No recent documents
          </div>
        )}
      </nav>

      <div className="sidebar-bottom" />
    </aside>
  );
};

export default Sidebar;
