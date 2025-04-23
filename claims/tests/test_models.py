from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from claims.models import BankDetails

class BankDetailsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_bank_details_creation(self):
        bank_details = BankDetails.objects.create(
            user=self.user,
            nickname="Primary Account",
            account_name="Test User",
            account_number="12345678",
            sort_code="123456",
            is_default=True
        )
        self.assertEqual(bank_details.nickname, "Primary Account")
        self.assertEqual(bank_details.account_name, "Test User")
        self.assertEqual(bank_details.account_number, "12345678")
        self.assertEqual(bank_details.sort_code, "123456")
        self.assertTrue(bank_details.is_default)

    def test_default_account_behavior(self):
        # Create first account as default
        account1 = BankDetails.objects.create(
            user=self.user,
            nickname="Account 1",
            account_name="Test User",
            account_number="12345678",
            sort_code="123456",
            is_default=True
        )

        # Create second account as default
        account2 = BankDetails.objects.create(
            user=self.user,
            nickname="Account 2",
            account_name="Test User",
            account_number="87654321",
            sort_code="654321",
            is_default=True
        )

        # Refresh from database to get updated state
        account1.refresh_from_db()

        # First account should no longer be default
        self.assertFalse(account1.is_default)
        self.assertTrue(account2.is_default)

    def test_bank_details_validation(self):
        # Test invalid account number (too short)
        with self.assertRaises(ValidationError):
            bank_details = BankDetails(
                user=self.user,
                nickname="Invalid Account",
                account_name="Test User",
                account_number="1234567",  # 7 digits, should be 8
                sort_code="123456"
            )
            bank_details.full_clean()

        # Test invalid sort code (containing letters)
        with self.assertRaises(ValidationError):
            bank_details = BankDetails(
                user=self.user,
                nickname="Invalid Account",
                account_name="Test User",
                account_number="12345678",
                sort_code="12A456"  # Contains a letter
            )
            bank_details.full_clean()
