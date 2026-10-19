import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
// defineConfig comes from "vitest/config" (not plain "vite") so the `test`
// block below type-checks under `tsc -b` -- it re-exports Vite's own
// defineConfig with Vitest's config types merged in; `vite build`/`vite dev`
// behave identically either way, since Vitest adds no runtime behavior here.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  // Vitest reuses this same config file -- `vite build`/`vite dev` ignore
  // the `test` block entirely, so it's safe to keep it here rather than a
  // separate vitest.config.ts.
  test: {
    environment: "node", // evidence.ts/api.ts are plain logic, no DOM needed yet
  },
});
