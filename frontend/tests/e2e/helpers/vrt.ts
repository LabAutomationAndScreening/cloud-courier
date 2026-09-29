/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { expect, type Locator, type Page } from "@playwright/test";
import { pushCopyrightYearMask, pushLogoMask } from "./vrt-masks";

type ColorScheme = "light" | "dark";

function withColorSchemeSuffix(name: string, colorScheme: ColorScheme): string {
  const baseName = name.endsWith(".png") ? name.slice(0, -4) : name;
  return `${baseName}-${colorScheme}.png`;
}
// Full-page visual snapshot taken in both light and dark mode by default. The app's color mode keys
// off prefers-color-scheme (@nuxtjs/color-mode preference defaults to "system"), so emulateMedia
// drives it programmatically — no UI toggle needed. Each scheme writes its own baseline (the scheme
// is appended to the filename). Override `colorSchemes` (e.g. ["light"]) to limit it.
//
// The copyright year (`new Date().getFullYear()`) and the company logo are masked by default. Playwright masks
// are z-unaware — they paint a flat rect at the element's bounding box over the final image — so
// anything stacked above (e.g. a slideover/popover over the logo) gets covered; pass
// `maskLogo: false` / `maskCopyrightYear: false` for those tests. Pass `mask` to add further regions.
export async function expectFullPageScreenshot(
  page: Page,
  name: string,
  {
    masks = [],
    maskLogo = true,
    maskCopyrightYear = true,
    colorSchemes = ["light", "dark"],
  }: { masks?: Locator[]; maskLogo?: boolean; maskCopyrightYear?: boolean; colorSchemes?: ColorScheme[] } = {},
): Promise<void> {
  for (const colorScheme of colorSchemes) {
    await page.emulateMedia({ colorScheme });
    await expectFullPageScreenshotInCurrentColorMode(page, withColorSchemeSuffix(name, colorScheme), {
      masks,
      maskLogo,
      maskCopyrightYear,
    });
  }
}

// Main-content-only visual snapshot (no navbar/header/footer) taken in both light and dark mode by
// default. Uses `#__nuxt > div > * > main` — the wildcard third segment avoids coupling to the
// layout wrapper's utility classes. Pass `mask` to cover any dynamic regions inside the content area
// (e.g. non-deterministic ids); masks are z-unaware and paint a flat rect over the element's box.
export async function expectContentPaneScreenshot(
  page: Page,
  name: string,
  { mask = [], colorSchemes = ["light", "dark"] }: { mask?: Locator[]; colorSchemes?: ColorScheme[] } = {},
): Promise<void> {
  for (const colorScheme of colorSchemes) {
    await page.emulateMedia({ colorScheme });
    const main = page.locator("#__nuxt > div > * > main");
    await expect(main).toHaveScreenshot(withColorSchemeSuffix(name, colorScheme), { mask });
  }
}

// Element-scoped visual snapshot taken in both light and dark mode by default. Screenshots just the
// given locator rather than the whole page or content pane, so the baseline is insensitive to
// unrelated layout changes elsewhere on the page. Use this for a self-contained widget/section that
// already has a broader page-level VRT covering overall layout. Pass `mask` to cover dynamic regions
// within the element; masks are z-unaware and paint a flat rect over the element's box.
export async function expectElementScreenshot(
  locator: Locator,
  name: string,
  { mask = [], colorSchemes = ["light", "dark"] }: { mask?: Locator[]; colorSchemes?: ColorScheme[] } = {},
): Promise<void> {
  for (const colorScheme of colorSchemes) {
    await locator.page().emulateMedia({ colorScheme });
    await expect(locator).toHaveScreenshot(withColorSchemeSuffix(name, colorScheme), { mask });
  }
}

// A single full-page snapshot in whatever color mode is currently active — does not touch
// emulateMedia. Use this when the color mode is driven another way (e.g. clicking the color-mode
// switch), so the snapshot reflects that state rather than a re-emulated one.
export async function expectFullPageScreenshotInCurrentColorMode(
  page: Page,
  name: string,
  {
    masks = [],
    maskLogo = true,
    maskCopyrightYear = true,
  }: { masks?: Locator[]; maskLogo?: boolean; maskCopyrightYear?: boolean } = {},
): Promise<void> {
  const defaultMasks: Locator[] = [];
  if (maskCopyrightYear) {
    pushCopyrightYearMask({ page, defaultMasks });
  }
  if (maskLogo) {
    pushLogoMask({ page, defaultMasks });
  }
  await expect(page).toHaveScreenshot(name, {
    fullPage: true,
    mask: [...defaultMasks, ...masks],
  });
}

// Navigation-rail-only visual snapshot (the ShellRail `<aside>`) taken in both light and dark mode by
// default. The logo is masked (it swaps light/dark variants); pass `colorSchemes` to limit the modes.
export async function expectNavigationRailScreenshot(
  page: Page,
  name: string,
  { colorSchemes = ["light", "dark"] }: { colorSchemes?: ColorScheme[] } = {},
): Promise<void> {
  for (const colorScheme of colorSchemes) {
    await page.emulateMedia({ colorScheme });
    const defaultMasks: Locator[] = [];
    pushLogoMask({ page, defaultMasks });
    const rail = page.locator("aside");
    await expect(rail).toHaveScreenshot(withColorSchemeSuffix(name, colorScheme), { mask: defaultMasks });
  }
}
