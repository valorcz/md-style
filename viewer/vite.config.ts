import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: path.resolve(import.meta.dirname, '../core/assets'),
    emptyOutDir: false,
    lib: {
      entry: path.resolve(import.meta.dirname, 'src/main.ts'),
      name: 'MdStyleViewer',
      formats: ['iife'],
      fileName: () => 'viewer.bundle.js'
    },
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'viewer.bundle.css';
          }
          return '[name].[ext]';
        }
      }
    }
  }
});
