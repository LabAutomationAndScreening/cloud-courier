import { expect, test } from "~~/tests/e2e/fixtures";

// The version is read at runtime from the installed package metadata, so a PyInstaller build that failed
// to bundle that metadata reports the wrong version, or fails outright, only once frozen. This is the
// check the old tests/executable/test_intact.py made against `--version`, moved somewhere that actually
// runs in CI: this suite launches the built executable.
test.describe("Reported version", () => {
  test("When the healthcheck is called, Then the version looks like semver", async ({ backendClient }) => {
    const expectedVersionSegments = 3;

    const response = await backendClient.api.healthcheck.get();
    const version = response?.version;

    expect(version).toBeTruthy();
    expect(version?.split(".")).toHaveLength(expectedVersionSegments);
  });

  test("Given prependV requested, When the healthcheck is called, Then the version is prefixed with v", async ({
    backendClient,
  }) => {
    const response = await backendClient.api.healthcheck.get({ queryParameters: { prependV: true } });
    const version = response?.version;

    expect(version).toBeTruthy();
    expect(version).toMatch(/^v/);
  });
});
