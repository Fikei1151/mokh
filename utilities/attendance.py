from datetime import datetime, timedelta
from models import User, Attendance, Leave,Holiday,DailyStatistics,JobRun
from database import db
from flask_migrate import Migrate
from sqlalchemy import func
from pytz import timezone  # Import this
import pytz
from threading import Lock

lock = Lock()
bangkok_tz = pytz.timezone('Asia/Bangkok')

def check_attendance():
    from app import app
    with lock, app.app_context():
        print("Checking attendance...")
        now = datetime.now(bangkok_tz)

        # Check if it's a holiday
        holiday = Holiday.query.filter_by(date=now.date()).first()
        if holiday:
            # If it's a holiday, don't check for absence
            print(f"Today {now.date()} is a holiday, skipping attendance check")
            return

        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
        
        users = User.query.all()

        for user in users:
            attendance = Attendance.query.filter_by(employee_id=user.id_card).filter(func.date(Attendance.check_in_timestamp) == now.date()).first()
            if not attendance:
                # User did not check in today, mark as absence
                absence = Attendance(employee_id=user.id_card, check_in_timestamp=start_of_day, check_out_timestamp=end_of_day, status='ขาด')
                db.session.add(absence)
                print(f"User {user.id_card} is absent")
        db.session.commit()
        print(f"Finished checking attendance for {now.date()}")

        pass