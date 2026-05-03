"""Fine-grained policy evaluation for admin CRUD endpoints."""
from __future__ import annotations
from coreAdmin_api.authz.rules import FieldPolicy, RecordPolicy


def _user_role_names(user) -> set[str]:
    return {r.name for r in (getattr(user, "roles", None) or [])}


def _roles_allow(required_roles: list[str] | None, user) -> bool:
    """
    None  → unrestricted (any user passes)
    []    → deny (superadmin-only; non-superadmin always fails here)
    [...] → user must hold at least one listed role
    """
    if required_roles is None:
        return True
    if not required_roles:
        return False
    return bool(_user_role_names(user).intersection(required_roles))


class PolicyEngine:

    def _privileged(self, user, token_payload: dict) -> bool:
        """True iff user is superadmin and token is not an impersonation token."""
        return user.is_superadmin and not bool(token_payload.get("impersonated_by"))

    def evaluate_field(
        self, user, model_admin, field_name: str, token_payload: dict
    ) -> FieldPolicy:
        if self._privileged(user, token_payload):
            return FieldPolicy(can_view=True, can_edit=True)

        field_policies = getattr(model_admin, "field_policies", {})
        policy = field_policies.get(field_name)
        if policy is None:
            return FieldPolicy(can_view=True, can_edit=True)

        can_view = _roles_allow(policy.get("view_roles"), user)
        # No view right means no edit right either
        can_edit = can_view and _roles_allow(policy.get("edit_roles"), user)
        return FieldPolicy(can_view=can_view, can_edit=can_edit)

    def can_perform_action(
        self, user, model_admin, action_name: str, token_payload: dict
    ) -> bool:
        if self._privileged(user, token_payload):
            return True
        action_policies = getattr(model_admin, "action_policies", {})
        policy = action_policies.get(action_name)
        if policy is None:
            return True
        return _roles_allow(policy.get("roles"), user)

    def get_record_filter(self, user, model_admin, token_payload: dict):
        """Return a SQLAlchemy WHERE clause to scope list queries, or None."""
        if self._privileged(user, token_payload):
            return None
        record_filter = getattr(model_admin, "record_filter", None)
        if record_filter is None:
            return None
        return record_filter(user)

    def check_record_access(
        self, user, model_admin, record, token_payload: dict
    ) -> RecordPolicy:
        if self._privileged(user, token_payload):
            return RecordPolicy()
        record_access = getattr(model_admin, "record_access", None)
        if record_access is None:
            return RecordPolicy()
        allowed = bool(record_access(user, record))
        return RecordPolicy(can_read=allowed, can_update=allowed, can_delete=allowed)

    def effective_model_caps(self, user, model_admin, token_payload: dict) -> dict:
        """Return CRUD capability flags for a user on a model."""
        if self._privileged(user, token_payload):
            return dict(
                can_list=True, can_create=True, can_read=True,
                can_update=True, can_delete=True, can_break_glass=True,
            )
        if getattr(model_admin, "admin_only", True):
            return dict(
                can_list=False, can_create=False, can_read=False,
                can_update=False, can_delete=False, can_break_glass=False,
            )
        access_roles = getattr(model_admin, "access_roles", [])
        if not _roles_allow(access_roles if access_roles else None, user):
            return dict(
                can_list=False, can_create=False, can_read=False,
                can_update=False, can_delete=False, can_break_glass=False,
            )
        return dict(
            can_list=True,
            can_create=self.can_perform_action(user, model_admin, "create", token_payload),
            can_read=True,
            can_update=self.can_perform_action(user, model_admin, "update", token_payload),
            can_delete=self.can_perform_action(user, model_admin, "delete", token_payload),
            can_break_glass=False,
        )


policy_engine = PolicyEngine()
