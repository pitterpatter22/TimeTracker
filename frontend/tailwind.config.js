module.exports = {
  purge: ['./index.html', './src/**/*.{js,jsx,ts,tsx,vue}'],
  darkMode: false, // or 'media' or 'class'
  theme: {
    extend: {
      fontFamily: {
        jetbrains: ['JetBrains Mono', 'monospace'],  // Missing closing brace
      },
      colors: {
        indigo: {
          light: '#b3bcf5',
          DEFAULT: '#5c6ac4',
          dark: '#202e78',
        },
        green: {
          light: '#6fcf97',
          DEFAULT: '#27ae60',
          dark: '#219653',
        },
      },
    },
  },
  plugins: [],
}