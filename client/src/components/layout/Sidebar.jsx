// src/components/layout/Sidebar.jsx
import React from 'react'
import { Upload, Target, MessageCircle, Brain, Navigation, ChevronLeft, ChevronRight } from 'lucide-react'

export default function Sidebar({ isCollapsed, onToggle }) {
  return (
    <aside
      className={`sticky top-4 h-[calc(100vh-2rem)] rounded-2xl border border-slate-200 bg-white shadow-soft transition-all duration-300 ${
        isCollapsed ? 'w-16 p-2' : 'w-64 p-4'
      }`}
    >
      {/* wrapper 'relative' pour que le bouton absolute reste ancré à la sidebar */}
      <div className="relative h-full">
        {/* Bouton toggle */}
        <button
          onClick={onToggle}
          className="absolute -right-3 top-4 flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm hover:bg-slate-50 transition-colors z-10"
          title={isCollapsed ? "Étendre" : "Réduire"}
        >
          {isCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
        </button>

        {/* Contenu */}
        {!isCollapsed ? (
          <>
            <div className="flex items-center gap-2 text-sm font-medium text-slate-600 mb-4">
              <Navigation className="h-4 w-4" />
              Navigation
            </div>
            
            <ul className="space-y-3 text-sm text-slate-700">
              <li>
                <a 
                  href="#upload" 
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors group"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600/10 group-hover:bg-blue-600/20 transition-colors">
                    <Upload className="h-4 w-4 text-blue-600" />
                  </div>
                  <span>Upload & Parsing</span>
                </a>
              </li>
              
              <li>
                <a 
                  href="#matching" 
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors group"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-600/10 group-hover:bg-green-600/20 transition-colors">
                    <Target className="h-4 w-4 text-green-600" />
                  </div>
                  <span>Scoring</span>
                </a>
              </li>
              
              <li>
                <a 
                  href="#chat" 
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors group"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-600/10 group-hover:bg-purple-600/20 transition-colors">
                    <MessageCircle className="h-4 w-4 text-purple-600" />
                  </div>
                  <span>Chat IA</span>
                </a>
              </li>
              
              <li>
                <a 
                  href="#quiz" 
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors group"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600/10 group-hover:bg-indigo-600/20 transition-colors">
                    <Brain className="h-4 w-4 text-indigo-600" />
                  </div>
                  <span>Quiz IA (Gemini)</span>
                </a>
              </li>
            </ul>
          </>
        ) : (
          // Version réduite avec icônes seulement
          <div className="flex flex-col items-center space-y-4 pt-6">
            <a 
              href="#upload" 
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10 hover:bg-blue-600/20 transition-colors"
              title="Upload & Parsing"
            >
              <Upload className="h-5 w-5 text-blue-600" />
            </a>
            
            <a 
              href="#matching" 
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-600/10 hover:bg-green-600/20 transition-colors"
              title="Scoring"
            >
              <Target className="h-5 w-5 text-green-600" />
            </a>
            
            <a 
              href="#chat" 
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-600/10 hover:bg-purple-600/20 transition-colors"
              title="Chat IA"
            >
              <MessageCircle className="h-5 w-5 text-purple-600" />
            </a>
            
            <a 
              href="#quiz" 
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600/10 hover:bg-indigo-600/20 transition-colors"
              title="Quiz IA (Gemini)"
            >
              <Brain className="h-5 w-5 text-indigo-600" />
            </a>
          </div>
        )}
      </div>
    </aside>
  )
}
