import smtplib
import pandas as pd
from email.message import EmailMessage
import os
import mimetypes
from datetime import datetime
import csv

# CSV path
csv_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/email_list.csv"
data = pd.read_csv(csv_path)

# Gmail credentials
EMAIL_ADDRESS = 'chiragkhanduja786@gmail.com'
EMAIL_PASSWORD = 'ibbe sacy xfxu olfe'  # App Password

# Attachment file (resume)
attachment_path = '/Users/chiragkhanduja/PycharmProjects/PythonProject11/Chirag_Khanduja_Sr_QA_SDET_AI_Resume_Latest.pdf'
if not os.path.isfile(attachment_path):
    raise FileNotFoundError(f"Attachment not found: {attachment_path}")

# Email body (same for all)
email_body = """\
Dear Hiring Manager,

I am thrilled to submit my application for the Senior QA Engineer role. With more than 3 years of experience in quality assurance and software testing, I have honed my skills in both manual and automated testing methodologies.

My proficiency encompasses tools like Selenium, Robot Framework, Postman, TestNG, Locust (for load testing), and JIRA. I possess practical experience in test planning, execution, automation of regression and API tests, and effective defect management within agile settings. In my past positions, my contributions have significantly enhanced product quality, expanded automation coverage, and ensured dependable, scalable releases.

I am confident that my technical expertise and process-oriented mindset can bring value to your QA team. Please find my resume attached for your review, and I am open to further discussions at your convenience.

Thank you for your time and consideration.

Sincerely,
Chirag Khanduja
9034226868
"""

# Setup SMTP server
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

emails_sent = 0

# Loop through recipients and send emails
for index, row in data.iterrows():
    msg = EmailMessage()
    # Add [Job Application] label prefix to subject for easy Gmail filtering/labeling
    msg['Subject'] = '[Job Application] Application for Senior QA Engineer Role'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = row['Email']
    msg.set_content(email_body)

    # Optional: Add a custom header for filtering (will be ignored by Gmail for native labels, but filterable)
    msg['X-Job-Label'] = 'Job Application'

    # Add attachment
    mime_type, _ = mimetypes.guess_type(attachment_path)
    mime_type = mime_type or 'application/octet-stream'
    maintype, subtype = mime_type.split('/')

    with open(attachment_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))

    try:
        server.send_message(msg)
        print(f"✅ Email sent to {row['Email']}")
        emails_sent += 1
    except Exception as e:
        print(f"❌ Failed to send email to {row['Email']}: {e}")

server.quit()

# === LOG EMAIL COUNT DATE-WISE ===
log_file = '/Users/chiragkhanduja/PycharmProjects/PythonProject11/email_log.csv'
today = datetime.now().strftime("%Y-%m-%d")

# If log exists, update today's row or append
if os.path.exists(log_file):
    with open(log_file, "r", newline="") as f:
        reader = list(csv.reader(f))

    found = False
    for i in range(1, len(reader)):
        if reader[i][0] == today:
            current_count = int(reader[i][1])
            reader[i][1] = str(current_count + emails_sent)
            found = True
            break

    if not found:
        reader.append([today, str(emails_sent)])

    with open(log_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(reader)

else:
    with open(log_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "EmailsSent"])
        writer.writerow([today, emails_sent])

print(f"\n📅 Total emails sent today ({today}): {emails_sent} — logged in email_log.csv")
