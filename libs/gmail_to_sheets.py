# gmail_to_sheets.py
import os
import base64
import json
import toml
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
import pandas as pd
from email.utils import parsedate_to_datetime

# Gmail API scopes
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Google Sheets API scopes
SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
                 'https://www.googleapis.com/auth/drive']

# Load configuration from secrets.toml
def load_config():
    """Load configuration from .streamlit/secrets.toml"""
    # Try multiple possible locations
    possible_paths = [
        '.streamlit/secrets.toml',
        '../.streamlit/secrets.toml',
        'secrets.toml',
        os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config = toml.load(f)
                print(f"✓ Loaded config from: {path}")
                return config
            except Exception as e:
                print(f"Error reading {path}: {e}")
                continue
    
    print("Error: secrets.toml not found!")
    print("Searched in:", possible_paths)
    exit(1)

config = load_config()
SHEET_ID = config.get("SHEET_ID")
ALLOWED_DOMAINS = ['umd.edu', 'terpmail.umd.edu']


def authenticate_gmail():
    """Authenticate and return Gmail API service using OAuth from secrets.toml."""
    creds = None
    
    # Check if we have a saved token
    token_path = os.path.join(os.path.dirname(__file__), '..', 'gmail_token.json')
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, GMAIL_SCOPES)
    
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Create OAuth config from secrets.toml
            gmail_oauth = config.get('gmail_oauth', {})
            if not gmail_oauth:
                print("Error: gmail_oauth section missing in secrets.toml")
                print("Please add Gmail OAuth credentials to your secrets.toml")
                exit(1)
            
            client_config = {
                "installed": {
                    "client_id": gmail_oauth.get('client_id'),
                    "client_secret": gmail_oauth.get('client_secret'),
                    "redirect_uris": gmail_oauth.get('redirect_uris', ["http://localhost"]),
                    "auth_uri": gmail_oauth.get('auth_uri', "https://accounts.google.com/o/oauth2/auth"),
                    "token_uri": gmail_oauth.get('token_uri', "https://oauth2.googleapis.com/token"),
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }
            }
            
            flow = InstalledAppFlow.from_client_config(client_config, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)


def authenticate_sheets():
    """Authenticate and return Google Sheets client using service account from secrets.toml."""
    service_account_info = config.get('gcp_service_account', {})
    
    if not service_account_info:
        print("Error: gcp_service_account section missing in secrets.toml")
        exit(1)
    
    creds = ServiceAccountCredentials.from_service_account_info(
        service_account_info, 
        scopes=SHEETS_SCOPES
    )
    return gspread.authorize(creds)


def get_email_body(payload):
    """Extract email body from message payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break
            elif part['mimeType'] == 'text/html' and not body:
                if 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            # Handle nested parts (multipart/alternative, etc.)
            elif 'parts' in part:
                nested_body = get_email_body(part)
                if nested_body:
                    body = nested_body
                    break
    else:
        if 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    
    return body.strip()


def extract_email_data(message, service):
    """Extract relevant data from a Gmail message."""
    try:
        msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        
        headers = msg['payload']['headers']
        header_dict = {h['name'].lower(): h['value'] for h in headers}
        
        # Extract sender email
        sender = header_dict.get('from', '')
        email_address = sender.split('<')[-1].strip('>') if '<' in sender else sender
        sender_name = sender.split('<')[0].strip().strip('"') if '<' in sender else email_address.split('@')[0]
        
        # Check if sender is from allowed domains
        domain = email_address.split('@')[-1] if '@' in email_address else ''
        if not any(allowed in domain for allowed in ALLOWED_DOMAINS):
            return None  # Skip non-UMD emails
        
        # Extract date
        date_str = header_dict.get('date', '')
        try:
            email_date = parsedate_to_datetime(date_str)
            date_only = email_date.strftime('%Y-%m-%d')
            time_only = email_date.strftime('%H:%M:%S')
        except:
            date_only = datetime.now().strftime('%Y-%m-%d')
            time_only = datetime.now().strftime('%H:%M:%S')
        
        # Extract subject and body
        subject = header_dict.get('subject', '(No Subject)')
        body = get_email_body(msg['payload'])
        
        return {
            'name': sender_name,
            'email': email_address,
            'uid': None,  # Will be filled by matching with student database
            'time': time_only,
            'date': date_only,
            'subject': subject,
            'content': body[:2000]  # Limit content length to avoid sheet size issues
        }
    
    except Exception as e:
        print(f"Error extracting email data for message {message.get('id')}: {e}")
        return None


def match_student_uid(email_address, student_cases_df):
    """Match email to student UID from the student database."""
    if student_cases_df is None or student_cases_df.empty:
        return None
    
    # Try to match by email (case-insensitive)
    match = student_cases_df[student_cases_df['Email'].str.lower() == email_address.lower()]
    if not match.empty:
        return str(match.iloc[0]['UID'])
    
    return None


def fetch_recent_emails(service, max_results=100):
    """Fetch recent emails from Gmail."""
    try:
        # Build query for UMD emails - look for emails in last 7 days
        query = f"({' OR '.join([f'from:*@{domain}' for domain in ALLOWED_DOMAINS])}) newer_than:7d"
        
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        return messages
    
    except HttpError as error:
        print(f"An error occurred fetching emails: {error}")
        return []


def load_student_database(gc, sheet_id):
    """Load student cases from Google Sheet."""
    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet("Student Case")
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error loading student database: {e}")
        return pd.DataFrame()


def append_to_email_sheet(gc, sheet_id, email_data_list):
    """Append new emails to the 'Email' sheet in Google Sheets."""
    try:
        sh = gc.open_by_key(sheet_id)
        
        # Try to open the "Email" sheet, create if doesn't exist
        try:
            worksheet = sh.worksheet("Email")
            print("Found existing 'Email' sheet")
        except:
            print("Creating new 'Email' sheet...")
            worksheet = sh.add_worksheet(title="Email", rows="1000", cols="10")
            # Add headers
            headers = ['Name', 'Email', 'UID', 'Time', 'Date', 'Subject', 'Content']
            worksheet.append_row(headers)
        
        # Get existing emails to avoid duplicates
        existing_data = worksheet.get_all_records()
        existing_df = pd.DataFrame(existing_data)
        
        # Append new emails
        rows_added = 0
        for email_data in email_data_list:
            # Check if email already exists (by email, date, and subject)
            if not existing_df.empty:
                duplicate = existing_df[
                    (existing_df['Email'].astype(str).str.lower() == email_data['email'].lower()) &
                    (existing_df['Date'].astype(str) == email_data['date']) &
                    (existing_df['Subject'].astype(str) == email_data['subject'])
                ]
                if not duplicate.empty:
                    print(f"  Skipping duplicate: {email_data['subject'][:50]}...")
                    continue  # Skip duplicate
            
            row = [
                email_data['name'],
                email_data['email'],
                email_data['uid'] or '',
                email_data['time'],
                email_data['date'],
                email_data['subject'],
                email_data['content']
            ]
            worksheet.append_row(row)
            rows_added += 1
            print(f"  Added: {email_data['subject'][:50]}... from {email_data['email']}")
        
        return rows_added
    
    except Exception as e:
        print(f"Error appending to sheet: {e}")
        return 0


def main():
    """Main function to sync Gmail to Google Sheets."""
    print("=" * 60)
    print("Gmail to Google Sheets Sync")
    print("=" * 60)
    
    print("\n[1/5] Authenticating with Gmail...")
    gmail_service = authenticate_gmail()
    print("✓ Gmail authenticated")
    
    print("\n[2/5] Authenticating with Google Sheets...")
    sheets_client = authenticate_sheets()
    print("✓ Google Sheets authenticated")
    
    print("\n[3/5] Loading student database...")
    student_cases_df = load_student_database(sheets_client, SHEET_ID)
    print(f"✓ Loaded {len(student_cases_df)} student records")
    
    print("\n[4/5] Fetching recent emails from UMD domains...")
    messages = fetch_recent_emails(gmail_service, max_results=100)
    print(f"✓ Found {len(messages)} emails from UMD domains (last 7 days)")
    
    # Process emails
    email_data_list = []
    print("\n[5/5] Processing emails...")
    for i, message in enumerate(messages, 1):
        print(f"  Processing email {i}/{len(messages)}...", end='\r')
        email_data = extract_email_data(message, gmail_service)
        if email_data:
            # Match UID from student database
            email_data['uid'] = match_student_uid(email_data['email'], student_cases_df)
            email_data_list.append(email_data)
    
    print(f"\n✓ Successfully processed {len(email_data_list)} valid emails")
    
    # Append to Google Sheet
    if email_data_list:
        print(f"\nAppending to 'Email' sheet in Google Sheets...")
        rows_added = append_to_email_sheet(sheets_client, SHEET_ID, email_data_list)
        print(f"\n{'=' * 60}")
        print(f"✓ COMPLETE: Added {rows_added} new emails to 'Email' sheet")
        print(f"{'=' * 60}")
    else:
        print("\n! No new emails to add (all may be duplicates)")


if __name__ == "__main__":
    main()