from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def professor_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.papel == "PROFESSOR"):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def aluno_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.papel != "ALUNO":
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
