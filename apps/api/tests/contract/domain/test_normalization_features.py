"""Contract cluster 5: ReferenceFrame, NormalizedFeature, ZoneFeatureVector."""

from app.domain import NormalizedFeature, ReferenceFrame, ZoneFeatureVector


def test_normalized_feature_field_names() -> None:
    assert set(NormalizedFeature.model_fields) == {
        "raw_value",
        "normalized_value",
        "unit",
        "reference_frame",
        "reference_definition",
        "evidence_refs",
        "quality_flags",
    }


def test_normalized_feature_allows_null_values() -> None:
    feature = NormalizedFeature(
        raw_value=None,
        normalized_value=None,
        unit=None,
        reference_frame=ReferenceFrame.HISTORICAL,
        reference_definition="zone historical percentile window",
        evidence_refs=[],
        quality_flags=["insufficient_evidence"],
    )
    assert feature.reference_frame == ReferenceFrame.HISTORICAL
    assert feature.raw_value is None


def test_zone_feature_vector_field_names() -> None:
    assert set(ZoneFeatureVector.model_fields) == {
        "zone_id",
        "hazard_peak",
        "hazard_anomaly",
        "hazard_duration",
        "exposure_population",
        "exposure_critical_facilities",
        "vulnerability_index",
        "cooling_access_score",
        "thermal_burden_score",
        "intervention_evidence_modifier",
        "recovery_score",
        "coverage_ratio",
        "quality_flags",
        "evidence_refs",
    }


def test_zone_feature_vector_optional_features_default_none() -> None:
    vector = ZoneFeatureVector(
        zone_id="tract-001",
        coverage_ratio=0.0,
        quality_flags=[],
        evidence_refs=[],
    )
    assert vector.hazard_peak is None
    assert vector.intervention_evidence_modifier is None
    assert vector.recovery_score is None
