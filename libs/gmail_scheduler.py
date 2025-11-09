# libs/gmail_scheduler.py
import os
import sys
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Add parent directory to path to import gmail_to_sheets
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import modules after path fix
try:
    from libs.gmail_to_sheets import (
        authenticate_gmail,
        authenticate_sheets,
        fetch_recent_emails,
        extract_email_data,
        match_student_uid,
        load_student_database,
        append_to_email_sheet,
        SHEET_ID
    )
except ImportError as e:
    print(f"Warning: Could not import gmail_to_sheets: {e}")
    print("Gmail sync capabilities disabled.")

    # Dummy fallback functions
    def authenticate_gmail(): return None
    def authenticate_sheets(): return None
    SHEET_ID = None


class GmailSyncScheduler:
    def __init__(self, sheet_name="Email"):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.last_sync_time = None
        self.last_sync_count = 0
        self.gmail_service = None
        self.sheets_client = None
        self.sheet_name = sheet_name

    def initialize_services(self):
        """Initialize Gmail + Sheets API once"""
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing services...")
            self.gmail_service = authenticate_gmail()
            self.sheets_client = authenticate_sheets()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Services initialized")
            return True
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Init error: {e}")
            return False

    def sync_emails(self):
        """Pull Gmail → append to Google Sheets"""
        try:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now}] === Syncing email ===")

            # Lazy init if needed
            if not self.gmail_service or not self.sheets_client:
                if not self.initialize_services():
                    return

            # Load student data
            student_cases_df = load_student_database(self.sheets_client, SHEET_ID)

            # Get Gmail messages
            messages = fetch_recent_emails(self.gmail_service, max_results=50)
            print(f"[{now}] Found {len(messages)} emails")

            # Process
            email_data_list = []
            for msg in messages:
                email_row = extract_email_data(msg, self.gmail_service)
                if email_row:
                    email_row["uid"] = match_student_uid(email_row["email"], student_cases_df)
                    email_data_list.append(email_row)

            # Append to GSheet
            if email_data_list:
                rows_added = append_to_email_sheet(
                    self.sheets_client,
                    SHEET_ID,
                    email_data_list,
                    sheet_name=self.sheet_name
                )
                self.last_sync_count = rows_added
                print(f"[{now}] ✓ Added {rows_added} rows")
            else:
                self.last_sync_count = 0
                print(f"[{now}] ✓ No new rows")

            self.last_sync_time = datetime.now()

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Sync error: {e}")
            import traceback
            traceback.print_exc()

    def start(self, interval_minutes=4):
        """Start background sync scheduler"""
        if not self.is_running:
            print(f"\n{'='*60}")
            print(f"Starting Gmail scheduler (every {interval_minutes} min)")
            print(f"{'='*60}")

            if self.initialize_services():
                # Run once immediately
                self.sync_emails()

                # Schedule recurring
                self.scheduler.add_job(
                    self.sync_emails,
                    'interval',
                    minutes=interval_minutes,
                    id='gmail_sync_job'
                )
                self.scheduler.start()
                self.is_running = True
                print("✓ Scheduler started")
            else:
                print("✗ Could not start scheduler")

    def stop(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print("Scheduler stopped")

    def get_status(self):
        """Return current status of scheduler"""
        next_run = None
        if self.is_running:
            try:
                job = self.scheduler.get_job('gmail_sync_job')
                if job:
                    next_run = job.next_run_time
            except:
                pass

        return {
            "is_running": self.is_running,
            "last_sync_time": self.last_sync_time,
            "last_sync_count": self.last_sync_count,
            "next_run_time": next_run,
        }


# Singleton
_scheduler = None

def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = GmailSyncScheduler()
    return _scheduler
