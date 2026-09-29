/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { faker } from "@faker-js/faker";
import { AnonymousAuthenticationProvider } from "@microsoft/kiota-abstractions";
import { FetchRequestAdapter, KiotaClientFactory } from "@microsoft/kiota-http-fetchlibrary";
import { test as base } from "@playwright/test";

import { type BackendClient, createBackendClient } from "~/generated/open-api/backend/backendClient";
import { backendBaseUrl } from "./ports";

function hasErrorCode(cause: unknown): cause is { code: string } {
  return typeof cause === "object" && cause !== null && "code" in cause && typeof cause.code === "string";
}

// Windows CI resets idle keep-alive sockets the backend has already closed; undici surfaces this as a
// `fetch failed` / ECONNRESET and does NOT auto-retry non-idempotent requests (e.g. POST /api/git/clone).
// A long gap with no backend traffic (the git work in createGenericRepo) makes the reset likely, so retry
// the transport here. The reset happens before the request reaches the server, so re-sending is safe.
async function retryingFetch(request: string, init: RequestInit): Promise<Response> {
  const maxAttempts = 4;
  let lastError: unknown;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fetch(request, init);
    } catch (error) {
      const isConnectionReset =
        error instanceof TypeError &&
        "cause" in error &&
        hasErrorCode(error.cause) &&
        error.cause.code === "ECONNRESET";
      if (!isConnectionReset) {
        throw error;
      }
      lastError = error;
      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 100 * attempt));
      }
    }
  }
  throw lastError;
}

// Mirrors tests/setup/faker.ts (used by the vitest unit/compiled projects). Seed once per worker so a
// failing run can be reproduced with TEST_FAKER_SEED=<logged value>. Playwright runs files in a stable
// order (no vitest-style shuffle), so seed + order reproduce the sequence.
const parsedSeed = Number(process.env.TEST_FAKER_SEED);
const fakerSeed = Number.isNaN(parsedSeed) ? Math.floor(Math.random() * 1e9) : parsedSeed;

// Build the kiota client directly (rather than via nuxt-common's useKiotaClient) with an explicit
// baseUrl — keeps this test harness free of a nuxt-common dependency. This is the same adapter
// useKiotaClient constructs internally.
function buildBackendClient(): BackendClient {
  const adapter = new FetchRequestAdapter(
    new AnonymousAuthenticationProvider(),
    undefined, // parseNodeFactory — use default
    undefined, // serializationWriterFactory — use default
    KiotaClientFactory.create(retryingFetch),
  );
  adapter.baseUrl = backendBaseUrl();
  return createBackendClient(adapter);
}

// eslint-disable-next-line @typescript-eslint/no-invalid-void-type -- `void` is Playwright's idiom for a worker fixture that provides no value (auto-run side effect only)
export const test = base.extend<{ backendClient: BackendClient }, { seedFaker: void }>({
  seedFaker: [
    // eslint-disable-next-line no-empty-pattern -- Playwright requires the first fixture arg to be object-destructured; `{}` is the zero-dependency form
    async ({}, use) => {
      console.log("[seed passed to faker]", fakerSeed);
      faker.seed(fakerSeed);
      await use();
    },
    { scope: "worker", auto: true },
  ],
  // The kiota client is built directly (FetchRequestAdapter + AnonymousAuthenticationProvider with an
  // explicit baseUrl) rather than via nuxt-common's useBackendClient, to keep nuxt-common not as a required dependency (for now).
  // eslint-disable-next-line no-empty-pattern -- Playwright requires the first fixture arg to be object-destructured; `{}` is the zero-dependency form
  backendClient: async ({}, use) => {
    await use(buildBackendClient());
  },
});

// Use this in anything calling toHaveScreenshot. It inherits backendClient and
// auto-skips on Windows, where we have no easy way to record platform-matching baselines. Behavioral
// specs keep using `test` so they still run on Windows. The skip is wired as an auto-fixture (rather
// than `vrtTest.skip()` inside a beforeEach) so the running test's TestInfo is threaded in explicitly —
// the static `test.skip(cond, msg)` form was a no-op for tests defined on an extended test instance.
// eslint-disable-next-line @typescript-eslint/no-invalid-void-type -- `void` is Playwright's idiom for an auto-run fixture that provides no value
export const vrtTest = test.extend<{ skipOnWindows: void }>({
  skipOnWindows: [
    // eslint-disable-next-line no-empty-pattern -- Playwright requires the first fixture arg to be object-destructured; `{}` is the zero-dependency form
    async ({}, use, testInfo) => {
      testInfo.skip(process.platform === "win32", "VRT baselines are generated on Linux only");
      await use();
    },
    { auto: true },
  ],
});

export { expect } from "@playwright/test";
