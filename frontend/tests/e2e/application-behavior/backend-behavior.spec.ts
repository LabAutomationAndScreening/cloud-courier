/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { expect, test } from "~~/tests/e2e/fixtures";

test.describe("API documentation", () => {
  test("When accessing Swagger from the frontend, Then loads correctly", async ({ page }) => {
    await page.goto("/api-docs");

    // arbitrary text that only appears after the page has loaded correctly
    await expect(page.getByText("/api/healthcheck")).toBeVisible();
  });
});
