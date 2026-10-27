import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        ink: '#080d13',
        panel: '#101923',
        line: '#223140',
        muted: '#91a1b2',
        accent: '#57e0bd',
      },
      boxShadow: { glow: '0 0 28px rgba(87, 224, 189, .08)' },
    },
  },
  plugins: [],
};

export default config;
