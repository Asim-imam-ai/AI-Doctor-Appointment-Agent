
/// <reference types="vitest/config" />

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  // ==========================================
  // React and Tailwind CSS Plugins
  // ==========================================
  plugins: [
    react(),
    tailwindcss(),
  ],

  // ==========================================
  // Development Server Configuration
  // ==========================================
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,

    // Proxy frontend API requests to FastAPI
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },

  // ==========================================
  // Production Build Optimization
  // ==========================================
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Only split third-party dependencies
          if (!id.includes("node_modules")) {
            return;
          }

          // Supabase SDK
          if (id.includes("@supabase")) {
            return "supabase";
          }

          // UI dependencies
          if (
            id.includes("lucide-react") ||
            id.includes("date-fns")
          ) {
            return "ui";
          }

          // React dependencies
          if (
            id.includes("react-dom") ||
            id.includes("react-router") ||
            id.includes("/react/")
          ) {
            return "react";
          }

          // Forms and validation
          if (
            id.includes("zod") ||
            id.includes("react-hook-form") ||
            id.includes("@tanstack")
          ) {
            return "forms";
          }

          // Let Vite handle remaining dependencies
          return;
        },
      },
    },
  },

  // ==========================================
  // Vitest Configuration
  // ==========================================
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
