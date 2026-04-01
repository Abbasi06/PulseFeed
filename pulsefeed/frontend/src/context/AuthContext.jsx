import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { API_URL } from "../config";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // null = unknown (loading), false = not authenticated, object = user
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  // On mount: ask the server if the httpOnly cookie is still valid
  useEffect(() => {
    fetch(`${API_URL}/users/me`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setUser(data ?? false))
      .catch(() => setUser(false))
      .finally(() => setChecking(false));
  }, []);

  // Called after successful onboarding — server already set the cookie
  const login = useCallback((userData) => {
    setUser(userData);
  }, []);

  const logout = useCallback(async () => {
    await fetch(`${API_URL}/users/logout`, {
      method: "POST",
      credentials: "include",
    });
    setUser(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        checking,
        isAuthenticated: !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
