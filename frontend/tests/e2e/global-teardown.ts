/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { APP_NAME } from "../setup/constants";
import { composeDown } from "./compose";
import { backendBaseUrl, isBuiltBackendE2E, isDockerComposeE2E } from "./ports";

const repoRoot = path.resolve(fileURLToPath(new URL("../../../", import.meta.url)));
const dockerComposeFile = path.resolve(repoRoot, "docker-compose.yaml");

function hasErrorCode(cause: unknown): cause is { code: string } {
  return typeof cause === "object" && cause !== null && "code" in cause && typeof cause.code === "string";
}

async function stopBuiltBackend(): Promise<void> {
  console.log("Stopping application...");
  try {
    const res = await fetch(`${backendBaseUrl()}/api/shutdown`, {
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });
    if (!res.ok) {
      throw new Error(`Failed to stop the application: ${res.statusText}`);
    }
    // Wait a bit for graceful shutdown
    await new Promise((resolve) => setTimeout(resolve, 1000));
  } catch (error) {
    // ECONNRESET is expected when the server shuts down during the request. This happens in Windows CI frequently
    if (error instanceof Error && "cause" in error && hasErrorCode(error.cause)) {
      if (
        error.cause.code === "ECONNRESET" ||
        error.cause.code === "ENOTFOUND" ||
        error.cause.code === "UND_ERR_SOCKET"
      ) {
        console.log("Application shutdown successfully (connection closed)");
        return;
      }
    }

    const logFilePath = path.resolve(repoRoot, `./frontend/logs/${APP_NAME}-backend.log`);
    // sometimes it takes a second for the log file to be fully written to disk
    await new Promise((resolve) => setTimeout(resolve, 1000));
    if (!fs.existsSync(logFilePath) || !fs.statSync(logFilePath).isFile()) {
      throw new Error(`Log file not found: ${logFilePath}`, { cause: error });
    }
    const logData = fs.readFileSync(logFilePath, "utf-8");
    console.log("Application logs:\n", logData);
    throw error;
  }
}

export default async function globalTeardown(): Promise<void> {
  if (isBuiltBackendE2E) {
    await stopBuiltBackend();
  }
  if (isDockerComposeE2E) {
    console.log("Stopping docker-compose...");
    composeDown({ composeFile: dockerComposeFile });
  }
}
