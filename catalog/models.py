from django.db import models


class Medicine(models.Model):
    class Form(models.TextChoices):
        TABLET = "tablet", "Tablet"
        CAPSULE = "capsule", "Capsule"
        SYRUP = "syrup", "Syrup"
        INJECTION = "injection", "Injection"
        CREAM = "cream", "Cream"

    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200)
    strength = models.CharField(max_length=50, help_text="For example 500 mg")
    form = models.CharField(max_length=20, choices=Form.choices)
    barcode = models.CharField(max_length=64, unique=True, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # PKR, Rule 1
    requires_prescription = models.BooleanField(default=False)
    reorder_level = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)  # never deleted, only inactive (Rule 8)

    class Meta:
        ordering = ["name", "strength"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="medicine_price_not_negative"
            ),
        ]

    def __str__(self):
        return f"{self.name} {self.strength} ({self.form})"