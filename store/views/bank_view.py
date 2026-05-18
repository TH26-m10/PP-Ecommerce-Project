from decimal import Decimal
from store.tasks import simulate_payment_task
from store.models import Bank
import time
import random
from decimal import Decimal

def bank_pay(bank_id,amount):

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
        simulate_payment_task.delay()
        return True

    except Bank.DoesNotExist:
        return False


def bank_charge(bank_id,amount):

    try:
        bank = Bank.objects.get(id=bank_id)

        # Random success rate (90% success)
        charge_success = random.randint(1, 10) <= 9
        if not charge_success:
            False
        
        bank.balance += Decimal(str(amount))
        bank.save()

        return True

    except Bank.DoesNotExist:
        return False