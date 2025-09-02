// App.jsx
import React, { useState } from 'react'
import Header from './components/layout/Header.jsx'
import Sidebar from './components/layout/Sidebar.jsx'
import UploadSection from './components/sections/UploadSection.jsx'
import MatchingSection from './components/sections/MatchingSection.jsx'
import HomePage from './components/layout/HomePage.jsx'
import ChatSection from './components/sections/ChatSection.jsx'
import QuizSection from './components/sections/QuizSection.jsx'

export default function App() {
  const [cvText, setCvText] = useState('');
  const [filename, setFilename] = useState('');
  const [jobText, setJobText] = useState('');
  const [lastResult, setLastResult] = useState(null);
  const [parsedCv, setParsedCv] = useState(null);
  
  // contrôle : page d'accueil ou application
  const [showHome, setShowHome] = useState(true);
  
  // contrôle sidebar rétractable
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="min-h-screen">
      <Header />
      
      {showHome ? (
        <HomePage onStart={() => setShowHome(false)} />
      ) : (
        <div className="mx-auto max-w-full p-4">
          <div className="flex gap-4">
            {/* Sidebar rétractable */}
            <Sidebar 
              isCollapsed={sidebarCollapsed}
              onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
            />
            
            {/* Contenu principal */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Colonne gauche - Upload et Matching */}
              <div className="space-y-4 lg:col-span-2">
                <UploadSection
                  cvText={cvText}
                  setCvText={setCvText}
                  setFilename={setFilename}
                  setParsedCv={setParsedCv}
                  parsedCv={parsedCv}
                  jobText={jobText}
                  setJobText={setJobText}
                  lastResult={lastResult}
                  setLastResult={setLastResult}
                />
                
                <MatchingSection
                  lastResult={lastResult}
                  parsedCv={parsedCv}
                />
                
                <QuizSection />
              </div>
              
              {/* Colonne droite - Assistant IA */}
              <div className="space-y-4">
                <div id="chat" className="sticky top-4">
                  <ChatSection apiUrl="/api/chat" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}