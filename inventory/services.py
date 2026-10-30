from django.db import transaction
from django.db.models import F

from .models import Batch, StockMovement


class StockError(Exception):
    """A stock change would break a batch's limits (below 0 or above received)."""


@transaction.atomic
def change_stock(batch_id, change, reason, user, sale=None, note=""):
    """The one door for stock changes: update the batch and write the movement together."""
    if change == 0:
        raise ValueError("A stock change cannot be zero.")

    if change > 0:
        # Never above quantity_received.
        allowed = Batch.objects.filter(
            pk=batch_id, quantity_left__lte=F("quantity_received") - change
        )
    else:
        # Never below zero.
        allowed = Batch.objects.filter(pk=batch_id, quantity_left__gte=-change)

    if not allowed.update(quantity_left=F("quantity_left") + change):
        raise StockError(f"Batch {batch_id}: a change of {change} is not possible.")

    return StockMovement.objects.create(
        batch_id=batch_id,
        change=change,
        reason=reason,
        sale=sale,
        note=note,
        created_by=user,
    )


@transaction.atomic
def receive_batch(*, medicine, supplier, batch_number, expiry_date, quantity, cost_price, user):
    """A new batch arrives: create it empty, then add the units as a purchase movement.

    The API (Day 2) refuses an expiry date in the past; this service does not, so
    seed_demo can create an already-expired batch to test with.
    """
    batch = Batch.objects.create(
        medicine=medicine,
        supplier=supplier,
        batch_number=batch_number,
        expiry_date=expiry_date,
        quantity_received=quantity,
        quantity_left=0,
        cost_price=cost_price,
    )
    change_stock(batch.pk, quantity, StockMovement.Reason.PURCHASE, user)
    batch.refresh_from_db()
    return batch