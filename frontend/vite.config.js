import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// CORS note (handoff doc §7):
// Backend CORS defaults to http://localhost:3000.
// host: true exposes the dev server across local Wi-Fi for teammates.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
  },
});
