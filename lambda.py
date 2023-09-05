import boto3
import json
import os

#The send_email function is going to handle the AWS SES email sending to the specified email addresses

def send_email(sender_email, recipient_emails, s3_url):
    #Email configuration
    ses_client = boto3.client('ses')
    subject = 'BalFolder'
    message = f'A file has been shared with you. You can download it using the link below:\n\n{s3_url}\n\n Best, \n\n BalFolder Team'
    #AWS SNS config for the email sending.
    for recipient_email in recipient_emails:
        ses_client.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [recipient_email]
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Text': {
                        'Data': message
                    }
                }
            }
        )
#This function handles the lambda event that will be taking place. In this case, the trigger on the "balfolder" s3 bucket will prompt the lambda event to begin tp send the email out.
def lambda_handler(event, context):
    recipient_emails = event['recipient_emails'][:5] 
    recipient_emails = [email.strip() for email in recipient_emails] 
    #"balfolder@gmail.com" is an email address I created for the project. I cleared this address through AWS SES for email sending
    sender_email = 'balfolder@gmail.com'  
    s3_url = f'https://{event["s3_bucket"]}.s3.amazonaws.com/{event["s3_object_key"]}'
    #finally, this sends the email out.
    send_email(sender_email, recipient_emails, s3_url)
    return {
        'statusCode': 200,
        'body': json.dumps('Emails sent successfully!')
    }
