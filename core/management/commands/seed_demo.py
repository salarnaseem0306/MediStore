import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import Medicine
from inventory.models import Batch, StockMovement, Supplier
from inventory.services import receive_batch

DEMO_PASSWORD = "medistore123"

USERS = [
    ("manager1", User.Role.MANAGER),
    ("pharmacist1", User.Role.PHARMACIST),
    ("cashier1", User.Role.CASHIER),
]

SUPPLIERS = [
    ("Al-Shifa Distributors", "021-3555-0101", "DR-1001"),
    ("MediLink Pharma", "042-3555-0202", "DR-1002"),
    ("Karachi Drug House", "021-3555-0303", "DR-1003"),
    ("HealthPlus Wholesale", "051-3555-0404", "DR-1004"),
]

T, C, S, INJ, CR = "tablet", "capsule", "syrup", "injection", "cream"

# (name, generic_name, strength, form, price in PKR, needs a prescription)
MEDICINES = [
    ("Panadol", "Paracetamol", "500 mg", T, "25.00", False),
    ("Calpol", "Paracetamol", "120 mg/5 ml", S, "180.00", False),
    ("Brufen", "Ibuprofen", "400 mg", T, "45.00", False),
    ("Disprin", "Aspirin", "300 mg", T, "15.00", False),
    ("Rigix", "Cetirizine", "10 mg", T, "60.00", False),
    ("Gaviscon", "Sodium alginate", "150 ml", S, "420.00", False),
    ("Surbex Z", "Multivitamin", "1 tablet", T, "350.00", False),
    ("Calcium-D", "Calcium carbonate", "500 mg", T, "280.00", False),
    ("Antiseptic Cream", "Chloroxylenol", "1%", CR, "160.00", False),
    ("Betadine", "Povidone iodine", "5%", CR, "220.00", False),
    ("Strepsils", "Amylmetacresol", "1.2 mg", T, "12.00", False),
    ("Imodium", "Loperamide", "2 mg", C, "35.00", False),
    ("Buscopan", "Hyoscine", "10 mg", T, "40.00", False),
    ("Risek", "Omeprazole", "20 mg", C, "55.00", False),
    ("Ponstan", "Mefenamic acid", "500 mg", C, "30.00", False),
    ("Clarityn", "Loratadine", "10 mg", T, "50.00", False),
    ("Cac-1000", "Vitamin C", "1000 mg", T, "200.00", False),
    ("Zincat", "Zinc sulfate", "20 mg", S, "140.00", False),
    ("Benadryl", "Diphenhydramine", "125 ml", S, "250.00", False),
    ("Voltaren Gel", "Diclofenac", "1%", CR, "380.00", False),
    ("Canesten", "Clotrimazole", "1%", CR, "290.00", False),
    ("Motilium", "Domperidone", "10 mg", T, "70.00", False),
    ("Augmentin", "Amoxicillin/Clavulanate", "625 mg", T, "480.00", True),
    ("Amoxil", "Amoxicillin", "500 mg", C, "150.00", True),
    ("Flagyl", "Metronidazole", "400 mg", T, "55.00", True),
    ("Ciproxin", "Ciprofloxacin", "500 mg", T, "120.00", True),
    ("Glucophage", "Metformin", "500 mg", T, "60.00", True),
    ("Norvasc", "Amlodipine", "5 mg", T, "90.00", True),
    ("Lipitor", "Atorvastatin", "20 mg", T, "310.00", True),
    ("Voltaren Injection", "Diclofenac", "75 mg/3 ml", INJ, "65.00", True),
]


def batch_plan(index):
    """(days until expiry, units) for each batch of the index-th medicine."""
    if index % 10 == 0:
        return [(-20, 40), (200, 120), (400, 80)]  # one is already expired
    if index % 10 == 1:
        return [(20, 30), (180, 100)]  # one expires within 30 days
    return [(90, 60), (250, 150)]


class Command(BaseCommand):
    help = "Create demo users, suppliers, medicines and batches. Safe to run twice."

    @transaction.atomic
    def handle(self, *args, **options):
        users = {}
        for username, role in USERS:
            user, created = User.objects.get_or_create(username=username, defaults={"role": role})
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[role] = user

        suppliers = []
        for name, phone, licence in SUPPLIERS:
            supplier, _ = Supplier.objects.get_or_create(
                name=name, defaults={"phone": phone, "licence_number": licence}
            )
            suppliers.append(supplier)

        today = timezone.localdate()
        manager = users[User.Role.MANAGER]
        for index, (name, generic, strength, form, price, needs_rx) in enumerate(MEDICINES):
            medicine, _ = Medicine.objects.get_or_create(
                name=name,
                strength=strength,
                form=form,
                defaults={
                    "generic_name": generic,
                    "barcode": f"MS{index + 1:06d}",
                    "price": Decimal(price),
                    "requires_prescription": needs_rx,
                    "reorder_level": 20,
                },
            )
            if medicine.batches.exists():
                continue  # already stocked, so running twice changes nothing
            for number, (days, units) in enumerate(batch_plan(index), start=1):
                receive_batch(
                    medicine=medicine,
                    supplier=suppliers[index % len(suppliers)],
                    batch_number=f"B{index + 1:02d}-{number}",
                    expiry_date=today + datetime.timedelta(days=days),
                    quantity=units,
                    cost_price=(medicine.price * Decimal("0.70")).quantize(Decimal("0.01")),
                    user=manager,
                )

        demo_users = User.objects.filter(username__in=[name for name, _ in USERS]).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {demo_users} demo users, "
                f"{Supplier.objects.count()} suppliers, "
                f"{Medicine.objects.count()} medicines, {Batch.objects.count()} batches, "
                f"{StockMovement.objects.count()} movements. "
                f"Demo password: {DEMO_PASSWORD}"
            )
        )