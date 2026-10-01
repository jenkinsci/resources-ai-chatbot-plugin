import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    plugins: [react()],
    base: "",
    define: {
      __VITE_API_BASE_URL__: JSON.stringify(env.VITE_API_BASE_URL),
    },
    build: {
      outDir: "../src/main/webapp/static",
      emptyOutDir: true,
      assetsDir: "assets",
      rollupOptions: {
        output: {
          entryFileNames: "assets/index.js",
          assetFileNames: "assets/index.css",
        },
      },
    },
  };
});
