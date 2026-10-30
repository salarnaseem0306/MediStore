from django.conf import settings
from django.db import models
from django.db.models import Q


class Prescription(models.Model):
    patient_name = models.CharField(max_length=200)
    doctor_name = models.CharField(max_length=200)
    issued_on = models.DateField()
    notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="verified_prescriptions",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_on", "-id"]
        constraints = [
            # Verified means both who and when are filled in; otherwise neither.
            models.CheckConstraint(
                condition=(
                    Q(verified_by__isnull=True, verified_at__isnull=True)
                    | Q(verified_by__isnull=False, verified_at__isnull=False)
                ),
                name="prescription_verified_by_and_at_together",
            ),
        ]

    @property
    def is_verified(self):
        return self.verified_at is not None

    def __str__(self):
        return f"Prescription #{self.pk} for {self.patient_name}"


class Sale(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"

    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    prescription = models.ForeignKey(
        Prescription, on_delete=models.PROTECT, null=True, blank=True, related_name="sales"
    )
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(total__gte=0), name="sale_total_not_negative"),
            # A paid or refunded sale always knows when it was paid.
            models.CheckConstraint(
                condition=~Q(status__in=["paid", "refunded"]) | Q(paid_at__isnull=False),
                name="sale_paid_has_paid_at",
            ),
        ]

    def __str__(self):
        return f"Sale #{self.pk} ({self.status})"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey(
        "catalog.Medicine", on_delete=models.PROTECT, related_name="sale_items"
    )
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # copied at add time (Rule 8)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["sale", "medicine"], name="one_line_per_medicine_per_sale"
            ),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="saleitem_quantity_positive"),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0), name="saleitem_price_not_negative"
            ),
            models.CheckConstraint(
                condition=Q(line_total__gte=0), name="saleitem_total_not_negative"
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.medicine}"


class SaleItemBatch(models.Model):
    """Exactly which batch (and how many units) a sale line was taken from."""

    sale_item = models.ForeignKey(
        SaleItem, on_delete=models.PROTECT, related_name="batch_allocations"
    )
    batch = models.ForeignKey(
        "inventory.Batch", on_delete=models.PROTECT, related_name="sale_allocations"
    )
    quantity = models.IntegerField()

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["sale_item", "batch"], name="one_row_per_batch_per_line"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="allocation_quantity_positive"
            ),
        ]

    def __str__(self):
        return f"{self.quantity} from {self.batch}"
