/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#E74C3C',
          600: '#C0392B',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
        physiome: '#E74C3C',
        genome: '#9B59B6',
        microbiome: '#27AE60',
        metabolome: '#F39C12',
        exposome: '#F1C40F',
        anatome: '#1ABC9C',
        epigenome: '#3498DB',
      },
    },
  },
  plugins: [],
}
