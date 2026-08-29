"""Contract cluster 9: InterventionDefinition stub."""

from app.domain import InterventionDefinition


def test_intervention_definition_field_names() -> None:
    assert {
        "intervention_id",
        "name",
        "catalog_version",
    }.issubset(set(InterventionDefinition.model_fields))


def test_intervention_definition_stub_construction() -> None:
    definition = InterventionDefinition(
        intervention_id="cooling-center-hours",
        name="Extend cooling-center hours",
        catalog_version="catalog-v0",
    )
    assert definition.intervention_id == "cooling-center-hours"
    assert definition.catalog_version == "catalog-v0"
