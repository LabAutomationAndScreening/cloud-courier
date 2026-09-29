# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from pydantic import JsonValue

# This is unit tested in the https://github.com/LabAutomationAndScreening/copier-base-template repo. It is excluded from coverage checks in other repos, so be cautious about making changes downstream as opposed to the copier base template...really it's for parsing OpenAPI schema...so I can't think of a reason you'd need custom changes that are repo-specific that shouldn't be backported to the template


def _merge_typed_members(typed_dicts: list[dict[str, JsonValue]]) -> dict[str, JsonValue] | None:
    merged: dict[str, JsonValue] = {}
    for typed_member in typed_dicts:
        for key, value in typed_member.items():
            if key == "type":
                continue
            if key not in merged:
                merged[key] = value
                continue
            if merged[key] != value:
                return None  # branches disagree on this key; a single merged schema would silently drop one value
    return merged


def _collapse_anyof(schema: dict[str, JsonValue]) -> None:
    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return
    null_marker = {"type": "null"}
    if null_marker not in any_of:
        return  # not a nullable wrapper — leave the union as-is
    cross_type_constraints = {"enum", "const"}
    typed_dicts: list[dict[str, JsonValue]] = []
    member_types: list[str] = []
    for member in any_of:
        if member == null_marker:
            continue
        assert isinstance(member, dict)
        member_type = member.get("type")
        if not isinstance(member_type, str):
            return  # a $ref/composed member can't be expressed in the type-array form
        if len(cross_type_constraints & member.keys()) > 0:
            return  # enum/const apply to every type, so merging them would wrongly reject null and the sibling types
        typed_dicts.append(member)
        member_types.append(member_type)
    merged = _merge_typed_members(typed_dicts)
    if merged is None:
        return  # branches carry conflicting per-key values; collapsing would be lossy, so leave the union as-is
    del schema["anyOf"]
    schema.update(merged)
    schema["type"] = [*member_types, "null"]


def collapse_nullable_anyof(node: JsonValue) -> None:
    """Simplify nullable unions in an OpenAPI document by rewriting ``anyOf: [T, {type: null}]`` into ``type: [T, "null"]``.

    Pydantic v2 emits ``Optional[X]`` as a composed ``anyOf`` (OpenAPI 3.1 dropped the ``nullable`` keyword). The two
    spellings are equivalent, but the composed form trips some codegen tools — Kiota, for example, only recognizes
    nullability in the type-array form and otherwise generates empty ``Member1`` wrapper types. The rewrite is only
    applied when it is lossless: members carrying ``enum``/``const`` (which apply across every type) or non-typed
    members (e.g. ``$ref``) are left as ``anyOf``. Operates in place on any OpenAPI document, including ones produced
    by servers we do not control.
    """
    if isinstance(node, dict):
        _collapse_anyof(node)
        for value in node.values():
            collapse_nullable_anyof(value)
    elif isinstance(node, list):
        for item in node:
            collapse_nullable_anyof(item)
