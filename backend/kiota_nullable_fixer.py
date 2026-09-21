# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
"""Fix Kiota's incorrect nullable handling for anyOf string or null fields.

Kiota generates complex "composed types" for simple anyOf: [simple_type, null] schemas. This script simplifies them back to Optional[str],
Optional[bool], Optional[int], Optional[float], or Optional[datetime].

Open github issue:
https://github.com/microsoft/kiota/issues/6869
(which just generally makes it challenging to use the composed types)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx
import humps


def load_openapi_schema(source: str) -> dict[str, Any]:
    """Load OpenAPI schema from URL or file path."""
    # Check if it looks like a URL
    if source.startswith(("http://", "https://")):
        try:
            response = httpx.get(source, timeout=5.0)
            _ = response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching OpenAPI schema from {source}: {e}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
            sys.exit(1)
    else:
        # pylint: disable=duplicate-code # this is shared with the fixer script for typescript code
        # Treat as file path
        file_path = Path(source)
        if not file_path.exists():
            print(f"Error: OpenAPI schema file not found: {file_path}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
            sys.exit(1)
        try:
            with file_path.open() as f:
                return json.load(f)

        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading OpenAPI schema from {file_path}: {e}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
            sys.exit(1)
        # pylint: enable=duplicate-code


def get_anyof_simple_nullable_fields(schema: dict[str, Any]) -> dict[str, dict[str, str]]:  # noqa: C901, PLR0912 # TODO: decide what to do about these fixer scripts long term
    """Parse OpenAPI schema to find fields defined as anyOf: [simple_type, null].

    Returns: dict mapping model_name -> {field_name: type_name}
    """
    result: dict[str, dict[str, str]] = {}
    schemas = schema.get("components", {}).get("schemas", {})

    for model_name, model_schema in schemas.items():
        properties = model_schema.get("properties", {})
        simple_nullable_fields: dict[str, str] = {}

        for field_name, field_schema in properties.items():
            # Check if it's an anyOf with exactly 2 items
            if "anyOf" in field_schema:
                any_of: list[dict[str, Any]] = field_schema["anyOf"]
                if len(any_of) == 2:  # noqa: PLR2004 # 2 is the exact expected length: [type, null]
                    # Check for null type
                    null_item: dict[str, Any] | None = None
                    other_item: dict[str, Any] | None = None
                    for item in any_of:
                        if item.get("type") == "null":
                            null_item = item
                        else:
                            other_item = item

                    if null_item and other_item:
                        other_type = other_item.get("type")
                        other_format = other_item.get("format")

                        # Handle arrays
                        if other_type == "array":
                            items = other_item.get("items", {})
                            item_type = items.get("type")
                            if item_type == "string":
                                simple_nullable_fields[field_name] = "list[str]"
                            elif item_type == "integer":
                                simple_nullable_fields[field_name] = "list[int]"
                            elif item_type == "number":
                                simple_nullable_fields[field_name] = "list[float]"
                            elif item_type == "boolean":
                                simple_nullable_fields[field_name] = "list[bool]"
                        # Handle string with date-time format
                        elif other_type == "string" and other_format == "date-time":
                            simple_nullable_fields[field_name] = "datetime"
                        # Handle regular simple types
                        elif other_type == "string":
                            simple_nullable_fields[field_name] = "str"
                        elif other_type == "boolean":
                            simple_nullable_fields[field_name] = "bool"
                        elif other_type == "integer":
                            simple_nullable_fields[field_name] = "int"
                        elif other_type == "number":
                            simple_nullable_fields[field_name] = "float"

        if simple_nullable_fields:
            result[model_name] = simple_nullable_fields

    return result


def fix_composed_type_file(file_path: Path) -> bool:
    """Remove a composed type file that's no longer needed."""
    if file_path.exists():
        file_path.unlink()
        print(f"  Removed composed type file: {file_path.name}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
        return True
    return False


def fix_model_file(file_path: Path, model_name: str, fields: dict[str, str]) -> bool:  # noqa: C901, PLR0912, PLR0915 # TODO: decide what to do about these fixer scripts long term
    """Fix a model file to use Optional[type] instead of composed types."""
    content = file_path.read_text()
    original_content = content

    needs_datetime_import = False

    for field, field_type in fields.items():
        # Convert field name from camelCase (in schema) to snake_case (in Python code)
        field_snake = humps.decamelize(field)

        # Convert to the composed type class name
        # NOTE: Kiota uses the camelCase field name in the class name, but snake_case in the file name
        composed_type_class_name = f"{model_name}_{field}"  # Uses camelCase field name

        # Determine the appropriate getter/writer methods and type name
        getter_method: str
        writer_method: str
        python_type: str
        primitive_type: str | None = None

        if field_type == "str":
            getter_method = "get_str_value"
            writer_method = "write_str_value"
            python_type = "str"
        elif field_type == "bool":
            getter_method = "get_bool_value"
            writer_method = "write_bool_value"
            python_type = "bool"
        elif field_type == "int":
            getter_method = "get_int_value"
            writer_method = "write_int_value"
            python_type = "int"
        elif field_type == "float":
            getter_method = "get_float_value"
            writer_method = "write_float_value"
            python_type = "float"
        elif field_type == "datetime":
            getter_method = "get_datetime_value"
            writer_method = "write_datetime_value"
            python_type = "datetime.datetime"
            needs_datetime_import = True
        elif field_type.startswith("list["):
            # Extract the inner type (e.g., "list[int]" -> "int")
            inner_type = field_type[5:-1]  # Remove "list[" and "]"
            getter_method = "get_collection_of_primitive_values"
            writer_method = "write_collection_of_primitive_values"
            python_type = field_type
            primitive_type = inner_type
        else:
            continue

        # 1. Fix the import statement - remove the composed type import (with any amount of leading/indentation whitespace)
        # Match both top-level and indented imports (e.g., inside if TYPE_CHECKING:)
        import_pattern = rf"^[ \t]*from \.{re.escape(humps.decamelize(model_name))}_{re.escape(field_snake)} import {re.escape(composed_type_class_name)}\n"
        matches_before = len(re.findall(import_pattern, content, flags=re.MULTILINE))
        content = re.sub(import_pattern, "", content, flags=re.MULTILINE)
        if matches_before > 0:
            print(f"    Removed {matches_before} import(s) for {composed_type_class_name}")  # noqa: T201 # this just runs as a simple script, so using print instead of log

        # 2. Fix the attribute declaration
        # Change: field_name: Optional[ComposedType] = None
        # To: field_name: Optional[str|bool|int|float|datetime.datetime] = None
        attr_pattern = (
            rf"(\s+{re.escape(field_snake)}:\s+)Optional\[{re.escape(composed_type_class_name)}\](\s*=\s*None)"
        )
        content = re.sub(attr_pattern, rf"\1Optional[{python_type}]\2", content)

        # 3. Fix get_field_deserializers
        # Change: lambda n: setattr(self, "field", n.get_object_value(ComposedType))  # noqa: ERA001 # documents the transformation, not commented-out code
        # To: lambda n: setattr(self, "field", n.get_str_value()) or n.get_bool_value() etc.
        # Note: The key in the dict is camelCase (from JSON), but the attribute name is snake_case
        deserializer_pattern = rf'("{re.escape(field)}":\s+lambda\s+n\s*:\s*setattr\(self,\s*[\'"]{re.escape(field_snake)}[\'"]\s*,\s*)n\.get_object_value\({re.escape(composed_type_class_name)}\)\)'
        if primitive_type:
            # For collections, pass the type
            content = re.sub(deserializer_pattern, rf"\1n.{getter_method}({primitive_type}))", content)
        else:
            content = re.sub(deserializer_pattern, rf"\1n.{getter_method}())", content)

        # 4. Fix serialize method
        # Change: writer.write_object_value("field", self.field)  # noqa: ERA001 # documents the transformation, not commented-out code
        # To: writer.write_str_value("field", self.field) or write_bool_value etc.
        # Note: The key is camelCase but the attribute is snake_case
        serialize_pattern = rf'writer\.write_object_value\("{re.escape(field)}",\s+self\.{re.escape(field_snake)}\)'
        content = re.sub(serialize_pattern, f'writer.{writer_method}("{field}", self.{field_snake})', content)

    # 5. Add datetime import if needed
    if needs_datetime_import and "import datetime" not in content:
        # Add after "from __future__ import annotations" line
        content = re.sub(r"(from __future__ import annotations\n)", r"\1import datetime\n", content)

    # 6. Clean up empty TYPE_CHECKING blocks
    # Remove: if TYPE_CHECKING:\n\n (with optional whitespace)
    empty_type_checking_pattern = r"if TYPE_CHECKING:\s*\n\s*\n"
    content = re.sub(empty_type_checking_pattern, "", content)

    # 7. Also remove TYPE_CHECKING from imports if the block is now gone
    if "if TYPE_CHECKING:" not in content:
        # Remove TYPE_CHECKING from the typing import
        content = re.sub(r",\s*TYPE_CHECKING", "", content)
        content = re.sub(r"TYPE_CHECKING,\s*", "", content)

    if content != original_content:
        _ = file_path.write_text(content)
        print(f"  Fixed model file: {model_name}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
        return True
    return False


def get_models_with_primitive_array_fields(schema: dict[str, Any]) -> dict[str, dict[str, str]]:  # noqa: C901, PLR0912 # TODO: decide what to do about these fixer scripts long term
    """Find models whose fields Kiota silently drops due to primitive array types.

    Kiota drops ALL fields from a model when any field has a direct (non-anyOf) primitive array
    type. This function identifies those models and returns ALL their simple (non-$ref) fields so
    they can be injected back into the generated output.

    Returns: dict mapping model_name -> {field_name: python_type}
    """
    result: dict[str, dict[str, str]] = {}
    schemas = schema.get("components", {}).get("schemas", {})

    for model_name, model_schema in schemas.items():
        properties = model_schema.get("properties", {})
        has_primitive_array = False
        field_types: dict[str, str] = {}

        for field_name, field_schema in properties.items():
            if "anyOf" in field_schema or "$ref" in field_schema:
                continue

            field_type = field_schema.get("type")
            field_format = field_schema.get("format")

            if field_type == "array":
                items = field_schema.get("items", {})
                item_type = items.get("type")
                item_format = items.get("format")
                if item_type == "string" and item_format == "date-time":
                    field_types[field_name] = "list[datetime.datetime]"
                    has_primitive_array = True
                elif item_type == "string":
                    field_types[field_name] = "list[str]"
                    has_primitive_array = True
                elif item_type == "integer":
                    field_types[field_name] = "list[int]"
                    has_primitive_array = True
                elif item_type == "number":
                    field_types[field_name] = "list[float]"
                    has_primitive_array = True
                elif item_type == "boolean":
                    field_types[field_name] = "list[bool]"
                    has_primitive_array = True
            elif field_type == "string" and field_format == "date-time":
                field_types[field_name] = "datetime"
            elif field_type == "string":
                field_types[field_name] = "str"
            elif field_type == "integer":
                field_types[field_name] = "int"
            elif field_type == "number":
                field_types[field_name] = "float"
            elif field_type == "boolean":
                field_types[field_name] = "bool"

        if has_primitive_array and field_types:
            result[model_name] = field_types

    return result


def inject_missing_python_fields(file_path: Path, model_name: str, fields: dict[str, str]) -> bool:  # noqa: C901, PLR0915 # TODO: decide what to do about these fixer scripts long term
    """Inject fields that Kiota dropped from a Python model due to the primitive array bug.

    Kiota issue: https://github.com/microsoft/kiota/issues/4054
    """
    content = file_path.read_text()
    original_content = content
    needs_datetime_import = False

    field_declarations: list[str] = []
    deser_entries: list[str] = []
    serializer_calls: list[str] = []

    for field_name, field_type in fields.items():
        field_snake = humps.decamelize(field_name)

        if f'"{field_name}"' in content:
            continue

        if field_type == "str":
            getter = "get_str_value()"
            writer_call = f'writer.write_str_value("{field_name}", self.{field_snake})'
            python_type = "str"
        elif field_type == "bool":
            getter = "get_bool_value()"
            writer_call = f'writer.write_bool_value("{field_name}", self.{field_snake})'
            python_type = "bool"
        elif field_type == "int":
            getter = "get_int_value()"
            writer_call = f'writer.write_int_value("{field_name}", self.{field_snake})'
            python_type = "int"
        elif field_type == "float":
            getter = "get_float_value()"
            writer_call = f'writer.write_float_value("{field_name}", self.{field_snake})'
            python_type = "float"
        elif field_type == "datetime":
            getter = "get_datetime_value()"
            writer_call = f'writer.write_datetime_value("{field_name}", self.{field_snake})'
            python_type = "datetime.datetime"
            needs_datetime_import = True
        elif field_type.startswith("list["):
            inner = field_type[5:-1]
            getter = f"get_collection_of_primitive_values({inner})"
            writer_call = f'writer.write_collection_of_primitive_values("{field_name}", self.{field_snake})'
            python_type = field_type
        else:
            continue

        field_declarations.append(f"    {field_snake}: Optional[{python_type}] = None")
        deser_entries.append(f"            \"{field_name}\": lambda n : setattr(self, '{field_snake}', n.{getter}),")
        serializer_calls.append(f"        {writer_call}")

    if not field_declarations:
        return False

    decl_block = "\n".join(field_declarations) + "\n"
    content = content.replace(
        "    @staticmethod\n    def create_from_discriminator_value",
        f"{decl_block}    @staticmethod\n    def create_from_discriminator_value",
        1,
    )

    deser_block = "\n".join(deser_entries) + "\n        "
    content = content.replace(
        "        fields: dict[str, Callable[[Any], None]] = {\n        }",
        f"        fields: dict[str, Callable[[Any], None]] = {{\n{deser_block}}}",
        1,
    )

    serializer_block = "\n".join(serializer_calls) + "\n"
    content = content.replace(
        '            raise TypeError("writer cannot be null.")\n    \n',
        f'            raise TypeError("writer cannot be null.")\n{serializer_block}    \n',
        1,
    )

    if needs_datetime_import and "import datetime" not in content:
        content = re.sub(r"(from __future__ import annotations\n)", r"\1import datetime\n", content)

    if content != original_content:
        _ = file_path.write_text(content)
        print(f"  Injected missing fields into {model_name}: {', '.join(fields.keys())}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
        return True
    return False


def main() -> None:  # noqa: C901, PLR0912 # TODO: decide what to do about these fixer scripts long term
    parser = argparse.ArgumentParser(description="Fix Kiota's incorrect nullable handling in generated Python models")
    _ = parser.add_argument(
        "openapi_source",
        help="OpenAPI schema source (URL starting with http:// or https://, or file path)",
    )
    _ = parser.add_argument(
        "kiota_dir",
        help="Path to the directory containing generated Kiota",
    )

    args = parser.parse_args()

    # Validate models directory
    models_dir = Path(args.kiota_dir) / "models"
    # pylint: disable=duplicate-code # this is shared with the fixer script for typescript code
    if not models_dir.exists():
        print(f"Error: Models directory not found: {models_dir.absolute()}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
        sys.exit(1)
    if not models_dir.is_dir():
        print(f"Error: Models path is not a directory: {models_dir.absolute()}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
        sys.exit(1)

    # Load OpenAPI schema
    print(f"Loading OpenAPI schema from: {args.openapi_source}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
    schema = load_openapi_schema(args.openapi_source)
    # pylint: enable=duplicate-code

    fixed_models = 0
    removed_files = 0

    # Fix 1: anyOf [simple_type, null] fields
    simple_nullable_fields = get_anyof_simple_nullable_fields(schema)
    if not simple_nullable_fields:
        print("No anyOf [simple_type, null] fields found in OpenAPI schema")  # noqa: T201 # this just runs as a simple script, so using print instead of log
    else:
        print(f"Found {len(simple_nullable_fields)} models with anyOf [simple_type, null] fields")  # noqa: T201 # this just runs as a simple script, so using print instead of log
        for model_name, fields in simple_nullable_fields.items():
            field_list = [f"{k}:{v}" for k, v in fields.items()]
            print(f"\nProcessing {model_name}: {', '.join(field_list)}")  # noqa: T201 # this just runs as a simple script, so using print instead of log

            model_file = models_dir / f"{humps.decamelize(model_name)}.py"
            if model_file.exists():
                if fix_model_file(model_file, model_name, fields):
                    fixed_models += 1
            else:
                print(f"  Warning: Model file not found: {model_file}")  # noqa: T201 # this just runs as a simple script, so using print instead of log

            for field in fields:
                field_snake = humps.decamelize(field)
                composed_type_file = models_dir / f"{humps.decamelize(model_name)}_{field_snake}.py"
                if fix_composed_type_file(composed_type_file):
                    removed_files += 1

    # pylint: disable=duplicate-code # this is shared with the fixer script for typescript code
    # Fix 2: Inject fields Kiota dropped due to primitive array types
    models_with_array_fields = get_models_with_primitive_array_fields(schema)
    if not models_with_array_fields:
        print("\nNo models with primitive array fields found")  # noqa: T201 # this just runs as a simple script, so using print instead of log
    else:
        print(f"\nFound {len(models_with_array_fields)} models with primitive array fields to inject")  # noqa: T201 # this just runs as a simple script, so using print instead of log
        for model_name, fields in models_with_array_fields.items():
            field_list = [f"{k}:{v}" for k, v in fields.items()]
            print(f"\nInjecting into {model_name}: {', '.join(field_list)}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
            model_file = models_dir / f"{humps.decamelize(model_name)}.py"
            if model_file.exists():
                if inject_missing_python_fields(model_file, model_name, fields):
                    fixed_models += 1
            else:
                print(f"  Warning: Model file not found: {model_file}")  # noqa: T201 # this just runs as a simple script, so using print instead of log
    # pylint: enable=duplicate-code

    print(f"\n✓ Fixed {fixed_models} model files")  # noqa: T201 # this just runs as a simple script, so using print instead of log
    print(f"✓ Removed {removed_files} composed type files")  # noqa: T201 # this just runs as a simple script, so using print instead of log


if __name__ == "__main__":
    main()
