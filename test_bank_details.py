"""
Test script to verify bank details encryption is working correctly.
Run this script to create encrypted bank details and verify they're properly stored.
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_name.settings')
django.setup()

from django.contrib.auth.models import User
from claims.models import BankDetails
from django.conf import settings
import base64

def test_encryption():
    # Create a test user if it doesn't exist
    try:
        user = User.objects.get(username='encryption_test')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='encryption_test',
            email='encryption_test@example.com',
            password='testpassword'
        )
    
    # Create a new bank details entry
    bank_details = BankDetails.objects.create(
        user=user,
        nickname='Encryption Test Account',
        account_name='Encryption Test',
        account_number='12345678',
        sort_code='123456',
        is_default=True
    )
    
    print(f"Created bank details with ID: {bank_details.id}")
    
    # Retrieve the saved bank details
    saved = BankDetails.objects.get(id=bank_details.id)
    
    print("\nVerifying encryption:")
    print(f"Account name (decrypted): {saved.account_name}")
    print(f"Account number (decrypted): {saved.account_number}")
    print(f"Sort code (decrypted): {saved.sort_code}")
    
    # Get the raw data from the database to verify it's encrypted
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT account_name, account_number, sort_code FROM claims_bankdetails WHERE id = %s", 
            [bank_details.id]
        )
        raw_data = cursor.fetchone()
    
    print("\nRaw data from database (should be encrypted):")
    print(f"Account name (encrypted): {raw_data[0]}")
    print(f"Account number (encrypted): {raw_data[1]}")
    print(f"Sort code (encrypted): {raw_data[2]}")
    
    # Verify the encrypted data is different from the plaintext
    if (raw_data[0] != 'Encryption Test' and 
        raw_data[1] != '12345678' and 
        raw_data[2] != '123456'):
        print("\n✅ Encryption test passed! Data is stored encrypted in the database.")
    else:
        print("\n❌ Encryption test failed! Data appears to be stored in plaintext.")
    
    # Clean up
    bank_details.delete()
    print("\nTest bank details deleted.")

if __name__ == '__main__':
    test_encryption()
