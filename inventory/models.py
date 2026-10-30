from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    licence_number = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Batch(models.Model):
    medicine = models.ForeignKey(
        "catalog.Medicine", on_delete=models.PROTECT, related_name="batches"
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="batches")
    batch_number = models.CharField(max_length=50)
    expiry_date = models.DateField(db_index=True)
    quantity_received = models.IntegerField()
    quantity_left = models.IntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expiry_date", "id"]  # first-expiry-first-out order
        constraints = [
            models.UniqueConstraint(
                fields=["medicine", "batch_number"], name="unique_batch_number_per_medicine"
            ),
            models.CheckConstraint(
                condition=Q(quantity_received__gt=0), name="batch_received_positive"
            ),
            models.CheckConstraint(
                condition=Q(quantity_left__gte=0), name="batch_left_not_negative"
            ),
            models.CheckConstraint(
                condition=Q(quantity_left__lte=F("quantity_received")),
                name="batch_left_not_above_received",
            ),
            models.CheckConstraint(condition=Q(cost_price__gte=0), name="batch_cost_not_negative"),
        ]

    @property
    def is_expired(self):
        return self.expiry_date < timezone.localdate()

    def __str__(self):
        return f"{self.medicine} / batch {self.batch_number}"


class StockMovement(models.Model):
    class Reason(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        SALE = "sale", "Sale"
        REFUND = "refund", "Refund"
        WRITE_OFF = "write_off", "Write-off"
        ADJUSTMENT = "adjustment", "Adjustment"

    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="movements")
    change = models.IntegerField()  # + units in, - units out
    reason = models.CharField(max_length=20, choices=Reason.choices)
    sale = models.ForeignKey(
        "sales.Sale", on_delete=models.PROTECT, null=True, blank=True, related_name="movements"
    )
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_movements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=~Q(change=0), name="movement_change_not_zero"),
        ]

    def __str__(self):
        return f"{self.batch} {self.change:+d} ({self.reason})"
