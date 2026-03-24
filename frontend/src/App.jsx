import { AnimatePresence, motion } from "framer-motion";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import DashboardLayout from "./components/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import LandingPage from "./pages/LandingPage";
import Onboarding from "./pages/Onboarding";
import Settings from "./pages/Settings";

// ---------------------------------------------------------------------------
// Page transition variants
// ---------------------------------------------------------------------------

const fade = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.35, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
};

const slideFromRight = {
  initial: { opacity: 0, x: 48 },
  animate: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
  },
  exit: { opacity: 0, x: -24, transition: { duration: 0.22 } },
};

function Page({ children, variant = fade }) {
  return (
    <motion.div
      variants={variant}
      initial="initial"
      animate="animate"
      exit="exit"
      style={{ minHeight: "100vh" }}
    >
      {children}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Loading screen shown while AuthContext checks the cookie
// ---------------------------------------------------------------------------

function Pulse() {
  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 rounded-full bg-emerald-500"
            animate={{ scale: [1, 1.6, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 0.9, delay: i * 0.18 }}
          />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Protected route: waits for auth check before deciding
// ---------------------------------------------------------------------------

function RootRedirect() {
  const { isAuthenticated, checking } = useAuth();
  if (checking) return <Pulse />;
  return (
    <Navigate to={isAuthenticated ? "/dashboard" : "/onboarding"} replace />
  );
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, checking } = useAuth();
  if (checking) return <Pulse />;
  return isAuthenticated ? children : <Navigate to="/" replace />;
}

// ---------------------------------------------------------------------------
// Routes tree (inside AuthProvider + BrowserRouter)
// ---------------------------------------------------------------------------

function AppRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait" initial={false}>
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/onboarding"
          element={
            <Page variant={slideFromRight}>
              <Onboarding />
            </Page>
          }
        />
        <Route
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route
            path="/dashboard"
            element={
              <Page variant={fade}>
                <Dashboard />
              </Page>
            }
          />
          <Route
            path="/settings"
            element={
              <Page variant={fade}>
                <Settings />
              </Page>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
