"""Boundary checks for source authorization and national-map geometry."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.geolocation import GeoPoint, MapQuery
from app.schemas.offline_video import RecordingRights


def valid_rights():
    return dict(
        source_name="Licensed test traffic clip",
        rightsholder="Test material rightsholder",
        permission_basis="licensed",
        authorization_reference="Local fixture license record",
        scope="Offline detection and incident evidence review",
        allow_analysis=True,
        allow_evidence_extraction=True,
        allow_retention=True,
        operator_declaration=True,
    )


def test_rights_reject_expiration_and_denied_extraction():
    rights = valid_rights()
    rights["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        RecordingRights.model_validate(rights)
    rights["expires_at"] = datetime.now(UTC) + timedelta(days=1)
    rights["allow_evidence_extraction"] = False
    with pytest.raises(ValidationError):
        RecordingRights.model_validate(rights)
    rights["allow_evidence_extraction"] = True
    assert RecordingRights.model_validate(rights).allow_analysis


@pytest.mark.parametrize("latitude,longitude", [(float("nan"), 25), (float("inf"), 25), (25, 181), (0, 0)])
def test_invalid_geo_points_do_not_enter_source_context(latitude, longitude):
    with pytest.raises(ValidationError):
        GeoPoint(latitude=latitude, longitude=longitude)


def test_bbox_is_west_south_east_north():
    assert MapQuery(bbox=(24, 44, 26, 46)).bbox == (24, 44, 26, 46)
    with pytest.raises(ValidationError):
        MapQuery(bbox=(46, 26, 44, 24))
