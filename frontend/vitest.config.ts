/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { fileURLToPath } from "node:url";
import { defineVitestProject } from "@nuxt/test-utils/config";
import { configDefaults, defineConfig, type TestProjectInlineConfiguration } from "vitest/config";

const fakerSeed = Number(process.env.TEST_FAKER_SEED) || Math.floor(Math.random() * 1e9); // to use this, you'll need to create a setup.ts file and add it to the vitest `setupFiles` config

const sharedDefine = {
  __TEST_FAKER_SEED__: JSON.stringify(fakerSeed),
};
const frontendDir = fileURLToPath(new URL(".", import.meta.url));
const appDir = fileURLToPath(new URL("./app", import.meta.url));
const fakerSetupPath = fileURLToPath(new URL("./tests/setup/faker.ts", import.meta.url));
const autoUnmountSetupPath = fileURLToPath(new URL("./tests/setup/auto-unmount.ts", import.meta.url));

const sharedAliases = {
  "~~": frontendDir,
  "@@": frontendDir,
  "~": appDir,
  "@": appDir,
};

// Tests against components/pages that rely on Nuxt — auto-imported composables,
// Nuxt UI components, mountSuspended, etc.
const unitNuxtProject = await defineVitestProject({
  define: sharedDefine,
  test: {
    name: "unit-nuxt",
    include: ["tests/unit/**/*.nuxt.spec.ts"],
    setupFiles: [fakerSetupPath, autoUnmountSetupPath],
  },
});

// Tests that need a DOM but no Nuxt runtime (e.g. plain @vue/test-utils mount,
// or non-Vue code that touches `document`/`window`).
const unitDomProject = {
  resolve: {
    alias: sharedAliases,
  },
  test: {
    name: "unit-dom",
    environment: "happy-dom",
    include: ["tests/unit/**/*.dom.spec.ts"],
    setupFiles: [autoUnmountSetupPath],
  },
} satisfies TestProjectInlineConfiguration;

// Pure logic tests — no DOM, no Vue. Fastest env; default unless a spec is
// named `.nuxt.spec.ts` or `.dom.spec.ts`.
const unitNodeProject = {
  resolve: {
    alias: sharedAliases,
  },
  test: {
    name: "unit-node",
    environment: "node",
    include: ["tests/unit/**/*.spec.ts"],
    exclude: [...configDefaults.exclude, "**/*.nuxt.spec.ts", "**/*.dom.spec.ts"],
  },
} satisfies TestProjectInlineConfiguration;

const bunTestStubPath = fileURLToPath(new URL("./tests/setup/bun-test-stub.ts", import.meta.url));

// The compiled-suite spec uses `@nuxt/test-utils/e2e` helpers (`setup()`, `createPage()`)
// which spawn their own Nuxt build/dev subprocess and drive a real browser. The vitest
// environment for this project therefore stays at "node" — there is no in-process Nuxt
// runtime to attach. Per https://github.com/nuxt/nuxt/issues/34645#issuecomment-4109134809
// (danielroe), `defineVitestProject` from `@nuxt/test-utils/config` is intended only for
// projects where `environment: "nuxt"` runs nuxt client code in-process; wrapping a
// node-environment project with it triggers the vite-node + `--conditions=node,import,default`
// path that breaks dual-export CJS deps inside @vue/compiler-sfc.
const compiledProject = {
  extends: true,
  define: sharedDefine,
  // @nuxt/test-utils v4 has an internal cross-runtime helper that dynamically imports "bun:test".
  // In the compiled test environment Vite tries to pre-bundle it and fails with "Cannot bundle
  // built-in module 'bun:test'". Aliasing to a local stub lets Vite resolve the import; the
  // Bun-runtime branch never runs under Node so the stub is never invoked.
  // Tracked upstream: https://github.com/nuxt/test-utils/issues/1490
  resolve: {
    alias: {
      "bun:test": bunTestStubPath,
      // The compiled spec imports `@nuxt/test-utils/e2e` helpers; those resolve nuxt's
      // `~`/`~~`/`@`/`@@` aliases internally. The vitest spec itself does not need the
      // aliases (no `~`-prefixed imports in tests/compiled), but adding them here matches
      // the e2e project so any future helper imports work without surprise.
      ...sharedAliases,
    },
  },
  test: {
    name: "compiled",
    include: ["tests/compiled/**/*.spec.ts"],
    setupFiles: [fakerSetupPath],
    // Dev mode cold-compiles modules on first page hit; production build serves prebuilt
    // chunks, so the dev pipeline needs a longer per-test budget than the prod one.
    testTimeout: process.env.NUXT_TEST_DEV === "1" ? 60000 : 15000,
  },
} satisfies TestProjectInlineConfiguration;

export default defineConfig({
  define: sharedDefine,
  test: {
    sequence: {
      shuffle: true,
      seed: fakerSeed,
    },
    root: ".",
    projects: [unitNuxtProject, unitDomProject, unitNodeProject, compiledProject],
    coverage: {
      provider: "istanbul",
      reporter: ["text", "json", "html"],
      reportsDirectory: ".coverage",
      thresholds: {
        "100": true,
      },
      include: ["app/**/*.{ts,vue}"],
      exclude: ["**/generated/**"],
    },
  },
});
