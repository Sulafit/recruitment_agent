import imaplib
import email
from email.header import decode_header
import os
from typing import List
from .config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailClient:
    def __init__(self):
        self.email_address = settings.email_address
        self.password = settings.email_password
        self.imap_server = settings.imap_server
        self.imap_port = settings.imap_port
        self.resumes_dir = settings.resumes_dir

        os.makedirs(self.resumes_dir, exist_ok=True)

    def connect(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            logger.info(f"Successfully connected to {self.imap_server}")
            return mail
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            raise

    def fetch_resumes(self, folder: str = "INBOX", unread_only: bool = True, max_emails: int = 50) -> List[str]:
        """
        Fetch resumes from email attachments

        Args:
            folder: Email folder to search (default: INBOX)
            unread_only: Only process unread emails (default: True)
            max_emails: Maximum number of emails to process (default: 50)

        Returns list of saved file paths
        """
        saved_files = []

        try:
            mail = self.connect()
            mail.select(folder)

            # Search for emails
            search_criteria = "UNSEEN" if unread_only else "ALL"
            status, messages = mail.search(None, search_criteria)

            if status != "OK":
                logger.warning("No messages found")
                return saved_files

            email_ids = messages[0].split()
            total_emails = len(email_ids)

            # Limit to most recent emails
            if max_emails and total_emails > max_emails:
                email_ids = email_ids[-max_emails:]  # Get last N emails
                logger.info(f"Found {total_emails} emails, processing last {max_emails}")
            else:
                logger.info(f"Found {total_emails} emails")

            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")

                if status != "OK":
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Process attachments
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_disposition() == "attachment":
                                    filename = part.get_filename()

                                    if filename:
                                        # Decode filename if needed
                                        filename = self._decode_filename(filename)

                                        # Check if it's a resume file
                                        if self._is_resume_file(filename):
                                            filepath = os.path.join(self.resumes_dir, filename)

                                            # Save attachment
                                            with open(filepath, "wb") as f:
                                                f.write(part.get_payload(decode=True))

                                            logger.info(f"Saved resume: {filename}")
                                            saved_files.append(filepath)

            mail.close()
            mail.logout()

        except Exception as e:
            logger.error(f"Error fetching resumes: {e}")
            raise

        return saved_files

    def _decode_filename(self, filename: str) -> str:
        """Decode email filename"""
        decoded = decode_header(filename)
        if decoded[0][1]:
            return decoded[0][0].decode(decoded[0][1])
        return decoded[0][0] if isinstance(decoded[0][0], str) else decoded[0][0].decode()

    def _is_resume_file(self, filename: str) -> bool:
        """Check if file is a resume based on extension"""
        valid_extensions = ['.pdf', '.doc', '.docx', '.txt', '.png', '.jpg', '.jpeg']
        return any(filename.lower().endswith(ext) for ext in valid_extensions)
