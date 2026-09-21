# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from uuid import uuid4

from backend_api.openapi_problem_responses import PROBLEM_DETAILS_REF
from backend_api.openapi_problem_responses import PROBLEM_JSON_MEDIA_TYPE
from backend_api.openapi_problem_responses import ProblemExample
from backend_api.openapi_problem_responses import problem_response
from httpx import codes


def test_Given_status_and_description__Then_responses_entry_is_keyed_by_status_code() -> None:
    responses = problem_response(codes.NOT_FOUND, "Widget not found")

    assert set(responses) == {codes.NOT_FOUND}
    assert responses[codes.NOT_FOUND]["description"] == "Widget not found"


def test_Given_status_and_description__Then_content_uses_problem_json_and_problem_details_ref() -> None:
    content = problem_response(codes.NOT_FOUND, "Widget not found")[codes.NOT_FOUND]["content"]

    assert set(content) == {PROBLEM_JSON_MEDIA_TYPE}
    assert content[PROBLEM_JSON_MEDIA_TYPE]["schema"] == {"$ref": PROBLEM_DETAILS_REF}


def test_Given_status_and_description__Then_example_is_synthesized_from_them() -> None:
    example = problem_response(codes.NOT_FOUND, "Widget not found")[codes.NOT_FOUND]["content"][
        PROBLEM_JSON_MEDIA_TYPE
    ]["example"]

    assert example["title"] == "Not Found"
    assert example["status"] == codes.NOT_FOUND
    assert example["detail"] == "Widget not found"
    assert example["instance"] == "about:blank"


def test_Given_explicit_instance__Then_example_points_at_it() -> None:
    example = problem_response(codes.NOT_FOUND, "Widget not found", instance="/api/widgets/7")[codes.NOT_FOUND][
        "content"
    ][PROBLEM_JSON_MEDIA_TYPE]["example"]

    assert example["instance"] == "/api/widgets/7"


def test_Given_named_examples__Then_content_carries_an_entry_per_name() -> None:
    examples = {
        "missing_widget": ProblemExample(summary=str(uuid4()), detail=str(uuid4())),
        "missing_bin": ProblemExample(summary=str(uuid4()), detail=str(uuid4())),
    }

    responses = problem_response(codes.NOT_FOUND, "Widget not found", examples=examples)

    content = responses[codes.NOT_FOUND]["content"][PROBLEM_JSON_MEDIA_TYPE]

    assert set(content["examples"]) == set(examples)
    assert content["examples"]["missing_widget"]["summary"] == examples["missing_widget"].summary
    assert content["examples"]["missing_bin"]["summary"] == examples["missing_bin"].summary


def test_Given_named_examples_and_an_explicit_instance__Then_each_value_is_a_complete_problem_details_body() -> None:
    detail = str(uuid4())
    instance = f"/api/widgets/{uuid4()}"

    responses = problem_response(
        codes.CONFLICT,
        "Widget conflicts with another widget",
        instance=instance,
        examples={"conflicting_widget": ProblemExample(summary=str(uuid4()), detail=detail)},
    )

    value = responses[codes.CONFLICT]["content"][PROBLEM_JSON_MEDIA_TYPE]["examples"]["conflicting_widget"]["value"]

    assert value["title"] == "Conflict"
    assert value["status"] == codes.CONFLICT
    assert value["detail"] == detail
    assert value["instance"] == instance
