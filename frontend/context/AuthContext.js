import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getStoredToken, storeToken } from "../lib/api";

const AuthContext = createContext(null);

/**
 * Accounts are optional: `user === null` is a perfectly normal state and
 * nothing in the app should block on it. `ready` flips true once we've
 * checked any stored token, so pages can avoid flashing the wrong UI.
 */
export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = getStoredToken();
    if (!stored) {
      setReady(true);
      return;
    }
    api("/api/auth/me", { token: stored })
      .then((u) => {
        setToken(stored);
        setUser(u);
      })
      .catch((err) => {
        // Only drop the token if the server says it's invalid — not on a
        // network blip or a cold-starting backend.
        if (err.status === 401) storeToken(null);
      })
      .finally(() => setReady(true));
  }, []);

  const signIn = useCallback((authResponse) => {
    storeToken(authResponse.access_token);
    setToken(authResponse.access_token);
    setUser(authResponse.user);
  }, []);

  const signOut = useCallback(() => {
    storeToken(null);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, ready, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
