/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "surface": "#F7F3E8",
        "background": "#F7F3E8",
        "surface-container-lowest": "#FFFDF5",
        "surface-container-low": "#FFF1E8",
        "surface-container": "#FEEADC",
        "surface-container-high": "#F8E5D6",
        "surface-container-highest": "#F2DFD1",
        "surface-dim": "#E9D7C8",
        "surface-variant": "#F2DFD1",
        
        "primary": "#6FAF5F",
        "primary-container": "#6FAF5F",
        "primary-dark": "#3F7042",
        "on-primary": "#FFFDF5",
        "on-primary-container": "#014100",
        "primary-fixed": "#B0F49C",
        "primary-fixed-dim": "#95D782",
        "on-primary-fixed-variant": "#14520D",

        "secondary": "#A9784F",
        "secondary-dark": "#80552F",
        "secondary-light": "#D8B892",
        "secondary-container": "#FDC394",
        "secondary-fixed": "#FFDCC2",
        "secondary-fixed-dim": "#F4BB8D",
        "on-secondary-container": "#794E29",
        "on-secondary-fixed": "#2E1500",

        "tertiary": "#E5B84B",
        "tertiary-dark": "#785A00",
        "tertiary-container": "#C49A2F",
        "tertiary-fixed": "#FFDF9B",
        "tertiary-fixed-dim": "#EEC052",
        "on-tertiary-container": "#473400",

        "sky-accent": "#8FC8D8",
        "sky-light": "#BFE5ED",

        "on-surface": "#2B2118",
        "on-surface-dark": "#231A11",
        "on-surface-variant": "#6B5C4D",
        "outline": "#717A6C",
        "outline-variant": "#C1C9B9",
        
        "track": "#EFE8D3",
        "error": "#BA1A1A",
        "error-container": "#FFDAD6",
        "on-error-container": "#93000A"
      },
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        body: ["Plus Jakarta Sans", "sans-serif"],
        "headline-sm": ["Space Grotesk", "sans-serif"],
        "body-sm": ["Plus Jakarta Sans", "sans-serif"],
        "body-md": ["Plus Jakarta Sans", "sans-serif"],
        "label-lg": ["Space Grotesk", "sans-serif"],
        "label-md": ["Plus Jakarta Sans", "sans-serif"],
        "label-sm": ["Plus Jakarta Sans", "sans-serif"],
      },
      borderRadius: {
        "xs": "2px",
        "sm": "2px",
        "DEFAULT": "4px",
        "md": "6px",
        "lg": "8px",
        "xl": "12px",
      },
      boxShadow: {
        "hard-sm": "0 2px 0 0 #2B2118",
        "hard-md": "0 4px 0 0 #2B2118",
        "hard-lg": "0 6px 0 0 #2B2118",
        "hard-xl": "0 8px 0 0 #2B2118",
        "hard-primary": "0 4px 0 0 #3F7042",
        "hard-secondary": "0 4px 0 0 #A9784F",
        "hard-xp": "0 4px 0 0 #B88526",
      }
    },
  },
  plugins: [],
}
