from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # A superuser must be able to use every manager endpoint.
        extra_fields.setdefault("role", User.Role.MANAGER)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        PHARMACIST = "pharmacist", "Pharmacist"
        CASHIER = "cashier", "Cashier"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)

    objects = UserManager()

    def __str__(self):
        return f"{self.username} ({self.role})"