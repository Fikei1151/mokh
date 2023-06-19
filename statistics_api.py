from flask import Flask, jsonify, request
from models import Attendance, User, Leave
from sqlalchemy import func, extract, and_, or_
from database import db
import calendar
from datetime import datetime, timedelta
from flask import render_template
from sqlalchemy import text

app = Flask(__name__)

def week_range(date=None):
    if date is None:
        date = datetime.now().date()
    start_date = date - timedelta(days=date.isoweekday() % 7)
    end_date = start_date + timedelta(days=6)
    return start_date, end_date

def month_range(date=None):
    if date is None:
        date = datetime.now().date()
    _, num_days = calendar.monthrange(date.year, date.month)
    start = date.replace(day=1)
    end = date.replace(day=num_days)
    return start, end

@app.route('/statistics/daily', methods=['GET'])
def daily_statistics():
    today = datetime.now().date()

    total_attendance = Attendance.query.filter(func.date(Attendance.check_in_timestamp)==today).count()
    total_late = Attendance.query.filter(and_(func.date(Attendance.check_in_timestamp)==today, Attendance.status=='สาย')).count()
    total_absent = Attendance.query.filter(and_(func.date(Attendance.check_in_timestamp)==today, Attendance.status=='absent')).count()
    total_no_checkout = Attendance.query.filter(and_(func.date(Attendance.check_in_timestamp)==today, Attendance.check_out_timestamp.is_(None))).count()
    total_leave = Leave.query.filter(and_(Leave.start_date<=today, Leave.end_date>=today, Leave.status=='อนุมัติ')).count()

    top_5_late = (db.session.query(Attendance.employee_id, func.count(Attendance.id).label('count'))
                  .filter(and_(func.date(Attendance.check_in_timestamp)==today, Attendance.status=='สาย'))
                  .group_by(Attendance.employee_id)
                  .order_by(db.desc('count'))
                  .limit(5)
                  .all())

    return {
        'date': today.strftime('%Y-%m-%d'),
        'total_attendance': total_attendance,
        'total_late': total_late,
        'total_absent': total_absent,
        'total_no_checkout': total_no_checkout,
        'total_leave': total_leave,
        'top_5_late': [dict(employee_id=i[0], late_count=i[1]) for i in top_5_late]
    }

@app.route('/statistics/weekly', methods=['GET'])
def weekly_statistics():
    today = datetime.now().date()
    start_of_week, end_of_week = week_range(today)

    total_attendance = Attendance.query.filter(Attendance.check_in_timestamp.between(start_of_week, end_of_week)).count()
    total_late = Attendance.query.filter(and_(Attendance.check_in_timestamp.between(start_of_week, end_of_week), Attendance.status=='สาย')).count()
    total_absent = Attendance.query.filter(and_(Attendance.check_in_timestamp.between(start_of_week, end_of_week), Attendance.status=='absent')).count()
    total_no_checkout = Attendance.query.filter(and_(Attendance.check_in_timestamp.between(start_of_week, end_of_week), Attendance.check_out_timestamp.is_(None))).count()
    total_leave = Leave.query.filter(and_(Leave.start_date.between(start_of_week, end_of_week), Leave.status=='อนุมัติ')).count()


    top_5_late = (db.session.query(Attendance.employee_id, func.count(Attendance.id).label('count'))
                  .filter(and_(Attendance.check_in_timestamp.between(start_of_week, end_of_week), Attendance.status=='สาย'))
                  .group_by(Attendance.employee_id)
                  .order_by(db.desc('count'))
                  .limit(5)
                  .all())

    return jsonify({
        'week': f'{start_of_week.strftime("%Y-%m-%d")} - {end_of_week.strftime("%Y-%m-%d")}',
        'total_attendance': total_attendance,
        'total_late': total_late,
        'total_absent': total_absent,
        'total_no_checkout': total_no_checkout,
        'total_leave': total_leave,
        'top_5_late': [dict(employee_id=i[0], late_count=i[1]) for i in top_5_late]
    })

@app.route('/statistics/monthly', methods=['GET'])
def monthly_statistics():
    today = datetime.now().date()
    start_of_month, end_of_month = month_range(today)

    total_attendance = Attendance.query.filter(Attendance.check_in_timestamp.between(start_of_month, end_of_month)).count()
    total_late = Attendance.query.filter(and_(Attendance.check_in_timestamp.between(start_of_month, end_of_month), Attendance.status=='สาย')).count()
    total_absent = Attendance.query.filter(and_(Attendance.check_in_timestamp.between(start_of_month, end_of_month), Attendance.status=='absent')).count()
    total_no_checkout = Attendance.query.filter(and_(Attendance.check_in_timestamp.between(start_of_month, end_of_month), Attendance.check_out_timestamp.is_(None))).count()
    total_leave = Leave.query.filter(and_(Leave.start_date.between(start_of_month, end_of_month), Leave.status=='อนุมัติ')).count()

    top_5_late = (db.session.query(Attendance.employee_id, func.count(Attendance.id).label('count'))
                  .filter(and_(Attendance.check_in_timestamp.between(start_of_month, end_of_month), Attendance.status=='สาย'))
                  .group_by(Attendance.employee_id)
                  .order_by(db.desc('count'))
                  .limit(5)
                  .all())

    return jsonify({
        'month': start_of_month.strftime('%Y-%m'),
        'total_attendance': total_attendance,
        'total_late': total_late,
        'total_absent': total_absent,
        'total_no_checkout': total_no_checkout,
        'total_leave': total_leave,
        'top_5_late': [dict(employee_id=i[0], late_count=i[1]) for i in top_5_late]
    })

