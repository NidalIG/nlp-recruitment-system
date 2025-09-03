// src/components/layout/AppHeader.jsx
import React from 'react';
import { useAuth } from "../../contexts/AuthContext";
import { useNavigate } from 'react-router-dom';
import { Bot } from "lucide-react";


export default function AppHeader() {
  const { user, setUser, setToken, logout } = useAuth();
  const navigate = useNavigate();


  function handleLogout() {
    logout();           // supprime token et user via AuthContext
    navigate("/");      // redirige vers Home proprement
  }


  return (
    <header className="relative z-50 px-6 py-4 bg-gray-900/80 backdrop-blur-md border-b border-gray-800">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Logo + Titre */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-600 rounded-lg flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            My Career AI
          </h1>
        </div>

        {/* Boutons Auth */}
        <div className="flex items-center space-x-4">
          
      
      <button onClick={handleLogout}
      className="bg-red-500 hover:bg-red-700 text-white px-4 py-2 rounded">
        Déconnexion
      </button>
        </div>

      </div>
    </header>
  );
}
