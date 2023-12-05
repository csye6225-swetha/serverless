# Project Title: Lambda Function for Email and File Processing

## Overview
This project includes a Python script designed to be deployed as an AWS Lambda function. It integrates various services such as AWS DynamoDB, Google Cloud Storage, and Mailgun to process messages, store files, and send emails.

## Environment Variables
The script requires the following environment variables:
- `DYNAMODB_TABLE_NAME`: Name of the DynamoDB table.
- `GCP_SERVICE_ACCOUNT_KEY_JSON`: Base64 encoded JSON key for Google Cloud Storage.
- `GCP_STORAGE_BUCKET_NAME`: Name of the Google Cloud Storage bucket.
- `MAILGUN_API_KEY`: API key for Mailgun.
- `MAILGUN_DOMAIN`: Domain for Mailgun.

## Prerequisites
- AWS account with access to Lambda and DynamoDB.
- Google Cloud account with a configured storage bucket.
- Mailgun account with a valid domain and API key.
- Python 3.x.

## Deployment
1. Install required AWS and Google Cloud Python packages.
2. Set up the necessary environment variables.
3. Deploy the script to AWS Lambda.
4. Configure an event source for the Lambda function, such as AWS SNS.

