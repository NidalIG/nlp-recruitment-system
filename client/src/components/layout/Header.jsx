// src/components/layout/Header.jsx
import React from "react";
import { Bot } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

export default function Header() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();         // supprime token et user
    navigate("/");    // redirige vers Home
  };

  return (
    <header className="relative ml-0 z-50 px-6 py-4 bg-gray-900/80 backdrop-blur-md border-b border-gray-800">
      <div className="max-w-full mx-3 flex items-center justify-between">
        
        {/* Logo + Titre */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-600 rounded-lg flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Assistant Carrière
          </h1>
        </div>

        {/* Boutons Auth */}
        <div className="flex items-center space-x-4">
          {user ? (
            <button
              onClick={handleLogout}
              className="bg-red-500 hover:bg-red-700 text-white px-4 py-2 rounded"
            >
              Déconnexion
            </button>
          ) : (
            <>
              <button
                onClick={() => navigate("/login")}
                className="px-6 py-2 text-gray-300 hover:text-white transition-colors duration-200 font-medium"
              >
                Connexion
              </button>
              <button
                onClick={() => navigate("/register")}
                className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-200 transform hover:scale-105 shadow-lg hover:shadow-xl"
              >
                Inscription
              </button>
            </>
          )}
        </div>

      </div>
    </header>
  );
}
