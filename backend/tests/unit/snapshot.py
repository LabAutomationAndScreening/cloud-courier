# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import json
from typing import override

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.single_file import SingleFileSnapshotExtension
from syrupy.extensions.single_file import WriteMode
from syrupy.types import PropertyFilter
from syrupy.types import PropertyMatcher
from syrupy.types import SerializableData
from syrupy.types import SerializedData


class SingleTextFileSnapshot(SingleFileSnapshotExtension):
    _write_mode = (
        WriteMode.TEXT
    )  # for some reason the default is binary, but it should be text to make diffs easier to read


class SingleFileJsonSnapshot(SingleTextFileSnapshot):
    file_extension = "json"

    @override
    def serialize(
        self,
        data: SerializableData,  # pyrefly: ignore[explicit-any] # syrupy defines this alias as Any, and the signature must match the method being overridden; https://github.com/facebook/pyrefly/issues/4088 tracks exempting this (pyrefly 1.3.0 already exempts the `matcher` param below)
        *,
        exclude: PropertyFilter | None = None,
        include: PropertyFilter | None = None,
        matcher: PropertyMatcher | None = None,
    ) -> SerializedData:
        # TODO: consider a way to apply the exclude/include/matcher filters to the data before dumping to pretty-format JSON
        pretty_data = json.dumps(data, indent=2) + "\n"
        return super().serialize(
            pretty_data,
            exclude=exclude,
            include=include,
            matcher=matcher,
        )


@pytest.fixture
def snapshot_json(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    return snapshot.use_extension(SingleFileJsonSnapshot)
