import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import dotenv

dotenv.load_dotenv()

# Create a multipart message object
msg = MIMEMultipart()

# Set the sender and recipient addresses
msg["From"] = "r10631039@g.ntu.edu.tw"
msg["To"] = "keepdling@gmail.com"
msg["Subject"] = "Test Email"
# Add the body of the message
message = "This is a test email"
msg.attach(MIMEText(message, "plain"))


with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
    try:
        smtp.ehlo()
        smtp.starttls()
        smtp.login("r10631039@g.ntu.edu.tw", os.getenv("PASSWORD"))
        smtp.send_message(msg)
        print("Email sent successfully")
    except Exception as e:
        print(e)
