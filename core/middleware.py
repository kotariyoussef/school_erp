# core/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class AdminOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow admin login page and static files
        if request.path.startswith(reverse('admin:login')) or request.path.startswith('/static/'):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect('admin:login')

        if not request.user.is_staff:
            return redirect('admin:login')

        return self.get_response(request)
