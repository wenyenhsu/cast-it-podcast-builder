"""Access control for the operations dashboard."""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

P = ParamSpec("P")
R = TypeVar("R")


def staff_required(
    view_func: Callable[P, HttpResponse],
) -> Callable[P, HttpResponse]:
    """Require an authenticated staff user; redirect to the ops login page."""

    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse:
        if request.user.is_authenticated and request.user.is_staff:
            return view_func(request, *args, **kwargs)
        return redirect_to_login(
            request.get_full_path(),
            login_url=reverse("login"),
        )

    return _wrapped
