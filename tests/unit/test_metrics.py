import time

import boto3
import pytest

from cloud_courier import CLOUDWATCH_HEARTBEAT_NAMESPACE
from cloud_courier import CLOUDWATCH_INSTANCE_ID_DIMENSION_NAME
from cloud_courier import HEARTBEAT_METRIC_NAME

from .fixtures import MainLoopMixin
from .fixtures import mocked_generic_config

_fixtures = (mocked_generic_config,)


class TestHeartbeat(MainLoopMixin):
    def test_When_boot_up__Then_heartbeat_sent(
        self,
    ):
        cloudwatch_client = boto3.client("cloudwatch", region_name=self.config.aws_region)
        expected_dimensions = 2

        self._start_loop()

        for _ in range(50):
            metrics_response = cloudwatch_client.list_metrics(Namespace=CLOUDWATCH_HEARTBEAT_NAMESPACE)
            metrics = metrics_response.get("Metrics", [])
            if len(metrics) > 0:
                break
            time.sleep(0.1)
        else:
            pytest.fail("No metrics found")

        metric = metrics[0]
        assert "MetricName" in metric
        assert metric["MetricName"] == HEARTBEAT_METRIC_NAME
        assert "Dimensions" in metric
        assert len(metric["Dimensions"]) == expected_dimensions
        specific_dimension = metric["Dimensions"][1]
        assert "Name" in specific_dimension
        assert specific_dimension["Name"] == CLOUDWATCH_INSTANCE_ID_DIMENSION_NAME
        assert "Value" in specific_dimension
        assert specific_dimension["Value"] == self.config.role_name
        # doesn't seem to be a way to assert things about the timestamp or other components of the metric
