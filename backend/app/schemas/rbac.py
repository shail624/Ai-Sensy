"""Role & permission schemas (Doc 04 §12.2)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.role import Permission, Role


class PermissionResponse(BaseModel):
    code: str
    resource: str
    action: str
    description: str | None

    @classmethod
    def from_permission(cls, permission: Permission) -> PermissionResponse:
        return cls(
            code=permission.code,
            resource=permission.resource,
            action=permission.action,
            description=permission.description,
        )


class RoleResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]

    @classmethod
    def from_role(cls, role: Role) -> RoleResponse:
        return cls(
            id=role.public_id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=[permission.code for permission in role.permissions],
        )


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)


class RolePermissionsRequest(BaseModel):
    permissions: list[str]
