from rest_framework.decorators import api_view
from rest_framework.response import Response
from store.services.load_balancer import get_next_server


@api_view(['GET'])
def distribute_request(request):

    result = get_next_server()

    return Response({
        "message": "Request distributed successfully",
        "round_robin": result["round_robin_server"],
        "smart_choice": result["smart_server"],
        "servers_status": result["status"]
    })