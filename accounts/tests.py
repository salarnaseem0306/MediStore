from django.test import TestCase

from accounts.models import User


class RoleTests(TestCase):
    def test_a_new_superuser_is_a_manager(self):
        admin = User.objects.create_superuser("root", password="pw")
        self.assertEqual(admin.role, User.Role.MANAGER)

    def test_a_normal_user_defaults_to_cashier(self):
        user = User.objects.create_user("till", password="pw")
        self.assertEqual(user.role, User.Role.CASHIER)