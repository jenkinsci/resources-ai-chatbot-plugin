import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const outDir = (process.env as { DOCKER_BUILD?: string }).DOCKER_BUILD
  ? "dist"
  : "../src/main/webapp/static";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],
    base: "",
    define: {
      "process.env.VITE_API_BASE_URL": JSON.stringify(env.VITE_API_BASE_URL),
      "process.env.NODE_ENV": JSON.stringify(mode),
    },
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
  };
});
