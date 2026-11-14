import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server forwards /api to the FastAPI backend so the browser only
// ever talks to one origin (no CORS configuration needed for local work).
export default defineConfig({
  plugins: [react()],
  // MapLibre starts its worker as an ES module.
  worker: { format: "es" },
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
    // Allow importing the shared example in ../contracts.
    fs: { allow: [".."] },
  },
});
