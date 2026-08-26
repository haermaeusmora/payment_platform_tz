from django.http import JsonResponse


def success_response(data, status=200):
    return JsonResponse(data, status=status)


def error_response(message, status=400, errors=None):
    response = {'error': message}
    if errors:
        response['errors'] = errors
    return JsonResponse(response, status=status)