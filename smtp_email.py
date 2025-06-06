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
import spnego

dotenv.load_dotenv()


class EmailSender:
    def __init__(self, smtp_server: str, smtp_port: int) -> None:
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def _ntlm_auth_with_pyspnego(
        self, smtp: smtplib.SMTP, username: str, password: str, domain: str
    ) -> bool:
        try:
            # create NTLM context
            context = spnego.client(
                username=f"{domain}\\{username}" if domain else username,
                password=password,
                protocol="ntlm",
            )

            # send AUTH NTLM command
            smtp.docmd("AUTH", "NTLM")

            # first step: send negotiate message
            negotiate_token = context.step()
            negotiate_b64 = base64.b64encode(negotiate_token).decode("ascii")

            code, challenge_b64 = smtp.docmd("", negotiate_b64)
            if code != 334:
                raise Exception(f"NTLM negotiate failed: {code}")

            # second step: process challenge and authenticate
            challenge_token = base64.b64decode(challenge_b64)
            auth_token = context.step(challenge_token)
            auth_b64 = base64.b64encode(auth_token).decode("ascii")

            code, response = smtp.docmd("", auth_b64)
            if code != 235:
                raise Exception(f"NTLM authentication failed: {code}")

            return True
        except Exception as e:
            print(f"NTLM authentication error: {e}")
            return False

    def send_email(
        self,
        sender: str | None = None,
        recipients: list[str] | None = None,
        subject: str | None = None,
        message: str | None = None,
        domain: str | None = None,
        password: str | None = None,
        attachments: list[str] | None = None,
        use_ntlm: bool = False,
        include_timestamp: bool = False,
        config: dict | None = None,
    ) -> bool:
        """
        Send an email using SMTP. Can use either direct parameters or a config dictionary.

        Args:
            sender (str): Sender email address
            recipients (list): List of recipient email addresses
            subject (str): Email subject
            message (str): Email body content
            domain (str): Domain for NTLM authentication
            password (str, optional): Email password. If None, will use PASSWORD from env
            attachments (list, optional): List of file paths to attach
            use_ntlm (bool): Whether to use NTLM authentication (default: False)
            include_timestamp (bool): Whether to include timestamp in the email body (default: False)
            config (dict, optional): Configuration dictionary that overrides other parameters
        """
        # If config is provided, override parameters
        if config:
            self.smtp_server = config.get("smtp_server", self.smtp_server)
            self.smtp_port = config.get("smtp_port", self.smtp_port)
            sender = config.get("sender", sender)
            recipients = config.get("recipients", recipients)
            subject = config.get("subject", subject)
            message = config.get("message", message)
            domain = config.get("domain", domain)
            password = config.get("password", password)
            attachments = config.get("attachments", attachments)
            use_ntlm = config.get("use_ntlm", use_ntlm)

            # Add timestamp if requested in config
            if config.get("include_timestamp", False):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message += f"\n\nTime: {timestamp}"

        if include_timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message += f"\n\nTime: {timestamp}"

        # Validate required fields
        if not sender:
            print("Error: sender is required")
            return False
        if not recipients:
            print("Error: recipients list is required")
            return False
        if not subject:
            print("Error: subject is required")
            return False
        if not message:
            print("Error: message is required")
            return False

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
                    if not self._ntlm_auth_with_pyspnego(
                        smtp,
                        sender,
                        password,
                        domain,
                    ):
                        return False
                else:
                    smtp.login(sender, password)

                smtp.send_message(msg)
                return True
            except Exception as e:
                print(f"Failed to send email: {e}")
                return False

    def load_config(self, config_path: str = None) -> dict | None:
        """
        Load email configuration from JSON file

        Args:
            config_path (str): Path to the configuration file

        Returns:
            dict: Configuration dictionary
        """
        try:
            if config_path is None:
                return None

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


if __name__ == "__main__":
    email_sender = EmailSender(
        smtp_server="smtp.gmail.com",  # default, can be overridden by config
        smtp_port=587,  # default, can be overridden by config
    )

    # Send email with direct parameters
    success = email_sender.send_email(
        sender="r10631039@g.ntu.edu.tw",
        recipients=["Tim_Wan@asrock.com.tw", "keepdling@gmail.com"],
        subject="ASRTranslator completed",
        message="Your attachment is ready and attached to this email.",
        domain="",
        password=os.getenv("PASSWORD"),
        attachments=["email_config.json"],
        use_ntlm=False,
        include_timestamp=True,
        config=None,
    )

    # # Load config from file
    # config_json = email_sender.load_config(config_path="email_config.json")
    # # Send email with config
    # success = email_sender.send_email(config=config_json)

    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")
