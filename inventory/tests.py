import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from catalog.models import Medicine
from inventory.models import Batch, StockMovement, Supplier
from inventory.services import StockError, change_stock, receive_batch


class StockTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user("t_mgr", password="pw", role=User.Role.MANAGER)
        cls.supplier = Supplier.objects.create(name="Test Supplier")
        cls.medicine = Medicine.objects.create(
            name="Panadol",
            generic_name="Paracetamol",
            strength="500 mg",
            form="tablet",
            price=Decimal("25.00"),
        )

    def receive(self, number="B1", days=90, quantity=50, medicine=None):
        return receive_batch(
            medicine=medicine or self.medicine,
            supplier=self.supplier,
            batch_number=number,
            expiry_date=timezone.localdate() + datetime.timedelta(days=days),
            quantity=quantity,
            cost_price=Decimal("17.50"),
            user=self.manager,
        )


class BatchRuleTests(StockTestCase):
    def test_receiving_a_batch_writes_a_purchase_movement(self):
        batch = self.receive(quantity=50)
        self.assertEqual(batch.quantity_received, 50)
        self.assertEqual(batch.quantity_left, 50)
        movement = batch.movements.get()
        self.assertEqual(movement.change, 50)
        self.assertEqual(movement.reason, StockMovement.Reason.PURCHASE)

    def test_service_refuses_to_go_below_zero(self):
        batch = self.receive(quantity=50)
        with self.assertRaises(StockError):
            change_stock(batch.pk, -51, StockMovement.Reason.SALE, self.manager)
        batch.refresh_from_db()
        self.assertEqual(batch.quantity_left, 50)
        self.assertEqual(batch.movements.count(), 1)  # no movement for the refused change

    def test_service_refuses_to_go_above_what_was_received(self):
        batch = self.receive(quantity=50)
        with self.assertRaises(StockError):
            change_stock(batch.pk, 1, StockMovement.Reason.ADJUSTMENT, self.manager)

    def test_database_itself_refuses_a_negative_quantity(self):
        batch = self.receive(quantity=50)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Batch.objects.filter(pk=batch.pk).update(quantity_left=-1)

    def test_batch_number_is_unique_per_medicine_only(self):
        self.receive(number="AX-1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.receive(number="AX-1")
        other = Medicine.objects.create(
            name="Brufen",
            generic_name="Ibuprofen",
            strength="400 mg",
            form="tablet",
            price=Decimal("45.00"),
        )
        self.receive(number="AX-1", medicine=other)  # same number, other medicine: fine

    def test_a_batch_is_expired_only_after_its_expiry_date(self):
        yesterday = self.receive(number="OLD", days=-1)
        today = self.receive(number="TODAY", days=0)
        self.assertTrue(yesterday.is_expired)
        self.assertFalse(today.is_expired)


class StockEqualsMovementsTests(StockTestCase):
    def test_quantity_left_equals_the_sum_of_movements(self):
        batch = self.receive(quantity=50)
        change_stock(batch.pk, -8, StockMovement.Reason.SALE, self.manager)
        change_stock(batch.pk, 3, StockMovement.Reason.REFUND, self.manager)
        change_stock(batch.pk, -5, StockMovement.Reason.WRITE_OFF, self.manager, note="damaged")
        batch.refresh_from_db()
        total = batch.movements.aggregate(total=Sum("change"))["total"]
        self.assertEqual(batch.quantity_left, 40)
        self.assertEqual(total, 40)