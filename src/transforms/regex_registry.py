"""Named deterministic regex definitions and column mapping."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from src.transforms.contracts import REGEX_FLAGS, RegexDefinition
from src.transforms.errors import ConfigurationError


class RegexRegistry:
    """Immutable collection of prevalidated named regex definitions."""

    def __init__(self, definitions: Iterable[RegexDefinition] = ()) -> None:
        records: dict[str, RegexDefinition] = {}
        compiled: dict[str, re.Pattern[str]] = {}
        for index, definition in enumerate(definitions):
            if not isinstance(definition, RegexDefinition):
                raise ConfigurationError(
                    "invalid_type",
                    "Regex registry entries must be RegexDefinition records.",
                    ("regex_definitions", index),
                )
            if definition.id in records:
                raise ConfigurationError(
                    "duplicate_registration",
                    f"Regex definition '{definition.id}' is already registered.",
                    ("regex_definitions", index, "id"),
                )
            flags = sum(REGEX_FLAGS[name] for name in definition.flags)
            records[definition.id] = definition
            compiled[definition.id] = re.compile(definition.pattern, flags)
        self._definitions = records
        self._compiled = compiled

    @classmethod
    def from_dicts(cls, payloads: Any) -> "RegexRegistry":
        if payloads is None:
            return cls()
        if not isinstance(payloads, list):
            raise ConfigurationError(
                "invalid_type",
                "regex_definitions must be an array.",
                ("regex_definitions",),
            )
        return cls(
            RegexDefinition.from_dict(payload, ("regex_definitions", index))
            for index, payload in enumerate(payloads)
        )

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    def resolve(
        self,
        pattern_id: str,
        path: tuple[str | int, ...] = ("pattern_id",),
    ) -> RegexDefinition:
        try:
            return self._definitions[pattern_id]
        except KeyError as exc:
            raise ConfigurationError(
                "unknown_pattern",
                f"Unknown regex definition '{pattern_id}'.",
                path,
            ) from exc

    def compiled(
        self,
        pattern_id: str,
        path: tuple[str | int, ...] = ("pattern_id",),
    ) -> re.Pattern[str]:
        self.resolve(pattern_id, path)
        return self._compiled[pattern_id]

    def validate_group(
        self,
        pattern_id: str,
        group: str,
        path: tuple[str | int, ...] = ("group",),
    ) -> None:
        pattern = self.compiled(pattern_id, path)
        if group not in pattern.groupindex:
            raise ConfigurationError(
                "unknown_regex_group",
                f"Regex definition '{pattern_id}' has no named group '{group}'.",
                path,
            )

    def map_series(
        self,
        series: pd.Series,
        *,
        pattern_id: str,
        group: str,
        on_no_match: str = "null",
        default: Any = None,
    ) -> pd.Series:
        pattern = self.compiled(pattern_id)
        self.validate_group(pattern_id, group)
        if on_no_match not in {"null", "keep", "default", "fail"}:
            raise ConfigurationError(
                "invalid_value",
                f"Unsupported on_no_match policy '{on_no_match}'.",
                ("on_no_match",),
            )

        mapped: list[Any] = []
        unmatched = False
        for value in series:
            if pd.isna(value):
                match = None
            else:
                match = pattern.search(str(value))
            if match is not None:
                mapped.append(match.group(group))
            elif on_no_match == "keep":
                mapped.append(value)
            elif on_no_match == "default":
                mapped.append(default)
            else:
                mapped.append(pd.NA)
                unmatched = True

        if on_no_match == "fail" and unmatched:
            raise ConfigurationError(
                "regex_no_match",
                "One or more values did not match the configured regex.",
                ("pattern_id",),
            )
        return pd.Series(mapped, index=series.index, dtype="object")

