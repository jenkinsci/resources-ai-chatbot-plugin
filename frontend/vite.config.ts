import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const outDir = (process.env as { DOCKER_BUILD?: string }).DOCKER_BUILD
  ? "dist"
  : "../src/main/webapp/static";

export default defineConfig({
  plugins: [react()],
  base: "",
  build: {
    outDir: outDir,
    assetsDir: "assets",
    rollupOptions: {
      output: {
        entryFileNames: "assets/index.js",
        assetFileNames: "assets/index.css",
      },
    },
  },
});
