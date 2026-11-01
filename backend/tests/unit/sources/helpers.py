"""Gemeinsame Test-Helfer für die Quellen-Adapter."""

from collections.abc import Callable

import httpx

from app.domain.inventory import Category, Component, Ecosystem

Handler = Callable[[httpx.Request], httpx.Response]


def mock_client(handler: Handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def status_client(status: int) -> httpx.Client:
    return mock_client(lambda _: httpx.Response(status))


def component(name: str, version: str, ecosystem: Ecosystem | None = Ecosystem.NPM) -> Component:
    return Component(
        name=name, version=version, category=Category.LIBRARY, ecosystem=ecosystem, direct=True
    )
