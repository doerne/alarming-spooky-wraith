from app.domain.inventory import Ecosystem
from app.infrastructure.sources.purl import package_url
from tests.unit.sources.helpers import component


def test_npm_scoped_package() -> None:
    assert package_url(component("@angular/core", "17.0.0")) == "pkg:npm/%40angular/core@17.0.0"


def test_maven_group_and_artifact() -> None:
    maven = component("org.springframework:spring-core", "6.1.0", Ecosystem.MAVEN)
    assert package_url(maven) == "pkg:maven/org.springframework/spring-core@6.1.0"


def test_pypi_name_is_normalized() -> None:
    assert (
        package_url(component("Django_Rest", "1.0", Ecosystem.PYPI)) == "pkg:pypi/django-rest@1.0"
    )


def test_unsupported_ecosystem_has_no_purl() -> None:
    assert package_url(component("lens", "5.0", Ecosystem.OPAM)) is None
