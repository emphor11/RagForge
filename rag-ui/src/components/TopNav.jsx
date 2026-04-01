const TopNav = ({ theme, toggleTheme }) => {
    return (
      <header className="topnav">
        <div className="topnav-search">
          <span className="topnav-search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search documents, insights..."
            id="global-search"
          />
          <span className="topnav-search-kbd">⌘K</span>
        </div>
  
        <div className="topnav-right">
          <button 
            className="topnav-notif" 
            onClick={toggleTheme} 
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            style={{ fontSize: '18px' }}
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>
          <button className="topnav-notif" id="notifications-btn">
            🔔
            <span className="topnav-notif-badge"></span>
          </button>
          <div className="topnav-profile">
            <div className="topnav-avatar">U</div>
            <div className="topnav-profile-info">
              <div className="topnav-profile-name">User</div>
              <div className="topnav-profile-email">user@ragforge.ai</div>
            </div>
          </div>
        </div>
      </header>
    );
  };
  
  export default TopNav;
