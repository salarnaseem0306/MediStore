from django.contrib import admin, messages

from .models import Medicine


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "strength",
        "form",
        "generic_name",
        "price",
        "requires_prescription",
        "is_active",
    )
    list_filter = ("form", "requires_prescription", "is_active")
    search_fields = ("name", "generic_name", "barcode")
    actions = ["mark_inactive"]

    def has_delete_permission(self, request, obj=None):
        # Medicines are never deleted, only marked inactive (Rule 8).
        return False

    @admin.action(description="Mark selected medicines inactive")
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} medicine(s) marked inactive.", messages.SUCCESS)