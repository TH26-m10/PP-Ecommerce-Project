import random
import time
from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth.models import User

from store.auth_helpers import deny_if_not_owner
from store.celery_utils import safe_delay
from store.models import Bank
from store.tasks import simulate_payment_task


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bank_show(request, user_id):

    denied = deny_if_not_owner(request, user_id)
    if denied:
        return denied

    try:
        user = User.objects.get(id=user_id)
        bank = Bank.objects.get(user=user)

        return Response({
            'user_id': user.id,
            'bank_id': bank.id,
            'balance': bank.balance
        })

    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    except Bank.DoesNotExist:
        return Response({'error': 'Bank account not found'}, status=404)


def bank_pay(bank_id, amount):

    time.sleep(2)
    payment_success = random.randint(1, 10) <= 9

    if not payment_success:
        return False

    try:
        bank = Bank.objects.get(id=bank_id)

        if bank.balance < Decimal(str(amount)):
            return False

        bank.balance -= Decimal(str(amount))
        bank.save()
        safe_delay(simulate_payment_task)
        return True

    except Bank.DoesNotExist:
        return False


def bank_charge(bank_id, amount):

    try:
        bank = Bank.objects.get(id=bank_id)
        bank.balance += Decimal(str(amount))
        bank.save()
        return True

    except Bank.DoesNotExist:
        return False
