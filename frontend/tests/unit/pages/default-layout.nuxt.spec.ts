/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { mountSuspended } from "@nuxt/test-utils/runtime";
import { describe, expect, test } from "vitest";

import DefaultLayout from "~/layouts/default.vue";

describe("default layout", () => {
  test("component mounts without error", async () => {
    expect.assertions(1);

    const wrapper = await mountSuspended(DefaultLayout);

    expect(wrapper.text()).toContain("Hello");
  });
});
