import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://tetsuoyamashita.github.io',
  base: '/trend-digest',
  output: 'static',
  build: {
    format: 'directory',
  },
  trailingSlash: 'ignore',
});
