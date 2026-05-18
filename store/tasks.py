from celery import shared_task
from django.core.mail import EmailMessage
from store.models import Order, ProductOrder
from reportlab.pdfgen import canvas
from io import BytesIO
import time
from django.utils import timezone
from django.db.models import Sum, Min, Max
from store.models import Order, DailySummary
@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def generate_invoice_task(self, order_id):


    try:
   
        order = Order.objects.get(id=order_id)
        items = ProductOrder.objects.filter(order=order)

      
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.setFont("Helvetica", 12)

        pdf.drawString(100, 800, f"Invoice for Order #{order.id}")
        pdf.drawString(100, 780, f"Status: {order.status}")

        y = 740
        total = 0

        for item in items:
            line = f"{item.product.name} - {item.quantity} x {item.price}"
            pdf.drawString(100, y, line)
            y -= 20
            total += item.quantity * item.price

        pdf.drawString(100, y - 20, f"Total: {total}")

        pdf.showPage()
        pdf.save()

     
        buffer.seek(0)
        pdf_data = buffer.getvalue()

        email = EmailMessage(
            subject=f"Invoice Order #{order.id}",
            body="Find your invoice attached.",
            from_email="saraatiah78@gmail.com",
            to=["saraatiah88@gmail.com"],
        )

        email.attach(
            f"invoice_{order.id}.pdf",
            pdf_data,
            "application/pdf"
        )

        email.send(fail_silently=False)

        return "Invoice sent"

    except Order.DoesNotExist:
        print("Invalid order ID")
        return "Order not found"


    except Exception as e:
        print("Error:", str(e))
        print("Retry count:", self.request.retries)

   
        if self.request.retries >= 3:
            return "Failed after retries"

     
        raise self.retry(exc=e)
    
    # fixed size chunking 
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def run_fixed_sales_job(self):

    try:

        today = timezone.now().date()

        orders = Order.objects.filter(
            created_at__date=today,
            status='success'
        )

        if not orders.exists():
            return "No orders today"

        ids = orders.aggregate(
            min_id=Min('id'),
            max_id=Max('id')
        )

        current_id = ids['min_id']
        max_id = ids['max_id']

        chunk_size = 100

        total_sales = 0
        total_orders_processed = 0
        start_time = time.time()
        
        while current_id <= max_id:

            next_id = current_id + chunk_size

            chunk_orders = Order.objects.filter(
                id__gte=current_id,
                id__lt=next_id,
                created_at__date=today,
                status='success'
            )

            chunk_count = chunk_orders.count()

            chunk_sum = chunk_orders.aggregate(
                total=Sum('total_amount')
            )['total'] or 0

            total_sales += chunk_sum
            total_orders_processed += chunk_count

            execution_time = time.time() - start_time

            print("=" * 40)

            print(f"Execution time: {execution_time:.4f} sec")

            print(f"Orders processed: {chunk_count}")

            print("=" * 60)

            current_id = next_id

        DailySummary.objects.update_or_create(
            date=today,
            defaults={
                'total_revenue': total_sales,
                'orders_processed': total_orders_processed
            }
        )

        return (
            f"Processed "
            f"{total_orders_processed} orders"
        )

    except Exception as exc:

        raise self.retry(exc=exc)

@shared_task
def simulate_payment_task():

    print("⏳ Simulating payment...")
    time.sleep(5)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def run_adaptive_sales_job(self):

    try:

        today = timezone.now().date()

        # only successful orders
        orders = Order.objects.filter(
            created_at__date=today,
            status='success'
        ).order_by('id')

        if not orders.exists():
            return "No successful orders today"

        min_id = orders.first().id
        max_id = orders.last().id

        current_id = min_id

        # adaptive chunk settings
        chunk_size = 500
        min_chunk = 50
        max_chunk = 5000

        # target execution time
        target_time = 0.2

        total_sales = 0
        total_orders_processed = 0

        while current_id <= max_id:

            # save current chunk before modifying
            current_chunk_size = chunk_size

            next_id = current_id + current_chunk_size

            start_time = time.time()

            # get chunk
            chunk_orders = Order.objects.filter(
                id__gte=current_id,
                id__lt=next_id,
                created_at__date=today,
                status='success'
            )

            # statistics
            chunk_count = chunk_orders.count()

            chunk_sum = chunk_orders.aggregate(
                total=Sum('total_amount')
            )['total'] or 0

            total_sales += chunk_sum
            total_orders_processed += chunk_count

            execution_time = time.time() - start_time

            # default next chunk
            new_chunk_size = current_chunk_size

            # adaptive algorithm
            if chunk_count > 0:

                time_ratio = target_time / max(
                    execution_time,
                    0.001
                )

                calculated_chunk_size = int(
                    current_chunk_size * time_ratio
                )

                new_chunk_size = max(
                    min_chunk,
                    min(calculated_chunk_size, max_chunk)
                )

            print("=" * 60)

            print(f"Current chunk size: {current_chunk_size}")

            print(f"Execution time: {execution_time:.4f} sec")

            print(f"Orders processed: {chunk_count}")

            print(f"Next chunk size: {new_chunk_size}")

            print("=" * 60)

            # apply new chunk size
            chunk_size = new_chunk_size

            # move to next chunk
            current_id = next_id

        # save summary
        DailySummary.objects.update_or_create(
            date=today,
            defaults={
                'total_revenue': total_sales,
                'orders_processed': total_orders_processed
            }
        )

        return (
            f"Adaptive processing finished "
            f"for {total_orders_processed} orders"
        )

    except Exception as exc:

        print("ERROR:", str(exc))

        raise self.retry(exc=exc)