from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image
import os

conn = sqlite3.connect('hospital.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE patients ADD COLUMN doctor_id INTEGER")
    conn.commit()
except:
    pass

conn.close()

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    # patients table
    cursor.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age TEXT,
    gender TEXT,
    phone TEXT,
    email TEXT,
    doctor TEXT,
    date TEXT
)
""")

# appointments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor TEXT,
        date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        amount TEXT,
        details TEXT,
        date TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialization TEXT
    )
    """)
    
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username,password) VALUES ('admin','admin123')")

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = sqlite3.connect('hospital.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = u
            return redirect('/dashboard')

    return render_template('login.html')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html')

# ---------------- ADD PATIENT ----------------
@app.route('/add-patient', methods=['GET','POST'])
def add_patient():
    if request.method == 'POST':
        conn = sqlite3.connect('hospital.db')
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO patients (name, age, gender, phone, email, doctor, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form['name'],
            request.form['age'],
            request.form['gender'],
            request.form.get('phone'),
            request.form.get('email'),
            request.form['doctor'],
            request.form['date']
        ))

        conn.commit()
        conn.close()

        return redirect('/patients')

    return render_template('add_patient.html')
# ---------------- VIEW PATIENTS ----------------
@app.route('/patients')
def patients():
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients")
    data = cursor.fetchall()
    conn.close()
    return render_template('patients.html', patients=data)

# ---------------- EDIT PATIENT ----------------
@app.route('/edit-patient/<int:id>', methods=['GET','POST'])
def edit_patient(id):
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        cursor.execute("""
        UPDATE patients SET name=?,age=?,gender=?,phone=?,email=? WHERE id=?
        """, (
            request.form['name'],
            request.form['age'],
            request.form['gender'],
            request.form['phone'],
            request.form['email'],
            id
        ))
        conn.commit()
        conn.close()
        return redirect('/patients')

    cursor.execute("SELECT * FROM patients WHERE id=?", (id,))
    patient = cursor.fetchone()
    conn.close()
    return render_template('edit_patient.html', patient=patient)

# ---------------- DELETE PATIENT ----------------
@app.route('/delete-patient/<int:id>')
def delete_patient(id):
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/patients')

# -------------- ADD APPOINTMENT ROUTE HERE --------------
@app.route('/appointment', methods=['GET','POST'])
def appointment():
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()

    if request.method == 'POST':
        cursor.execute(
            "INSERT INTO appointments (patient_id, doctor, date) VALUES (?, ?, ?)",
            (
                request.form['patient_id'],
                request.form['doctor'],
                request.form['date']
            )
        )

        conn.commit()
        conn.close()
        return redirect('/appointments')

    return render_template('appointment.html', patients=patients)
# -------------- VIEW APPOINTMENTS --------------
@app.route('/appointments')
def appointments():
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    # ✅ ADD YOUR QUERY HERE
    cursor.execute("""
    SELECT a.id, p.name, a.doctor, a.date
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    """)

    data = cursor.fetchall()
    conn.close()

    return render_template('appointments.html', appointments=data)

# ---------------- BILLING ----------------
from datetime import datetime

@app.route('/billing/<int:patient_id>', methods=['GET','POST'])
def billing(patient_id):
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        amount = request.form.get('amount')
        details = request.form.get('details')
        date = datetime.now().strftime("%Y-%m-%d")  # ✅ add date

        cursor.execute("""
        INSERT INTO bills (patient_id, amount, details, date)
        VALUES (?, ?, ?, ?)
        """, (patient_id, amount, details, date))

        conn.commit()
        conn.close()

        return redirect('/bills')

    return render_template('billing.html', patient_id=patient_id)
# ---------------- VIEW BILLS ----------------
@app.route('/bills')
def bills():
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT b.id, p.name, b.amount, b.details, b.date
    FROM bills b
    JOIN patients p ON b.patient_id = p.id
    """)

    data = cursor.fetchall()

    # ✅ CALCULATE TOTAL
    total = 0
    for b in data:
        total += int(b[2])

    conn.close()
    return render_template('bills.html', bills=data, total=total)

# ---------------- PDF BILL ----------------
@app.route('/bill-pdf/<int:id>')
def bill_pdf(id):
    import os

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT p.name, b.amount, b.details, b.date
    FROM bills b
    JOIN patients p ON b.patient_id = p.id
    WHERE b.id=?
    """, (id,))

    bill = cursor.fetchone()
    conn.close()

    # ✅ create folder
    os.makedirs("static/bills", exist_ok=True)

    filename = f"bill_{id}.pdf"
    filepath = os.path.join("static/bills", filename)

    doc = SimpleDocTemplate(filepath)
    styles = getSampleStyleSheet()

    # ✅ ADD HERE 👇
    content = []

    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        img = Image(logo_path, width=100, height=100)
        img.hAlign = 'CENTER'
        content.append(img)

    content.append(Paragraph("Hospital Bill", styles['Title']))

    # ✅ BILL DETAILS
    content.append(Paragraph(f"Name: {bill[0]}", styles['Normal']))
    content.append(Paragraph(f"Amount: {bill[1]}", styles['Normal']))
    content.append(Paragraph(f"Details: {bill[2]}", styles['Normal']))
    content.append(Paragraph(f"Date: {bill[3]}", styles['Normal']))

    doc.build(content)

    return send_file(filepath, as_attachment=True)

# ---------------- VIEW PATIENT BILLS ----------------
@app.route('/patient-bills/<int:patient_id>')
def patient_bills(patient_id):
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT amount, details, date
    FROM bills
    WHERE patient_id = ?
    """, (patient_id,))

    bills = cursor.fetchall()

    conn.close()
    return render_template('patient_bills.html', bills=bills)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)