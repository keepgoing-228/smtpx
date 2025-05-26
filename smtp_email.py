import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import dotenv

dotenv.load_dotenv()


class EmailSender:
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_email(
        self, sender, recipients, subject, message, password=None, attachments=None
    ):
        """
        Send an email using SMTP

        Args:
            sender (str): Sender email address
            recipients (list): List of recipient email addresses
            subject (str): Email subject
            message (str): Email body content
            password (str, optional): Email password. If None, will use PASSWORD from env
            attachments (list, optional): List of file paths to attach
        """
        # Create a multipart message object
        msg = MIMEMultipart()

        # Set the sender and recipient addresses
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        # Add the body of the message
        msg.attach(MIMEText(message, "plain"))

        # Add attachments if provided
        if attachments:
            for file_path in attachments:
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "rb") as attachment:
                            # Create MIMEBase object
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())

                        # Encode file in ASCII characters to send by email
                        encoders.encode_base64(part)

                        # Add header as key/value pair to attachment part
                        filename = os.path.basename(file_path)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {filename}",
                        )

                        # Attach the part to message
                        msg.attach(part)
                        print(f"Attached file: {filename}")
                    except Exception as e:
                        print(f"Failed to attach file {file_path}: {e}")
                else:
                    print(f"File not found: {file_path}")

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
    recipients = [
        # "Tim_Wan@asrock.com.tw",
        "keepdling@gmail.com",
    ]
    subject = "Test Email"
    message = "This is a test email"

    # Example with IDML attachment
    attachments = [
        "/home/tim/Documents/X870_Nova_WiFi.idml"
    ]  # Add your IDML file paths here

    email_sender = EmailSender()
    email_sender.send_email(
        sender, recipients, subject, message, attachments=attachments
    )
