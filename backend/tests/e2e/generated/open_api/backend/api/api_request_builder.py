# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from __future__ import annotations
from collections.abc import Callable
from kiota_abstractions.base_request_builder import BaseRequestBuilder
from kiota_abstractions.get_path_parameters import get_path_parameters
from kiota_abstractions.request_adapter import RequestAdapter
from typing import Any, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .healthcheck.healthcheck_request_builder import HealthcheckRequestBuilder
    from .shutdown.shutdown_request_builder import ShutdownRequestBuilder

class ApiRequestBuilder(BaseRequestBuilder):
    """
    Builds and executes requests for operations under /api
    """
    def __init__(self,request_adapter: RequestAdapter, path_parameters: Union[str, dict[str, Any]]) -> None:
        """
        Instantiates a new ApiRequestBuilder and sets the default values.
        param path_parameters: The raw url or the url-template parameters for the request.
        param request_adapter: The request adapter to use to execute the requests.
        Returns: None
        """
        super().__init__(request_adapter, "{+baseurl}/api", path_parameters)
    
    @property
    def healthcheck(self) -> HealthcheckRequestBuilder:
        """
        The healthcheck property
        """
        from .healthcheck.healthcheck_request_builder import HealthcheckRequestBuilder

        return HealthcheckRequestBuilder(self.request_adapter, self.path_parameters)
    
    @property
    def shutdown(self) -> ShutdownRequestBuilder:
        """
        The shutdown property
        """
        from .shutdown.shutdown_request_builder import ShutdownRequestBuilder

        return ShutdownRequestBuilder(self.request_adapter, self.path_parameters)
    

