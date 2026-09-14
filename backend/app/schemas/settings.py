"""Settings and feature-flag schemas (Doc 04 §22)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.settings import FeatureFlag, Setting


class SettingResponse(BaseModel):
    key: str
    value: Any | None
    scope: str
    value_type: str
    is_secret: bool
    updated_at: datetime

    @classmethod
    def from_setting(cls, setting: Setting) -> SettingResponse:
        # Secret values are never returned (Doc 04 §13.2 principle).
        return cls(
            key=setting.key_name,
            value=None if setting.is_secret else setting.value_json,
            scope=setting.scope,
            value_type=setting.value_type,
            is_secret=setting.is_secret,
            updated_at=setting.updated_at,
        )


class SettingsUpdateRequest(BaseModel):
    values: dict[str, Any] = Field(min_length=1)


Keyword = Annotated[str, Field(min_length=1, max_length=40)]
Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _default_working_days() -> list[WorkingDaySettings]:
    return [
        WorkingDaySettings(day=day, enabled=day not in {"saturday", "sunday"})
        for day in (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
    ]


class ConsentKeywordSettings(BaseModel):
    """Explicit inbound keywords that change a contact's consent state.

    Disabled by default: an organization must deliberately opt into interpreting message text as
    consent. Exact normalized matches only, so a sentence that merely contains ``STOP`` cannot
    accidentally opt somebody out.
    """

    enabled: bool = False
    opt_in_keywords: list[Keyword] = Field(default_factory=lambda: ["START", "YES"], max_length=20)
    opt_out_keywords: list[Keyword] = Field(
        default_factory=lambda: ["STOP", "UNSUBSCRIBE"], max_length=20
    )

    @field_validator("opt_in_keywords", "opt_out_keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for keyword in value:
            candidate = " ".join(keyword.strip().upper().split())
            if candidate and candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @model_validator(mode="after")
    def validate_keyword_sets(self) -> ConsentKeywordSettings:
        if self.enabled and (not self.opt_in_keywords or not self.opt_out_keywords):
            raise ValueError("enabled consent automation requires opt-in and opt-out keywords")
        overlap = set(self.opt_in_keywords) & set(self.opt_out_keywords)
        if overlap:
            raise ValueError(
                f"consent keywords cannot appear in both lists: {', '.join(sorted(overlap))}"
            )
        return self


class WorkingDaySettings(BaseModel):
    """One local-time interval; an end before its start crosses midnight."""

    day: Weekday
    enabled: bool = True
    start: str = Field(default="09:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(default="18:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def validate_interval(self) -> WorkingDaySettings:
        if self.enabled and self.start == self.end:
            raise ValueError("an enabled working day must have different start and end times")
        return self


class WorkingHoursSettings(BaseModel):
    """Weekly hours interpreted in the existing organization timezone."""

    enabled: bool = False
    days: list[WorkingDaySettings] = Field(
        default_factory=_default_working_days, min_length=7, max_length=7
    )

    @model_validator(mode="after")
    def validate_week(self) -> WorkingHoursSettings:
        actual = [day.day for day in self.days]
        if len(set(actual)) != 7:
            raise ValueError("working hours must contain each weekday exactly once")
        if self.enabled and not any(day.enabled for day in self.days):
            raise ValueError("enabled working hours require at least one enabled day")
        return self


class AutomaticReplySettings(BaseModel):
    """Optional text replies; every capability is deliberately disabled by default."""

    welcome_enabled: bool = False
    welcome_body: str = Field(default="", max_length=1000)
    off_hours_enabled: bool = False
    off_hours_body: str = Field(default="", max_length=1000)

    @field_validator("welcome_body", "off_hours_body")
    @classmethod
    def trim_body(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_enabled_messages(self) -> AutomaticReplySettings:
        if self.welcome_enabled and not self.welcome_body:
            raise ValueError("an enabled welcome reply requires message text")
        if self.off_hours_enabled and not self.off_hours_body:
            raise ValueError("an enabled off-hours reply requires message text")
        return self


class AutoResolveSettings(BaseModel):
    """Optional inactivity policy; disabled until an organization deliberately enables it."""

    enabled: bool = False
    inactive_after_hours: int = Field(default=72, ge=1, le=720)


class InboxOperationsSettings(BaseModel):
    """Validated organization policy consumed by the shared inbox and inbound ledger."""

    assignment_mode: Literal["manual", "least_open"] = "manual"
    auto_mark_read: bool = True
    consent: ConsentKeywordSettings = Field(default_factory=ConsentKeywordSettings)
    working_hours: WorkingHoursSettings = Field(default_factory=WorkingHoursSettings)
    automatic_replies: AutomaticReplySettings = Field(default_factory=AutomaticReplySettings)
    auto_resolve: AutoResolveSettings = Field(default_factory=AutoResolveSettings)

    @model_validator(mode="after")
    def validate_reply_dependencies(self) -> InboxOperationsSettings:
        if self.automatic_replies.off_hours_enabled and not self.working_hours.enabled:
            raise ValueError("off-hours replies require working hours to be enabled")
        return self


class InboxOperationsResponse(InboxOperationsSettings):
    """The effective policy plus persistence metadata for the settings UI."""

    configured: bool
    updated_at: datetime | None
    organization_timezone: str


class FeatureFlagResponse(BaseModel):
    key: str
    description: str | None
    is_enabled: bool
    rollout: dict[str, Any] | None
    updated_at: datetime

    @classmethod
    def from_flag(cls, flag: FeatureFlag) -> FeatureFlagResponse:
        return cls(
            key=flag.key_name,
            description=flag.description,
            is_enabled=flag.is_enabled,
            rollout=flag.rollout_json,
            updated_at=flag.updated_at,
        )


class FeatureFlagPatchRequest(BaseModel):
    is_enabled: bool | None = None
    description: str | None = Field(default=None, max_length=255)
    rollout: dict[str, Any] | None = None
