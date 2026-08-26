from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


def disable_csrf(view_func):
    return csrf_exempt(view_func)


def csrf_exempt_view(view_class):
    return method_decorator(csrf_exempt, name='dispatch')(view_class)