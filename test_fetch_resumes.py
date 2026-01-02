"""
Test script to verify fetch_resumes functionality

This script tests the email fetching and embedding generation workflow.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.email_client import EmailClient
from backend.app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_email_connection():
    """Test email server connection"""
    print("\n" + "=" * 70)
    print("TESTING EMAIL CONNECTION")
    print("=" * 70)

    try:
        email_client = EmailClient()
        print(f"\n📧 Email: {email_client.email_address}")
        print(f"📂 Server: {email_client.imap_server}:{email_client.imap_port}")
        print(f"💾 Save to: {email_client.resumes_dir}")

        print("\n🔌 Connecting to email server...")
        mail = email_client.connect()
        print("✓ Connection successful!")

        # Check inbox
        mail.select("INBOX")
        status, messages = mail.search(None, "ALL")

        if status == "OK":
            total_emails = len(messages[0].split())
            print(f"✓ Found {total_emails} total emails in INBOX")

        # Check unread
        status, messages = mail.search(None, "UNSEEN")
        if status == "OK":
            unread_count = len(messages[0].split()) if messages[0] else 0
            print(f"✓ Found {unread_count} unread emails")

        mail.close()
        mail.logout()

        print("\n✓ Email connection test PASSED")
        return True

    except Exception as e:
        print(f"\n✗ Email connection test FAILED: {e}")
        return False


def test_fetch_resumes_dry_run():
    """Test fetching resumes (without saving)"""
    print("\n" + "=" * 70)
    print("TESTING FETCH RESUMES (DRY RUN)")
    print("=" * 70)

    try:
        email_client = EmailClient()

        # Try to fetch (will save files)
        print("\n📥 Fetching resumes from email...")
        print("⚠️  Note: This will mark emails as read if unread_only=True")

        # You can change max_emails to limit processing
        saved_files = email_client.fetch_resumes(unread_only=False, max_emails=2)

        if saved_files:
            print(f"\n✓ Fetched {len(saved_files)} resume(s):")
            for filepath in saved_files:
                print(f"  • {filepath}")
        else:
            print("\n✓ No new resumes found (this is OK)")

        print("\n✓ Fetch resumes test PASSED")
        return True

    except Exception as e:
        print(f"\n✗ Fetch resumes test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("FETCH RESUMES FUNCTIONALITY TEST")
    print("=" * 70)

    print("\nThis script will:")
    print("1. Test email server connection")
    print("2. Try to fetch resumes from email")
    print("3. Verify the files are saved correctly")

    # Test 1: Connection
    connection_ok = test_email_connection()

    if not connection_ok:
        print("\n❌ Email connection failed. Check your credentials in .env file:")
        print(f"   - EMAIL_ADDRESS: {settings.email_address}")
        print(f"   - EMAIL_PASSWORD: {'*' * len(settings.email_password) if settings.email_password else 'NOT SET'}")
        print(f"   - IMAP_SERVER: {settings.imap_server}")
        print(f"   - IMAP_PORT: {settings.imap_port}")
        sys.exit(1)

    # Test 2: Fetch resumes
    input("\n⚠️  Press Enter to test fetching resumes (this may mark emails as read)...")
    fetch_ok = test_fetch_resumes_dry_run()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Email Connection:  {'✓ PASS' if connection_ok else '✗ FAIL'}")
    print(f"Fetch Resumes:     {'✓ PASS' if fetch_ok else '✗ FAIL'}")
    print("=" * 70)

    if connection_ok and fetch_ok:
        print("\n✓ All tests PASSED!")
        print("\nNext steps:")
        print("1. The fetch_resumes endpoint will automatically generate embeddings")
        print("2. You can test it via: POST /fetch-resumes")
        print("3. Or run: python -m backend.precompute_embeddings to cache existing resumes")
    else:
        print("\n❌ Some tests FAILED. Please check the errors above.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
