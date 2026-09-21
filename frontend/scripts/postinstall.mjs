/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

// Cross-platform postinstall script since E2E tests need to execute in Windows CI too, and the postinstall logic was getting complicated
const rootDir = fileURLToPath(new URL("..", import.meta.url));
const shouldInstallPlaywright = process.env.SKIP_PLAYWRIGHT_INSTALL !== "1";
const useShell = process.platform === "win32";

const run = (...args) => {
  execFileSync("pnpm", args, {
    cwd: rootDir,
    env: process.env,
    shell: useShell,
    stdio: "inherit",
  });
};

run("exec", "nuxt", "prepare");

if (shouldInstallPlaywright) {
  run("exec", "playwright-core", "install", "--with-deps", "chromium");
}
