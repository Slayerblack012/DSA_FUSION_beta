"""
DSA AutoGrader - Containers Package.

Dependency Injection Container.
"""

from app.containers.container import Container, get_container, reset_container

__all__ = [
    "Container",
    "get_container",
    "reset_container",
]
