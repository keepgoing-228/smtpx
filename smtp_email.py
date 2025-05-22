import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import dotenv

dotenv.load_dotenv()


class EmailSender:
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_email(self, sender, recipient, subject, message, password=None):
        """
        Send an email using SMTP

        Args:
            sender (str): Sender email address
            recipient (str): Recipient email address
            subject (str): Email subject
            message (str): Email body content
            password (str, optional): Email password. If None, will use PASSWORD from env
        """
        # Create a multipart message object
        msg = MIMEMultipart()

        # Set the sender and recipient addresses
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject

        # Add the body of the message
        msg.attach(MIMEText(message, "plain"))

        # Use environment variable if password not provided
        if password is None:
            password = os.getenv("PASSWORD")

        # Send the email
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as smtp:
            try:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(sender, password)
                smtp.send_message(msg)
                print("Email sent successfully")
                return True
            except Exception as e:
                print(f"Failed to send email: {e}")
                return False


# Example usage
if __name__ == "__main__":
    sender = "r10631039@g.ntu.edu.tw"
    recipient = "keepdling@gmail.com"
    subject = "Test Email"
    message = "This is a test email"

    email_sender = EmailSender()
    email_sender.send_email(sender, recipient, subject, message)
