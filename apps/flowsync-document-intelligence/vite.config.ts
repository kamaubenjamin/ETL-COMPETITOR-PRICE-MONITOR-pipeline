import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [
    react(),
    {
      name: "remove-upstream-local-auth-default",
      apply: "build",
      generateBundle(_options, bundle) {
        for (const output of Object.values(bundle)) {
          if (output.type === "chunk") {
            output.code = output.code.replaceAll("http://localhost:9999", "https://localhost.invalid");
          }
        }
      },
    },
  ],
  build: {
    sourcemap: false,
  },
  server: {
    host: "127.0.0.1",
    port: 4174,
  },
  preview: {
    host: "127.0.0.1",
    port: 4175,
  },
});

