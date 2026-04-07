import { Search, Bell, Sun, Moon } from "lucide-react";

const TopNav = ({ theme, toggleTheme }) => {
  return (
    <header className="topnav">
      <div className="topnav-search">
        <span className="topnav-search-icon">
          <Search />
        </span>
        <input
          type="text"
          placeholder="Search documents, insights…"
          id="global-search"
        />
        <span className="topnav-search-kbd">⌘K</span>
      </div>

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
            <div className="topnav-profile-email">user@ragforge.ai</div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default TopNav;
