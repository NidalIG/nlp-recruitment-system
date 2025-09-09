import React from 'react';

export default function ProgressCircle({
  value = 0,
  size = 160,
  stroke = 10,
  textColor,     // <-- on passe une couleur (#hex / rgb / hsl)
  textClass = "",// <-- optionnel si tu veux ajouter d'autres classes (taille, font, etc.)
}) {
  const v = Math.max(0, Math.min(100, value));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (v / 100) * c;

  // taille du texte proportionnelle
  const fontSize = Math.round(size * 0.22);

  return (
    <svg width={size} height={size}>
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        strokeWidth={stroke}
        stroke="#e5e7eb"
        fill="none"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={offset}
        stroke="currentColor"
        className="text-blue-600"
        fill="none"
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="middle"
        textAnchor="middle"
        // on force la couleur via style.fill pour SVG
        style={{ fill: textColor, fontSize }}
        className={`font-bold ${textClass}`}
      >
        {v}%
      </text>
    </svg>
  );
}
