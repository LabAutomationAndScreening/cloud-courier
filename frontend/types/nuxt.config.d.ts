/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { NuxtConfig } from "nuxt/schema"; // unclear why this is showing up as an unused-var...it seems to be used as interface down below

declare module "nuxt/schema" {
  interface NuxtConfig {
    apollo?: {
      clients: {
        default: {
          httpEndpoint: string;
        };
      };
    };
  }
}
