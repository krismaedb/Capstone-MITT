from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, date
from . import db
from .models import User, Patient, Appointment
from sqlalchemy import text

main_bp = Blueprint('main', __name__)

# ========== PUBLIC ROUTES ==========

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            appt_date = datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date()
            appt_time = request.form.get('appointment_time')
            doctor = request.form.get('doctor')
            department = request.form.get('department')
            reason = request.form.get('reason')
            
            # 🔍 NEW: Check if patient ID was provided
            patient_id_input = request.form.get('patient_id_input', '').strip()
            linked_patient = None
            actual_patient_id = None

            if patient_id_input:
                # Look up patient by patient_id (e.g., "P00001")
                linked_patient = Patient.query.filter_by(patient_id=patient_id_input).first()
                if linked_patient:
                    actual_patient_id = linked_patient.id
                    # Use stored name/email/phone if not provided
                    name = name or f"{linked_patient.first_name} {linked_patient.last_name}"
                    email = email or linked_patient.email
                    phone = phone or linked_patient.phone

            appointment = Appointment(
                patient_id=actual_patient_id,  # ← Will be None or valid ID
                patient_name=name,
                patient_email=email,
                patient_phone=phone,
                appointment_date=appt_date,
                appointment_time=appt_time,
                doctor=doctor,
                department=department,
                reason=reason,
                status="pending",
                notes=None
            )

            db.session.add(appointment)
            db.session.commit()

            flash("Your appointment request has been submitted! Please wait for admin approval.", "success")
            return redirect(url_for('main.appointment'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error submitting appointment: {str(e)}", "error")

    return render_template('appointment.html')

# ========== AUTHENTICATION ==========

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=remember)
                user.last_login = datetime.utcnow()
                db.session.commit()
                flash(f'Welcome back, {user.full_name}!', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('Your account has been deactivated. Contact admin.', 'error')
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

# ========== DASHBOARD ==========

@main_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        total_patients = Patient.query.count() or 0
        total_appointments = Appointment.query.count() or 0
        pending_appointments = Appointment.query.filter_by(status='pending').count() or 0
        today = date.today()
        today_appointments = Appointment.query.filter_by(appointment_date=today).count() or 0
        recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    except Exception as e:
        print(f"Dashboard error: {e}")
        total_patients = 0
        total_appointments = 0
        pending_appointments = 0
        today_appointments = 0
        recent_appointments = []
    return render_template('dashboard.html',
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         pending_appointments=pending_appointments,
                         today_appointments=today_appointments,
                         recent_appointments=recent_appointments,
                         current_user=current_user)  # ← Add this
                         

# ========== PATIENTS ==========

@main_bp.route('/patients')
@login_required
def patients_list():
    try:
        search = request.args.get('search', '')
        if search:
            patients = Patient.query.filter(
                (Patient.first_name.ilike(f'%{search}%')) |
                (Patient.last_name.ilike(f'%{search}%')) |
                (Patient.patient_id.ilike(f'%{search}%'))
            ).order_by(Patient.created_at.desc()).all()
        else:
            patients = Patient.query.order_by(Patient.created_at.desc()).all()
        return render_template('patients_list.html', patients=patients, search=search)
    except Exception as e:
        flash(f'Error loading patients: {str(e)}', 'error')
        return render_template('patients_list.html', patients=[], search='')

@main_bp.route('/patients/add', methods=['GET', 'POST'])
@login_required
def patients_add():
    if request.method == 'POST':
        try:
            last_patient = Patient.query.order_by(Patient.id.desc()).first()
            if last_patient and last_patient.patient_id:
                last_num = int(last_patient.patient_id.replace('P', ''))
                patient_id = f'P{last_num + 1:05d}'
            else:
                patient_id = 'P00001'
            dob_str = request.form.get('date_of_birth')
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
            patient = Patient(
                patient_id=patient_id,
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                date_of_birth=dob,
                gender=request.form.get('gender'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                address=request.form.get('address'),
                emergency_contact=request.form.get('emergency_contact'),
                emergency_phone=request.form.get('emergency_phone'),
                blood_type=request.form.get('blood_type'),
                allergies=request.form.get('allergies'),
                medical_notes=request.form.get('medical_notes')
            )
            db.session.add(patient)
            db.session.commit()
            flash(f'Patient {patient.first_name} {patient.last_name} added successfully! (ID: {patient_id})', 'success')
            return redirect(url_for('main.patients_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding patient: {str(e)}', 'error')
    return render_template('patients_add.html')

@main_bp.route('/patients/view/<int:id>')
@login_required
def patients_view(id):
    try:
        patient = Patient.query.get_or_404(id)
        appointments = Appointment.query.filter_by(patient_id=id).order_by(Appointment.appointment_date.desc()).all()
        return render_template('patients_view.html', patient=patient, appointments=appointments)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('main.patients_list'))

@main_bp.route('/patients/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def patients_edit(id):
    try:
        patient = Patient.query.get_or_404(id)
        if request.method == 'POST':
            dob_str = request.form.get('date_of_birth')
            patient.first_name = request.form.get('first_name')
            patient.last_name = request.form.get('last_name')
            patient.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
            patient.gender = request.form.get('gender')
            patient.phone = request.form.get('phone')
            patient.email = request.form.get('email')
            patient.address = request.form.get('address')
            patient.emergency_contact = request.form.get('emergency_contact')
            patient.emergency_phone = request.form.get('emergency_phone')
            patient.blood_type = request.form.get('blood_type')
            patient.allergies = request.form.get('allergies')
            patient.medical_notes = request.form.get('medical_notes')
            patient.updated_at = datetime.utcnow()
            db.session.commit()
            flash(f'Patient {patient.first_name} {patient.last_name} updated successfully!', 'success')
            return redirect(url_for('main.patients_view', id=id))
        return render_template('patients_edit.html', patient=patient)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('main.patients_list'))

@main_bp.route('/patients/delete/<int:id>', methods=['POST'])
@login_required
def patients_delete(id):
    try:
        patient = Patient.query.get_or_404(id)
        name = f"{patient.first_name} {patient.last_name}"
        db.session.delete(patient)
        db.session.commit()
        flash(f'Patient {name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting patient: {str(e)}', 'error')
    return redirect(url_for('main.patients_list'))

# ========== APPOINTMENTS ==========

@main_bp.route('/appointments')
@login_required
def appointments_list():
    try:
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date', '')
        query = Appointment.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter_by(appointment_date=filter_date)
            except:
                pass
        appointments = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
        return render_template('appointments_list.html', 
                             appointments=appointments,
                             status_filter=status_filter,
                             date_filter=date_filter)
    except Exception as e:
        flash(f'Error loading appointments: {str(e)}', 'error')
        return render_template('appointments_list.html', appointments=[], status_filter='', date_filter='')

@main_bp.route('/appointments/book', methods=['GET', 'POST'])
@login_required
def appointments_book():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            patient = Patient.query.get(patient_id)
            
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('main.appointments_book'))
            
            appt_date = datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date()
            
            appointment = Appointment(
                patient_id=patient.id,
                patient_name=f"{patient.first_name} {patient.last_name}",
                patient_email=patient.email,
                patient_phone=patient.phone,
                appointment_date=appt_date,
                appointment_time=request.form.get('appointment_time'),
                doctor=request.form.get('doctor'),
                department=request.form.get('department'),
                reason=request.form.get('reason'),
                status='confirmed',
                notes=request.form.get('notes')
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            flash(f'Appointment booked successfully for {patient.first_name} {patient.last_name} on {appt_date}!', 'success')
            return redirect(url_for('main.appointments_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error booking appointment: {str(e)}', 'error')
            return redirect(url_for('main.appointments_book'))
    
    try:
        patients = Patient.query.order_by(Patient.first_name).all()
        return render_template('appointments_book.html', patients=patients)
    except Exception as e:
        flash(f'Error loading patients: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/appointments/view/<int:id>')
@login_required
def appointments_view(id):
    try:
        appointment = Appointment.query.get_or_404(id)
        patient = Patient.query.get(appointment.patient_id)
        return render_template('appointments_view.html', appointment=appointment, patient=patient)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('main.appointments_list'))

@main_bp.route('/appointments/update-status/<int:id>', methods=['POST'])
@login_required
def appointments_update_status(id):
    try:
        appointment = Appointment.query.get_or_404(id)
        new_status = request.form.get('status')
        appointment.status = new_status
        appointment.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Appointment status updated to {new_status}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
    return redirect(url_for('main.appointments_view', id=id))

@main_bp.route('/appointments/delete/<int:id>', methods=['POST'])
@login_required
def appointments_delete(id):
    try:
        appointment = Appointment.query.get_or_404(id)
        db.session.delete(appointment)
        db.session.commit()
        flash('Appointment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting appointment: {str(e)}', 'error')
    return redirect(url_for('main.appointments_list'))

@main_bp.route('/reports')
@login_required
def reports():
    try:
        total_patients = db.session.query(Patient).count()

        # Gender
        gender_rows = db.session.query(Patient.gender, db.func.count(Patient.id))\
                                .filter(Patient.gender.isnot(None))\
                                .group_by(Patient.gender).all()
        gender_labels = [str(g[0]) for g in gender_rows]
        gender_data = [int(g[1]) for g in gender_rows]

        # Blood Type
        blood_rows = db.session.query(Patient.blood_type, db.func.count(Patient.id))\
                               .filter(Patient.blood_type.isnot(None))\
                               .group_by(Patient.blood_type).all()
        blood_labels = [str(b[0]) for b in blood_rows]
        blood_data = [int(b[1]) for b in blood_rows]

        # Appointment Status
        status_rows = db.session.query(Appointment.status, db.func.count(Appointment.id))\
                                .filter(Appointment.status.isnot(None))\
                                .group_by(Appointment.status).all()
        status_labels = [str(s[0]) for s in status_rows]
        status_data = [int(s[1]) for s in status_rows]

        # Monthly Appointments (PostgreSQL-friendly)
        month_rows = db.session.execute(
            text("""
                SELECT TO_CHAR(appointment_date, 'Mon YYYY'), COUNT(*)
                FROM appointments
                WHERE appointment_date IS NOT NULL
                GROUP BY TO_CHAR(appointment_date, 'Mon YYYY'),
                         EXTRACT(YEAR FROM appointment_date),
                         EXTRACT(MONTH FROM appointment_date)
                ORDER BY EXTRACT(YEAR FROM appointment_date),
                         EXTRACT(MONTH FROM appointment_date)
            """)
        ).fetchall()
        month_labels = [str(m[0]) for m in month_rows]
        month_data = [int(m[1]) for m in month_rows]

        
        # DEBUG: Print to console
        print("Gender:", list(zip(gender_labels, gender_data)))
        print("Blood:", list(zip(blood_labels, blood_data)))
        print("Status:", list(zip(status_labels, status_data)))
        print("Months:", list(zip(month_labels, month_data)))

        # Ensure all are lists (even if empty)
        context = {
            'total_patients': total_patients,
            'gender_labels': gender_labels or [],
            'gender_data': gender_data or [],
            'blood_labels': blood_labels or [],
            'blood_data': blood_data or [],
            'status_labels': status_labels or [],
            'status_data': status_data or [],
            'month_labels': month_labels or [],
            'month_data': month_data or []
        }

        return render_template('reports.html', **context)

    except Exception as e:
        print("REPORTS ERROR:", str(e))  # ← Check terminal!
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('main.dashboard'))



# ========== STAFF MANAGEMENT ==========

@main_bp.route('/staff')
@login_required
def staff_list():
    if current_user.role not in ['admin', 'it']:
        flash('Access denied. Staff management requires admin or IT privileges.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        search = request.args.get('search', '')
        if search:
            staff = User.query.filter(
                (User.full_name.ilike(f'%{search}%')) |
                (User.username.ilike(f'%{search}%')) |
                (User.email.ilike(f'%{search}%'))
            ).order_by(User.created_at.desc()).all()
        else:
            staff = User.query.order_by(User.created_at.desc()).all()
        return render_template('staff_list.html', staff=staff, search=search)
    except Exception as e:
        flash(f'Error loading staff: {str(e)}', 'error')
        return render_template('staff_list.html', staff=[], search='')

@main_bp.route('/staff/add', methods=['GET', 'POST'])
@login_required
def staff_add():
    if current_user.role not in ['admin', 'it']:
        flash('Access denied. Staff management requires admin or IT privileges.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            
            # Validate required fields
            if not username or not full_name or not email or not password or not role:
                flash('All fields are required!', 'error')
                return redirect(url_for('main.staff_add'))
            
            # Check if username/email already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'error')
                return redirect(url_for('main.staff_add'))
            if User.query.filter_by(email=email).first():
                flash('Email already exists.', 'error')
                return redirect(url_for('main.staff_add'))
            
            # Create new user
            user = User(
                username=username,
                full_name=full_name,
                email=email,
                role=role,
                is_active=True  # default active
            )
            user.set_password(password)  # Hash password
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'Staff member "{full_name}" added successfully!', 'success')
            return redirect(url_for('main.staff_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding staff: {str(e)}', 'error')
    
    return render_template('staff_add.html')

@main_bp.route('/staff/view/<int:id>')
@login_required
def staff_view(id):
    if current_user.role not in ['admin', 'it']:
        flash('Access denied. Staff management requires admin or IT privileges.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        staff = User.query.get_or_404(id)
        return render_template('staff_view.html', staff=staff)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('main.staff_list'))

@main_bp.route('/staff/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def staff_edit(id):
    if current_user.role not in ['admin', 'it']:
        flash('Access denied. Staff management requires admin or IT privileges.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        staff = User.query.get_or_404(id)
        if request.method == 'POST':
            staff.full_name = request.form.get('full_name')
            staff.email = request.form.get('email')
            staff.role = request.form.get('role')
            staff.is_active = True if request.form.get('is_active') else False
            staff.updated_at = datetime.utcnow()
            
            # Optional: Change password
            new_password = request.form.get('new_password')
            if new_password:
                staff.set_password(new_password)
            
            db.session.commit()
            flash(f'Staff member "{staff.full_name}" updated successfully!', 'success')
            return redirect(url_for('main.staff_view', id=id))
        
        return render_template('staff_edit.html', staff=staff)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('main.staff_list'))

@main_bp.route('/staff/delete/<int:id>', methods=['POST'])
@login_required
def staff_delete(id):
    if current_user.role not in ['admin', 'it']:
        flash('Access denied. Staff management requires admin or IT privileges.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        staff = User.query.get_or_404(id)
        name = staff.full_name
        db.session.delete(staff)
        db.session.commit()
        flash(f'Staff member "{name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting staff: {str(e)}', 'error')
    return redirect(url_for('main.staff_list'))






# ========== SETTINGS ==========

@main_bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)


@main_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        flash('All fields are required.', 'error')
        return redirect(url_for('main.settings'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('main.settings'))

    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('main.settings'))

    current_user.set_password(new_password)
    db.session.commit()
    flash('Password updated successfully!', 'success')
    return redirect(url_for('main.settings'))