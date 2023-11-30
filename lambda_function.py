import os
import boto3
import json
import base64
import requests
import re
from botocore.exceptions import ClientError
from google.cloud import storage
from google.oauth2 import service_account

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['DYNAMODB_TABLE_NAME']
table = dynamodb.Table(table_name)


encoded_key = os.environ['GCP_SERVICE_ACCOUNT_KEY_JSON']
decoded_key_json = base64.b64decode(encoded_key).decode('utf-8')

gcp_credentials_json = json.loads(decoded_key_json)
gcp_credentials = service_account.Credentials.from_service_account_info(gcp_credentials_json)

gcp_client = storage.Client(credentials=gcp_credentials, project=gcp_credentials.project_id)
bucket_name = os.environ['GCP_STORAGE_BUCKET_NAME']
bucket = gcp_client.bucket(bucket_name)


MAILGUN_API_KEY = os.environ['MAILGUN_API_KEY']
MAILGUN_DOMAIN = os.environ['MAILGUN_DOMAIN']


def extract_email(text):
    """
    Extract an email address from a text using regular expressions.
    """
    # Regular expression pattern for extracting email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    matches = re.findall(email_pattern, text)
    if matches:
        return matches[0]  # Return the first email address found
    else:
        return None  # Return None if no email address is found

def send_email(to_email, subject, message):
    """
    Send an email using Mailgun.
    """
    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": "your_email@example.com",
                "to": to_email,
                "subject": subject,
                "text": message,
            },
        )
        response.raise_for_status()
        return True  # Email sent successfully
    except Exception as e:
        print(f"Error sending email: {e}")
        return False  # Email sending failed


def download_file(url):
    """
    Download a file from a given URL.
    """
    local_filename = '/tmp/' + url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def is_zip_file(filename):
    """
    Check if a file is a ZIP file based on its file extension.
    """
    return filename.lower().endswith('.zip')


def lambda_handler(event, context):
    # Iterate over each record
    for record in event['Records']:
        sns_message = record['Sns']
        message_id = sns_message['MessageId']
        message = sns_message['Message']

        url = re.search("(https?://[^\s]+)", message).group(0)

        email = extract_email(message)


        if email:
            # Prepare the item to insert into DynamoDB
            item = {
                'MessageId': message_id,
                'Message': message,
                'URL': url,
                'Email': email,
                'EmailSent': False  # Initialize the 'EmailSent' attribute as False
            }

            # Insert the item into DynamoDB
            try:
                response = table.put_item(Item=item)
            except ClientError as e:
                print(e.response['Error']['Message'])
                send_email("recipient@example.com", "DynamoDB Error", f"Error storing data in DynamoDB: {e}")

     


        try:
                filename = download_file(url)

                # Check if the file is a ZIP file
                if is_zip_file(filename):
                    # Upload the downloaded ZIP file to GCP Storage
                    blob = bucket.blob(f"{message_id}/{filename}")
                    blob.upload_from_filename(filename)

                    # If the ZIP file is successfully stored in GCP bucket, send a success email with the GCS object URL
                    gcs_object_url = f"https://storage.googleapis.com/{bucket_name}/{message_id}/{filename}"
                    email_sent = send_email(email, "File Stored Successfully", f"The ZIP file {filename} is stored in GCP bucket. URL: {gcs_object_url}")

                    # Update the 'EmailSent' attribute in DynamoDB based on whether the email was sent
                    if email_sent:
                        table.update_item(
                            Key={'MessageId': message_id},
                            UpdateExpression="SET EmailSent = :sent",
                            ExpressionAttributeValues={':sent': True}
                        )
                else:
                    # If the file is not a ZIP file, handle it accordingly
                    email_sent = send_email(email, "File Type Error", f"The file {filename} is not a ZIP file and was not stored.")
                    if email_sent:
                        table.update_item(
                            Key={'MessageId': message_id},
                            UpdateExpression="SET EmailSent = :sent",
                            ExpressionAttributeValues={':sent': True}
                        )
            except Exception as e:
                print(f"Error uploading to GCP Storage: {e}")
                send_email(email, "File Storage Error", f"Error storing the file {filename} in GCP bucket: {e}")
                if email_sent:
                        table.update_item(
                            Key={'MessageId': message_id},
                            UpdateExpression="SET EmailSent = :sent",
                            ExpressionAttributeValues={':sent': True}
                        )

    return "Success"

