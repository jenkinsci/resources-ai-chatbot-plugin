import { Chatbot } from "./Chatbot";

export const Dashboard = () => {
  return (
    <div className="app-container">
      {/* Sidebar */}
      <nav className="sidebar">
        <div className="sidebar-header">
          <div className="logo-circle">J</div>
          <div className="logo-text">
            <h1 className="app-title">Jenkins AI</h1>
            <span className="app-subtitle">Precision CI/CD</span>
          </div>
        </div>
        <button className="new-pipeline-button">
          <span className="material-symbols-outlined">add</span>
          <span>New Pipeline</span>
        </button>
        <ul className="nav-list">
          <li><a href="#" className="nav-item"><span className="material-symbols-outlined">account_tree</span><span>Pipelines</span></a></li>
          <li><a href="#" className="nav-item"><span className="material-symbols-outlined">history</span><span>Build History</span></a></li>
          <li><a href="#" className="nav-item"><span className="material-symbols-outlined">dns</span><span>Nodes</span></a></li>
          <li><a href="#" className="nav-item active"><span className="material-symbols-outlined">auto_awesome</span><span>AI Insights</span></a></li>
        </ul>
        <div className="sidebar-footer">
          <ul className="footer-list">
            <li><a href="#" className="footer-item"><span className="material-symbols-outlined">terminal</span><span>System Log</span></a></li>
            <li><a href="#" className="footer-item"><span className="material-symbols-outlined">admin_panel_settings</span><span>Admin</span></a></li>
          </ul>
        </div>
      </nav>

      {/* Main Content */}
      <div className="main-area">
        <header className="top-app-bar">
          <div className="left-section">
            <button className="mobile-menu-button"><span className="material-symbols-outlined">menu</span></button>
            <div className="workspace-breadcrumb">Workspace / <span className="current">AI Insights</span></div>
          </div>
          <div className="right-section">
            <div className="search-wrapper">
              <span className="material-symbols-outlined">search</span>
              <input className="search-input" placeholder="Search pipelines, builds..." type="text" />
            </div>
            <button className="notification-button"><span className="material-symbols-outlined">notifications</span></button>
            <div className="user-avatar"><img src="https://lh3.googleusercontent.com/aida-public/AB6AXuBD-X7_6zh-ve42nEMOBvzUZNAGW5qZCOPJoNux3Sox9zhpFT0_yvHAvb0fevBzZVypWMKePiD14uHvXtDbp4nK8a-_v6Wa2zgzbj5iHLjH4TgihzAZXVpx8oYgRJlEBhd21CBwOVCqsE1SLQL-9JDU4ou12kT2yZ_g09-4aHn34jOJRIwGcCh4VuMrLwAvPbPjE3mNTSM2CO9uZa-MJCho1OSmjOr6rG6LEHjl8CJ_sJHOHXNDIDQx0BEoY1GcxcWYNC0IuTk2bn1G" alt="User" /></div>
          </div>
        </header>

        <main className="content-area">
          <section className="welcome-section">
            <div className="logo-wrapper">
              <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuBD-X7_6zh-ve42nEMOBvzUZNAGW5qZCOPJoNux3Sox9zhpFT0_yvHAvb0fevBzZVypWMKePiD14uHvXtDbp4nK8a-_v6Wa2zgzbj5iHLjH4TgihzAZXVpx8oYgRJlEBhd21CBwOVCqsE1SLQL-9JDU4ou12kT2yZ_g09-4aHn34jOJRIwGcCh4VuMrLwAvPbPjE3mNTSM2CO9uZa-MJCho1OSmjOr6rG6LEHjl8CJ_sJHOHXNDIDQx0BEoY1GcxcWYNC0IuTk2bn1G" alt="Jenkins Logo" className="logo-image" />
            </div>
            <h2 className="welcome-title">How can I assist your builds today?</h2>
            <p className="welcome-subtitle">I'm analyzing 14 active nodes and 3 recent pipeline failures. Ask me anything to optimise your CI/CD flow.</p>
          </section>

          <section className="quick-actions">
            <button className="quick-card">
              <div className="icon-circle"><span className="material-symbols-outlined">extension</span></div>
              <div className="card-text">
                <span className="card-title">Check Plugin Compatibility</span>
                <span className="card-desc">Scan for deprecation warnings and cross-version conflicts.</span>
              </div>
            </button>
            <button className="quick-card">
              <div className="icon-circle"><span className="material-symbols-outlined">troubleshoot</span></div>
              <div className="card-text">
                <span className="card-title">Analyze Build Logs</span>
                <span className="card-desc">Find root cause of recent failures and OOM errors.</span>
              </div>
            </button>
            <button className="quick-card">
              <div className="icon-circle"><span className="material-symbols-outlined">route</span></div>
              <div className="card-text">
                <span className="card-title">Pipeline Generator</span>
                <span className="card-desc">Draft a declarative Jenkinsfile for new microservices.</span>
              </div>
            </button>
          </section>
        </main>

        {/* Floating Chatbot – same component used previously */}
        <Chatbot />
      </div>
    </div>
  );
};
