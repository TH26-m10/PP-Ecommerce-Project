from rest_framework.decorators import api_view
from rest_framework.response import Response

from store.services.load_balancer import get_next_server
from store.services.lrt_status import fetch_lrt_proxy_status


@api_view(['GET'])
def distribute_request(request):
    """In-memory simulation (unchanged). Real LRT runs via Docker on port 8080."""

    result = get_next_server()

    return Response({
        "message": "Request distributed successfully",
        "round_robin": result["round_robin_server"],
        "smart_choice": result["smart_server"],
        "servers_status": result["status"],
        "note": (
            "This endpoint is a simulation only. "
            "For real Least Response Time across 3 servers, use Docker: "
            "http://localhost:8080 and GET /lb/status"
        ),
    })


@api_view(['GET'])
def lrt_status(request):
    """Live stats from the Docker LRT proxy (no effect on other API routes)."""

    data = fetch_lrt_proxy_status()
    if data is None:
        return Response({
            "strategy": "least_response_time",
            "configured": False,
            "message": (
                "LRT proxy not configured. Start with: docker compose up --build"
            ),
            "docker_entry": "http://localhost:8080",
            "status_url": "http://localhost:8080/lb/status",
        })

    return Response({
        "configured": True,
        **data,
    })