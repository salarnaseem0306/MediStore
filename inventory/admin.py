from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Batch, StockMovement, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "licence_number")
    search_fields = ("name", "licence_number")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = (
        "medicine",
        "batch_number",
        "expiry_date",
        "days_to_expiry",
        "expiry_status",
        "quantity_left",
        "quantity_received",
        "supplier",
    )
    list_filter = ("supplier",)
    search_fields = ("batch_number", "medicine__name", "medicine__generic_name")
    list_select_related = ("medicine", "supplier")
    # Quantities only change through inventory.services (every change leaves a movement).
    readonly_fields = (
        "medicine",
        "supplier",
        "batch_number",
        "expiry_date",
        "quantity_received",
        "quantity_left",
        "cost_price",
        "received_at",
    )

    def has_add_permission(self, request):
        return False  # batches arrive through the receive endpoint / service

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Days to expiry", ordering="expiry_date")
    def days_to_expiry(self, obj):
        return (obj.expiry_date - timezone.localdate()).days

    @admin.display(description="Status")
    def expiry_status(self, obj):
        days = (obj.expiry_date - timezone.localdate()).days
        if days < 0:
            return format_html('<b style="color:#b00020">EXPIRED</b>')
        if days <= 30:
            return format_html('<b style="color:#b26a00">Expires soon</b>')
        return "OK"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "batch", "change", "reason", "sale", "created_by")
    list_filter = ("reason",)
    date_hierarchy = "created_at"
    list_select_related = ("batch__medicine", "sale", "created_by")

    # The movement log is history: nobody adds, edits or deletes rows by hand.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False