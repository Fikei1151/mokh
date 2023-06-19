from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dateutil.parser import parse
from flask_cors import CORS
from models import User, Attendance, Leave
from flask import session
from database import db
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://Fikei1151:Fikree24@localhost/attendance'


app.secret_key = 'Fikree24@' 
CORS(app)
statusUpdates = [] # ตรงนี้ครับยรย


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
