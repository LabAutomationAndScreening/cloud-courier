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

test.describe("Index page", () => {
  test("Page displays Hello World", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Hello World")).toBeVisible();
  });
});
