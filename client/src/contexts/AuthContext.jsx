import React, { createContext, useContext, useState, useEffect } from 'react';
import jwtDecode from "jwt-decode";

export const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => sessionStorage.getItem('authToken'));
  const [loading, setLoading] = useState(true);

  // Vérification du token au chargement
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const decoded = jwtDecode(token);
          const userId = decoded.sub;

          const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
          });

          if (response.ok) {
            const data = await response.json();
            const currentUser = data.user ? { id: userId, ...data.user } : { id: userId };
            setUser(currentUser);
          } else {
            logout();
          }
        } catch (err) {
          console.error('Auth check failed:', err);
          logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [token]);

  const login = async (email, password) => {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (response.ok) {
        const decoded = jwtDecode(data.accessToken);
        setToken(data.accessToken);
        setUser({ id: decoded.sub, ...data.user });
        sessionStorage.setItem('authToken', data.accessToken);
        return { success: true, user: { id: decoded.sub, ...data.user }, token: data.accessToken };
      } else {
    return { success: false, error: data.error || 'Erreur de connexion' };
}
    } catch (err) {
      return { success: false, error: 'Erreur de connexion' };
    }
  };

  const register = async (userData) => {
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });

      const data = await response.json();

      if (response.ok) {
        const decoded = jwtDecode(data.accessToken);
        setToken(data.accessToken);
        setUser({ id: decoded.sub, ...data.user });
        sessionStorage.setItem('authToken', data.accessToken);
        return { success: true, user: { id: decoded.sub, ...data.user }, token: data.accessToken };
      } else {
        return { success: false, error: data.error || 'Erreur lors de l\'inscription' };
      }
    } catch (err) {
      return { success: false, error: 'Erreur lors de l\'inscription' };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem('authToken');
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!token && !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
