import { Bell, Sun, Moon, Home, ChevronRight } from "lucide-react";
import { useLocation, useParams, Link } from "react-router-dom";

const ROUTE_LABELS = {
  "/": "Dashboard",
  "/reports": "Reports",
  "/documents": "Documents",
  "/analytics": "Analytics",
};

const TopNav = ({ theme, toggleTheme }) => {
  const location = useLocation();
  const params = useParams();

  // Build breadcrumb segments
  const buildBreadcrumbs = () => {
    const path = location.pathname;

    // Home is always first
    const crumbs = [{ label: "Dashboard", to: "/" }];

    if (path === "/") return crumbs;

    if (path.startsWith("/documents/") && params.id) {
      const docId = decodeURIComponent(params.id);
      crumbs.push({ label: "Documents", to: "/documents" });
      crumbs.push({
        label: docId.length > 28 ? docId.slice(0, 28) + "…" : docId,
        to: null,
        title: docId, // full name as tooltip
      });
      return crumbs;
    }

    const label = ROUTE_LABELS[path];
    if (label) {
      crumbs.push({ label, to: null });
    }

    return crumbs;
  };

  const crumbs = buildBreadcrumbs();

  return (
    <header className="topnav">
      {/* Breadcrumb */}
      <nav className="topnav-breadcrumb" aria-label="Breadcrumb">
        {crumbs.map((crumb, idx) => {
          const isLast = idx === crumbs.length - 1;
          return (
            <span
              key={idx}
              style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0 }}
            >
              {idx > 0 && (
                <ChevronRight size={12} className="topnav-breadcrumb-sep" />
              )}
              {crumb.to ? (
                <Link
                  to={crumb.to}
                  className="topnav-breadcrumb-item"
                  title={crumb.title}
                >
                  {idx === 0 ? (
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <Home size={12} />
                      <span>{crumb.label}</span>
                    </span>
                  ) : (
                    crumb.label
                  )}
                </Link>
              ) : (
                <span
                  className={`topnav-breadcrumb-item ${isLast ? "active" : ""}`}
                  title={crumb.title}
                >
                  {crumb.label}
                </span>
              )}
            </span>
          );
        })}
      </nav>

      <div className="topnav-right">
        <button
          className="topnav-btn"
          id="theme-toggle-btn"
          title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
          onClick={toggleTheme}
        >
          {theme === "light" ? <Moon /> : <Sun />}
        </button>
        <button
          className="topnav-btn"
          id="notifications-btn"
          title="Notifications"
        >
          <Bell />
        </button>
        <div className="topnav-profile">
          <div className="topnav-avatar">U</div>
          <div>
            <div className="topnav-profile-name">User</div>
            <div className="topnav-profile-email">user@jurisight.ai</div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default TopNav;
