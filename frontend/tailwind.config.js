/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary-start': '#6B77B7',
        'primary-end':   '#7697CE',
        'primary-dark':  '#08102B',
        'background':    '#F4F5F8',
        'status-success': '#3D9A6B',
        'status-warning': '#C97A27',
        'status-danger':  '#C04B4B',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(to right, #6B77B7, #7697CE)',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(8 16 43 / 0.06), 0 1px 2px -1px rgb(8 16 43 / 0.04)',
        'card-hover': '0 4px 12px 0 rgb(8 16 43 / 0.08), 0 2px 4px -1px rgb(8 16 43 / 0.04)',
      },
    },
  },
  plugins: [],
};
