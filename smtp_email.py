import base64
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import dotenv
from ntlm_auth.ntlm import NtlmContext

dotenv.load_dotenv()


class EmailSender:
    # def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
    def __init__(self, smtp_server="mail.asrock.com.tw", smtp_port=587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def _ntlm_auth(self, smtp, username, password):
        """
        Perform NTLM authentication manually
        """
        try:
            # Create NTLM context
            ntlm_context = NtlmContext(
                username, password, None, None, ntlm_compatibility=3
            )

            # Send AUTH NTLM command
            smtp.docmd("AUTH", "NTLM")

            # Step 1: Send Type 1 message
            negotiate_message = ntlm_context.step()
            negotiate_b64 = base64.b64encode(negotiate_message).decode("ascii")

            # Send negotiate message and get challenge
            code, challenge_b64 = smtp.docmd("", negotiate_b64)

            if code != 334:
                raise Exception(f"NTLM negotiation failed with code {code}")

            # Step 2: Process challenge and send authentication
            challenge_message = base64.b64decode(challenge_b64)
            authenticate_message = ntlm_context.step(challenge_message)
            authenticate_b64 = base64.b64encode(authenticate_message).decode("ascii")

            # Send authentication message
            code, response = smtp.docmd("", authenticate_b64)

            if code != 235:
                raise Exception(
                    f"NTLM authentication failed with code {code}: {response}"
                )

            print("NTLM authentication successful")
            return True

        except Exception as e:
            print(f"NTLM authentication error: {e}")
            return False

    def send_email(
        self,
        sender: str,
        recipients: list[str],
        subject: str,
        message: str,
        password: str | None = None,
        attachments: list[str] | None = None,
        use_ntlm: bool = True,
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
            use_ntlm (bool): Whether to use NTLM authentication (default: True)
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
        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as smtp:
            try:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                if use_ntlm:
                    # Use NTLM authentication
                    if not self._ntlm_auth(smtp, sender, password):
                        return False
                else:
                    smtp.login(sender, password)

                smtp.send_message(msg)
                print("Email sent successfully")
                return True
            except Exception as e:
                print(f"Failed to send email: {e}")
                return False


# Example usage
if __name__ == "__main__":
    sender = "Tim_Wan@asrock.com.tw"
    recipients = [
        "Tim_Wan@asrock.com.tw",
        "keepdling@gmail.com",
    ]
    subject = "ASRTranslator completed"
    message = f"Your attachment is ready and attached to this email. \n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Example with IDML attachment
    attachments = [
        # "/home/tim/Documents/X870_Nova_WiFi.idml"
    ]

    email_sender = EmailSender()
    email_sender.send_email(
        sender, recipients, subject, message, attachments=attachments, use_ntlm=True
    )
