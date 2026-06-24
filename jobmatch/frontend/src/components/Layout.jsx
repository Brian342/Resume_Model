import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    function handleLogout() {
        logout();
        navigate("/login");
        }

    const seekerLinks = [
        { to: "/dashboard", label: "My Dashboard" },
        { to: "/jobs", label: "Browse Jobs" },
        { to: "/preferences", label: "Job Preferences" },
        ];

    const employerLinks = [
        { to: "/employer", label: "Dashboard" },
        { to: "/employer/post", label: "Post a job" },
        ];

    const links = user?.role === "employer" ? employerLinks : seekerLinks;

    return (
        <div className="app-shell">
            <aside className="sidebar">
                <div className="sidebar-brand">
                    <span className="sidebar-brand-mark">JM</span>
                    <div>
                        <div className="sidebar-brand-name"> JobMatch</div>
                        <div className="sidebar-brand-sub">Pioneer insurance Group</div>
                        </div>
                        </div>

                       <div className="sidebar-user">
                           <div className="sidebar-user-name">{user?.full_name}</div>
                           <span className="badge badge-pending sidebar-role-badge">
                               {user?.role === "seeker" ? "Job Seeker" : "Employer"}
                              </span>
                            </div>

                          <nav className="sidebar-nav">
                              {links.map((link) => (
                                  <NavLink
                                    key={link.to}
                                    to={link.to}
                                    className={({ isActive }) =>
                                    "sidebar-link" + (isActive ? " sidebar-link-active" : "")}
                                  >
                                  {link.label}
                                  </NavLink>
                                  ))}
                                  </nav>

                                  <button className="btn btn-ghost sidebar-logout" onClick={handleLogout}>
                                      Log Out
                                  </button>
                                  </aside>

                                  <main className="main-content">
                                      <Outlet />
                                  </main>

                                  <style> {`
                                      .app-shell {
                                          display:grid;
                                          grid-template-columns: 248px 1fr;
                                          min-height: 100vh;
                                          }
                                      .sidebar {
                                          background: var(--navy-700);
                                          color: white;
                                          padding: 28px 22px;
                                          display: flex;
                                          flex-direction: column;
                                          position: sticky;
                                          top: 0;
                                          height: 100vh;
                                          }
                                       .sidebar-brand {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 32px;
        }
        .sidebar-brand-mark {
          width: 38px;
          height: 38px;
          border-radius: 10px;
          background: var(--amber-500);
          color: var(--navy-900);
          font-family: var(--font-display);
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 16px;
          flex-shrink: 0;
        }
        .sidebar-brand-name {
          font-family: var(--font-display);
          font-size: 17px;
          font-weight: 600;
          color: white;
        }
        .sidebar-brand-sub {
          font-size: 11px;
          color: var(--slate-400);
        }
        .sidebar-user {
          padding: 14px 16px;
          background: rgba(255,255,255,0.06);
          border-radius: var(--radius-sm);
          margin-bottom: 24px;
        }
        .sidebar-user-name {
          font-size: 14px;
          font-weight: 600;
          color: white;
          margin-bottom: 6px;
        }
        .sidebar-role-badge {
          background: rgba(217,142,61,0.18);
          color: var(--amber-100);
        }
        .sidebar-nav {
          display: flex;
          flex-direction: column;
          gap: 4px;
          flex: 1;
        }
        .sidebar-link {
          padding: 11px 14px;
          border-radius: var(--radius-sm);
          color: var(--slate-200);
          font-size: 14.5px;
          font-weight: 500;
          transition: background 0.15s ease, color 0.15s ease;
        }
        .sidebar-link:hover {
          background: rgba(255,255,255,0.06);
          color: white;
        }
        .sidebar-link-active {
          background: var(--amber-500);
          color: var(--navy-900);
          font-weight: 600;
        }
        .sidebar-logout {
          color: var(--slate-200);
          border-color: rgba(255,255,255,0.16);
        }
        .sidebar-logout:hover {
          color: white;
          border-color: rgba(255,255,255,0.3);
        }
        .main-content {
          background: var(--cream-50);
          min-height: 100vh;
        }
        @media (max-width: 820px) {
          .app-shell {
            grid-template-columns: 1fr;
          }
          .sidebar {
            position: relative;
            height: auto;
          }
        }
    `}</style>
    </div>
      );
    }