"""Meta's template shapes (Doc 04 §15/§18.2; FR-TPL-01/02/04).

Graph speaks "components" in two different dialects and the platform speaks neither:

- a **definition** (what the template looks like) — uppercase types, uppercase formats;
- a **send payload** (what fills it this time) — a parallel component list of typed parameters.

This module is the only place either exists. The platform stores the Doc 04 §15 definition shape
and hands the adapter :class:`~app.channels.models.TemplateContent` *values*; everything Graph
needs is derived here (Doc 07 §5.3).
"""

from __future__ import annotations

from typing import Any

from app.channels.errors import ChannelConfigError
from app.channels.models import ChannelTemplate, MediaContent, TemplateContent

#: Doc 03 §7.1 vocabularies ↔ Meta's. Identical but for case, mapped explicitly so a Meta rename
#: surfaces here rather than as an unknown state in the registry.
_STATUS = {
    "APPROVED": "approved",
    "PENDING": "pending",
    "IN_APPEAL": "pending",
    "PENDING_DELETION": "pending",
    "REJECTED": "rejected",
    "PAUSED": "paused",
    "DISABLED": "disabled",
}
_CATEGORY = {"MARKETING": "marketing", "UTILITY": "utility", "AUTHENTICATION": "authentication"}

#: A media header carries its file as this parameter type (Graph's name for each kind).
_MEDIA_PARAM = {"image": "image", "video": "video", "document": "document"}

#: Graph's parameter shape per button type (Doc 04 §18.2's `buttons[]`).
_BUTTON_PARAM = {
    "url": lambda value: {"type": "text", "text": value},
    "quick_reply": lambda value: {"type": "payload", "payload": value},
    "copy_code": lambda value: {"type": "coupon_code", "coupon_code": value},
}


def to_channel_template(node: dict[str, Any]) -> ChannelTemplate:
    """A Graph template node → canonical (FR-TPL-01/03)."""
    return ChannelTemplate(
        name=str(node.get("name") or ""),
        language=str(node.get("language") or ""),
        category=_CATEGORY.get(str(node.get("category") or "").upper(), "utility"),
        status=_STATUS.get(str(node.get("status") or "").upper(), "pending"),
        components=[_to_definition(c) for c in node.get("components") or []],
        channel_template_id=str(node["id"]) if node.get("id") else None,
        quality_score=(node.get("quality_score") or {}).get("score")
        if isinstance(node.get("quality_score"), dict)
        else node.get("quality_score"),
        # Meta names the field differently depending on the endpoint; both mean "why".
        rejection_reason=node.get("rejected_reason") or node.get("rejection_reason"),
    )


def _to_definition(component: dict[str, Any]) -> dict[str, Any]:
    """Graph definition component → the Doc 04 §15 shape the platform stores and renders."""
    kind = str(component.get("type") or "").lower()
    if kind == "buttons":
        return {"type": "buttons", "buttons": [_to_button(b) for b in component.get("buttons") or []]}

    out: dict[str, Any] = {"type": kind}
    if component.get("format"):
        out["format"] = str(component["format"]).lower()
    if component.get("text") is not None:
        out["text"] = component["text"]
    if component.get("example"):
        out["example"] = component["example"]
    return out


def _to_button(button: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"type": str(button.get("type") or "").lower()}
    for field in ("text", "url", "phone_number"):
        if button.get(field) is not None:
            out[field] = button[field]
    return out


def to_create_payload(
    *, name: str, language: str, category: str, components: list[dict[str, Any]]
) -> dict[str, Any]:
    """Canonical definition → Graph's create body (FR-TPL-02)."""
    return {
        "name": name,
        "language": language,
        "category": category.upper(),
        "components": [_to_graph_definition(c) for c in components],
    }


def _to_graph_definition(component: dict[str, Any]) -> dict[str, Any]:
    kind = str(component.get("type") or "").lower()
    if kind == "buttons":
        return {
            "type": "BUTTONS",
            "buttons": [
                {**{k: v for k, v in b.items() if k != "type"}, "type": str(b.get("type", "")).upper()}
                for b in component.get("buttons") or []
            ],
        }

    out: dict[str, Any] = {"type": kind.upper()}
    if component.get("format"):
        out["format"] = str(component["format"]).upper()
    if component.get("text") is not None:
        out["text"] = component["text"]
    if component.get("example"):
        out["example"] = component["example"]
    return out


def send_components(content: TemplateContent) -> list[dict[str, Any]]:
    """Canonical variables → Graph's send components (Doc 04 §18.2).

    Only the parts that actually carry a value are emitted: Graph rejects an empty parameter list,
    and a template with no variables must send no components at all.
    """
    components: list[dict[str, Any]] = []

    if content.header_media is not None:
        components.append(
            {"type": "header", "parameters": [_media_parameter(content.header_media)]}
        )
    elif content.header:
        components.append({"type": "header", "parameters": _text_parameters(content.header)})

    if content.body:
        components.append({"type": "body", "parameters": _text_parameters(content.body)})

    for button in content.buttons:
        shape = _BUTTON_PARAM.get(button.type)
        if shape is None:
            raise ChannelConfigError(f"unsupported template button type {button.type!r}")
        components.append(
            {
                "type": "button",
                "sub_type": button.type,
                # Graph wants the index as a string even though it is an integer everywhere else.
                "index": str(button.index),
                "parameters": [shape(button.value)],
            }
        )
    return components


def _text_parameters(values: list[str]) -> list[dict[str, Any]]:
    return [{"type": "text", "text": value} for value in values]


def _media_parameter(media: MediaContent) -> dict[str, Any]:
    kind = _MEDIA_PARAM.get(media.kind.value)
    if kind is None:
        raise ChannelConfigError(f"{media.kind.value!r} cannot be a template header")
    if bool(media.media_id) == bool(media.link):
        raise ChannelConfigError("a template header needs exactly one of media_id or link")
    return {"type": kind, kind: {"id": media.media_id} if media.media_id else {"link": media.link}}
