import React, { useState } from 'react'
import Header from './components/layout/Header.jsx'
import Sidebar from './components/layout/Sidebar.jsx'
import UploadSection from './components/sections/UploadSection.jsx'
import MatchingSection from './components/sections/MatchingSection.jsx'
// import QuickInsights from './components/sections/QuickInsights.jsx'
// import ReportActions from './components/sections/ReportActions.jsx'
import ChatSection from './components/sections/ChatSection.jsx'
import QuizSection from './components/sections/QuizSection.jsx'

export default function App() {
  const [cvText, setCvText] = useState('');
  const [filename, setFilename] = useState('');
  const [jobText, setJobText] = useState('');
  const [lastResult, setLastResult] = useState(null);
  const [parsedCv, setParsedCv] = useState(null);

  return (
    <div className="min-h-screen">
      <Header />
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-4 p-4 md:grid-cols-[220px_1fr]">
        <Sidebar />
        <div className="flex flex-col gap-4">
          <UploadSection 
            cvText={cvText} 
            setCvText={setCvText} 
            setFilename={setFilename}
            setParsedCv={setParsedCv}
            parsedCv={parsedCv}
          />
          <MatchingSection 
            cvText={cvText} 
            jobText={jobText} 
            setJobText={setJobText} 
            lastResult={lastResult} 
            setLastResult={setLastResult}
            parsedCv={parsedCv}
          />
          {/* <QuickInsights 
            cvText={cvText} 
            jobText={jobText} 
          /> */}
          {/* <ReportActions 
            cvText={cvText} 
            jobText={jobText} 
            result={lastResult} 
          /> */}
          <ChatSection apiUrl="/api/chat" />
          <QuizSection />
        </div>
      </div>
    </div>
  )
}