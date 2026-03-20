from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'nexaverse_payroll_super_secret_key' 

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',         
        password='root', 
        database='EmployeeManagement'
    )

# --- PUBLIC ROUTES ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

# --- AUTHENTICATION ROUTES (SEPARATED) ---
@app.route('/employee_login', methods=['GET', 'POST'])
def employee_login():
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (emp_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            if user.get('role') == 'HR':
                flash('You are an HR Admin. Please use the HR Admin Portal.')
                return redirect(url_for('employee_login'))
                
            session['loggedin'] = True
            session['employee_id'] = user['employee_id']
            session['first_name'] = user['first_name']
            session['role'] = 'Employee'
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect Employee ID or Password!')
    return render_template('employee_login.html')

@app.route('/hr_login', methods=['GET', 'POST'])
def hr_login():
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (emp_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            if user.get('role') != 'HR':
                flash('Access Denied. You do not have HR privileges.')
                return redirect(url_for('hr_login'))
                
            session['loggedin'] = True
            session['employee_id'] = user['employee_id']
            session['first_name'] = user['first_name']
            session['role'] = 'HR'
            return redirect(url_for('hr_dashboard'))
        else:
            flash('Incorrect HR ID or Password!')
    return render_template('hr_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        emp_id = request.form['employee_id'] 
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        gender = request.form['gender']
        job_title = request.form['job_title']
        contact = request.form['contact']
        hashed_password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Employee (employee_id, first_name, last_name, dob, gender, job_title, contact, password, role) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Employee')
            """, (emp_id, first_name, last_name, dob, gender, job_title, contact, hashed_password))
            conn.commit()
            
            # --- SMART REDIRECT LOGIC ---
            if session.get('loggedin') and session.get('role') == 'HR':
                flash(f'New employee ({first_name} {last_name}) added successfully!')
                return redirect(url_for('admin_employees'))
            else:
                flash('Registration successful! You can now login.')
                return redirect(url_for('employee_login'))
                
        except mysql.connector.IntegrityError:
            flash('Error: That Employee ID is already taken.')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/hr_register', methods=['GET', 'POST'])
def hr_register():
    if request.method == 'POST':
        emp_id = request.form['employee_id'] 
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        gender = request.form['gender']
        job_title = request.form['job_title']
        contact = request.form['contact']
        hashed_password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Employee (employee_id, first_name, last_name, dob, gender, job_title, contact, password, role) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'HR')
            """, (emp_id, first_name, last_name, dob, gender, job_title, contact, hashed_password))
            conn.commit()
            flash('HR Registration successful! Welcome to the Admin team.')
            return redirect(url_for('hr_login'))
        except mysql.connector.IntegrityError:
            flash('Error: That Admin ID is already taken.')
        finally:
            cursor.close()
            conn.close()
    return render_template('hr_register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- EMPLOYEE DASHBOARD ROUTES ---
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session.get('role') != 'Employee': return redirect(url_for('employee_login'))
    return render_template('dashboard.html', first_name=session['first_name'])

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'loggedin' not in session: return redirect(url_for('employee_login'))
    emp_id = session['employee_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        date = request.form['date']
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        try:
            t1 = datetime.strptime(check_in, '%H:%M')
            t2 = datetime.strptime(check_out, '%H:%M')
            total_hours = round((t2 - t1).total_seconds() / 3600, 2)
        except: total_hours = 0.0
            
        cursor.execute("INSERT INTO Attendance (employee_id, date, check_in, check_out, total_hours) VALUES (%s, %s, %s, %s, %s)", (emp_id, date, check_in, check_out, total_hours))
        conn.commit()
        flash('Attendance logged successfully!')
        return redirect(url_for('attendance'))
        
    cursor.execute("SELECT * FROM Attendance WHERE employee_id = %s ORDER BY date DESC", (emp_id,))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('attendance.html', records=records)

@app.route('/salary')
def salary():
    if 'loggedin' not in session: return redirect(url_for('employee_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Salary WHERE employee_id = %s ORDER BY pay_date DESC", (session['employee_id'],))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('salary.html', records=records)

@app.route('/leave', methods=['GET', 'POST'])
def leave():
    if 'loggedin' not in session: return redirect(url_for('employee_login'))
    emp_id = session['employee_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        leave_type = request.form['leave_type']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        cursor.execute("INSERT INTO Leave_Table (employee_id, leave_type, start_date, end_date, status) VALUES (%s, %s, %s, %s, %s)", (emp_id, leave_type, start_date, end_date, 'Pending'))
        conn.commit()
        flash('Leave request submitted successfully!')
        return redirect(url_for('leave'))
        
    cursor.execute("SELECT * FROM Leave_Table WHERE employee_id = %s ORDER BY start_date DESC", (emp_id,))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('leave.html', records=records)

# --- HR ADMIN ROUTES ---
@app.route('/hr_dashboard')
def hr_dashboard():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    return render_template('hr_dashboard.html', first_name=session['first_name'])

@app.route('/admin/employees')
def admin_employees():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Employee WHERE role = 'Employee' ORDER BY employee_id DESC")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_employees.html', employees=employees)

@app.route('/admin/delete_employee/<int:emp_id>')
def delete_employee(emp_id):
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Employee WHERE employee_id = %s", (emp_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Employee record deleted successfully.')
    return redirect(url_for('admin_employees'))

@app.route('/admin/payroll', methods=['GET', 'POST'])
def admin_payroll():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # --- ⚙️ AUTOMATED LEAVE PENALTY CONFIGURATION ---
    # Deducts $50 for every day of approved leave taken by the employee
    PENALTY_PER_LEAVE_DAY = 50.00 
    
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        pay_period = request.form['pay_period']
        base_pay = float(request.form['base_pay'])
        allowances = float(request.form['allowances'])
        bonuses = float(request.form['bonuses'])
        standard_deductions = float(request.form['deductions'])
        tax = float(request.form['tax'])
        
        # 1. Fetch all "Approved" leaves for this specific employee
        cursor.execute("SELECT start_date, end_date FROM Leave_Table WHERE employee_id = %s AND status = 'Approved'", (emp_id,))
        approved_leaves = cursor.fetchall()
        
        # 2. Calculate total leave days across all approved requests
        total_leave_days = 0
        for leave in approved_leaves:
            try:
                if isinstance(leave['start_date'], str):
                    start = datetime.strptime(leave['start_date'], '%Y-%m-%d')
                    end = datetime.strptime(leave['end_date'], '%Y-%m-%d')
                else:
                    start = leave['start_date']
                    end = leave['end_date']
                days = (end - start).days + 1 
                total_leave_days += days
            except Exception as e:
                print(f"Date math error: {e}")
        
        # 3. Calculate the Leave Penalty
        leave_penalty = total_leave_days * PENALTY_PER_LEAVE_DAY
        
        # 4. Calculate Final Net Pay
        total_earnings = base_pay + allowances + bonuses
        total_deductions = standard_deductions + tax + leave_penalty
        net_pay = total_earnings - total_deductions
        
        pay_date = datetime.today().strftime('%Y-%m-%d')
        
        # 5. Insert into database (combining standard deductions + leave penalty)
        cursor.execute("""
            INSERT INTO Salary (employee_id, pay_period, base_pay, allowances, bonuses, deductions, tax, net_pay, status, pay_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Paid', %s)
        """, (emp_id, pay_period, base_pay, allowances, bonuses, (standard_deductions + leave_penalty), tax, net_pay, pay_date))
        conn.commit()
        
        flash(f'Salary processed! {total_leave_days} leave days deducted at ${PENALTY_PER_LEAVE_DAY}/day. Final Net Pay: ${net_pay:.2f}')
        return redirect(url_for('admin_payroll'))
        
    cursor.execute("SELECT employee_id, first_name, last_name FROM Employee WHERE role = 'Employee'")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_payroll.html', employees=employees)

@app.route('/admin/leaves', methods=['GET', 'POST'])
def admin_leaves():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        leave_id = request.form['leave_id']
        action = request.form['action']
        cursor.execute("UPDATE Leave_Table SET status = %s WHERE leave_id = %s", (action, leave_id))
        conn.commit()
        flash(f'Leave {action} successfully!')
        return redirect(url_for('admin_leaves'))
        
    cursor.execute("""
        SELECT l.*, e.first_name, e.last_name 
        FROM Leave_Table l 
        JOIN Employee e ON l.employee_id = e.employee_id 
        ORDER BY l.start_date DESC
    """)
    all_leaves = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_leaves.html', leaves=all_leaves)

@app.route('/admin/reports')
def admin_reports():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as count FROM Employee WHERE role='Employee'")
    emp_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT SUM(net_pay) as total FROM Salary WHERE status='Paid'")
    total_salary = cursor.fetchone()['total'] or 0.00
    
    cursor.execute("SELECT COUNT(*) as count FROM Leave_Table WHERE status='Pending'")
    pending_leaves = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT s.pay_date, s.pay_period, s.net_pay, e.first_name, e.last_name 
        FROM Salary s JOIN Employee e ON s.employee_id = e.employee_id ORDER BY s.pay_date DESC LIMIT 10
    """)
    recent_payouts = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_reports.html', emp_count=emp_count, total_salary=total_salary, pending_leaves=pending_leaves, payouts=recent_payouts)

@app.route('/admin/settings')
def admin_settings():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    return render_template('admin_settings.html')

if __name__ == '__main__':
    app.run(debug=True)