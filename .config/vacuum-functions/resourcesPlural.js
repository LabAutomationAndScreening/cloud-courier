/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
// Vacuum custom JS function (goja runtime: no npm, no require/import — plain self-contained JS).
//
// Flags static path segments that look like singular resource nouns; REST collections should be plural
// (gov.au naming). `given: $.paths[*]~` passes each path key (e.g. "/api/data/devices/{device_id}") as
// the single `input` argument. We split on "/", ignore "{param}" segments, and check each static segment.
//
// Pluralization is heuristic. To keep false positives down we DO NOT try to pluralize every word; instead
// we flag a segment only when it is clearly singular (does not end in "s") AND is not in the ALLOWLIST of
// non-collection segments (namespaces, versions, actions, status/singleton sub-resources, uncountable
// nouns). Projects can edit ALLOWLIST below — this file is copier-managed but locally customizable.

// Segments that are legitimately not plural collections.
var ALLOWLIST = [
  // namespace / versioning
  "api", "v1", "v2", "v3",
  // uncountable / mass nouns
  "data", "series", "telemetry", "equipment", "info", "metadata", "media", "config", "configuration",
  // health / status / lifecycle singletons
  "health", "healthcheck", "healthz", "readyz", "livez", "status", "shutdown", "ping", "version",
  // common actions, filters and singleton sub-resources
  "me", "self", "search", "online", "offline", "push", "polling", "dashboard", "summary", "latest", "current",
  // non-REST endpoints (not resource collections)
  "graphql"
];

function getSchema() {
  return { name: "resourcesPlural" };
}

function isAllowed(seg) {
  var lower = seg.toLowerCase();
  for (var i = 0; i < ALLOWLIST.length; i++) {
    if (ALLOWLIST[i] === lower) {
      return true;
    }
  }
  return false;
}

// Lenient: anything ending in "s" is treated as already plural. This intentionally under-flags words like
// "status"/"analysis" (safe: those are allowlisted or uncountable) so we never wrongly flag a plural.
function looksPlural(seg) {
  return seg.length > 1 && seg.charAt(seg.length - 1) === "s";
}

function runRule(input) {
  if (typeof input !== "string") {
    return [];
  }
  var results = [];
  var segments = input.split("/");
  for (var i = 0; i < segments.length; i++) {
    var seg = segments[i];
    if (seg === "") {
      continue; // leading slash / empty
    }
    if (seg.charAt(0) === "{") {
      continue; // path parameter, not a resource segment
    }
    if (isAllowed(seg) || looksPlural(seg)) {
      continue;
    }
    results.push({
      message: "path segment '" + seg + "' should be a plural resource noun (or added to the allowlist if it is not a collection)"
    });
  }
  return results;
}
