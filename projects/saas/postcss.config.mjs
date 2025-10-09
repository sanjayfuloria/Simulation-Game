import autoprefixer from 'autoprefixer';

// We compile Tailwind ahead-of-time via the `build:css` script to avoid
// requiring native transformers (lightningcss) during the Next/Turbopack
// build. Keep autoprefixer enabled for vendor prefixing.
const config = {
  plugins: {
    autoprefixer: {},
  },
};

export default config;
