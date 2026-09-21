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
import { beforeAll } from "vitest";

declare const __TEST_FAKER_SEED__: number;

console.log("[seed passed to faker]", __TEST_FAKER_SEED__);
beforeAll(() => {
  // ensure faker has specified seed so that test runs could be recreated with the logged seed.
  faker.seed(__TEST_FAKER_SEED__);
});
