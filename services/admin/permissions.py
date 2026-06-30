"""Admin role and permission helpers."""

from django.contrib.auth.models import Group

ROLE_ADMINISTRATOR = "Administrator"
ROLE_OPERATOR = "Operator"
ROLE_REVIEWER = "Reviewer"

ADMIN_ROLES = (ROLE_ADMINISTRATOR, ROLE_OPERATOR, ROLE_REVIEWER)


def ensure_admin_roles() -> None:
    """Create default admin role groups if they do not exist."""
    for role in ADMIN_ROLES:
        Group.objects.get_or_create(name=role)


def user_has_role(user, role: str) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=role).exists()


def is_administrator(user) -> bool:
    return user.is_superuser or user_has_role(user, ROLE_ADMINISTRATOR)


def is_operator(user) -> bool:
    return is_administrator(user) or user_has_role(user, ROLE_OPERATOR)


def is_reviewer(user) -> bool:
    return is_operator(user) or user_has_role(user, ROLE_REVIEWER)
