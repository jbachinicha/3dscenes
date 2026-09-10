import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const here = (p) => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  // Relative base so the built files work from any subpath (e.g. GitHub Pages
  // project sites at username.github.io/repo-name/) as well as from the root.
  base: './',
  build: {
    rollupOptions: {
      // Multi-page: every scene needs listing here or it won't be built.
      // The dev server serves any .html without this, so it's easy to forget.
      input: {
        home: here('index.html'),
        island: here('scenes/island/index.html'),
        timeline: here('scenes/timeline/index.html'),
        lanternWay: here('scenes/lantern-way/index.html'),
      },
    },
  },
});
