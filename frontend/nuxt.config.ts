/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
// https://nuxt.com/docs/api/configuration/nuxt-config
import { defineNuxtConfig } from "nuxt/config";

const useOptimizeDeps = process.env.NUXT_DISABLE_OPTIMIZE_DEPS !== "1";

export default defineNuxtConfig({
  compatibilityDate: "2024-11-01",
  future: {
    compatibilityVersion: 4, // as of 2026-03-05, @nuxt/icon v2.1.1 was not compatible with v5, so waiting a bit longer
  },
  devtools: { enabled: process.env.NODE_ENV !== "test" },
  telemetry: process.env.NODE_ENV !== "test",
  // the conditional modules added in by the template make it complicated to format consistently...at least with only 3 'always included' modules
  // prettier-ignore
  modules: [
    "@nuxt/ui",
    ["@nuxt/eslint", { devOnly: true }],
    ["@nuxt/test-utils/module", { devOnly: true }],
  ],
  icon: {
    provider: "none", // bundle all icons into the build for air-gapped deployments
    clientBundle: {
      scan: true,
      icons: [
        "lucide:check", // the way @nuxt/ui creates checkboxes, the check mark doesn't seem to be picked up by scanning.
        "lucide:chevron-down", // the way @nuxt/ui creates accordions, the chevron-down doesn't seem to be picked up by scanning.
        "lucide:x", // UInputTags needs lucide:x
        "lucide:plus", // and UInputNumber needs lucide:plus and lucide:minus
        "lucide:minus", // and UInputNumber needs lucide:plus and lucide:minus
        "lucide:arrow-up-right", // the way @nuxt/ui creates Navigation Menu links that open in new windows it uses this icon
        "lucide:arrow-up-down", // this is used for sortable table headers and it looks like `scan` doesn't pick it up from the .ts file
        "lucide:arrow-up-narrow-wide", // this is used for sortable table headers and it looks like `scan` doesn't pick it up from the .ts file
        "lucide:arrow-down-wide-narrow", // this is used for sortable table headers and it looks like `scan` doesn't pick it up from the .ts file
        "lucide:moon", // UColorModeSwitch needs lucide:moon and lucide:sun
        "lucide:sun", // UColorModeSwitch needs lucide:moon and lucide:sun
        "lucide:menu", // UDashboard needs lucide:menu
      ],
      sizeLimitKb: 256, // fail the build if there's somehow more than this amount of icons
    },
  },
  css: ["~/assets/css/main.css"],
  experimental: { appManifest: false }, // https://github.com/nuxt/nuxt/issues/30461#issuecomment-2572616714
  nitro: {
    esbuild: {
      options: {
        target: "es2024", // no specific reason for pinning to this version, but the default for nitro was 2019, so using something a bit more modern
      },
    },
    prerender: {
      concurrency: 1, // lower the concurrency to not be such a memory hog
      interval: 200, // ms pause between batches – lets the Garbage Collector catch up
    },
    devProxy: {
      // this is just a proxy used for `pnpm dev`
      "/api": {
        target: "http://localhost:4000/api", // backend dev port
        changeOrigin: true, // rewrite Host header
      },
    },
  },
  vite: {
    server: {
      watch: {
        usePolling: true, // this seems to be explicitly needed when in a devcontainer in order for hot reloading to work
      },
    },
    ...(useOptimizeDeps
      ? {
          optimizeDeps: {
            // the conditional modules added in by the template make it complicated to format consistently
            // prettier-ignore
            include: [
                        "@microsoft/kiota-abstractions",
                        "@microsoft/kiota-http-fetchlibrary",
                     ],
          },
        }
      : {}),
  },
});
