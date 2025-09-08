// client/src/contexts/AuthContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const API_BASE =
    import.meta.env.VITE_API_BASE ||
    (window.location.hostname === "localhost" ? "http://localhost:3001" : "");

  const [token, setToken] = useState(() => sessionStorage.getItem("authToken") || "");
  const [user, setUser] = useState(() => {
    try {
      const raw = sessionStorage.getItem("authUser");
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  // Headers d'auth
  const authHeaders = (extra = {}) => ({
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  });

  // Au boot: si token connu, récupérer /me
  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!token) { setLoading(false); return; }
      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() });
        const data = await res.json();
        if (res.ok && data?.success) {
          const u = data.user;
          const normalized = {
            id: u.id || u._id,
            email: u.email,
            firstName: u.firstName,
            lastName: u.lastName,
            createdAt: u.createdAt
          };
          setUser(normalized);
          sessionStorage.setItem("authUser", JSON.stringify(normalized));
        } else {
          // token expiré/invalid → purge
          sessionStorage.removeItem("authToken");
          sessionStorage.removeItem("authUser");
          setToken("");
          setUser(null);
        }
      } catch {
        // réseau down → on ne purge pas, on laissera réessayer plus tard
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --------- ACTIONS ----------
 async function login(email, password) {
  try {
    const r = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await r.json();

    if (!r.ok) {
      // ❗ Ne force plus "Mot de passe incorrect" : affiche le message renvoyé
      const msg = data?.error || `HTTP ${r.status}`;
      return { success: false, error: msg };
    }

    const t = data.accessToken;
    const u = data.user || {};
    const normalized = {
      id: u.id,
      email: u.email,
      firstName: u.firstName,
      lastName: u.lastName
    };

    sessionStorage.setItem("authToken", t);
    sessionStorage.setItem("authUser", JSON.stringify(normalized));
    setToken(t);
    setUser(normalized);
    return { success: true, user: normalized };
  } catch (e) {
    return { success: false, error: e?.message || "Erreur de connexion" };
  }
}


  // Rem: par conception, on NE connecte PAS automatiquement après inscription.
  async function register(payload) {
    try {
      const r = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await r.json();
      if (!r.ok) {
        return { success: false, error: data?.error || `HTTP ${r.status}` };
      }

      // Pas d'auto-login ici: on laisse la page d'inscription rediriger vers /login
      // Si vous voulez auto-login, dé-commentez les 5 lignes ci-dessous:
      // const t = data.accessToken;
      // const u = data.user || {};
      // sessionStorage.setItem("authToken", t);
      // sessionStorage.setItem("authUser", JSON.stringify(u));
      // setToken(t); setUser({ id: u.id, email: u.email, firstName: u.firstName, lastName: u.lastName });

      return { success: true, user: { id: data?.user?.id, ...data.user } };
    } catch (e) {
      return { success: false, error: e?.message || "Erreur d'inscription" };
    }
  }

  function logout() {
    sessionStorage.removeItem("authToken");
    sessionStorage.removeItem("authUser");
    setToken("");
    setUser(null);
  }

  const isAuthenticated = !!token;
  const value = { token, user, loading, isAuthenticated, login, register, logout, authHeaders };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
