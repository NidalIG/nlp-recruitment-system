// App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

import Header from './components/layout/Header.jsx';
import HomePage from './components/layout/HomePage.jsx';
import UploadSection from './components/sections/UploadSection.jsx';
import MatchingSection from './components/sections/MatchingSection.jsx';
import QuizSection from './components/sections/QuizSection.jsx';
import ChatSection from './components/sections/ChatSection.jsx';
import Sidebar from './components/layout/Sidebar.jsx';
import AuthPage from './pages/AuthPage.jsx';
import AppHeader from './components/layout/AppHeader.jsx';

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <HeaderWrapper />
        <Routes>
          {/* Pages publiques */}
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<AuthPage defaultForm="login" />} />
          <Route path="/register" element={<AuthPage defaultForm="register" />} />

          {/* Pages protégées */}
          <Route
            path="/app/*"
            element={
              <ProtectedRoute>
                <MainApp />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

// HeaderWrapper : affiche Header sauf sur login/register
function HeaderWrapper() {
  const location = useLocation();

  if (location.pathname === "/") {
    // Page d'accueil => Header classique
    return <Header />;
  }

  if (location.pathname.startsWith("/app")) {
    // Pages internes => Header avec bouton Déconnexion
    return <AppHeader />;
  }

  // Ne rien afficher sur login/register
  return null;
}




function MainApp() {
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  const [cvText, setCvText] = React.useState('');
  const [filename, setFilename] = React.useState('');
  const [jobText, setJobText] = React.useState('');
  const [lastResult, setLastResult] = React.useState(null);
  const [parsedCv, setParsedCv] = React.useState(null);

  return (
    <div className="min-h-screen mx-auto max-w-full">
      {/* Nouveau Header pour MainApp */}
      

      <div className="p-4 flex gap-4">
        {/* Sidebar rétractable */}
        <Sidebar
          isCollapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* Contenu principal */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4">
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
            <MatchingSection lastResult={lastResult} parsedCv={parsedCv} />
            <QuizSection />
          </div>

          {/* Assistant IA / Chat */}
          <div className="space-y-4">
            <div id="chat" className="sticky top-4">
              <ChatSection apiUrl="/api/chat" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

