/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import type { Locator, Page } from "@playwright/test";

export function pushCopyrightYearMask({
  page: _page,
  defaultMasks: _defaultMasks,
}: {
  page: Page;
  defaultMasks: Locator[];
}): void {
  // Repo-specific: push the copyright year locator into defaultMasks, e.g.:
  // defaultMasks.push(page.getByTestId(forComponent({ selector: layout.copyrightYear })));
}

export function pushLogoMask({
  page: _page,
  defaultMasks: _defaultMasks,
}: {
  page: Page;
  defaultMasks: Locator[];
}): void {
  // Repo-specific: push the company logo locator into defaultMasks, e.g.:
  // defaultMasks.push(page.getByTestId(forComponent({ selector: layout.logo })));
}
