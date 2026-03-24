import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const feedNavItem = {
  to: "/dashboard",
  label: "Feed",
  icon: (
    <svg
      className="w-5 h-5"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
      />
    </svg>
  ),
};

function getInitials(name) {
  return (name || "")
    .trim()
    .split(/\s+/)
    .map((w) => w[0]?.toUpperCase() || "")
    .slice(0, 2)
    .join("");
}

export default function DashboardLayout() {
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const initials = getInitials(user?.name);

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* ── Desktop Sidebar ── */}
      <aside className="hidden md:flex flex-col w-60 bg-gradient-to-b from-slate-900 to-slate-950 border-r border-slate-800/80 shrink-0">

        {/* Nav — top */}
        <nav className="flex-1 px-3 py-4">
          <NavLink
            to={feedNavItem.to}
            end
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-violet-500/15 text-violet-300 shadow-[inset_0_0_0_1px_rgba(139,92,246,0.2)]"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/70"
              }`
            }
          >
            {feedNavItem.icon}
            {feedNavItem.label}
          </NavLink>
        </nav>

        {/* Bottom section — brand + settings + logout */}
        <div className="px-3 pb-5 pt-3 border-t border-slate-800 space-y-1">

          {/* User avatar + PulseBoard brand */}
          <div className="flex items-center gap-3 px-3 py-3 mb-1">
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 select-none"
              style={{
                background: "linear-gradient(135deg, #B7397A, #4C6E94)",
                boxShadow: "0 0 14px rgba(183,57,122,0.4)",
              }}
            >
              {initials || "?"}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-white leading-tight">
                Pulse<span className="text-violet-400">Board</span>
              </p>
              <p className="text-[10px] text-slate-500 leading-tight truncate">
                Your AI knowledge feed
              </p>
            </div>
          </div>

          {/* Settings */}
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-violet-500/15 text-violet-300 shadow-[inset_0_0_0_1px_rgba(139,92,246,0.2)]"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/70"
              }`
            }
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.8}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            Settings
          </NavLink>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.8}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Mobile top bar ── */}
      <div className="md:hidden fixed top-0 inset-x-0 z-10 bg-slate-900 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold shrink-0"
            style={{ background: "linear-gradient(135deg, #B7397A, #4C6E94)" }}
          >
            {initials || "?"}
          </div>
          <span className="text-base font-bold text-white">
            Pulse<span className="text-violet-400">Board</span>
          </span>
        </div>
        <nav className="flex gap-1">
          <NavLink
            to="/dashboard"
            end
            className={({ isActive }) =>
              `p-2 rounded-lg transition-colors ${
                isActive ? "text-violet-400" : "text-slate-400 hover:text-slate-200"
              }`
            }
            title="Feed"
          >
            {feedNavItem.icon}
          </NavLink>
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `p-2 rounded-lg transition-colors ${
                isActive ? "text-violet-400" : "text-slate-400 hover:text-slate-200"
              }`
            }
            title="Settings"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.8}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </NavLink>
        </nav>
      </div>

      {/* ── Main content ── */}
      <main className="flex-1 md:pt-0 pt-14 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
