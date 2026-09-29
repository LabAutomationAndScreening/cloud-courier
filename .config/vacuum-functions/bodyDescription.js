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
// Replaces the built-in `operation-description` rule's requestBody/response checks. That rule only looks
// at requestBody.description / response.description directly and does not resolve $ref, so it can't see
// a description that comes from the referenced schema's docstring. That forced every route to carry a
// hand-typed description duplicating the payload/response model's own docstring.
//
// Vacuum resolves $ref before handing the node to a custom function, so `input.content[mediaType].schema`
// here is already the dereferenced schema — its `description` (from the pydantic model's docstring) is
// visible. This function passes if there's a description directly on the body object OR on any of its
// content schemas, and only flags a body with no description anywhere.
//
// An Optional payload (`payload: Model | None = None`) produces an `anyOf: [<model schema>, {type: null}]`
// wrapper instead of the model schema directly, so the description lives one level deeper — branches of
// anyOf/oneOf are checked too.

function getSchema() {
  return { name: "bodyDescription" };
}

function hasOwnDescription(node) {
  return !!node && typeof node.description === "string" && node.description.length > 0;
}

// An Optional[Model] field (e.g. `payload: Model | None = None`) resolves to
// {"anyOf": [{...model schema, with its docstring as description...}, {"type": "null"}]} — the
// description lives on a branch, not on the anyOf node itself, so branches must be checked too.
function schemaHasDescription(schema) {
  if (!schema || typeof schema !== "object") {
    return false;
  }
  if (hasOwnDescription(schema)) {
    return true;
  }
  var branches = schema.anyOf || schema.oneOf;
  if (Array.isArray(branches)) {
    for (var i = 0; i < branches.length; i++) {
      if (schemaHasDescription(branches[i])) {
        return true;
      }
    }
  }
  return false;
}

function runRule(input) {
  if (!input || typeof input !== "object") {
    return [];
  }
  if (hasOwnDescription(input)) {
    return [];
  }
  var content = input.content;
  if (content && typeof content === "object") {
    for (var mediaType in content) {
      var schema = content[mediaType] && content[mediaType].schema;
      if (schemaHasDescription(schema)) {
        return [];
      }
    }
  }
  return [{ message: "body is missing a description (own, or via its schema's docstring)" }];
}
