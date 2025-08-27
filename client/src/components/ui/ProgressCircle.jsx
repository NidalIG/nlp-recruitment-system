import React from 'react'
export default function ProgressCircle({ value=0, size=96, stroke=10 }){
  const v=Math.max(0,Math.min(100,value)); const r=(size-stroke)/2; const c=2*Math.PI*r; const offset=c-(v/100)*c;
  return(<svg width={size} height={size}><circle cx={size/2} cy={size/2} r={r} strokeWidth={stroke} stroke="#e5e7eb" fill="none"/>
    <circle cx={size/2} cy={size/2} r={r} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset} stroke="currentColor" className="text-blue-600" fill="none"/>
    <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" className="fill-slate-700 text-sm">{v}%</text></svg>)
}