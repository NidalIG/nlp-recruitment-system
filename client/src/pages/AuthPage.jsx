// src/pages/AuthPage.js 
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import LoginForm from '../components/auth/LoginForm';
import RegisterForm from '../components/auth/RegisterForm';

const AuthPage = ({ defaultForm = 'login' }) => {
  const [isLogin, setIsLogin] = useState(defaultForm === 'login');
  const { isAuthenticated, user } = useAuth();


  // Redirection si déjà connecté
  if (isAuthenticated && user) {
  return <Navigate to={`/app/${user.id}`} replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        
        {/* Formulaires d'authentification */}
        {isLogin ? (
          <LoginForm toggleForm={() => setIsLogin(false)} />
        ) : (
          <RegisterForm toggleForm={() => setIsLogin(true)} />
        )}
      </div>
    </div>
  );
};

export default AuthPage;
