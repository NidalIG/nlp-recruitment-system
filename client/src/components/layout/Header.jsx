// src/components/layout/Header.jsx
import React from "react";
import { Bot } from "lucide-react";

export default function Header() {
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
          <button className="px-6 py-2 text-gray-300 hover:text-white transition-colors duration-200 font-medium">
            Sign In
          </button>
          <button className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-200 transform hover:scale-105 shadow-lg hover:shadow-xl">
            Sign Up
          </button>
        </div>

      </div>
    </header>
  );
}
