"""Shared configuration validation."""

from __future__ import annotations

from collections.abc import Mapping


def _name(value: str, kind: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f'{kind} name must be a string')
    if not value.strip():
        raise ValueError(f'{kind} name must not be empty')


def _tokens(
    values: Mapping[str, str], defaults: Mapping[str, str], kind: str
) -> dict[str, str]:
    if not isinstance(values, Mapping):
        raise TypeError(f'{kind} tokens must be a mapping')
    result = dict(values)
    for key, value in result.items():
        if key not in defaults:
            raise ValueError(f'Unknown {kind} token: {key!r}')
        if not isinstance(value, str):
            raise TypeError(f'{kind} token {key!r} must be a string')
        if not value.strip():
            raise ValueError(f'{kind} token {key!r} must not be empty')
    return result
