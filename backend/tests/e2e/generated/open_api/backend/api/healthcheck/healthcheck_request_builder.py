# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from kiota_abstractions.base_request_builder import BaseRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration
from kiota_abstractions.default_query_parameters import QueryParameters
from kiota_abstractions.get_path_parameters import get_path_parameters
from kiota_abstractions.method import Method
from kiota_abstractions.request_adapter import RequestAdapter
from kiota_abstractions.request_information import RequestInformation
from kiota_abstractions.request_option import RequestOption
from kiota_abstractions.serialization import Parsable, ParsableFactory
from typing import Any, Optional, TYPE_CHECKING, Union
from warnings import warn

if TYPE_CHECKING:
    from ...models.healthcheck_response import HealthcheckResponse
    from ...models.h_t_t_p_validation_error import HTTPValidationError
    from ...models.problem_details import ProblemDetails

class HealthcheckRequestBuilder(BaseRequestBuilder):
    """
    Builds and executes requests for operations under /api/healthcheck
    """
    def __init__(self,request_adapter: RequestAdapter, path_parameters: Union[str, dict[str, Any]]) -> None:
        """
        Instantiates a new HealthcheckRequestBuilder and sets the default values.
        param path_parameters: The raw url or the url-template parameters for the request.
        param request_adapter: The request adapter to use to execute the requests.
        Returns: None
        """
        super().__init__(request_adapter, "{+baseurl}/api/healthcheck{?prepend_v*}", path_parameters)
    
    async def get(self,request_configuration: Optional[RequestConfiguration[HealthcheckRequestBuilderGetQueryParameters]] = None) -> Optional[HealthcheckResponse]:
        """
        Check API health
        param request_configuration: Configuration for the request such as headers, query parameters, and middleware options.
        Returns: Optional[HealthcheckResponse]
        """
        request_info = self.to_get_request_information(
            request_configuration
        )
        from ...models.h_t_t_p_validation_error import HTTPValidationError
        from ...models.problem_details import ProblemDetails

        error_mapping: dict[str, type[ParsableFactory]] = {
            "422": HTTPValidationError,
            "500": ProblemDetails,
            "XXX": ProblemDetails,
        }
        if not self.request_adapter:
            raise Exception("Http core is null") 
        from ...models.healthcheck_response import HealthcheckResponse

        return await self.request_adapter.send_async(request_info, HealthcheckResponse, error_mapping)
    
    def to_get_request_information(self,request_configuration: Optional[RequestConfiguration[HealthcheckRequestBuilderGetQueryParameters]] = None) -> RequestInformation:
        """
        Check API health
        param request_configuration: Configuration for the request such as headers, query parameters, and middleware options.
        Returns: RequestInformation
        """
        request_info = RequestInformation(Method.GET, self.url_template, self.path_parameters)
        request_info.configure(request_configuration)
        request_info.headers.try_add("Accept", "application/json")
        return request_info
    
    def with_url(self,raw_url: str) -> HealthcheckRequestBuilder:
        """
        Returns a request builder with the provided arbitrary URL. Using this method means any other path or query parameters are ignored.
        param raw_url: The raw URL to use for the request builder.
        Returns: HealthcheckRequestBuilder
        """
        if raw_url is None:
            raise TypeError("raw_url cannot be null.")
        return HealthcheckRequestBuilder(self.request_adapter, raw_url)
    
    @dataclass
    class HealthcheckRequestBuilderGetQueryParameters():
        """
        Check API health
        """
        # Include a 'v' before the version number
        prepend_v: Optional[bool] = None

    
    @dataclass
    class HealthcheckRequestBuilderGetRequestConfiguration(RequestConfiguration[HealthcheckRequestBuilderGetQueryParameters]):
        """
        Configuration for the request such as headers, query parameters, and middleware options.
        """
        warn("This class is deprecated. Please use the generic RequestConfiguration class generated by the generator.", DeprecationWarning)
    

