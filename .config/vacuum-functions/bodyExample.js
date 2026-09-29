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
// Replaces the built-in `oas3-missing-example` rule's requestBody/response checks. That rule only looks
// for an `example`/`examples` key on the media type object itself (or, at the schema-property level, on
// that property's own node) and does not drill into a `$ref`'d schema's own fields. Every field-level
// `Field(examples=[...])` on a payload/response model is therefore invisible to it, which forced routes
// to carry a hand-typed body example duplicating examples that already exist on the model.
//
// Vacuum resolves $ref before handing the node to a custom function, so `input.content[mediaType].schema`
// here is already the dereferenced schema. This function passes if there's an example directly on the
// body/media object, or anywhere within its (dereferenced) schema: on the schema itself, on any of its
// properties (recursively), on array items, or on an anyOf/oneOf branch (the shape of an `Optional[Model]`
// field). It only flags a body with no example reachable anywhere in that tree.

function getSchema() {
  return { name: "bodyExample" };
}

function hasOwnExample(node) {
  if (!node || typeof node !== "object") {
    return false;
  }
  if (Array.isArray(node.examples) && node.examples.length > 0) {
    return true;
  }
  return "example" in node && node.example !== undefined;
}

// Walks a resolved schema looking for an example anywhere within it: on itself, on a property
// (recursively, since a nested model's own field examples count), inside array items, or on an
// anyOf/oneOf branch (how an `Optional[Model]` field is represented). `seen` guards against infinite
// recursion on a self-referencing schema.
function schemaHasExample(schema, seen) {
  if (!schema || typeof schema !== "object") {
    return false;
  }
  if (seen.indexOf(schema) !== -1) {
    return false;
  }
  seen.push(schema);

  if (hasOwnExample(schema)) {
    return true;
  }

  var branches = schema.anyOf || schema.oneOf || schema.allOf;
  if (Array.isArray(branches)) {
    for (var i = 0; i < branches.length; i++) {
      if (schemaHasExample(branches[i], seen)) {
        return true;
      }
    }
  }

  if (schema.items && schemaHasExample(schema.items, seen)) {
    return true;
  }

  var properties = schema.properties;
  if (properties && typeof properties === "object") {
    for (var key in properties) {
      if (schemaHasExample(properties[key], seen)) {
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
  var content = input.content;
  if (!content || typeof content !== "object") {
    return [];
  }

  var results = [];
  for (var mediaType in content) {
    var mediaObject = content[mediaType];
    if (hasOwnExample(mediaObject)) {
      continue;
    }
    if (schemaHasExample(mediaObject && mediaObject.schema, [])) {
      continue;
    }
    results.push({ message: "body (" + mediaType + ") is missing an example, own or via its schema's fields" });
  }
  return results;
}
