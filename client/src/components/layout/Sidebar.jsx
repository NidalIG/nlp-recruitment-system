import React from 'react'
export default function Sidebar(){
  return (
    <aside className="hidden h-full rounded-2xl border border-slate-200 bg-white p-4 shadow-soft md:block">
      <div className="text-sm font-medium text-slate-600">Navigation</div>
      <ul className="mt-3 space-y-2 text-sm text-slate-700">
        <li><a href="#upload" className="hover:underline">Upload & Parsing</a></li>
        <li><a href="#matching" className="hover:underline">Scoring</a></li>
        {/* <li><a href="#insights" className="hover:underline">Insights</a></li> */}
        {/* <li><a href="#report" className="hover:underline">Export PDF</a></li> */}
        <li><a href="#chat" className="hover:underline">Chat IA</a></li>
        <li><a href="#quiz" className="hover:underline">Quiz IA (Gemini)</a></li>
      </ul>
    </aside>
  )
}
