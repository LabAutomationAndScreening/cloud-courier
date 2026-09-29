/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { createPage, setup, url } from "@nuxt/test-utils/e2e";
import { describe, expect, test } from "vitest";

describe("Index page", async () => {
  await setup();
  test("Page displays Hello World", async () => {
    expect.assertions(1);
    const page = await createPage();

    await page.goto(url("/"), { waitUntil: "hydration" });

    const text = await page.textContent("div");

    expect(text).toContain("Hello World");
  });
});
