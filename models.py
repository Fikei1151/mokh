
from database import db



class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String, db.ForeignKey('user.id_card'), nullable=False)
    check_in_timestamp = db.Column(db.DateTime, nullable=False)
    check_out_timestamp = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False)

    employee = db.relationship('User')

class User(db.Model):
    id_card = db.Column(db.String(13), primary_key=True)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    account_type = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # Add this line

    def __init__(self, id_card, password, name, surname, position, email, account_type, gender):
        self.id_card = id_card
        self.password = password
        self.name = name
        self.surname = surname
        self.position = position
        self.email = email
        self.account_type = account_type
        self.gender = gender  # And this line


class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'leave_type': self.leave_type,
            'reason': self.reason,
            'status': self.status,
        }

class Holiday(db.Model):
    __tablename__ = 'holiday'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=False)

class DailyStatistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    total_employees = db.Column(db.Integer, default=0)
    total_absent = db.Column(db.Integer, default=0)
    total_late = db.Column(db.Integer, default=0)
    total_not_checked_out = db.Column(db.Integer, default=0)
