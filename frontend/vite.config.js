import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_BASE = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": { target: API_BASE, changeOrigin: true },
      "/users": { target: API_BASE, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
