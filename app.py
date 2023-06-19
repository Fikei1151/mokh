from flask_sqlalchemy import SQLAlchemy
from flask import flash, session
from flask import Flask, render_template, request, redirect, url_for, session
import os
from flask import jsonify
from dateutil.parser import parse
from flask_apscheduler import APScheduler # นำเข้า Flask-APScheduler
from datetime import datetime, date, timedelta
from collections import Counter
from collections import defaultdict
from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired
from models import User, Attendance, Leave,Holiday,DailyStatistics
from database import db
from statistics_api import daily_statistics, weekly_statistics, monthly_statistics, week_range, month_range
from api import *


statusUpdates = [] # ตรงนี้ครับยรย

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://Fikei1151:Fikree24@localhost/attendance'


db.init_app(app)
app.secret_key = os.urandom(24)
scheduler = APScheduler() 



class MonthForm(FlaskForm):
    month = SelectField('เลือกเดือน', choices=[], validators=[DataRequired()])


@app.route('/')
def home():
    return redirect(url_for('web_login'))

@app.route('/login', methods=['GET', 'POST'])
def web_login():
    if request.method == 'POST':
        id_card = request.form['id_card']
        password = request.form['password']
        user = User.query.get(id_card)
        if user and user.password == password:
            session['user_id'] = user.id_card
            flash('Logged in successfully.', 'success')

            if request.is_json:
                return jsonify({"result": "success", "username": user.name + ' ' + user.surname, "position": user.position})
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid ID card or password.', 'danger')

            if request.is_json:
                return jsonify({"result": "error"})
            else:
                return render_template('login.html')
    return render_template('login.html')

# หมดยาวๆ

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('web_login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        id_card = request.form['id_card']
        password = request.form['password']
        name = request.form['name']
        surname = request.form['surname']
        position = request.form['position']
        email = request.form['email']
        account_type = request.form['account_type']
        existing_user = User.query.get(id_card)
        if existing_user:
            flash('ID card already exists.', 'danger')
        else:
            new_user = User(id_card=id_card, password=password, name=name, surname=surname, position=position, email=email, account_type=account_type)  # กำหนดค่าใหม่
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.name, User.surname).paginate(page=page, per_page=10)
    counter_start = (page - 1) * 10 + 1

    for user in users.items:
        attendances = Attendance.query.filter_by(employee_id=user.id_card).all()
        user.absences = len([a for a in attendances if a.status == 'ขาด'])
        user.leaves = len([a for a in attendances if a.status == 'ลา'])
        user.late = len([a for a in attendances if a.status == 'สาย'])
        user.not_checked_out = len([a for a in attendances if a.check_out_timestamp is None])

        # Count approved leaves
        approved_leaves = Leave.query.filter_by(employee_id=user.id_card, status='อนุมัติ').count()
        user.approved_leaves = approved_leaves

    return render_template('index.html', users=users, page=page, counter_start=counter_start)




@app.route('/profile/<string:id_card>', methods=['GET', 'POST'])
def profile(id_card):
    user = User.query.get(id_card)
    if not user:
        return "User not found", 404

    if request.method == 'POST':
        new_account_type = request.form['account_type']
        user.account_type = new_account_type
        db.session.commit()
        flash('Account type updated.', 'success')

    attendances = Attendance.query.filter_by(employee_id=user.id_card).order_by(Attendance.check_in_timestamp.desc()).all()

    # Get leave records for the user
    leaves = Leave.query.filter_by(employee_id=user.id_card).all()

    # Add leaves to the template
    return render_template('profile.html', user=user, attendances=attendances, leaves=leaves)


@app.route('/delete_user/<string:id_card>', methods=['POST'])
def delete_user(id_card):
    user = User.query.get(id_card)
    if user:
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('index'))
    else:
        return "User not found", 404

@app.route('/holidays', methods=['GET', 'POST'])
def holidays():
    if request.method == 'POST':
        date = parse(request.form['date']).date()
        name = request.form['name']
        new_holiday = Holiday(date=date, name=name)
        db.session.add(new_holiday)
        db.session.commit()

    holidays = Holiday.query.order_by(Holiday.date).all()
    return render_template('holidays.html', holidays=holidays)

@app.route('/attendance', methods=['POST'])
def add_attendance():
    # รับข้อมูลจากแอพพลิเคชัน (ควรตรวจสอบความถูกต้องด้วย)
    id_card = request.form['id_card']
    timestamp = request.form['timestamp']
    status = request.form['status']

    new_attendance = Attendance(id_card=id_card, timestamp=timestamp, status=status)
    db.session.add(new_attendance)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/statistics', methods=['GET'])
def statistics():
    today = datetime.today().date()

    daily_stats = daily_statistics()
    weekly_stats = weekly_statistics() # no argument here
    monthly_stats = monthly_statistics() # no argument here

    return render_template('statistics.html', daily_stats=daily_stats, weekly_stats=weekly_stats, monthly_stats=monthly_stats)


def check_attendance():
    today = date.today()

    # ตรวจสอบว่าเป็นวันหยุดหรือไม่
    holiday = Holiday.query.filter_by(date=today).first()
    if holiday:
        # ถ้าเป็นวันหยุด ควรจะไม่ทำการตรวจสอบว่าพนักงานขาดงาน
        return

    users = User.query.all()
    daily_stats = DailyStatistics(date=today)

    for user in users:
        attendance = Attendance.query.filter_by(employee_id=user.id_card, check_in_timestamp=today).first()
        if not attendance:
            # User did not check in today, mark as absence
            absence = Attendance(employee_id=user.id_card, check_in_timestamp=today, status='ขาด')
            db.session.add(absence)
            daily_stats.total_absent += 1
        else:
            if attendance.status == 'สาย':
                daily_stats.total_late += 1
            if attendance.check_out_timestamp is None:
                daily_stats.total_not_checked_out += 1

    daily_stats.total_employees = len(users)
    db.session.add(daily_stats)
    db.session.commit()


# กำหนดการทำงานจัดตารางสำหรับการตรวจสอบการเข้างาน
# กำหนดการทำงานจัดตารางสำหรับการตรวจสอบการเข้างาน
# เพิ่ม job ใน scheduler ให้ทำงานในเวลา 00:01 น. ของวันจันทร์ถึงศุกร์
scheduler.add_job(id='attendance_check_job', func=check_attendance, trigger='cron', day_of_week='mon-fri', hour=18, minute=1)
scheduler.init_app(app)
scheduler.start()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    #app.run(host='0.0.0.0', port=5000)
    app.run(debug=True, port=5001)
    #app.run()

