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
import urllib.parse


statusUpdates = [] # ตรงนี้ครับยรย

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://Fikei1151:Fikree24@localhost/attendance'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://Fikei1151:Fikree24@localhost:5432/attendance'

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

@app.route('/api/login', methods=['POST'])
def app_login():

    id_card = request.json['id_card']
    password = request.json['password']
    user = User.query.get(id_card)
    session['id_card'] = id_card
    if user and user.password == password:
        return jsonify({
            "result": "success", 
            "username": user.name + ' ' + user.surname, 
            "position": user.position, 
            "account_type": user.account_type  # Add this line
        })
    else:
        return jsonify({"result": "error"})

    


@app.route('/api/checkin', methods=['POST'])
def checkin():
    id_card = request.json.get('id_card', None)
    print("Received id_card: ", id_card)
    if id_card is None:
        return jsonify({"error": "Missing id_card"}), 400

    employee = User.query.get(id_card)

    if employee is None:
        return jsonify({"error": "Employee not found"}), 404

    check_in_timestamp = datetime.now()

    # Define the work start time as 7:00 and late check-in threshold as 8:00.
    work_start_time = check_in_timestamp.replace(hour=14, minute=20, second=0, microsecond=0)
    late_threshold = check_in_timestamp.replace(hour=14, minute=30, second=0, microsecond=0)

    # If current time is earlier than work start time, return error.
    if check_in_timestamp < work_start_time:
        return jsonify({"error": "Too early to check in"}), 400

    status = "สาย" if check_in_timestamp > late_threshold else "มา"

    attendance = Attendance(
        employee_id=employee.id_card,
        check_in_timestamp=check_in_timestamp,
        status=status
    )
    db.session.add(attendance)
    db.session.commit()

    return jsonify({"message": "Checked in successfully"}), 200

@app.route('/api/checkout', methods=['POST'])
def checkout():
    id_card = request.json.get('id_card', None)
    if id_card is None:
        return jsonify({"error": "Missing id_card"}), 400

    employee = User.query.get(id_card)
    if employee is None:
        return jsonify({"error": "Employee not found"}), 404

    check_out_timestamp = datetime.now()

    # Define the work end time window as 16:00 to 17:00.
    work_end_start_time = check_out_timestamp.replace(hour=14, minute=35, second=0, microsecond=0)
    work_end_end_time = check_out_timestamp.replace(hour=23, minute=0, second=0, microsecond=0)

    # If current time is not within work end time window, return error.
    if not (work_end_start_time <= check_out_timestamp <= work_end_end_time):
        return jsonify({"error": "Not within work end time window"}), 400

    attendance = Attendance.query.filter_by(employee_id=employee.id_card).order_by(Attendance.check_in_timestamp.desc()).first()
    if attendance is None or attendance.check_out_timestamp is not None:
        return jsonify({"error": "Invalid check out"}), 400

    attendance.check_out_timestamp = check_out_timestamp
    db.session.commit()

    return jsonify({"message": "Checked out successfully"}), 200

@app.route('/api/checkin_shift', methods=['POST'])
def checkin_shift():
    try:
        employee_id = request.json['employee_id']
        timestamp = parse(request.json['timestamp']) # parse timestamp
        new_attendance = Attendance(id_card=employee_id, timestamp=timestamp, status="เข้าเวร")
        db.session.add(new_attendance)
        db.session.commit()
        return {"message": "success"}, 200
    except Exception as e:
        print(e)
        return {"message": "error"}, 400
@app.route('/api/attendance_history/<string:id_card>', methods=['GET'])
def attendance_history(id_card):
    attendances = Attendance.query.filter_by(id_card=id_card).order_by(Attendance.timestamp.desc()).all()
    attendance_data = [{"id": attendance.id, "id_card": attendance.id_card, "timestamp": attendance.timestamp.isoformat(), "status": attendance.status} for attendance in attendances]
    return jsonify({"attendance_history": attendance_data})


@app.route('/api/leave_request', methods=['POST'])
def leave_request():
    try:
        employee_id = request.json['employee_id']
        start_date = parse(request.json['start_date'])
        end_date = parse(request.json['end_date'])
        leave_type = request.json['leave_type']
        reason = request.json['reason']

        new_leave = Leave(employee_id=employee_id, start_date=start_date, end_date=end_date, leave_type=leave_type, reason=reason, status='รออนุมัติ')
        db.session.add(new_leave)
        db.session.commit()

        return jsonify(new_leave.to_dict()), 200
    except Exception as e:
        print(e)
        return {"message": "error"}, 400


@app.route('/api/user_leaves/<string:employee_id>', methods=['GET'])
def user_leaves(employee_id):
    leaves = db.session.query(Leave, User.name, User.surname).join(User, User.id_card == Leave.employee_id).filter(Leave.employee_id == employee_id).all()
    leaves_data = [{"id": leave.Leave.id, "employee_id": leave.Leave.employee_id, "employee_name": leave.name + ' ' + leave.surname, "start_date": leave.Leave.start_date, "end_date": leave.Leave.end_date, "leave_type": leave.Leave.leave_type, "status": leave.Leave.status} for leave in leaves]
    return jsonify({"leaves": leaves_data})



@app.route('/api/pending_leaves', methods=['GET'])
def pending_leaves():
    leaves = db.session.query(Leave, User.name, User.surname).join(User, User.id_card == Leave.employee_id).filter(Leave.status == 'รออนุมัติ').all()
    leaves_data = [{
        "id": leave[0].id, 
        "employee_id": leave[0].employee_id, 
        "employee_name": leave[1] + ' ' + leave[2], 
        "start_date": leave[0].start_date, 
        "end_date": leave[0].end_date, 
        "leave_type": leave[0].leave_type,
        "reason": leave[0].reason,
        "status": leave[0].status
    } for leave in leaves]

    return jsonify({"leaves": leaves_data})

@app.route('/api/get_user/<string:id_card>', methods=['GET'])
def get_user(id_card):
    user = User.query.get(id_card)
    if user:
        return jsonify({
            "id_card": user.id_card,
            "password": user.password, 
            "name": user.name,
            "surname": user.surname,
            "position": user.position,
            "email": user.email,
            "account_type": user.account_type,
        })
    else:
        return jsonify({"error": "User not found"}), 404


@app.route('/api/update_leave_status', methods=['PATCH'])
def update_leave_status():
    leave_id = request.json['leave_id']
    status = request.json['status']

    leave = Leave.query.get(leave_id)
    if leave:
        leave.status = status
        db.session.commit()
        # Add leave to status updates
        statusUpdates.append(leave)
        return {"message": "success"}, 200
    else:
        return {"message": "Leave not found"}, 404

@app.route('/api/status_updates', methods=['GET'])
def get_status_updates():
    # Convert status updates to JSON serializable format
    status_updates_json = [update.to_dict() for update in statusUpdates]
    return jsonify(status_updates_json), 200

@app.route('/api/leave_requests/<int:leave_id>', methods=['PUT'])
def update_leave_request(leave_id):
    try:
        data = request.get_json()

        if 'status' not in data:
            return jsonify({"message": "Missing status field in request"}), 400

        leave_request = Leave.query.get(leave_id)

        if not leave_request:
            return jsonify({"message": "No leave request found with given id"}), 404

        leave_request.status = data['status']
        db.session.commit()

        return jsonify(leave_request.to_dict()), 200

    except Exception as e:
        app.logger.error(str(e))
        return jsonify({"message": "Error occurred"}), 500
    
@app.route('/api/leave_requests/<int:leave_id>', methods=['GET'])
def get_leave_request(leave_id):
    try:
        leave_request = Leave.query.get(leave_id)
        if not leave_request:
            return jsonify({"message": "No leave request found with given id"}), 404

        return jsonify(leave_request.to_dict()), 200

    except Exception as e:
        app.logger.error(str(e))
        return jsonify({"message": "Error occurred"}), 500
    
@app.route('/api/my_leaves/<string:id_card>', methods=['GET'])
def get_my_leaves(id_card):
    user = User.query.get(id_card)
    if not user:
        return jsonify({"message": "User not found"}), 404

    leaves = Leave.query.filter_by(employee_id=user.id_card).all()

    return jsonify({
        "leaves": [leave.to_dict() for leave in leaves] # แก้ไขในบรรทัดนี้
    })
@app.route('/api/latest_checkin/<string:id_card>', methods=['GET'])
def get_latest_checkin(id_card):
    # Retrieve the user with the given id_card
    user = User.query.get(id_card)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    # Query the latest attendance record of this user
    attendance = Attendance.query.filter_by(employee_id=user.id_card).order_by(Attendance.check_in_timestamp.desc()).first()

    if attendance is None:
        return jsonify({"error": "No attendance record found for the user"}), 404

    # Check if the user has already checked out
    if attendance.check_out_timestamp is not None:
        return jsonify({"message": "The user has already checked out today."}), 200

    # If the user hasn't checked out, return the check-in status
    return jsonify({
        "message": "The user checked in but hasn't checked out yet.",
        "check_in_timestamp": attendance.check_in_timestamp.isoformat(),
        "status": attendance.status
    }), 200

@app.route('/api/latest_checkout/<string:id_card>', methods=['GET'])
def get_latest_checkout(id_card):
    # Retrieve the user with the given id_card
    user = User.query.get(id_card)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    # Query the latest attendance record of this user
    attendance = Attendance.query.filter_by(employee_id=user.id_card).order_by(Attendance.check_in_timestamp.desc()).first()

    if attendance is None:
        return jsonify({"error": "No attendance record found for the user"}), 404

    # Check if the user has already checked out
    if attendance.check_out_timestamp is None:
        return jsonify({"message": "The user has not checked out today."}), 200

    # If the user has checked out, return the checkout status
    return jsonify({
        "message": "The user has checked out.",
        "check_out_timestamp": attendance.check_out_timestamp.isoformat()
    }), 200

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
    #app.run(debug=True, port=5001)
    app.run()

