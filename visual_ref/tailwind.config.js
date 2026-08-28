/** @type {import('tailwindcss').Config} */
import typography from '@tailwindcss/typography';

export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Paleta Trifecta - Company Brand Colors (Cold first for visualizations)
                primary: {
                    50: '#e0f7ff',
                    100: '#b3efff',
                    200: '#66e0ff',
                    300: '#33d9ff',
                    400: '#14E0F8',
                    500: '#00c0d9',
                    600: '#009db5',
                    700: '#007a94',
                    800: '#005a72',
                    900: '#004054',
                    950: '#002b38',
                },
                accent: {
                    50: '#fff4e8',
                    100: '#ffe8d0',
                    200: '#ffd4a0',
                    300: '#ffb870',
                    400: '#fd6040',
                    500: '#FD4239',
                    600: '#e03830',
                    700: '#c0143c',
                    800: '#a01030',
                    900: '#800c28',
                    950: '#600820',
                },
                success: {
                    400: '#4ade80',
                    500: '#22c55e',
                    600: '#16a34a',
                },
                warning: {
                    400: '#facc15',
                    500: '#eab308',
                    600: '#ca8a04',
                },
                danger: {
                    400: '#f87171',
                    500: '#ef4444',
                    600: '#dc2626',
                },
                dark: {
                    50: '#f8fafc',
                    100: '#f1f5f9',
                    200: '#e2e8f0',
                    300: '#cbd5e1',
                    400: '#979BA3',
                    500: '#5B626C',
                    600: '#3C3F48',
                    700: '#2a2d35',
                    800: '#1a1d24',
                    900: '#0f1116',
                    950: '#091923',
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                display: ['Outfit', 'system-ui', 'sans-serif'],
            },
            boxShadow: {
                'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
                'glow': '0 0 40px rgba(12, 142, 230, 0.3)',
                'glow-accent': '0 0 40px rgba(217, 70, 239, 0.3)',
            },
            backdropBlur: {
                xs: '2px',
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out',
                'slide-up': 'slideUp 0.5s ease-out',
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
            },
        },
    },
    plugins: [
        typography,
    ],
}
