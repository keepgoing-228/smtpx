import base64
import json
import os
import smtplib
import sys
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import dotenv
from ntlm_auth.ntlm import NtlmContext

dotenv.load_dotenv()


class EmailSender:
    def __init__(self, smtp_server: str, smtp_port: int) -> None:
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def _ntlm_auth(
        self,
        smtp: smtplib.SMTP,
        username: str,
        password: str,
        domain: str,
        ntlm_compatibility: int = 3,
    ) -> bool:
        """
        Perform NTLM authentication manually
        """
        try:
            # Create NTLM context
            ntlm_context = NtlmContext(
                username, password, domain, None, ntlm_compatibility=ntlm_compatibility
            )
            print(f"NTLM context: {ntlm_context}")

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
        domain: str,
        password: str | None = None,
        attachments: list[str] | None = None,
        use_ntlm: bool = True,
        ntlm_compatibility: int = 3,
    ) -> bool:
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

        # Send the email
        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as smtp:
            try:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                if use_ntlm:
                    # Use NTLM authentication
                    if not self._ntlm_auth(
                        smtp,
                        sender,
                        password,
                        domain,
                        ntlm_compatibility=ntlm_compatibility,
                    ):
                        return False
                else:
                    smtp.login(sender, password)

                smtp.send_message(msg)
                return True
            except Exception as e:
                return False

    def load_config(self, config_path: str = "email_config.json") -> dict | None:
        """
        Load email configuration from JSON file

        Args:
            config_path (str): Path to the configuration file

        Returns:
            dict: Configuration dictionary
        """
        try:
            # If running as exe, look for config file in the same directory
            if getattr(sys, "frozen", False):
                # Running as exe
                exe_dir = os.path.dirname(sys.executable)
                config_path = os.path.join(exe_dir, config_path)

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config

        except FileNotFoundError:
            print(f"Configuration file not found: {config_path}")
            print("Please create email_config.json file with the required settings.")
            return None
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in configuration file: {e}")
            return None
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return None

    def send_email_from_config(self, config: dict) -> bool:
        """
        Send email using configuration from JSON file

        Args:
            config_path (str): Path to the configuration file

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        # Extract configuration
        self.smtp_server = config.get("smtp_server")
        self.smtp_port = config.get("smtp_port")
        sender = config.get("sender")
        password = config.get("password")
        recipients = config.get("recipients", [])
        domain = config.get("domain", "")
        subject = config.get("subject", "")
        message = config.get("message", "")
        attachments = config.get("attachments", [])
        use_ntlm = config.get("use_ntlm", True)
        ntlm_compatibility = config.get("ntlm_compatibility", 3)
        include_timestamp = config.get("include_timestamp", False)

        # Validate required fields
        if not sender:
            print("Error: sender is required in configuration")
            return False
        if not recipients:
            print("Error: recipients list is required in configuration")
            return False

        # Add timestamp to message if requested
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message += f"\n\nTime: {timestamp}"

        # Send email
        return self.send_email(
            sender=sender,
            recipients=recipients,
            subject=subject,
            domain=domain,
            message=message,
            password=password,
            attachments=attachments,
            use_ntlm=use_ntlm,
            ntlm_compatibility=ntlm_compatibility,
        )


if __name__ == "__main__":
    email_password = os.getenv("PASSWORD")
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    email_sender = EmailSender(smtp_server=smtp_server, smtp_port=smtp_port)

    # # Send email
    # success = email_sender.send_email(
    #     sender="r10631039@g.ntu.edu.tw",
    #     recipients=["Tim_Wan@asrock.com.tw", "keepdling@gmail.com"],
    #     subject="ASRTranslator completed",
    #     message="Your attachment is ready and attached to this email.",
    #     password=email_password,
    #     attachments=[],
    #     use_ntlm=False,
    #     use_tls=True,
    # )

    # Send email using configuration file
    config = email_sender.load_config()
    success = email_sender.send_email_from_config(config)

    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")
