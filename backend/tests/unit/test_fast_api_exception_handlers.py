# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import json
import random
from uuid import uuid4

import pytest
from backend_api import fast_api_exception_handlers
from backend_api.app_def import HealthcheckResponse
from backend_api.app_def import app
from backend_api.fast_api_exception_handlers import ProblemDetails
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import codes
from pytest_mock import MockerFixture

from .spy_helpers import logged_message


def _random_error_status_code() -> codes:
    return random.choice((codes.BAD_REQUEST, codes.FORBIDDEN, codes.CONFLICT, codes.SERVICE_UNAVAILABLE))


class TestExceptionHandlers:
    @pytest.fixture(autouse=True)
    def _setup(self, mocker: MockerFixture):
        self.mocker = mocker
        self.client = TestClient(
            app,
            raise_server_exceptions=False,  # this makes sure our exception handlers get exercised
        )
        self.spied_logger_error = mocker.spy(fast_api_exception_handlers.logger, "error")
        self.spied_uuid_generator = mocker.spy(fast_api_exception_handlers, "uuid7")
        self.spied_logger_warning = mocker.spy(fast_api_exception_handlers.logger, "warning")

    def test_Given_malformed_input_to_api_route__Then_uuid_in_log_and_response_and_response_contains_details_and_cors_headers(
        self,
    ):
        response = self.client.get("/api/healthcheck?prependV=not_a_bool")

        self.spied_uuid_generator.assert_called_once()
        expected_uuid = str(self.spied_uuid_generator.spy_return)
        assert response.status_code == codes.UNPROCESSABLE_ENTITY
        assert response.headers["Content-Type"] == "application/problem+json"
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Credentials" in response.headers

        problem = ProblemDetails.model_validate(response.json())
        assert problem.type == "about:blank"
        assert problem.title == "Validation Error"
        assert problem.status == codes.UNPROCESSABLE_ENTITY
        assert "prependV" in problem.detail
        assert "valid boolean" in problem.detail
        assert problem.instance == f"urn:uuid:{expected_uuid}"
        self.spied_logger_warning.assert_called_once()
        log_message = logged_message(self.spied_logger_warning)
        assert expected_uuid in log_message
        assert "GET" in log_message
        assert "/api/healthcheck" in log_message

    def test_Given_calling_route_that_triggers_http_error__Then_uuid_in_log_and_response_and_response_contains_details_and_cors_headers(
        self,
    ):
        expected_route = "/api/healthcheck"
        response = self.client.delete(expected_route)

        self.spied_uuid_generator.assert_called_once()
        expected_uuid = str(self.spied_uuid_generator.spy_return)
        assert response.status_code == codes.METHOD_NOT_ALLOWED
        assert response.headers["Content-Type"] == "application/problem+json"
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Credentials" in response.headers
        problem = ProblemDetails.model_validate(response.json())
        assert problem.type == "about:blank"
        assert problem.title == "HTTP Error"
        assert problem.status == codes.METHOD_NOT_ALLOWED
        assert problem.detail == "Method Not Allowed"
        assert problem.error_type == "HTTPException"
        assert problem.instance == f"urn:uuid:{expected_uuid}"
        self.spied_logger_warning.assert_called_once()
        log_message = logged_message(self.spied_logger_warning)
        assert expected_uuid in log_message
        assert "DELETE" in log_message
        assert expected_route in log_message

    def test_Given_route_raises_http_exception_with_a_non_string_detail__Then_detail_is_json_encoded(self):
        expected_status_code = _random_error_status_code()
        expected_detail = {"field": str(uuid4()), "codes": [random.randint(1, 100), random.randint(1, 100)]}
        _ = self.mocker.patch.object(
            HealthcheckResponse,
            "__init__",
            side_effect=HTTPException(status_code=expected_status_code, detail=expected_detail),
        )

        response = self.client.get("/api/healthcheck")

        problem = ProblemDetails.model_validate(response.json())

        assert response.status_code == expected_status_code
        assert json.loads(problem.detail) == expected_detail

    def test_Given_route_mocked_to_error_and_error_details_should_be_displayed__Then_uuid_in_log_and_response__and_details_in_response_and_log__and_cors_headers_in_response(
        self,
    ):
        expected_route = "/api/healthcheck"
        expected_error_message = str(uuid4())
        _ = self.mocker.patch.object(
            fast_api_exception_handlers,
            fast_api_exception_handlers.should_show_error_details.__name__,
            autospec=True,
            return_value=True,
        )
        expected_error = RuntimeError(expected_error_message)
        _ = self.mocker.patch.object(
            HealthcheckResponse,
            "__init__",
            side_effect=expected_error,
        )

        response = self.client.get(expected_route)

        self.spied_uuid_generator.assert_called_once()
        expected_uuid = str(self.spied_uuid_generator.spy_return)
        assert response.status_code == codes.INTERNAL_SERVER_ERROR
        assert response.headers["Content-Type"] == "application/problem+json"
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Credentials" in response.headers
        problem = ProblemDetails.model_validate(response.json())
        assert problem.type == "about:blank"
        assert problem.title == "Internal Server Error"
        assert problem.status == codes.INTERNAL_SERVER_ERROR
        assert expected_error_message in problem.detail
        assert problem.error_type == expected_error.__class__.__name__
        assert problem.instance == f"urn:uuid:{expected_uuid}"
        self.spied_logger_error.assert_called_once()
        log_call_kwargs = self.spied_logger_error.call_args[1]
        log_message = logged_message(self.spied_logger_error)
        log_stack_trace = str(log_call_kwargs["exc_info"])
        assert expected_uuid in log_message
        assert "GET" in log_message
        assert expected_route in log_message
        assert expected_error_message in log_stack_trace

    def test_Given_route_mocked_to_error_and_error_details_should_not_be_displayed__Then_uuid_in_log_and_response__and_no_details_in_response_but_details_in_log(
        self,
    ):
        expected_route = "/api/healthcheck"
        expected_error_message = str(uuid4())
        _ = self.mocker.patch.object(
            fast_api_exception_handlers,
            fast_api_exception_handlers.should_show_error_details.__name__,
            autospec=True,
            return_value=False,
        )
        expected_error = ValueError(expected_error_message)  # arbitrary error type
        _ = self.mocker.patch.object(
            HealthcheckResponse,
            "__init__",
            side_effect=expected_error,
        )

        response = self.client.get(expected_route)

        self.spied_uuid_generator.assert_called_once()
        expected_uuid = str(self.spied_uuid_generator.spy_return)
        assert response.status_code == codes.INTERNAL_SERVER_ERROR
        assert response.headers["Content-Type"] == "application/problem+json"
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Credentials" in response.headers
        problem = ProblemDetails.model_validate(response.json())
        assert problem.type == "about:blank"
        assert problem.title == "Internal Server Error"
        assert problem.status == codes.INTERNAL_SERVER_ERROR
        assert problem.detail == "An unexpected error occurred."
        assert problem.error_type == expected_error.__class__.__name__
        assert problem.instance == f"urn:uuid:{expected_uuid}"
        self.spied_logger_error.assert_called_once()
        log_call_kwargs = self.spied_logger_error.call_args[1]
        log_message = logged_message(self.spied_logger_error)
        log_stack_trace = str(log_call_kwargs["exc_info"])
        assert expected_uuid in log_message
        assert "GET" in log_message
        assert expected_route in log_message
        assert expected_error_message in log_stack_trace
