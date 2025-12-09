from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, date
from . import db
from .models import User, Patient, Appointment

main_bp = Blueprint('main', __name__)

# ========== PUBLIC ROUTES ==========

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/appointment')
def appointment():
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
                         recent_appointments=recent_appointments)

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
        # Patient stats
        total_patients = Patient.query.count()
        male_patients = Patient.query.filter_by(gender='Male').count()
        female_patients = Patient.query.filter_by(gender='Female').count()

        # Appointment stats
        total_appointments = Appointment.query.count()
        pending_appointments = Appointment.query.filter_by(status='pending').count()
        confirmed_appointments = Appointment.query.filter_by(status='confirmed').count()
        cancelled_appointments = Appointment.query.filter_by(status='cancelled').count()

        # Appointments by month (for charts)
        monthly_counts = db.session.execute("""
            SELECT 
                EXTRACT(MONTH FROM appointment_date) AS month,
                COUNT(*) 
            FROM appointment
            GROUP BY month
            ORDER BY month;
        """).fetchall()

        # Prepare data for charts
        months = [int(row[0]) for row in monthly_counts]
        counts = [row[1] for row in monthly_counts]

        stats = {
            "patients": {
                "total": total_patients,
                "male": male_patients,
                "female": female_patients,
            },
            "appointments": {
                "total": total_appointments,
                "pending": pending_appointments,
                "confirmed": confirmed_appointments,
                "cancelled": cancelled_appointments,
            },
            "monthly": {
                "months": months,
                "counts": counts
            }
        }

        return render_template('reports.html', stats=stats)

    except Exception as e:
        flash(f"Error loading reports: {str(e)}", "error")
        return render_template('reports.html', stats={})
