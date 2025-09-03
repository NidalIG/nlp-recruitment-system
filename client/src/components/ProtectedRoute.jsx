import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  // Tant que le contexte vérifie le token
  if (loading) return <div>Loading...</div>;

  // Si pas d'utilisateur, rediriger vers login
  if (!user) return <Navigate to="/login" replace />;

  return children;
}
