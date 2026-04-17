from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'government-system-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///government_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ==================== Database Models ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='employee')
    department = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Correspondence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doc_number = db.Column(db.String(50), unique=True, nullable=False)
    doc_type = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    sender = db.Column(db.String(200), nullable=False)
    recipient = db.Column(db.String(200))
    content = db.Column(db.Text)
    priority = db.Column(db.String(20), default='normal')
    status = db.Column(db.String(50), default='pending')
    attachment = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    tracking = db.relationship('Tracking', backref='correspondence', lazy=True)

class Tracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    correspondence_id = db.Column(db.Integer, db.ForeignKey('correspondence.id'))
    action = db.Column(db.String(200), nullable=False)
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_name = db.Column(db.String(200))
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_number = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    national_id = db.Column(db.String(50), unique=True)
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(20))
    marital_status = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.String(500))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    hire_date = db.Column(db.Date)
    contract_type = db.Column(db.String(50))
    salary = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)
    photo = db.Column(db.String(500))
    attendance = db.relationship('Attendance', backref='employee', lazy=True)
    leaves = db.relationship('Leave', backref='employee', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='present')
    notes = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Promotion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    old_position = db.Column(db.String(100))
    new_position = db.Column(db.String(100))
    old_salary = db.Column(db.Float)
    new_salary = db.Column(db.Float)
    reason = db.Column(db.Text)
    effective_date = db.Column(db.Date)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Discipline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    violation_type = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    penalty = db.Column(db.String(200))
    penalty_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_number = db.Column(db.String(50), unique=True, nullable=False)
    fiscal_year = db.Column(db.String(10), nullable=False)
    department = db.Column(db.String(100))
    allocated_amount = db.Column(db.Float, nullable=False)
    spent_amount = db.Column(db.Float, default=0)
    remaining_amount = db.Column(db.Float)
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_number = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    expense_type = db.Column(db.String(100))
    department = db.Column(db.String(100))
    vendor = db.Column(db.String(200))
    invoice_number = db.Column(db.String(100))
    budget_id = db.Column(db.Integer, db.ForeignKey('budget.id'))
    status = db.Column(db.String(50), default='pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_number = db.Column(db.String(50), unique=True, nullable=False)
    contract_type = db.Column(db.String(100))
    contractor_name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(500))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    value = db.Column(db.Float)
    status = db.Column(db.String(50), default='active')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_number = db.Column(db.String(50), unique=True, nullable=False)
    project_name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    department = db.Column(db.String(100))
    manager = db.Column(db.Integer, db.ForeignKey('user.id'))
    contractor = db.Column(db.String(200))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget = db.Column(db.Float)
    completion_percentage = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default='planning')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    milestones = db.relationship('Milestone', backref='project', lazy=True)

class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    completion_percentage = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default='pending')

class Archive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    archive_number = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    doc_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    related_module = db.Column(db.String(50))
    related_id = db.Column(db.Integer)
    department = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_number = db.Column(db.String(50), unique=True, nullable=False)
    asset_name = db.Column(db.String(200), nullable=False)
    asset_type = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    purchase_price = db.Column(db.Float)
    current_value = db.Column(db.Float)
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='active')
    assigned_to = db.Column(db.Integer, db.ForeignKey('employee.id'))
    notes = db.Column(db.Text)
    maintenance = db.relationship('Maintenance', backref='asset', lazy=True)

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'))
    maintenance_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    cost = db.Column(db.Float)
    performed_by = db.Column(db.String(200))
    maintenance_date = db.Column(db.Date)
    next_maintenance = db.Column(db.Date)
    status = db.Column(db.String(50), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_number = db.Column(db.String(50), unique=True, nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=0)
    min_quantity = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(50))
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='available')

class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(50), unique=True, nullable=False)
    citizen_name = db.Column(db.String(200), nullable=False)
    national_id = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    service_type = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(300))
    description = db.Column(db.Text)
    attachment = db.Column(db.String(500))
    status = db.Column(db.String(50), default='pending')
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== Helper Functions ====================

def generate_number(prefix):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = str(uuid.uuid4())[:4].upper()
    return f"{prefix}-{timestamp}-{random_suffix}"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xls', 'xlsx']

# ==================== Authentication Routes ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash('حسابك غير مفعل. يرجى التواصل مع المدير.', 'danger')
                return render_template('login.html')

            login_user(user)
            flash('تم تسجيل الدخول بنجاح', 'success')

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))

        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))

# ==================== Dashboard ====================

@app.route('/dashboard')
@login_required
def dashboard():
    correspondence_count = Correspondence.query.count()
    employees_count = Employee.query.filter_by(is_active=True).count()
    projects_count = Project.query.count()
    pending_expenses = Expense.query.filter_by(status='pending').count()
    active_contracts = Contract.query.filter_by(status='active').count()
    pending_services = ServiceRequest.query.filter_by(status='pending').count()

    recent_correspondences = Correspondence.query.order_by(Correspondence.created_at.desc()).limit(5).all()
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()

    return render_template('dashboard.html',
                         correspondence_count=correspondence_count,
                         employees_count=employees_count,
                         projects_count=projects_count,
                         pending_expenses=pending_expenses,
                         active_contracts=active_contracts,
                         pending_services=pending_services,
                         recent_correspondences=recent_correspondences,
                         recent_projects=recent_projects,
                         now=datetime.now())

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

# ==================== Correspondence Management ====================

@app.route('/correspondence')
@login_required
def correspondence_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    doc_type = request.args.get('doc_type')
    status = request.args.get('status')
    search = request.args.get('search')

    query = Correspondence.query

    if doc_type:
        query = query.filter_by(doc_type=doc_type)
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Correspondence.subject.contains(search) | Correspondence.doc_number.contains(search))

    correspondences = query.order_by(Correspondence.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('correspondence_list.html', correspondences=correspondences)

@app.route('/correspondence/add', methods=['GET', 'POST'])
@login_required
def correspondence_add():
    if request.method == 'POST':
        doc_type = request.form.get('doc_type')
        subject = request.form.get('subject')
        sender = request.form.get('sender')
        recipient = request.form.get('recipient')
        content = request.form.get('content')
        priority = request.form.get('priority')
        due_date = request.form.get('due_date')

        file = request.files.get('attachment')
        attachment_filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            attachment_filename = f"{uuid.uuid4()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename))

        correspondence = Correspondence(
            doc_number=generate_number(doc_type.upper()[:3]),
            doc_type=doc_type,
            subject=subject,
            sender=sender,
            recipient=recipient,
            content=content,
            priority=priority,
            attachment=attachment_filename,
            created_by=current_user.id,
            due_date=datetime.strptime(due_date, '%Y-%m-%d') if due_date else None
        )

        db.session.add(correspondence)
        db.session.commit()

        tracking = Tracking(
            correspondence_id=correspondence.id,
            action='تم إنشاء المعاملة',
            performed_by=current_user.id
        )
        db.session.add(tracking)
        db.session.commit()

        flash('تم تسجيل المعاملة بنجاح', 'success')
        return redirect(url_for('correspondence_list'))

    return render_template('correspondence_add.html')

@app.route('/correspondence/<int:id>')
@login_required
def correspondence_view(id):
    correspondence = Correspondence.query.get_or_404(id)
    tracking_records = Tracking.query.filter_by(correspondence_id=id).order_by(Tracking.timestamp.desc()).all()
    return render_template('correspondence_view.html', correspondence=correspondence, tracking_records=tracking_records)

@app.route('/correspondence/<int:id>/track', methods=['POST'])
@login_required
def correspondence_track(id):
    correspondence = Correspondence.query.get_or_404(id)
    action = request.form.get('action')
    recipient_name = request.form.get('recipient_name')
    notes = request.form.get('notes')

    tracking = Tracking(
        correspondence_id=id,
        action=action,
        performed_by=current_user.id,
        recipient_name=recipient_name,
        notes=notes
    )

    correspondence.status = 'in_progress' if correspondence.status == 'pending' else correspondence.status

    db.session.add(tracking)
    db.session.commit()

    flash('تم تحديث حالة التتبع بنجاح', 'success')
    return redirect(url_for('correspondence_view', id=id))

@app.route('/correspondence/<int:id>/complete')
@login_required
def correspondence_complete(id):
    correspondence = Correspondence.query.get_or_404(id)
    correspondence.status = 'completed'

    tracking = Tracking(
        correspondence_id=id,
        action='تم إتمام المعاملة',
        performed_by=current_user.id
    )

    db.session.add(tracking)
    db.session.commit()

    flash('تم إتمام المعاملة بنجاح', 'success')
    return redirect(url_for('correspondence_view', id=id))

# ==================== Employee Management ====================

@app.route('/employees')
@login_required
def employees_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    department = request.args.get('department')
    search = request.args.get('search')
    is_active = request.args.get('is_active', 'true')

    query = Employee.query

    if department:
        query = query.filter_by(department=department)
    if search:
        query = query.filter(Employee.full_name.contains(search) | Employee.employee_number.contains(search))
    if is_active == 'true':
        query = query.filter_by(is_active=True)

    employees = query.order_by(Employee.full_name).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('employees_list.html', employees=employees, departments=get_departments())

@app.route('/employees/add', methods=['GET', 'POST'])
@login_required
def employees_add():
    if request.method == 'POST':
        employee = Employee(
            employee_number=request.form.get('employee_number'),
            full_name=request.form.get('full_name'),
            national_id=request.form.get('national_id'),
            birth_date=datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d') if request.form.get('birth_date') else None,
            gender=request.form.get('gender'),
            marital_status=request.form.get('marital_status'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            department=request.form.get('department'),
            position=request.form.get('position'),
            hire_date=datetime.strptime(request.form.get('hire_date'), '%Y-%m-%d') if request.form.get('hire_date') else None,
            contract_type=request.form.get('contract_type'),
            salary=float(request.form.get('salary', 0))
        )

        db.session.add(employee)
        db.session.commit()

        flash('تم إضافة الموظف بنجاح', 'success')
        return redirect(url_for('employees_list'))

    return render_template('employees_add.html')

@app.route('/employees/<int:id>')
@login_required
def employees_view(id):
    employee = Employee.query.get_or_404(id)
    attendance_records = Attendance.query.filter_by(employee_id=id).order_by(Attendance.date.desc()).limit(30).all()
    leave_records = Leave.query.filter_by(employee_id=id).order_by(Leave.created_at.desc()).limit(10).all()
    discipline_records = Discipline.query.filter_by(employee_id=id).order_by(Discipline.created_at.desc()).limit(10).all()
    promotion_records = Promotion.query.filter_by(employee_id=id).order_by(Promotion.created_at.desc()).limit(10).all()

    return render_template('employees_view.html',
                         employee=employee,
                         attendance_records=attendance_records,
                         leave_records=leave_records,
                         discipline_records=discipline_records,
                         promotion_records=promotion_records)

@app.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def employees_edit(id):
    employee = Employee.query.get_or_404(id)

    if request.method == 'POST':
        employee.full_name = request.form.get('full_name')
        employee.national_id = request.form.get('national_id')
        employee.birth_date = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d') if request.form.get('birth_date') else None
        employee.gender = request.form.get('gender')
        employee.marital_status = request.form.get('marital_status')
        employee.phone = request.form.get('phone')
        employee.email = request.form.get('email')
        employee.address = request.form.get('address')
        employee.department = request.form.get('department')
        employee.position = request.form.get('position')
        employee.contract_type = request.form.get('contract_type')
        employee.salary = float(request.form.get('salary', 0))

        db.session.commit()
        flash('تم تحديث بيانات الموظف بنجاح', 'success')
        return redirect(url_for('employees_view', id=id))

    return render_template('employees_edit.html', employee=employee)

# ==================== Attendance Management ====================

@app.route('/attendance')
@login_required
def attendance_list():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    department = request.args.get('department')

    query = Attendance.query.filter_by(date=datetime.strptime(date, '%Y-%m-%d'))

    if department:
        query = query.join(Employee).filter(Employee.department == department)

    attendance_records = query.all()
    employees = Employee.query.filter_by(is_active=True).all()

    return render_template('attendance_list.html',
                         attendance_records=attendance_records,
                         employees=employees,
                         selected_date=date,
                         departments=get_departments())

@app.route('/attendance/checkin', methods=['POST'])
@login_required
def attendance_checkin():
    employee_id = request.form.get('employee_id')

    existing = Attendance.query.filter_by(
        employee_id=employee_id,
        date=datetime.now().date()
    ).first()

    if existing:
        flash('تم تسجيل الحضور مسبقاً اليوم', 'warning')
        return redirect(url_for('attendance_list'))

    attendance = Attendance(
        employee_id=employee_id,
        check_in=datetime.now(),
        date=datetime.now().date(),
        status='present'
    )

    db.session.add(attendance)
    db.session.commit()

    flash('تم تسجيل الحضور بنجاح', 'success')
    return redirect(url_for('attendance_list'))

@app.route('/attendance/<int:id>/checkout', methods=['POST'])
@login_required
def attendance_checkout(id):
    attendance = Attendance.query.get_or_404(id)

    if attendance.check_out:
        flash('تم تسجيل الانصراف مسبقاً', 'warning')
        return redirect(url_for('attendance_list'))

    attendance.check_out = datetime.now()

    work_hours = (attendance.check_out - attendance.check_in).total_seconds() / 3600
    if work_hours < 4:
        attendance.status = 'half_day'
    elif work_hours >= 8:
        attendance.status = 'present'
    else:
        attendance.status = 'partial'

    db.session.commit()
    flash('تم تسجيل الانصراف بنجاح', 'success')
    return redirect(url_for('attendance_list'))

# ==================== Leave Management ====================

@app.route('/leaves')
@login_required
def leaves_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status')
    leave_type = request.args.get('leave_type')

    query = Leave.query

    if status:
        query = query.filter_by(status=status)
    if leave_type:
        query = query.filter_by(leave_type=leave_type)

    leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('leaves_list.html', leaves=leaves)

@app.route('/leaves/add', methods=['GET', 'POST'])
@login_required
def leaves_add():
    if request.method == 'POST':
        leave = Leave(
            employee_id=request.form.get('employee_id'),
            leave_type=request.form.get('leave_type'),
            start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d'),
            end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d'),
            reason=request.form.get('reason')
        )

        db.session.add(leave)
        db.session.commit()

        flash('تم تقديم طلب الإجازة بنجاح', 'success')
        return redirect(url_for('leaves_list'))

    employees = Employee.query.filter_by(is_active=True).all()
    return render_template('leaves_add.html', employees=employees)

@app.route('/leaves/<int:id>/approve')
@login_required
def leaves_approve(id):
    leave = Leave.query.get_or_404(id)
    leave.status = 'approved'
    leave.approved_by = current_user.id

    db.session.commit()
    flash('تم الموافقة على طلب الإجازة', 'success')
    return redirect(url_for('leaves_list'))

@app.route('/leaves/<int:id>/reject')
@login_required
def leaves_reject(id):
    leave = Leave.query.get_or_404(id)
    leave.status = 'rejected'
    leave.approved_by = current_user.id

    db.session.commit()
    flash('تم رفض طلب الإجازة', 'success')
    return redirect(url_for('leaves_list'))

# ==================== Promotions & Discipline ====================

@app.route('/promotions/add', methods=['GET', 'POST'])
@login_required
def promotions_add():
    if request.method == 'POST':
        promotion = Promotion(
            employee_id=request.form.get('employee_id'),
            old_position=request.form.get('old_position'),
            new_position=request.form.get('new_position'),
            old_salary=float(request.form.get('old_salary', 0)),
            new_salary=float(request.form.get('new_salary', 0)),
            reason=request.form.get('reason'),
            effective_date=datetime.strptime(request.form.get('effective_date'), '%Y-%m-%d'),
            approved_by=current_user.id
        )

        employee = Employee.query.get(request.form.get('employee_id'))
        employee.position = request.form.get('new_position')
        employee.salary = float(request.form.get('new_salary', 0))

        db.session.add(promotion)
        db.session.commit()

        flash('تم تسجيل الترقية بنجاح', 'success')
        return redirect(url_for('employees_view', id=employee.id))

    employees = Employee.query.filter_by(is_active=True).all()
    return render_template('promotions_add.html', employees=employees)

@app.route('/discipline/add', methods=['GET', 'POST'])
@login_required
def discipline_add():
    if request.method == 'POST':
        discipline = Discipline(
            employee_id=request.form.get('employee_id'),
            violation_type=request.form.get('violation_type'),
            description=request.form.get('description'),
            penalty=request.form.get('penalty'),
            penalty_date=datetime.strptime(request.form.get('penalty_date'), '%Y-%m-%d'),
            approved_by=current_user.id
        )

        db.session.add(discipline)
        db.session.commit()

        flash('تم تسجيل المخالفة بنجاح', 'success')
        return redirect(url_for('employees_view', id=request.form.get('employee_id')))

    employees = Employee.query.filter_by(is_active=True).all()
    return render_template('discipline_add.html', employees=employees)

# ==================== Financial Management ====================

@app.route('/budget')
@login_required
def budget_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    budgets = Budget.query.order_by(Budget.fiscal_year.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('budget_list.html', budgets=budgets)

@app.route('/budget/add', methods=['GET', 'POST'])
@login_required
def budget_add():
    if request.method == 'POST':
        budget = Budget(
            budget_number=generate_number('BUD'),
            fiscal_year=request.form.get('fiscal_year'),
            department=request.form.get('department'),
            allocated_amount=float(request.form.get('allocated_amount', 0)),
            remaining_amount=float(request.form.get('allocated_amount', 0))
        )

        db.session.add(budget)
        db.session.commit()

        flash('تم إضافة الميزانية بنجاح', 'success')
        return redirect(url_for('budget_list'))

    return render_template('budget_add.html', now=datetime.now())

@app.route('/expenses')
@login_required
def expenses_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status')

    query = Expense.query
    if status:
        query = query.filter_by(status=status)

    expenses = query.order_by(Expense.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('expenses_list.html', expenses=expenses)

@app.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def expenses_add():
    if request.method == 'POST':
        expense = Expense(
            expense_number=generate_number('EXP'),
            description=request.form.get('description'),
            amount=float(request.form.get('amount', 0)),
            expense_type=request.form.get('expense_type'),
            department=request.form.get('department'),
            vendor=request.form.get('vendor'),
            invoice_number=request.form.get('invoice_number'),
            status='pending',
            created_by=current_user.id
        )

        db.session.add(expense)
        db.session.commit()

        flash('تم تسجيل المصروف بنجاح', 'success')
        return redirect(url_for('expenses_list'))

    budgets = Budget.query.filter_by(status='active').all()
    return render_template('expenses_add.html', budgets=budgets)

@app.route('/expenses/<int:id>/approve')
@login_required
def expenses_approve(id):
    expense = Expense.query.get_or_404(id)
    expense.status = 'approved'
    expense.approved_by = current_user.id

    budget = Budget.query.get(expense.budget_id)
    if budget:
        budget.spent_amount += expense.amount
        budget.remaining_amount = budget.allocated_amount - budget.spent_amount

    db.session.commit()
    flash('تم اعتماد المصروف بنجاح', 'success')
    return redirect(url_for('expenses_list'))

@app.route('/contracts')
@login_required
def contracts_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status')

    query = Contract.query
    if status:
        query = query.filter_by(status=status)

    contracts = query.order_by(Contract.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('contracts_list.html', contracts=contracts)

@app.route('/contracts/add', methods=['GET', 'POST'])
@login_required
def contracts_add():
    if request.method == 'POST':
        contract = Contract(
            contract_number=generate_number('CON'),
            contract_type=request.form.get('contract_type'),
            contractor_name=request.form.get('contractor_name'),
            subject=request.form.get('subject'),
            start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d') if request.form.get('start_date') else None,
            end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d') if request.form.get('end_date') else None,
            value=float(request.form.get('value', 0)),
            notes=request.form.get('notes')
        )

        db.session.add(contract)
        db.session.commit()

        flash('تم تسجيل العقد بنجاح', 'success')
        return redirect(url_for('contracts_list'))

    return render_template('contracts_add.html')

# ==================== Projects Management ====================

@app.route('/projects')
@login_required
def projects_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status')

    query = Project.query
    if status:
        query = query.filter_by(status=status)

    projects = query.order_by(Project.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('projects_list.html', projects=projects)

@app.route('/projects/add', methods=['GET', 'POST'])
@login_required
def projects_add():
    if request.method == 'POST':
        project = Project(
            project_number=generate_number('PRJ'),
            project_name=request.form.get('project_name'),
            description=request.form.get('description'),
            department=request.form.get('department'),
            manager=current_user.id,
            contractor=request.form.get('contractor'),
            start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d') if request.form.get('start_date') else None,
            end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d') if request.form.get('end_date') else None,
            budget=float(request.form.get('budget', 0)),
            status='planning'
        )

        db.session.add(project)
        db.session.commit()

        flash('تم إضافة المشروع بنجاح', 'success')
        return redirect(url_for('projects_list'))

    return render_template('projects_add.html')

@app.route('/projects/<int:id>')
@login_required
def projects_view(id):
    project = Project.query.get_or_404(id)
    milestones = Milestone.query.filter_by(project_id=id).order_by(Milestone.due_date).all()
    return render_template('projects_view.html', project=project, milestones=milestones)

@app.route('/projects/<int:id>/update', methods=['POST'])
@login_required
def projects_update(id):
    project = Project.query.get_or_404(id)
    project.completion_percentage = float(request.form.get('completion_percentage', 0))
    project.status = request.form.get('status')

    if project.completion_percentage == 100:
        project.status = 'completed'

    db.session.commit()
    flash('تم تحديث حالة المشروع بنجاح', 'success')
    return redirect(url_for('projects_view', id=id))

@app.route('/projects/<int:id>/milestone/add', methods=['POST'])
@login_required
def milestones_add(id):
    milestone = Milestone(
        project_id=id,
        title=request.form.get('title'),
        description=request.form.get('description'),
        due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d') if request.form.get('due_date') else None
    )

    db.session.add(milestone)
    db.session.commit()

    flash('تم إضافة里程碑 بنجاح', 'success')
    return redirect(url_for('projects_view', id=id))

# ==================== Archive Management ====================

@app.route('/archive')
@login_required
def archive_list():
    page = request.args.get('page', 1, type=int)
    per_page = 30
    doc_type = request.args.get('doc_type')
    search = request.args.get('search')

    query = Archive.query

    if doc_type:
        query = query.filter_by(doc_type=doc_type)
    if search:
        query = query.filter(Archive.title.contains(search) | Archive.archive_number.contains(search))

    archives = query.order_by(Archive.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('archive_list.html', archives=archives)

@app.route('/archive/add', methods=['GET', 'POST'])
@login_required
def archive_add():
    if request.method == 'POST':
        file = request.files.get('file_path')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            saved_filename = f"{uuid.uuid4()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))

        archive = Archive(
            archive_number=generate_number('ARC'),
            title=request.form.get('title'),
            doc_type=request.form.get('doc_type'),
            description=request.form.get('description'),
            file_path=saved_filename if file and allowed_file(file.filename) else None,
            related_module=request.form.get('related_module'),
            related_id=request.form.get('related_id') if request.form.get('related_id') else None,
            department=request.form.get('department'),
            created_by=current_user.id
        )

        db.session.add(archive)
        db.session.commit()

        flash('تم الأرشفة بنجاح', 'success')
        return redirect(url_for('archive_list'))

    return render_template('archive_add.html')

@app.route('/archive/<int:id>')
@login_required
def archive_view(id):
    archive = Archive.query.get_or_404(id)
    return render_template('archive_view.html', archive=archive)

# ==================== Assets Management ====================

@app.route('/assets')
@login_required
def assets_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    asset_type = request.args.get('asset_type')
    status = request.args.get('status')

    query = Asset.query

    if asset_type:
        query = query.filter_by(asset_type=asset_type)
    if status:
        query = query.filter_by(status=status)

    assets = query.order_by(Asset.asset_name).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('assets_list.html', assets=assets)

@app.route('/assets/add', methods=['GET', 'POST'])
@login_required
def assets_add():
    if request.method == 'POST':
        asset = Asset(
            asset_number=generate_number('AST'),
            asset_name=request.form.get('asset_name'),
            asset_type=request.form.get('asset_type'),
            serial_number=request.form.get('serial_number'),
            purchase_date=datetime.strptime(request.form.get('purchase_date'), '%Y-%m-%d') if request.form.get('purchase_date') else None,
            purchase_price=float(request.form.get('purchase_price', 0)),
            current_value=float(request.form.get('current_value', 0)),
            location=request.form.get('location'),
            assigned_to=request.form.get('assigned_to') if request.form.get('assigned_to') else None,
            notes=request.form.get('notes')
        )

        db.session.add(asset)
        db.session.commit()

        flash('تم إضافة الأصل بنجاح', 'success')
        return redirect(url_for('assets_list'))

    employees = Employee.query.filter_by(is_active=True).all()
    return render_template('assets_add.html', employees=employees)

@app.route('/assets/<int:id>/maintenance/add', methods=['POST'])
@login_required
def maintenance_add(id):
    maintenance = Maintenance(
        asset_id=id,
        maintenance_type=request.form.get('maintenance_type'),
        description=request.form.get('description'),
        cost=float(request.form.get('cost', 0)),
        performed_by=request.form.get('performed_by'),
        maintenance_date=datetime.strptime(request.form.get('maintenance_date'), '%Y-%m-%d') if request.form.get('maintenance_date') else None,
        next_maintenance=datetime.strptime(request.form.get('next_maintenance'), '%Y-%m-%d') if request.form.get('next_maintenance') else None
    )

    db.session.add(maintenance)
    db.session.commit()

    flash('تم تسجيل الصيانة بنجاح', 'success')
    return redirect(url_for('assets_list'))

# ==================== Inventory Management ====================

@app.route('/inventory')
@login_required
def inventory_list():
    page = request.args.get('page', 1, type=int)
    per_page = 30
    category = request.args.get('category')

    query = Inventory.query
    if category:
        query = query.filter_by(category=category)

    inventory = query.order_by(Inventory.item_name).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('inventory_list.html', inventory=inventory)

@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def inventory_add():
    if request.method == 'POST':
        item = Inventory(
            item_number=generate_number('INV'),
            item_name=request.form.get('item_name'),
            category=request.form.get('category'),
            quantity=int(request.form.get('quantity', 0)),
            min_quantity=int(request.form.get('min_quantity', 0)),
            unit=request.form.get('unit'),
            location=request.form.get('location')
        )

        db.session.add(item)
        db.session.commit()

        flash('تم إضافة المادة بنجاح', 'success')
        return redirect(url_for('inventory_list'))

    return render_template('inventory_add.html')

@app.route('/inventory/<int:id>/update', methods=['POST'])
@login_required
def inventory_update(id):
    item = Inventory.query.get_or_404(id)
    item.quantity = int(request.form.get('quantity', 0))

    if item.quantity <= item.min_quantity:
        item.status = 'low_stock'
    else:
        item.status = 'available'

    db.session.commit()
    flash('تم تحديث الكمية بنجاح', 'success')
    return redirect(url_for('inventory_list'))

# ==================== Service Requests ====================

@app.route('/services')
@login_required
def services_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status')

    query = ServiceRequest.query
    if status:
        query = query.filter_by(status=status)

    services = query.order_by(ServiceRequest.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('services_list.html', services=services)

@app.route('/services/add', methods=['GET', 'POST'])
def services_add():
    if request.method == 'POST':
        file = request.files.get('attachment')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            saved_filename = f"{uuid.uuid4()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))

        service = ServiceRequest(
            request_number=generate_number('SVC'),
            citizen_name=request.form.get('citizen_name'),
            national_id=request.form.get('national_id'),
            phone=request.form.get('phone'),
            service_type=request.form.get('service_type'),
            subject=request.form.get('subject'),
            description=request.form.get('description'),
            attachment=saved_filename if file and allowed_file(file.filename) else None,
            status='pending'
        )

        db.session.add(service)
        db.session.commit()

        flash('تم تقديم الطلب بنجاح', 'success')
        if current_user.is_authenticated:
            return redirect(url_for('services_list'))
        return redirect(url_for('login'))

    return render_template('services_add.html')

@app.route('/services/<int:id>')
@login_required
def services_view(id):
    service = ServiceRequest.query.get_or_404(id)
    return render_template('services_view.html', service=service)

@app.route('/services/<int:id>/update', methods=['POST'])
@login_required
def services_update(id):
    service = ServiceRequest.query.get_or_404(id)
    service.status = request.form.get('status')
    service.assigned_to = request.form.get('assigned_to') if request.form.get('assigned_to') else None
    service.notes = request.form.get('notes')
    service.updated_at = datetime.now()

    db.session.commit()
    flash('تم تحديث حالة الطلب بنجاح', 'success')
    return redirect(url_for('services_view', id=id))

# ==================== Reports ====================

@app.route('/reports/correspondence')
@login_required
def reports_correspondence():
    from datetime import datetime, timedelta

    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))

    correspondences = Correspondence.query.filter(
        Correspondence.created_at >= datetime.strptime(start_date, '%Y-%m-%d'),
        Correspondence.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    ).all()

    return render_template('reports_correspondence.html',
                         correspondences=correspondences,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/reports/financial')
@login_required
def reports_financial():
    fiscal_year = request.args.get('fiscal_year', datetime.now().year)

    budgets = Budget.query.filter_by(fiscal_year=str(fiscal_year)).all()
    
    # تحسين فلترة المصروفات حسب السنة
    expenses = Expense.query.filter(db.extract('year', Expense.created_at) == int(fiscal_year)).all()

    total_allocated = sum(b.allocated_amount for b in budgets)
    total_spent = sum(e.amount for e in expenses if e.status == 'approved')

    return render_template('reports_financial.html',
                         budgets=budgets,
                         expenses=expenses,
                         fiscal_year=fiscal_year,
                         total_allocated=total_allocated,
                         total_spent=total_spent)

@app.route('/reports/projects')
@login_required
def reports_projects():
    projects = Project.query.all()
    return render_template('reports_projects.html', projects=projects)

# ==================== User Management ====================

@app.route('/users')
@login_required
def users_list():
    if current_user.role != 'admin':
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    users = User.query.all()
    return render_template('users_list.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def users_add():
    if current_user.role != 'admin':
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if User.query.filter_by(username=request.form.get('username')).first():
            flash('اسم المستخدم موجود مسبقاً', 'danger')
            return redirect(url_for('users_add'))

        user = User(
            username=request.form.get('username'),
            password=generate_password_hash(request.form.get('password')),
            full_name=request.form.get('full_name'),
            role=request.form.get('role'),
            department=request.form.get('department')
        )

        db.session.add(user)
        db.session.commit()

        flash('تم إضافة المستخدم بنجاح', 'success')
        return redirect(url_for('users_list'))

    return render_template('users_add.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/correspondence/<int:id>/delete')
@login_required
def correspondence_delete(id):
    if current_user.role != 'admin':
        flash('غير مصرح لك بحذف المعاملات', 'danger')
        return redirect(url_for('correspondence_list'))
    
    corr = Correspondence.query.get_or_404(id)
    # حذف سجلات التتبع أولاً
    Tracking.query.filter_by(correspondence_id=id).delete()
    db.session.delete(corr)
    db.session.commit()
    flash('تم حذف المعاملة بنجاح', 'success')
    return redirect(url_for('correspondence_list'))

@app.route('/employees/<int:id>/delete')
@login_required
def employees_delete(id):
    if current_user.role != 'admin':
        flash('غير مصرح لك بحذف الموظفين', 'danger')
        return redirect(url_for('employees_list'))
    
    emp = Employee.query.get_or_404(id)
    # بدلاً من الحذف الفعلي، نجعله غير نشط
    emp.is_active = False
    db.session.commit()
    flash('تم تعطيل حساب الموظف بنجاح', 'success')
    return redirect(url_for('employees_list'))

@app.route('/projects/<int:id>/delete')
@login_required
def projects_delete(id):
    if current_user.role != 'admin':
        flash('غير مصرح لك بحذف المشاريع', 'danger')
        return redirect(url_for('projects_list'))
    
    project = Project.query.get_or_404(id)
    Milestone.query.filter_by(project_id=id).delete()
    db.session.delete(project)
    db.session.commit()
    flash('تم حذف المشروع بنجاح', 'success')
    return redirect(url_for('projects_list'))

@app.route('/archive/<int:id>/delete')
@login_required
def archive_delete(id):
    if current_user.role != 'admin':
        flash('غير مصرح لك بحذف الأرشيف', 'danger')
        return redirect(url_for('archive_list'))
    
    arch = Archive.query.get_or_404(id)
    db.session.delete(arch)
    db.session.commit()
    flash('تم حذف الوثيقة بنجاح', 'success')
    return redirect(url_for('archive_list'))

@app.route('/assets/<int:id>/delete')
@login_required
def assets_delete(id):
    if current_user.role != 'admin':
        flash('غير مصرح لك بحذف الأصول', 'danger')
        return redirect(url_for('assets_list'))
    
    asset = Asset.query.get_or_404(id)
    Maintenance.query.filter_by(asset_id=id).delete()
    db.session.delete(asset)
    db.session.commit()
    flash('تم حذف الأصل بنجاح', 'success')
    return redirect(url_for('assets_list'))

@app.route('/inventory/<int:id>/delete')
@login_required
def inventory_delete(id):
    if current_user.role != 'admin':
        flash('غير مصرح لك بحذف المواد', 'danger')
        return redirect(url_for('inventory_list'))
    
    item = Inventory.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('تم حذف المادة بنجاح', 'success')
    return redirect(url_for('inventory_list'))

@app.route('/services/<int:id>/delete')
@login_required
def services_delete(id):
    if current_user.role != 'admin':
        flash('غير مصرح لك بحذف الطلبات', 'danger')
        return redirect(url_for('services_list'))
    
    service = ServiceRequest.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash('تم حذف الطلب بنجاح', 'success')
    return redirect(url_for('services_list'))

# ==================== Utility Functions ====================

def get_departments():
    return [
        'الإدارة العامة',
        'الشؤون المالية',
        'شؤون الموظفين',
        'التقنية المعلومات',
        'الشؤون القانونية',
        'الخدمات العامة',
        'المشاريع والإنشاءات',
        'الشؤون الإدارية'
    ]

# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# ==================== Main ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                full_name='مدير النظام',
                role='admin',
                department='الإدارة العامة'
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True, host='0.0.0.0', port=5000)
