from app.domain.sources import (
    ApiKeyRequirement,
    MatchScope,
    SourceDescriptor,
    SourceKind,
    SourceSetting,
    SourceStatus,
    source_status,
)


def _descriptor(requirement: ApiKeyRequirement) -> SourceDescriptor:
    return SourceDescriptor(
        key="demo",
        name="Demo",
        homepage_url="https://example.org",
        description="Testquelle",
        kind=SourceKind.PACKAGE_QUERY,
        scope=MatchScope.PACKAGE,
        api_key_requirement=requirement,
    )


def test_disabled_source_is_disabled() -> None:
    setting = SourceSetting(source_key="demo", enabled=False, api_key="secret")
    assert source_status(_descriptor(ApiKeyRequirement.REQUIRED), setting) == SourceStatus.DISABLED


def test_required_key_missing_is_missing_key() -> None:
    setting = SourceSetting(source_key="demo")
    status = source_status(_descriptor(ApiKeyRequirement.REQUIRED), setting)
    assert status == SourceStatus.MISSING_KEY


def test_optional_key_missing_is_ready() -> None:
    setting = SourceSetting(source_key="demo")
    assert source_status(_descriptor(ApiKeyRequirement.OPTIONAL), setting) == SourceStatus.READY


def test_required_key_present_is_ready() -> None:
    setting = SourceSetting(source_key="demo", api_key="secret")
    assert source_status(_descriptor(ApiKeyRequirement.REQUIRED), setting) == SourceStatus.READY
