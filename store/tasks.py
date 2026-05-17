from celery import shared_task
from django.core.mail import EmailMessage
from store.models import Order, ProductOrder
from reportlab.pdfgen import canvas
from io import BytesIO

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

        print("PDF size:", len(pdf_data))  # debug

  
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
            print(f"Moved to DLQ: order {order_id}")
            # ممكن تخزنيها بالداتابيس
            # FailedTask.objects.create(order_id=order_id, error=str(e))
            return "Failed after retries"

     
        raise self.retry(exc=e)