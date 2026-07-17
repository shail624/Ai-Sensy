"""Template definition & variable validation (Doc 04 §15; FR-TPL-02/04).

Validated **before** submission "to cut rejection loops" (Doc 04 §15): a template Meta rejects
costs hours of round-trip, so every rule we can check ourselves, we check. The limits are Meta's,
but the rules are the platform's own — they read the canonical Doc 04 §15 definition, never a Graph
payload, exactly as :mod:`app.storage.validation` checks a file against Cloud API limits without
knowing anything about Graph.

Placeholders are the load-bearing part. Meta numbers variables ``{{1}}, {{2}}, …`` per component
and rejects gaps; a send then supplies exactly that many values, positionally. Counting them here
is what makes ``variable_count`` trustworthy and a bad send a ``422`` instead of a failed delivery.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.exceptions import ValidationError
from app.models.template import CATEGORIES

#: Meta's structural limits (Cloud API template rules).
MAX_BODY_CHARS = 1024
MAX_HEADER_CHARS = 60
MAX_FOOTER_CHARS = 60
MAX_BUTTONS = 10
MAX_HEADER_VARIABLES = 1

COMPONENT_HEADER = "header"
COMPONENT_BODY = "body"
COMPONENT_FOOTER = "footer"
COMPONENT_BUTTONS = "buttons"
COMPONENTS = (COMPONENT_HEADER, COMPONENT_BODY, COMPONENT_FOOTER, COMPONENT_BUTTONS)

#: A header is either text or one media kind (Doc 04 §15 "media-header rules").
FORMAT_TEXT = "text"
MEDIA_FORMATS = ("image", "video", "document")
HEADER_FORMATS = (FORMAT_TEXT, *MEDIA_FORMATS, "location")

#: Button types the platform can bind a value to at send time (FR-TPL-04).
BUTTON_URL = "url"
BUTTON_QUICK_REPLY = "quick_reply"
BUTTON_PHONE = "phone_number"
BUTTON_COPY_CODE = "copy_code"
BUTTON_TYPES = (BUTTON_URL, BUTTON_QUICK_REPLY, BUTTON_PHONE, BUTTON_COPY_CODE)
#: Buttons that take a value from the sender; the rest are fixed at approval time.
VARIABLE_BUTTONS = (BUTTON_URL, BUTTON_QUICK_REPLY, BUTTON_COPY_CODE)

_PLACEHOLDER = re.compile(r"\{\{\s*(\d+)\s*\}\}")


class TemplateInvalid(ValidationError):
    """The definition breaks a rule Meta would reject it for (Doc 04 §15 → 422)."""

    code = "template_invalid"
    title = "Template Invalid"


def placeholders(text: str | None) -> list[int]:
    """The variable indices a component's text declares, in order of appearance."""
    return [int(match) for match in _PLACEHOLDER.findall(text or "")]


def _require_sequential(indices: list[int], *, where: str) -> None:
    """Meta numbers variables from 1 with no gaps; anything else is a rejection."""
    if not indices:
        return
    unique = sorted(set(indices))
    if unique != list(range(1, len(unique) + 1)):
        raise TemplateInvalid(
            f"{where} variables must be numbered from {{{{1}}}} with no gaps; found {unique}.",
            errors=[{"field": where, "code": "placeholder_sequence", "message": "Non-sequential."}],
        )


def component_of(components: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    for component in components:
        if str(component.get("type", "")).lower() == kind:
            return component
    return None


def validate_definition(*, category: str, components: list[dict[str, Any]]) -> None:
    """Everything Doc 04 §15 says to check before Meta sees it."""
    if category not in CATEGORIES:
        raise TemplateInvalid(
            f"Category must be one of {', '.join(CATEGORIES)}.",
            errors=[{"field": "category", "code": "invalid", "message": "Unknown category."}],
        )
    if not components:
        raise TemplateInvalid(
            "A template needs at least a body component.",
            errors=[{"field": "components", "code": "required", "message": "Body is required."}],
        )

    seen: list[str] = []
    for component in components:
        kind = str(component.get("type", "")).lower()
        if kind not in COMPONENTS:
            raise TemplateInvalid(
                f"Unknown component type {kind!r}.",
                errors=[{"field": "components", "code": "invalid", "message": kind}],
            )
        if kind in seen:
            raise TemplateInvalid(
                f"A template may have only one {kind} component.",
                errors=[{"field": kind, "code": "duplicate", "message": "Repeated component."}],
            )
        seen.append(kind)

    if COMPONENT_BODY not in seen:
        raise TemplateInvalid(
            "A template needs a body component.",
            errors=[{"field": "body", "code": "required", "message": "Body is required."}],
        )

    _validate_body(component_of(components, COMPONENT_BODY))
    _validate_header(component_of(components, COMPONENT_HEADER))
    _validate_footer(component_of(components, COMPONENT_FOOTER))
    _validate_buttons(component_of(components, COMPONENT_BUTTONS))


def _validate_body(body: dict[str, Any] | None) -> None:
    text = (body or {}).get("text") or ""
    if not text.strip():
        raise TemplateInvalid(
            "The body component needs text.",
            errors=[{"field": "body.text", "code": "required", "message": "Text is required."}],
        )
    if len(text) > MAX_BODY_CHARS:
        raise TemplateInvalid(
            f"Body text may not exceed {MAX_BODY_CHARS} characters.",
            errors=[{"field": "body.text", "code": "too_long", "message": str(len(text))}],
        )
    _require_sequential(placeholders(text), where="body")


def _validate_header(header: dict[str, Any] | None) -> None:
    if header is None:
        return
    fmt = str(header.get("format") or FORMAT_TEXT).lower()
    if fmt not in HEADER_FORMATS:
        raise TemplateInvalid(
            f"Header format must be one of {', '.join(HEADER_FORMATS)}.",
            errors=[{"field": "header.format", "code": "invalid", "message": fmt}],
        )
    if fmt != FORMAT_TEXT:
        # A media header carries a file, never text: Meta rejects the combination outright.
        if header.get("text"):
            raise TemplateInvalid(
                "A media header cannot also carry text.",
                errors=[{"field": "header.text", "code": "conflict", "message": fmt}],
            )
        return

    text = header.get("text") or ""
    if not text.strip():
        raise TemplateInvalid(
            "A text header needs text.",
            errors=[{"field": "header.text", "code": "required", "message": "Text is required."}],
        )
    if len(text) > MAX_HEADER_CHARS:
        raise TemplateInvalid(
            f"Header text may not exceed {MAX_HEADER_CHARS} characters.",
            errors=[{"field": "header.text", "code": "too_long", "message": str(len(text))}],
        )
    found = placeholders(text)
    if len(set(found)) > MAX_HEADER_VARIABLES:
        raise TemplateInvalid(
            f"A header may contain at most {MAX_HEADER_VARIABLES} variable.",
            errors=[{"field": "header.text", "code": "too_many", "message": str(len(found))}],
        )
    _require_sequential(found, where="header")


def _validate_footer(footer: dict[str, Any] | None) -> None:
    if footer is None:
        return
    text = footer.get("text") or ""
    if len(text) > MAX_FOOTER_CHARS:
        raise TemplateInvalid(
            f"Footer text may not exceed {MAX_FOOTER_CHARS} characters.",
            errors=[{"field": "footer.text", "code": "too_long", "message": str(len(text))}],
        )
    if placeholders(text):
        raise TemplateInvalid(
            "A footer cannot contain variables.",
            errors=[{"field": "footer.text", "code": "invalid", "message": "No variables."}],
        )


def _validate_buttons(buttons: dict[str, Any] | None) -> None:
    if buttons is None:
        return
    items = buttons.get("buttons") or []
    if not items:
        raise TemplateInvalid(
            "A buttons component needs at least one button.",
            errors=[{"field": "buttons", "code": "required", "message": "At least one."}],
        )
    if len(items) > MAX_BUTTONS:
        raise TemplateInvalid(
            f"A template may have at most {MAX_BUTTONS} buttons.",
            errors=[{"field": "buttons", "code": "too_many", "message": str(len(items))}],
        )
    for index, button in enumerate(items):
        kind = str(button.get("type", "")).lower()
        if kind not in BUTTON_TYPES:
            raise TemplateInvalid(
                f"Unknown button type {kind!r}.",
                errors=[{"field": f"buttons.{index}.type", "code": "invalid", "message": kind}],
            )
        if not (button.get("text") or "").strip():
            raise TemplateInvalid(
                "Every button needs a label.",
                errors=[{"field": f"buttons.{index}.text", "code": "required", "message": "Label."}],
            )
        if kind == BUTTON_URL and not button.get("url"):
            raise TemplateInvalid(
                "A URL button needs a url.",
                errors=[{"field": f"buttons.{index}.url", "code": "required", "message": "URL."}],
            )
        if kind == BUTTON_PHONE and not button.get("phone_number"):
            raise TemplateInvalid(
                "A phone button needs a phone_number.",
                errors=[
                    {"field": f"buttons.{index}.phone_number", "code": "required", "message": "No."}
                ],
            )


def variable_count(components: list[dict[str, Any]]) -> int:
    """How many values a send must supply in total (Doc 03 ``variable_count``)."""
    return sum(expected_variables(components))


def has_media_header(components: list[dict[str, Any]]) -> bool:
    header = component_of(components, COMPONENT_HEADER)
    if header is None:
        return False
    return str(header.get("format") or FORMAT_TEXT).lower() in MEDIA_FORMATS


def expected_variables(components: list[dict[str, Any]]) -> tuple[int, int]:
    """``(header, body)`` variable counts — what a send is checked against."""
    header = component_of(components, COMPONENT_HEADER) or {}
    body = component_of(components, COMPONENT_BODY) or {}
    header_vars = 0 if str(header.get("format", FORMAT_TEXT)).lower() != FORMAT_TEXT else len(
        set(placeholders(header.get("text")))
    )
    return header_vars, len(set(placeholders(body.get("text"))))


def render(components: list[dict[str, Any]], *, header: list[str], body: list[str]) -> dict[str, str]:
    """Substitute values into the text components (FR-TPL-08 preview)."""
    return {
        "header": _substitute((component_of(components, COMPONENT_HEADER) or {}).get("text"), header),
        "body": _substitute((component_of(components, COMPONENT_BODY) or {}).get("text"), body),
        "footer": (component_of(components, COMPONENT_FOOTER) or {}).get("text") or "",
    }


def _substitute(text: str | None, values: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        position = int(match.group(1)) - 1
        # Out-of-range leaves the placeholder visible: a preview must not invent a value.
        return values[position] if 0 <= position < len(values) else match.group(0)

    return _PLACEHOLDER.sub(replace, text or "")
