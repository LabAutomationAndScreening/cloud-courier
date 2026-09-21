/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { createServer } from "node:net";

import { DEPLOYED_BACKEND_PORT_NUMBER, DEPLOYED_FRONTEND_PORT_NUMBER } from "../setup/constants";

// Two ways the E2E suite gets a backend to run against, selected by env var:
// - USE_BUILT_BACKEND_FOR_E2E: a single PyInstaller executable serves both the static frontend and the
//   API on ONE port. The port is chosen at random (see BUILT_BACKEND_PORT_ENV) because the default port
//   is sometimes already taken in CI.
// - USE_DOCKER_COMPOSE_FOR_E2E: docker-compose exposes the frontend and backend on their two separate
//   deployed ports.
export const isBuiltBackendE2E = Boolean(process.env.USE_BUILT_BACKEND_FOR_E2E);
export const isDockerComposeE2E = Boolean(process.env.USE_DOCKER_COMPOSE_FOR_E2E);

// playwright.config.ts loads first (main process) and calls ensureBuiltBackendPort to compute the port
// and stash it here. Worker processes inherit the resolved env and re-read it, so every process —
// config, globalSetup, and the test workers building the backend client — agrees on the same port.
const BUILT_BACKEND_PORT_ENV = "E2E_BUILT_BACKEND_PORT";

function getRandomOpenPort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.on("error", (err) => {
      reject(err);
    });
    server.listen(0, () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close();
        reject(new Error("Failed to get port number"));
        return;
      }
      const { port } = address;
      server.close(() => {
        resolve(port);
      });
    });
  });
}

export async function ensureBuiltBackendPort(): Promise<void> {
  if (isBuiltBackendE2E && !process.env[BUILT_BACKEND_PORT_ENV]) {
    process.env[BUILT_BACKEND_PORT_ENV] = (await getRandomOpenPort()).toString();
  }
}

function builtBackendPort(): number {
  const port = process.env[BUILT_BACKEND_PORT_ENV];
  if (!port) {
    throw new Error(
      `${BUILT_BACKEND_PORT_ENV} is not set — playwright.config.ts must call ensureBuiltBackendPort first`,
    );
  }
  return Number(port);
}

export function frontendBaseUrl(): string {
  if (isBuiltBackendE2E) {
    return `http://127.0.0.1:${builtBackendPort()}`;
  }
  return `http://127.0.0.1:${DEPLOYED_FRONTEND_PORT_NUMBER}`;
}

export function backendBaseUrl(): string {
  if (isBuiltBackendE2E) {
    return `http://127.0.0.1:${builtBackendPort()}`;
  }
  return `http://127.0.0.1:${DEPLOYED_BACKEND_PORT_NUMBER}`;
}
