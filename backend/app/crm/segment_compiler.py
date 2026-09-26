"""Segment rule validation & compilation (Doc 03 §6.4, Doc 04 §7.1/§14.3).

Compiles normalized ``segment_rules`` rows into a parameterized SQLAlchemy condition over
``contacts``. Tag, attribute and Vi-domain rules use tenant-scoped membership subqueries, keeping
the outer contact page stable and free of duplicate rows. Pure and side-effect free.

Grouping semantics: rules sharing a ``group_index`` are ANDed; the resulting groups are then
combined by the segment's ``match_type`` (``all`` → AND, ``any`` → OR — Doc 03 §6.4
"top level").

Supported ``field_source``: ``contact``, ``engagement``, ``tag``, ``attribute`` (typed EAV),
``reactivation``, ``kyc``, ``document`` and ``activation``. Attribute rules are resolved through an
``AttributeSpec`` map supplied by the caller, keeping this module free of DB access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, NoReturn

from sqlalchemy import and_, func, or_, select

from app.core.exceptions import ValidationError
from app.crm.attribute_types import (
    TYPE_BOOLEAN,
    TYPE_DATETIME,
    TYPE_ENUM,
    TYPE_NUMBER,
    VALUE_COLUMN,
    AttributeValueError,
    coerce_value,
)
from app.models.attribute import ContactAttributeValue
from app.models.contact import Contact
from app.models.contact_document import DOCUMENT_STATUSES, DOCUMENT_TYPES, ContactDocument
from app.models.segment import (
    MATCH_ANY,
    SOURCE_ACTIVATION,
    SOURCE_ATTRIBUTE,
    SOURCE_CONTACT,
    SOURCE_DOCUMENT,
    SOURCE_ENGAGEMENT,
    SOURCE_KYC,
    SOURCE_REACTIVATION,
    SOURCE_SCAN,
    SOURCE_TAG,
)
from app.models.tag import Tag, contact_tags
from app.models.vi_domain import (
    ACTIVATION_STATUSES,
    ELIGIBILITY_STATUSES,
    KYC_STATUSES,
    REACTIVATION_STAGES,
    ActivationRecord,
    EligibilityCheck,
    KycCase,
    ReactivationCase,
)
from app.repositories.reachability import VERDICTS, verdict_condition


@dataclass(frozen=True, slots=True)
class AttributeSpec:
    """Resolved custom-attribute definition needed to compile an ``attribute`` rule."""

    attribute_id: int
    data_type: str
    enum_values: list[str] | None = None


@dataclass(frozen=True, slots=True)
class DomainFieldSpec:
    """One tenant-scoped domain field exposed to the segment rule grammar."""

    id_column: Any
    organization_column: Any
    contact_column: Any
    value_column: Any
    choices: tuple[str, ...]
    active_column: Any | None = None
    latest_per_contact: bool = False

_STR = "str"
_BOOL = "bool"
_DT = "datetime"

_CONTACT_FIELDS: dict[str, tuple[Any, str]] = {
    "full_name": (Contact.full_name, _STR),
    "first_name": (Contact.first_name, _STR),
    "last_name": (Contact.last_name, _STR),
    "email": (Contact.email, _STR),
    "phone_e164": (Contact.phone_e164, _STR),
    "wa_id": (Contact.wa_id, _STR),
    "country_code": (Contact.country_code, _STR),
    "locale": (Contact.locale, _STR),
    "opt_in_status": (Contact.opt_in_status, _STR),
    "source": (Contact.source, _STR),
    # Set from Live Chat (UI-AIS-06); filterable on the Contacts page (UI-AIS-13).
    "sale_status": (Contact.sale_status, _STR),
    "release_date": (Contact.release_date, _DT),
    "is_active_on_wa": (Contact.is_active_on_wa, _BOOL),
    "created_at": (Contact.created_at, _DT),
}
_ENGAGEMENT_FIELDS: dict[str, tuple[Any, str]] = {
    "last_inbound_at": (Contact.last_inbound_at, _DT),
    "last_outbound_at": (Contact.last_outbound_at, _DT),
    "last_contacted_at": (Contact.last_contacted_at, _DT),
}

_OPS_BY_TYPE: dict[str, set[str]] = {
    _STR: {"eq", "ne", "contains", "starts", "ends", "in", "nin", "exists"},
    _BOOL: {"eq", "exists"},
    _DT: {"eq", "ne", "gt", "gte", "lt", "lte", "between", "exists"},
}
_TAG_OPS = {"has_tag", "in", "nin"}
_DOMAIN_OPS = {"eq", "ne", "in", "nin", "exists"}

_DOMAIN_FIELDS: dict[str, dict[str, DomainFieldSpec]] = {
    SOURCE_REACTIVATION: {
        "stage": DomainFieldSpec(
            ReactivationCase.id,
            ReactivationCase.organization_id,
            ReactivationCase.contact_id,
            ReactivationCase.stage,
            REACTIVATION_STAGES,
            active_column=ReactivationCase.deleted_at,
        ),
        # Eligibility decisions are append-only. The highest internal id is the latest committed
        # decision for one contact and avoids treating a superseded decision as current truth.
        "eligibility_status": DomainFieldSpec(
            EligibilityCheck.id,
            EligibilityCheck.organization_id,
            EligibilityCheck.contact_id,
            EligibilityCheck.status,
            ELIGIBILITY_STATUSES,
            latest_per_contact=True,
        ),
    },
    SOURCE_KYC: {
        "status": DomainFieldSpec(
            KycCase.id,
            KycCase.organization_id,
            KycCase.contact_id,
            KycCase.status,
            KYC_STATUSES,
        ),
    },
    SOURCE_DOCUMENT: {
        "status": DomainFieldSpec(
            ContactDocument.id,
            ContactDocument.organization_id,
            ContactDocument.contact_id,
            ContactDocument.status,
            DOCUMENT_STATUSES,
            active_column=ContactDocument.deleted_at,
        ),
        "document_type": DomainFieldSpec(
            ContactDocument.id,
            ContactDocument.organization_id,
            ContactDocument.contact_id,
            ContactDocument.document_type,
            DOCUMENT_TYPES,
            active_column=ContactDocument.deleted_at,
        ),
    },
    SOURCE_ACTIVATION: {
        "status": DomainFieldSpec(
            ActivationRecord.id,
            ActivationRecord.organization_id,
            ActivationRecord.contact_id,
            ActivationRecord.status,
            ACTIVATION_STATUSES,
        ),
    },
}

#: custom-attribute data_type → the operator set it supports.
_ATTR_OPS_BY_TYPE: dict[str, set[str]] = {
    "string": _OPS_BY_TYPE[_STR],
    TYPE_ENUM: {"eq", "ne", "in", "nin", "exists"},
    TYPE_NUMBER: {"eq", "ne", "gt", "gte", "lt", "lte", "between", "in", "nin", "exists"},
    TYPE_DATETIME: _OPS_BY_TYPE[_DT],
    TYPE_BOOLEAN: _OPS_BY_TYPE[_BOOL],
}


def _fail(message: str, field: str = "rules") -> NoReturn:
    # `NoReturn`, not `None`: this helper always raises. Declaring it accurately lets a type
    # checker treat `if spec is None: _fail(...)` as narrowing, the way the code already reads.
    # With `-> None` every subsequent `spec.data_type` looks like an attribute access on None.
    raise ValidationError(
        "One or more segment rules are invalid.",
        errors=[{"field": field, "code": "invalid_rule", "message": message}],
    )


def _column_for(field_source: str, field_key: str) -> tuple[Any, str]:
    table = _CONTACT_FIELDS if field_source == SOURCE_CONTACT else _ENGAGEMENT_FIELDS
    if field_key not in table:
        _fail(f"unknown {field_source} field {field_key!r}")
    return table[field_key]


def _coerce(value: Any, value_type: str) -> Any:
    if value_type == _DT and isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            _fail(f"{value!r} is not an ISO-8601 datetime")
    if value_type == _BOOL and not isinstance(value, bool):
        _fail(f"{value!r} is not a boolean")
    return value


def _validate_attribute_rule(
    field_key: str, operator: str, value: Any, spec: AttributeSpec | None
) -> None:
    if spec is None:
        _fail(f"unknown custom attribute {field_key!r}")
    allowed = _ATTR_OPS_BY_TYPE[spec.data_type]
    if operator not in allowed:
        _fail(f"attribute {field_key!r} ({spec.data_type}) supports {sorted(allowed)}")
    if operator == "exists":
        if not isinstance(value, bool):
            _fail("exists expects a boolean")
        return
    try:
        if operator == "between":
            if not isinstance(value, list) or len(value) != 2:
                _fail("between expects a list of exactly two values")
            for item in value:
                coerce_value(spec.data_type, item, spec.enum_values)
            return
        if operator in {"in", "nin"}:
            if not isinstance(value, list) or not value:
                _fail(f"{operator} expects a non-empty list")
            for item in value:
                coerce_value(spec.data_type, item, spec.enum_values)
            return
        coerce_value(spec.data_type, value, spec.enum_values)
    except AttributeValueError as exc:
        _fail(f"attribute {field_key!r}: {exc}")


def _domain_spec(field_source: str, field_key: str) -> DomainFieldSpec:
    source = _DOMAIN_FIELDS.get(field_source)
    if source is None:
        _fail(f"unknown field_source {field_source!r}")
    spec = source.get(field_key)
    if spec is None:
        _fail(f"unknown {field_source} field {field_key!r}")
    return spec


def _validate_domain_rule(field_source: str, field_key: str, operator: str, value: Any) -> None:
    spec = _domain_spec(field_source, field_key)
    if operator not in _DOMAIN_OPS:
        _fail(f"{field_source}.{field_key} supports {sorted(_DOMAIN_OPS)}, got {operator!r}")
    if operator == "exists":
        if not isinstance(value, bool):
            _fail("exists expects a boolean")
        return
    values = value if operator in {"in", "nin"} else [value]
    if not isinstance(values, list) or not values:
        _fail(f"{operator} expects a non-empty list")
    for item in values:
        if not isinstance(item, str) or item not in spec.choices:
            _fail(
                f"{field_source}.{field_key} expects one of {sorted(spec.choices)}, got {item!r}"
            )


def validate_rule(
    field_source: str,
    field_key: str,
    operator: str,
    value: Any,
    attributes: dict[str, AttributeSpec] | None = None,
) -> None:
    """Raise :class:`ValidationError` (422) if the rule is not supported."""
    if field_source == SOURCE_ATTRIBUTE:
        _validate_attribute_rule(field_key, operator, value, (attributes or {}).get(field_key))
        return
    if field_source == SOURCE_TAG:
        if operator not in _TAG_OPS:
            _fail(f"tag rules support {sorted(_TAG_OPS)}, got {operator!r}")
        if operator == "has_tag" and not isinstance(value, str):
            _fail("has_tag expects a tag name")
        if operator in {"in", "nin"} and not isinstance(value, list):
            _fail(f"{operator} expects a list of tag names")
        return
    if field_source in _DOMAIN_FIELDS:
        _validate_domain_rule(field_source, field_key, operator, value)
        return
    if field_source == SOURCE_SCAN:
        _validate_scan_rule(field_key, operator, value)
        return
    if field_source not in (SOURCE_CONTACT, SOURCE_ENGAGEMENT):
        _fail(f"unknown field_source {field_source!r}")

    _, value_type = _column_for(field_source, field_key)
    allowed = _OPS_BY_TYPE[value_type]
    if operator not in allowed:
        _fail(f"{field_key!r} supports {sorted(allowed)}, got {operator!r}")
    if operator == "between":
        if not isinstance(value, list) or len(value) != 2:
            _fail("between expects a list of exactly two values")
        for item in value:
            _coerce(item, value_type)
        return
    if operator in {"in", "nin"}:
        if not isinstance(value, list) or not value:
            _fail(f"{operator} expects a non-empty list")
        return
    if operator == "exists":
        if not isinstance(value, bool):
            _fail("exists expects a boolean")
        return
    _coerce(value, value_type)


def _tag_condition(organization_id: int, operator: str, value: Any) -> Any:
    names = [value] if operator == "has_tag" else list(value)
    member = Contact.id.in_(
        select(contact_tags.c.contact_id)
        .join(Tag, Tag.id == contact_tags.c.tag_id)
        .where(
            Tag.organization_id == organization_id,
            Tag.name.in_(names),
            Tag.deleted_at.is_(None),
        )
    )
    return ~member if operator == "nin" else member


def _attribute_condition(spec: AttributeSpec, operator: str, value: Any) -> Any:
    """Membership over the typed EAV table, hitting (attribute_id, value_*) indexes."""
    column = getattr(ContactAttributeValue, VALUE_COLUMN[spec.data_type])
    base = ContactAttributeValue.attribute_id == spec.attribute_id

    if operator == "exists":
        inner = and_(base, column.isnot(None))
        member = Contact.id.in_(select(ContactAttributeValue.contact_id).where(inner))
        return member if value else ~member

    def coerce(item: Any) -> Any:
        return coerce_value(spec.data_type, item, spec.enum_values)

    if operator == "between":
        low, high = (coerce(v) for v in value)
        predicate = column.between(low, high)
    elif operator in {"in", "nin"}:
        coerced = [coerce(v) for v in value]
        predicate = column.in_(coerced)
    else:
        target = coerce(value)
        predicate = {
            "eq": lambda: column == target,
            # Positive match; membership is negated below so "ne"/"nin" also match contacts
            # that have no value for the attribute at all.
            "ne": lambda: column == target,
            "contains": lambda: column.ilike(f"%{target}%"),
            "starts": lambda: column.ilike(f"{target}%"),
            "ends": lambda: column.ilike(f"%{target}"),
            "gt": lambda: column > target,
            "gte": lambda: column >= target,
            "lt": lambda: column < target,
            "lte": lambda: column <= target,
        }[operator]()

    member = Contact.id.in_(
        select(ContactAttributeValue.contact_id).where(and_(base, predicate))
    )
    # 'ne'/'nin' must also match contacts that have no value for the attribute at all.
    return ~member if operator in {"ne", "nin"} else member


def _domain_condition(
    organization_id: int, field_source: str, field_key: str, operator: str, value: Any
) -> Any:
    """Compile a current, tenant-scoped Vi-domain membership predicate."""
    spec = _domain_spec(field_source, field_key)
    base = [spec.organization_column == organization_id]
    if spec.active_column is not None:
        base.append(spec.active_column.is_(None))
    if spec.latest_per_contact:
        latest_ids = (
            select(func.max(spec.id_column))
            .where(spec.organization_column == organization_id)
            .group_by(spec.contact_column)
        )
        base.append(spec.id_column.in_(latest_ids))

    if operator == "exists":
        member = Contact.id.in_(select(spec.contact_column).where(*base))
        return member if value else ~member

    targets = value if operator in {"in", "nin"} else [value]
    member = Contact.id.in_(
        select(spec.contact_column).where(*base, spec.value_column.in_(targets))
    )
    # Negative domain rules deliberately include contacts with no corresponding current domain
    # row, matching the established custom-attribute ``ne``/``nin`` semantics.
    return ~member if operator in {"ne", "nin"} else member


#: The one scan field, and the only operators that mean anything for it. A verdict is one of three
#: states, so ``contains`` or ``gt`` would be nonsense and are refused rather than quietly ignored.
_SCAN_FIELD = "reachability"
_SCAN_OPS = {"eq", "ne", "in", "nin"}


def _validate_scan_rule(field_key: str, operator: str, value: Any) -> None:
    if field_key != _SCAN_FIELD:
        _fail(f"unknown scan field {field_key!r}; only {_SCAN_FIELD!r} exists")
    if operator not in _SCAN_OPS:
        _fail(f"{_SCAN_FIELD!r} supports {sorted(_SCAN_OPS)}, got {operator!r}")
    values = value if operator in {"in", "nin"} else [value]
    if operator in {"in", "nin"} and not isinstance(value, list):
        _fail(f"{operator} expects a list of verdicts")
    for item in values:
        if item not in VERDICTS:
            _fail(f"unknown verdict {item!r}; expected one of {sorted(VERDICTS)}")


def _scan_condition(organization_id: int, operator: str, value: Any) -> Any:
    """What WhatsApp has said about the number, as a segment predicate.

    Built from :func:`verdict_condition`, which is the Scan screen's own logic, so a segment of
    "not on WhatsApp" is exactly the set that screen shows. Two implementations would drift, and
    that drift would present as a campaign quietly excluding a different population from the one
    the operator read before building it.

    This is what scope §13's "Create segment" means under the delivery-evidence method: the
    reachability list stops being something to look at and becomes something to act on -- excluded
    from the next campaign, or targeted by it.
    """
    verdicts = value if operator in {"in", "nin"} else [value]
    matched = or_(*(verdict_condition(organization_id, verdict) for verdict in verdicts))
    return ~matched if operator in {"ne", "nin"} else matched


def _rule_condition(
    organization_id: int,
    field_source: str,
    field_key: str,
    operator: str,
    value: Any,
    attributes: dict[str, AttributeSpec] | None = None,
) -> Any:
    if field_source == SOURCE_TAG:
        return _tag_condition(organization_id, operator, value)
    if field_source == SOURCE_ATTRIBUTE:
        return _attribute_condition((attributes or {})[field_key], operator, value)
    if field_source in _DOMAIN_FIELDS:
        return _domain_condition(organization_id, field_source, field_key, operator, value)
    if field_source == SOURCE_SCAN:
        return _scan_condition(organization_id, operator, value)

    column, value_type = _column_for(field_source, field_key)
    if operator == "exists":
        return column.isnot(None) if value else column.is_(None)
    if operator == "between":
        low, high = (_coerce(v, value_type) for v in value)
        return column.between(low, high)
    if operator in {"in", "nin"}:
        coerced = [_coerce(v, value_type) for v in value]
        return column.notin_(coerced) if operator == "nin" else column.in_(coerced)

    coerced = _coerce(value, value_type)
    if operator == "eq":
        return column == coerced
    if operator == "ne":
        return column != coerced
    if operator == "contains":
        return column.ilike(f"%{coerced}%")
    if operator == "starts":
        return column.ilike(f"{coerced}%")
    if operator == "ends":
        return column.ilike(f"%{coerced}")
    if operator == "gt":
        return column > coerced
    if operator == "gte":
        return column >= coerced
    if operator == "lt":
        return column < coerced
    return column <= coerced  # 'lte' — the only remaining validated operator


def compile_rules(
    *,
    organization_id: int,
    match_type: str,
    rules: list[dict[str, Any]],
    attributes: dict[str, AttributeSpec] | None = None,
) -> Any | None:
    """Compile rule dicts into one SQLAlchemy condition (or None when there are no rules)."""
    if not rules:
        return None
    groups: dict[int, list[Any]] = {}
    for rule in rules:
        condition = _rule_condition(
            organization_id,
            rule["field_source"],
            rule["field_key"],
            rule["operator"],
            rule.get("value"),
            attributes,
        )
        groups.setdefault(int(rule.get("group_index", 0)), []).append(condition)

    group_conditions = [and_(*conditions) for _, conditions in sorted(groups.items())]
    if len(group_conditions) == 1:
        return group_conditions[0]
    return or_(*group_conditions) if match_type == MATCH_ANY else and_(*group_conditions)
