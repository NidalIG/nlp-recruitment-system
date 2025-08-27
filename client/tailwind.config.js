/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html","./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 10px 30px -12px rgba(2,6,23,.1), 0 6px 18px -8px rgba(2,6,23,.08)"
      },
      animation: {
        'fade-in': 'fadeIn .4s ease-out',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: 0, transform: 'translateY(4px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
      }
    },
  },
  plugins: [],
}
