/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          bg: '#0a0a0f',
          card: '#111118',
          border: 'rgba(255,255,255,0.08)',
        },
        accent: {
          primary: '#a78bfa', // violet
          healthy: '#10b981', // emerald
          warning: '#f59e0b', // amber
          error: '#f43f5e', // rose
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
