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
from kiota_abstractions.api_error import APIError
from kiota_abstractions.serialization import Parsable, ParseNode, SerializationWriter
from typing import Any, Optional, Union

@dataclass
class ProblemDetails(APIError, Parsable):
    # The type property
    type: Optional[str] = "about:blank"
    # The detail property
    detail: Optional[str] = None
    # The errorType property
    error_type: Optional[str] = None
    # The instance property
    instance: Optional[str] = None
    # The status property
    status: Optional[int] = None
    # The title property
    title: Optional[str] = None
    
    @staticmethod
    def create_from_discriminator_value(parse_node: ParseNode) -> ProblemDetails:
        """
        Creates a new instance of the appropriate class based on discriminator value
        param parse_node: The parse node to use to read the discriminator value and create the object
        Returns: ProblemDetails
        """
        if parse_node is None:
            raise TypeError("parse_node cannot be null.")
        return ProblemDetails()
    
    def get_field_deserializers(self,) -> dict[str, Callable[[ParseNode], None]]:
        """
        The deserialization information for the current model
        Returns: dict[str, Callable[[ParseNode], None]]
        """


        fields: dict[str, Callable[[Any], None]] = {
            "detail": lambda n : setattr(self, 'detail', n.get_str_value()),
            "errorType": lambda n : setattr(self, 'error_type', n.get_str_value()),
            "instance": lambda n : setattr(self, 'instance', n.get_str_value()),
            "status": lambda n : setattr(self, 'status', n.get_int_value()),
            "title": lambda n : setattr(self, 'title', n.get_str_value()),
            "type": lambda n : setattr(self, 'type', n.get_str_value()),
        }
        return fields
    
    def serialize(self,writer: SerializationWriter) -> None:
        """
        Serializes information the current object
        param writer: Serialization writer to use to serialize this model
        Returns: None
        """
        if writer is None:
            raise TypeError("writer cannot be null.")
        writer.write_str_value("detail", self.detail)
        writer.write_str_value("errorType", self.error_type)
        writer.write_str_value("instance", self.instance)
        writer.write_int_value("status", self.status)
        writer.write_str_value("title", self.title)
        writer.write_str_value("type", self.type)
    
    @property
    def primary_message(self) -> Optional[str]:
        """
        The primary error message.
        """
        if self.detail is not None:
            return '' if self.detail is None else self.detail
        return ''

