import datetime
from io import StringIO

from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase
from django.utils import timezone

from catalog.models import Medicine
from inventory.models import Batch, StockMovement


def seed():
    call_command("seed_demo", stdout=StringIO())


class SeedDemoTests(TestCase):
    def test_running_it_twice_changes_nothing(self):
        seed()
        first = (Medicine.objects.count(), Batch.objects.count(), StockMovement.objects.count())
        seed()
        second = (Medicine.objects.count(), Batch.objects.count(), StockMovement.objects.count())
        self.assertEqual(first, second)

    def test_demo_data_has_the_shape_the_exercise_asks_for(self):
        seed()
        today = timezone.localdate()
        self.assertEqual(Medicine.objects.count(), 30)
        self.assertEqual(Medicine.objects.filter(requires_prescription=True).count(), 8)
        self.assertTrue(Batch.objects.filter(expiry_date__lt=today).exists())
        soon = today + datetime.timedelta(days=30)
        self.assertTrue(
            Batch.objects.filter(expiry_date__gte=today, expiry_date__lte=soon).exists()
        )
        for medicine in Medicine.objects.all():
            self.assertGreaterEqual(medicine.batches.count(), 2)

    def test_every_batch_equals_the_sum_of_its_movements(self):
        seed()
        for batch in Batch.objects.all():
            total = batch.movements.aggregate(total=Sum("change"))["total"] or 0
            self.assertEqual(batch.quantity_left, total, batch)