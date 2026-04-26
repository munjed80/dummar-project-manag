"""Helpers for SQLAlchemy enum persistence."""

from __future__ import annotations

from enum import Enum


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """Return enum values so SQLAlchemy persists `.value` instead of `.name`."""
    return [str(member.value) for member in enum_cls]

