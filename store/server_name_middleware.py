import os

from django.utils.deprecation import MiddlewareMixin


class ServerNameMiddleware(MiddlewareMixin):
    """Expose container name in responses when SERVER_NAME is set (Docker only)."""

    def process_response(self, request, response):
        server_name = os.environ.get("SERVER_NAME")
        if server_name:
            response["X-Server-Name"] = server_name
        return response
