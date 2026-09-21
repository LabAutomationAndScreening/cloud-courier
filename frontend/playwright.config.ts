/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";
import { ensureBuiltBackendPort, frontendBaseUrl } from "./tests/e2e/ports";

const e2eDir = fileURLToPath(new URL("./tests/e2e", import.meta.url));

// The built-backend executable serves frontend + API on one randomly-chosen port. Resolve it here, in
// the main process, before referencing frontendBaseUrl() — worker processes inherit the env and re-read
// the same value. No-op in docker-compose mode (fixed ports).
await ensureBuiltBackendPort();

export default defineConfig({
  testDir: e2eDir,
  // The {platform} token means a baseline recorded on linux CI will not silently match a developer's
  // macOS run — font hinting/antialiasing differ per OS, so a mismatch is surfaced rather than hidden.
  // Regenerate per-platform with `--update-snapshots`.
  snapshotPathTemplate: "{testDir}/__screenshots__/{testFilePath}/{arg}-{platform}{ext}",
  fullyParallel: false, // shared docker-compose backend state across specs
  forbidOnly: process.env.CI === "true",
  retries: process.env.CI === "true" ? 1 : 0,
  workers: 1,
  reporter: process.env.CI === "true" ? [["html", { open: "never" }], ["list"]] : [["list"]],
  globalSetup: fileURLToPath(new URL("./tests/e2e/global-setup.ts", import.meta.url)),
  globalTeardown: fileURLToPath(new URL("./tests/e2e/global-teardown.ts", import.meta.url)),
  use: {
    baseURL: frontendBaseUrl(),
    // View a failure's trace.zip (which will be generated in the `test-results` folder) with:
    //   pnpm exec playwright show-trace --host 0.0.0.0 --port <any-open-port> <path/to/trace.zip>
    // The --host/--port flags are required in the devcontainer so the viewer is reachable via a
    // forwarded port (the default `show-trace` launches a local browser and errors out with no display).
    trace: "retain-on-failure",
  },
  expect: {
    toHaveScreenshot: {
      // disable CSS animations/transitions and hide the text caret so neither introduces per-run noise
      animations: "disabled",
      caret: "hide",
      // tolerate sub-pixel antialiasing differences without masking real regressions
      maxDiffPixelRatio: 0.01,
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
