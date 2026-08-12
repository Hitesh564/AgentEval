"""Minimal YAML/JSON loader for the repository's fixture files.

This parser intentionally supports only the structured subset used by the
project's benchmark and calibration fixtures:
- top-level lists of mapping items
- top-level mappings with nested lists under keys like ``examples``
- inline scalars, booleans, numbers, and inline list literals

It keeps the project runnable even when PyYAML is not installed.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, List, Tuple


def _strip_comment(line: str) -> str:
    if "#" not in line:
        return line
    in_quote = False
    quote_char = ""
    for idx, char in enumerate(line):
        if char in {"'", '"'}:
            if not in_quote:
                in_quote = True
                quote_char = char
            elif quote_char == char:
                in_quote = False
        elif char == "#" and not in_quote:
            return line[:idx]
    return line


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value or value in {"~", "null", "Null", "NULL"}:
        return None
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if value[0] in {"'", '"', "[", "{", "("}:
        try:
            return ast.literal_eval(value)
        except Exception:
            return value.strip("'\"")
    try:
        if any(marker in value for marker in (".", "e", "E")):
            return float(value)
        return int(value)
    except Exception:
        return value.strip("'\"")


def _parse_map(lines: List[Tuple[int, str]], idx: int, indent: int) -> Tuple[dict, int]:
    result: dict = {}
    while idx < len(lines):
        line_indent, line = lines[idx]
        if line_indent < indent:
            break
        if line_indent > indent:
            # Nested content is consumed by the previous key.
            break
        if line.startswith("- "):
            break
        if ":" not in line:
            idx += 1
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        idx += 1
        if raw_value:
            result[key] = _parse_scalar(raw_value)
            continue

        if idx < len(lines) and lines[idx][0] > indent:
            next_indent, next_line = lines[idx]
            if next_line.startswith("- "):
                nested, idx = _parse_list(lines, idx, next_indent)
                result[key] = nested
            else:
                nested, idx = _parse_map(lines, idx, next_indent)
                result[key] = nested
        else:
            result[key] = None
    return result, idx


def _parse_list(lines: List[Tuple[int, str]], idx: int, indent: int) -> Tuple[list, int]:
    result: list = []
    while idx < len(lines):
        line_indent, line = lines[idx]
        if line_indent < indent:
            break
        if line_indent != indent or not line.startswith("- "):
            break

        content = line[2:].strip()
        idx += 1
        if not content:
            if idx < len(lines) and lines[idx][0] > indent:
                next_indent, next_line = lines[idx]
                if next_line.startswith("- "):
                    nested, idx = _parse_list(lines, idx, next_indent)
                    result.append(nested)
                else:
                    nested, idx = _parse_map(lines, idx, next_indent)
                    result.append(nested)
            else:
                result.append(None)
            continue

        if ":" in content:
            key, raw_value = content.split(":", 1)
            item = {key.strip(): _parse_scalar(raw_value.strip()) if raw_value.strip() else None}
            while idx < len(lines):
                next_indent, next_line = lines[idx]
                if next_indent <= indent:
                    break
                if next_line.startswith("- "):
                    break
                if ":" not in next_line:
                    idx += 1
                    continue
                sub_key, sub_value = next_line.split(":", 1)
                sub_key = sub_key.strip()
                sub_value = sub_value.strip()
                idx += 1
                if sub_value:
                    item[sub_key] = _parse_scalar(sub_value)
                    continue
                if idx < len(lines) and lines[idx][0] > next_indent:
                    nested_indent, nested_line = lines[idx]
                    if nested_line.startswith("- "):
                        nested, idx = _parse_list(lines, idx, nested_indent)
                        item[sub_key] = nested
                    else:
                        nested, idx = _parse_map(lines, idx, nested_indent)
                        item[sub_key] = nested
                else:
                    item[sub_key] = None
            result.append(item)
            continue

        result.append(_parse_scalar(content))
    return result, idx


def load_structured_data(path: str) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    stripped = text.lstrip()
    if path.lower().endswith(".json") or stripped.startswith(("{", "[")):
        return json.loads(text)

    lines: List[Tuple[int, str]] = []
    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).rstrip()
        if not line.strip():
            continue
        lines.append((_leading_spaces(line), line.strip()))

    if not lines:
        return []

    first_indent, first_line = lines[0]
    if first_line.startswith("- "):
        parsed, _ = _parse_list(lines, 0, first_indent)
        return parsed
    parsed, _ = _parse_map(lines, 0, first_indent)
    return parsed
