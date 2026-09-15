import sqlite3
import hashlib
import os
from datetime import datetime

DB_NAME = "attendance.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
#                     إنشاء قاعدة البيانات
# ============================================================
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ---------- جدول المستخدمين ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------- جدول الشيفتات ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            shift_type TEXT NOT NULL,
            work_hours REAL NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            sick_leave_policy TEXT,
            overtime_rate REAL DEFAULT 1.0,
            work_days TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------- جدول الموظفين ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            phone TEXT,
            base_salary REAL DEFAULT 0,
            total_salary REAL DEFAULT 0,
            incentive REAL DEFAULT 0,
            medical_insurance REAL DEFAULT 0,
            social_insurance REAL DEFAULT 0,
            meal_allowance REAL DEFAULT 0,
            transport_allowance REAL DEFAULT 0,
            expat_allowance REAL DEFAULT 0,
            other_allowances REAL DEFAULT 0,
            annual_leave_balance REAL DEFAULT 0,
            shift_id INTEGER,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shift_id) REFERENCES shifts(id)
        )
    """)

    # ---------- جدول قواعد الخصم للشيفت ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shift_deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL,
            from_time TEXT NOT NULL,
            to_time TEXT NOT NULL,
            deduction_type TEXT NOT NULL,
            deduction_value REAL DEFAULT 0,
            FOREIGN KEY (shift_id) REFERENCES shifts(id) ON DELETE CASCADE
        )
    """)

    # ---------- جدول الحضور والانصراف ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            shift_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            check_in TEXT,
            check_out TEXT,
            status TEXT DEFAULT 'present',
            notes TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    # ---------- جدول الخصومات اليدوية ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS manual_deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            reason TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------- جدول ملفات الموظفين ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employee_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER DEFAULT 0,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)

    # ---------- جدول البصمات الخام ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw_punches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code TEXT NOT NULL,
            employee_id INTEGER,
            punch_time TEXT NOT NULL,
            punch_date TEXT NOT NULL,
            source TEXT DEFAULT 'upload',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_rp_code ON raw_punches(employee_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rp_emp_date ON raw_punches(employee_id, punch_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rp_date ON raw_punches(punch_date)")

    # ---------- جدول تعديلات الحضور اليدوية ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            day_status TEXT NOT NULL DEFAULT 'auto',
            check_in TEXT,
            check_out TEXT,
            annual_leave_deduction REAL DEFAULT 0,
            sick_leave_deduction REAL DEFAULT 0,
            notes TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, date),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_ao_emp_date ON attendance_overrides(employee_id, date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ao_date ON attendance_overrides(date)")

    # ---------- جدول إعدادات جهاز البصمة ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS device_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            device_ip TEXT DEFAULT '',
            device_port INTEGER DEFAULT 4370,
            device_password INTEGER DEFAULT 0,
            device_name TEXT DEFAULT 'جهاز البصمة الرئيسي',
            auto_listen INTEGER DEFAULT 0,
            last_connected TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_device = cur.execute(
        "SELECT id FROM device_settings WHERE id=1"
    ).fetchone()
    if not existing_device:
        cur.execute("""
            INSERT INTO device_settings
                (id, device_ip, device_port, device_password, device_name, auto_listen)
            VALUES (1, '', 4370, 0, 'جهاز البصمة الرئيسي', 0)
        """)

    # ---------- ✅ جدول الموظفين المسحوبين من الجهاز ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS device_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_uid INTEGER,
            user_id TEXT NOT NULL,
            name TEXT,
            privilege INTEGER DEFAULT 0,
            password TEXT,
            group_id TEXT,
            card INTEGER DEFAULT 0,
            device_ip TEXT,
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_du_user_id ON device_users(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_du_name ON device_users(name)")

    conn.commit()
    conn.close()

    migrate_employees()
    migrate_files_table()
    migrate_device_users_table()


# ============================================================
#              Migration
# ============================================================
def migrate_employees():
    conn = get_connection()
    cur = conn.cursor()

    existing_cols = [r[1] for r in cur.execute("PRAGMA table_info(employees)").fetchall()]

    new_cols = {
        "phone":                "TEXT",
        "total_salary":         "REAL DEFAULT 0",
        "incentive":            "REAL DEFAULT 0",
        "medical_insurance":    "REAL DEFAULT 0",
        "social_insurance":     "REAL DEFAULT 0",
        "meal_allowance":       "REAL DEFAULT 0",
        "transport_allowance":  "REAL DEFAULT 0",
        "expat_allowance":      "REAL DEFAULT 0",
        "other_allowances":     "REAL DEFAULT 0",
        "annual_leave_balance": "REAL DEFAULT 0",
        "created_at":           "TEXT",
    }

    added = False
    for col, col_type in new_cols.items():
        if col not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE employees ADD COLUMN {col} {col_type}")
                added = True
                print(f"[Migration] Added column: employees.{col}")
            except sqlite3.OperationalError as e:
                print(f"[Migration] Skipped {col}: {e}")

    if added:
        conn.commit()
        print("[Migration] Employees table updated successfully ✅")

    conn.close()


def migrate_files_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employee_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER DEFAULT 0,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def migrate_device_users_table():
    """إنشاء جدول device_users للنسخ القديمة (لو مش موجود)"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS device_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_uid INTEGER,
            user_id TEXT NOT NULL,
            name TEXT,
            privilege INTEGER DEFAULT 0,
            password TEXT,
            group_id TEXT,
            card INTEGER DEFAULT 0,
            device_ip TEXT,
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_du_user_id ON device_users(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_du_name ON device_users(name)")
    conn.commit()
    conn.close()


# ============================================================
#                       Users
# ============================================================
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def create_user(username, password):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        return True, "تم إنشاء الحساب بنجاح"
    except sqlite3.IntegrityError:
        return False, "اسم المستخدم موجود بالفعل"
    finally:
        conn.close()


def verify_user(username, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    return row is not None


def change_password(username, old_pw, new_pw):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_password(old_pw))
    ).fetchone()

    if not row:
        conn.close()
        return False, "كلمة المرور القديمة غير صحيحة"

    conn.execute(
        "UPDATE users SET password=? WHERE username=?",
        (hash_password(new_pw), username)
    )
    conn.commit()
    conn.close()
    return True, "تم تغيير كلمة المرور"


# ============================================================
#                     Employees
# ============================================================
def add_employee(data: dict):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO employees (
                code, name, department, phone,
                base_salary, total_salary, incentive,
                medical_insurance, social_insurance,
                meal_allowance, transport_allowance,
                expat_allowance, other_allowances,
                annual_leave_balance, shift_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("code", "").strip(),
            data.get("name", "").strip(),
            data.get("department", ""),
            data.get("phone", ""),
            float(data.get("base_salary", 0) or 0),
            float(data.get("total_salary", 0) or 0),
            float(data.get("incentive", 0) or 0),
            float(data.get("medical_insurance", 0) or 0),
            float(data.get("social_insurance", 0) or 0),
            float(data.get("meal_allowance", 0) or 0),
            float(data.get("transport_allowance", 0) or 0),
            float(data.get("expat_allowance", 0) or 0),
            float(data.get("other_allowances", 0) or 0),
            float(data.get("annual_leave_balance", 0) or 0),
            data.get("shift_id"),
        ))
        conn.commit()
        return True, "تم إضافة الموظف بنجاح ✅"
    except sqlite3.IntegrityError:
        return False, "كود الموظف مستخدم بالفعل"
    except Exception as e:
        return False, f"حدث خطأ: {e}"
    finally:
        conn.close()


def update_employee(emp_id: int, data: dict):
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE employees SET
                code = ?, name = ?, department = ?, phone = ?,
                base_salary = ?, total_salary = ?, incentive = ?,
                medical_insurance = ?, social_insurance = ?,
                meal_allowance = ?, transport_allowance = ?,
                expat_allowance = ?, other_allowances = ?,
                annual_leave_balance = ?, shift_id = ?
            WHERE id = ?
        """, (
            data.get("code", "").strip(),
            data.get("name", "").strip(),
            data.get("department", ""),
            data.get("phone", ""),
            float(data.get("base_salary", 0) or 0),
            float(data.get("total_salary", 0) or 0),
            float(data.get("incentive", 0) or 0),
            float(data.get("medical_insurance", 0) or 0),
            float(data.get("social_insurance", 0) or 0),
            float(data.get("meal_allowance", 0) or 0),
            float(data.get("transport_allowance", 0) or 0),
            float(data.get("expat_allowance", 0) or 0),
            float(data.get("other_allowances", 0) or 0),
            float(data.get("annual_leave_balance", 0) or 0),
            data.get("shift_id"),
            emp_id,
        ))
        conn.commit()
        return True, "تم تحديث بيانات الموظف ✅"
    except sqlite3.IntegrityError:
        return False, "كود الموظف مستخدم بالفعل"
    except Exception as e:
        return False, f"حدث خطأ: {e}"
    finally:
        conn.close()


def get_employees(include_inactive: bool = False):
    conn = get_connection()
    if include_inactive:
        rows = conn.execute("""
            SELECT e.*, s.name as shift_name
            FROM employees e
            LEFT JOIN shifts s ON e.shift_id = s.id
            ORDER BY e.active DESC, e.id DESC
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT e.*, s.name as shift_name
            FROM employees e
            LEFT JOIN shifts s ON e.shift_id = s.id
            WHERE e.active = 1
            ORDER BY e.id DESC
        """).fetchall()
    conn.close()
    return rows


def get_employee(emp_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM employees WHERE id=?", (emp_id,)).fetchone()
    conn.close()
    return row


def get_employee_by_code(code: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM employees WHERE code=?", (code,)).fetchone()
    conn.close()
    return row


def delete_employee(emp_id: int):
    conn = get_connection()
    conn.execute("UPDATE employees SET active=0 WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()


def hard_delete_employee(emp_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM employee_files WHERE employee_id=?", (emp_id,))
    conn.execute("DELETE FROM attendance WHERE employee_id=?", (emp_id,))
    conn.execute("DELETE FROM manual_deductions WHERE employee_id=?", (emp_id,))
    conn.execute("DELETE FROM raw_punches WHERE employee_id=?", (emp_id,))
    conn.execute("DELETE FROM attendance_overrides WHERE employee_id=?", (emp_id,))
    conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()


def toggle_employee_status(emp_id: int):
    conn = get_connection()
    row = conn.execute("SELECT active, name FROM employees WHERE id=?", (emp_id,)).fetchone()
    if not row:
        conn.close()
        return False, "الموظف غير موجود"

    new_status = 0 if row["active"] == 1 else 1
    conn.execute("UPDATE employees SET active=? WHERE id=?", (new_status, emp_id))
    conn.commit()
    conn.close()

    if new_status == 1:
        return True, f"تم تفعيل الموظف «{row['name']}» ✅"
    else:
        return True, f"تم إيقاف الموظف «{row['name']}» مؤقتاً ⏸"


def count_active_employees():
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as c FROM employees WHERE active=1").fetchone()
    conn.close()
    return row["c"] if row else 0


# ============================================================
#                       Shifts
# ============================================================
def add_shift(name, shift_type, work_hours, start_time, end_time,
              sick_leave, overtime_rate, work_days, deductions):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO shifts
        (name, shift_type, work_hours, start_time, end_time,
         sick_leave_policy, overtime_rate, work_days)
        VALUES (?,?,?,?,?,?,?,?)""",
        (name, shift_type, work_hours, start_time, end_time,
         sick_leave, overtime_rate, work_days))
    shift_id = cur.lastrowid

    for d in deductions:
        cur.execute("""INSERT INTO shift_deductions
            (shift_id, from_time, to_time, deduction_type, deduction_value)
            VALUES (?,?,?,?,?)""",
            (shift_id, d["from"], d["to"], d["type"], d["value"]))

    conn.commit()
    conn.close()
    return shift_id


def get_shifts():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM shifts ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_shift(shift_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM shifts WHERE id=?", (shift_id,)).fetchone()
    conn.close()
    return row


def get_shift_deductions(shift_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM shift_deductions WHERE shift_id=?",
        (shift_id,)
    ).fetchall()
    conn.close()
    return rows


def delete_shift(shift_id):
    conn = get_connection()
    conn.execute("DELETE FROM shift_deductions WHERE shift_id=?", (shift_id,))
    conn.execute("DELETE FROM shifts WHERE id=?", (shift_id,))
    conn.commit()
    conn.close()


def update_shift(shift_id, name, shift_type, work_hours, start_time, end_time,
                 sick_leave, overtime_rate, work_days, deductions):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""UPDATE shifts SET
        name=?, shift_type=?, work_hours=?, start_time=?, end_time=?,
        sick_leave_policy=?, overtime_rate=?, work_days=?
        WHERE id=?""",
        (name, shift_type, work_hours, start_time, end_time,
         sick_leave, overtime_rate, work_days, shift_id))

    cur.execute("DELETE FROM shift_deductions WHERE shift_id=?", (shift_id,))
    for d in deductions:
        cur.execute("""INSERT INTO shift_deductions
            (shift_id, from_time, to_time, deduction_type, deduction_value)
            VALUES (?,?,?,?,?)""",
            (shift_id, d["from"], d["to"], d["type"], d["value"]))

    conn.commit()
    conn.close()


# ============================================================
#                    Attendance
# ============================================================
def get_open_attendance(employee_id, date):
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM attendance
        WHERE employee_id=? AND date=? AND check_out IS NULL
        ORDER BY id DESC LIMIT 1
    """, (employee_id, date)).fetchone()
    conn.close()
    return row


def check_in(employee_id, shift_id, date, time_str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO attendance (employee_id, shift_id, date, check_in, status)
        VALUES (?,?,?,?,'present')
    """, (employee_id, shift_id, date, time_str))
    conn.commit()
    conn.close()


def check_out(attendance_id, time_str):
    conn = get_connection()
    conn.execute(
        "UPDATE attendance SET check_out=? WHERE id=?",
        (time_str, attendance_id)
    )
    conn.commit()
    conn.close()


def get_attendance_for_employee(employee_id, from_date, to_date):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM attendance
        WHERE employee_id=? AND date BETWEEN ? AND ?
        ORDER BY date
    """, (employee_id, from_date, to_date)).fetchall()
    conn.close()
    return rows


def get_all_attendance(from_date, to_date):
    conn = get_connection()
    rows = conn.execute("""
        SELECT a.*, e.name as employee_name, e.code as employee_code
        FROM attendance a
        LEFT JOIN employees e ON a.employee_id = e.id
        WHERE a.date BETWEEN ? AND ?
        ORDER BY a.date DESC, a.id DESC
    """, (from_date, to_date)).fetchall()
    conn.close()
    return rows


def delete_attendance(attendance_id):
    conn = get_connection()
    conn.execute("DELETE FROM attendance WHERE id=?", (attendance_id,))
    conn.commit()
    conn.close()


# ============================================================
#                Manual Deductions
# ============================================================
def add_manual_deduction(employee_id, amount, reason):
    conn = get_connection()
    conn.execute("""
        INSERT INTO manual_deductions (employee_id, amount, reason)
        VALUES (?,?,?)
    """, (employee_id, amount, reason))
    conn.commit()
    conn.close()


def get_manual_deductions(employee_id, from_date=None, to_date=None):
    conn = get_connection()
    if from_date and to_date:
        rows = conn.execute("""
            SELECT * FROM manual_deductions
            WHERE employee_id=? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (employee_id, from_date, to_date)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM manual_deductions
            WHERE employee_id=?
            ORDER BY date DESC
        """, (employee_id,)).fetchall()
    conn.close()
    return rows


def delete_manual_deduction(deduction_id):
    conn = get_connection()
    conn.execute("DELETE FROM manual_deductions WHERE id=?", (deduction_id,))
    conn.commit()
    conn.close()


# ============================================================
#                Employee Files
# ============================================================
def add_employee_file(employee_id, file_name, file_path, file_type="", file_size=0):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO employee_files
                (employee_id, file_name, file_path, file_type, file_size)
            VALUES (?,?,?,?,?)
        """, (employee_id, file_name, file_path, file_type, int(file_size)))
        conn.commit()
        return True, "تم إضافة الملف ✅"
    except Exception as e:
        return False, f"حدث خطأ: {e}"
    finally:
        conn.close()


def get_employee_files(employee_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM employee_files
        WHERE employee_id=?
        ORDER BY uploaded_at DESC
    """, (employee_id,)).fetchall()
    conn.close()
    return rows


def get_employee_file(file_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM employee_files WHERE id=?", (file_id,)).fetchone()
    conn.close()
    return row


def delete_employee_file(file_id):
    conn = get_connection()
    row = conn.execute("SELECT file_path FROM employee_files WHERE id=?", (file_id,)).fetchone()
    conn.execute("DELETE FROM employee_files WHERE id=?", (file_id,))
    conn.commit()
    conn.close()
    return row["file_path"] if row else None


def delete_all_employee_files(employee_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT file_path FROM employee_files WHERE employee_id=?",
        (employee_id,)
    ).fetchall()
    conn.execute("DELETE FROM employee_files WHERE employee_id=?", (employee_id,))
    conn.commit()
    conn.close()
    return [r["file_path"] for r in rows]


def count_employee_files(employee_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM employee_files WHERE employee_id=?",
        (employee_id,)
    ).fetchone()
    conn.close()
    return row["c"] if row else 0


# ============================================================
#                Raw Punches
# ============================================================
def init_raw_punches_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_punches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code TEXT NOT NULL,
            employee_id INTEGER,
            punch_time TEXT NOT NULL,
            punch_date TEXT NOT NULL,
            source TEXT DEFAULT 'upload',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rp_code ON raw_punches(employee_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rp_emp_date ON raw_punches(employee_id, punch_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rp_date ON raw_punches(punch_date)")
    conn.commit()
    conn.close()


def add_raw_punches_bulk(records):
    if not records:
        return 0, 0

    conn = get_connection()
    cur = conn.cursor()

    emp_rows = cur.execute("SELECT id, code FROM employees").fetchall()
    code_to_id = {r["code"]: r["id"] for r in emp_rows}

    inserted = 0
    skipped = 0

    for rec in records:
        code = str(rec.get("employee_code", "")).strip()
        punch_time = rec.get("punch_time")

        if not code or not punch_time:
            skipped += 1
            continue

        emp_id = code_to_id.get(code)
        if emp_id is None:
            skipped += 1
            continue

        punch_date = punch_time.split(" ")[0]

        cur.execute("""
            INSERT INTO raw_punches
                (employee_code, employee_id, punch_time, punch_date, source)
            VALUES (?, ?, ?, ?, 'upload')
        """, (code, emp_id, punch_time, punch_date))
        inserted += 1

    conn.commit()
    conn.close()
    return inserted, skipped


def get_raw_punches_by_date(employee_id, date_str):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM raw_punches
        WHERE employee_id=? AND punch_date=?
        ORDER BY punch_time ASC
    """, (employee_id, date_str)).fetchall()
    conn.close()
    return rows


def get_all_raw_punches_in_range(from_date, to_date):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM raw_punches
        WHERE punch_date BETWEEN ? AND ?
        ORDER BY employee_id, punch_time
    """, (from_date, to_date)).fetchall()
    conn.close()
    return rows


def delete_raw_punches_range(employee_id, from_date, to_date):
    conn = get_connection()
    conn.execute("""
        DELETE FROM raw_punches
        WHERE employee_id=? AND punch_date BETWEEN ? AND ?
    """, (employee_id, from_date, to_date))
    conn.commit()
    conn.close()


def delete_all_raw_punches():
    conn = get_connection()
    conn.execute("DELETE FROM raw_punches")
    conn.commit()
    conn.close()


def count_raw_punches():
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as c FROM raw_punches").fetchone()
    conn.close()
    return row["c"] if row else 0


def count_raw_punches_for_employee(employee_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM raw_punches WHERE employee_id=?",
        (employee_id,)
    ).fetchone()
    conn.close()
    return row["c"] if row else 0


# ============================================================
#        Attendance Overrides (تعديلات يدوية على أيام الحضور)
# ============================================================
def init_attendance_overrides_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            day_status TEXT NOT NULL DEFAULT 'auto',
            check_in TEXT,
            check_out TEXT,
            annual_leave_deduction REAL DEFAULT 0,
            sick_leave_deduction REAL DEFAULT 0,
            notes TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, date),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ao_emp_date ON attendance_overrides(employee_id, date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ao_date ON attendance_overrides(date)")
    conn.commit()
    conn.close()


def get_attendance_override(employee_id, date_str):
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM attendance_overrides
        WHERE employee_id=? AND date=?
    """, (employee_id, date_str)).fetchone()
    conn.close()
    return row


def get_overrides_in_range(employee_id, from_date, to_date):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM attendance_overrides
        WHERE employee_id=? AND date BETWEEN ? AND ?
    """, (employee_id, from_date, to_date)).fetchall()
    conn.close()
    return rows


def get_all_overrides_in_range(from_date, to_date):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM attendance_overrides
        WHERE date BETWEEN ? AND ?
    """, (from_date, to_date)).fetchall()
    conn.close()
    return rows


def save_attendance_override(employee_id, date_str, data):
    conn = get_connection()
    cur = conn.cursor()
    try:
        existing = cur.execute("""
            SELECT id FROM attendance_overrides WHERE employee_id=? AND date=?
        """, (employee_id, date_str)).fetchone()

        if existing:
            cur.execute("""
                UPDATE attendance_overrides SET
                    day_status=?, check_in=?, check_out=?,
                    annual_leave_deduction=?, sick_leave_deduction=?,
                    notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE employee_id=? AND date=?
            """, (
                data.get("day_status", "auto"),
                data.get("check_in"),
                data.get("check_out"),
                float(data.get("annual_leave_deduction", 0) or 0),
                float(data.get("sick_leave_deduction", 0) or 0),
                data.get("notes", ""),
                employee_id, date_str,
            ))
        else:
            cur.execute("""
                INSERT INTO attendance_overrides
                    (employee_id, date, day_status, check_in, check_out,
                     annual_leave_deduction, sick_leave_deduction, notes)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                employee_id, date_str,
                data.get("day_status", "auto"),
                data.get("check_in"),
                data.get("check_out"),
                float(data.get("annual_leave_deduction", 0) or 0),
                float(data.get("sick_leave_deduction", 0) or 0),
                data.get("notes", ""),
            ))
        conn.commit()
        return True, "تم حفظ التعديل ✅"
    except Exception as e:
        return False, f"حدث خطأ: {e}"
    finally:
        conn.close()


def delete_attendance_override(employee_id, date_str):
    conn = get_connection()
    conn.execute(
        "DELETE FROM attendance_overrides WHERE employee_id=? AND date=?",
        (employee_id, date_str)
    )
    conn.commit()
    conn.close()


def delete_all_overrides_for_employee(employee_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM attendance_overrides WHERE employee_id=?",
        (employee_id,)
    )
    conn.commit()
    conn.close()


def count_overrides_for_employee(employee_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM attendance_overrides WHERE employee_id=?",
        (employee_id,)
    ).fetchone()
    conn.close()
    return row["c"] if row else 0


def count_all_overrides():
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as c FROM attendance_overrides").fetchone()
    conn.close()
    return row["c"] if row else 0


# ============================================================
#        حساب رصيد الإجازة السنوية
# ============================================================
def get_annual_leave_used(employee_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(annual_leave_deduction), 0) as total
        FROM attendance_overrides
        WHERE employee_id=? AND day_status='annual_leave'
    """, (employee_id,)).fetchone()
    conn.close()
    return float(row["total"]) if row else 0.0


def get_all_annual_leave_used():
    conn = get_connection()
    rows = conn.execute("""
        SELECT employee_id, COALESCE(SUM(annual_leave_deduction), 0) as total
        FROM attendance_overrides
        WHERE day_status='annual_leave'
        GROUP BY employee_id
    """).fetchall()
    conn.close()
    return {r["employee_id"]: float(r["total"]) for r in rows}


def get_annual_leave_used_in_range(employee_id, from_date, to_date):
    conn = get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(annual_leave_deduction), 0) as total
        FROM attendance_overrides
        WHERE employee_id=? AND day_status='annual_leave'
          AND date BETWEEN ? AND ?
    """, (employee_id, from_date, to_date)).fetchone()
    conn.close()
    return float(row["total"]) if row else 0.0


def get_annual_leave_used_except_date(employee_id, exclude_date):
    conn = get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(annual_leave_deduction), 0) as total
        FROM attendance_overrides
        WHERE employee_id=? AND day_status='annual_leave'
          AND date != ?
    """, (employee_id, exclude_date)).fetchone()
    conn.close()
    return float(row["total"]) if row else 0.0


def get_annual_leave_remaining(employee_id):
    emp = get_employee(employee_id)
    if not emp:
        return 0.0, 0.0, 0.0
    initial = float(emp["annual_leave_balance"] or 0)
    used = get_annual_leave_used(employee_id)
    return initial, used, initial - used


# ============================================================
#         البصمة الحية (Live Device Punch)
# ============================================================
def add_live_punch(employee_code: str, punch_time: str, source_device: str = "live"):
    conn = get_connection()
    cur = conn.cursor()
    try:
        emp = cur.execute(
            "SELECT id FROM employees WHERE code=?", (employee_code,)
        ).fetchone()
        if not emp:
            conn.close()
            return False, f"كود {employee_code} غير مسجل في النظام", None

        emp_id = emp["id"]
        punch_date = punch_time.split(" ")[0]

        dup = cur.execute("""
            SELECT id FROM raw_punches
            WHERE employee_code=? AND punch_time=?
        """, (employee_code, punch_time)).fetchone()

        if dup:
            conn.close()
            return False, "بصمة مكررة (تم تجاهلها)", emp_id

        cur.execute("""
            INSERT INTO raw_punches
                (employee_code, employee_id, punch_time, punch_date, source)
            VALUES (?, ?, ?, ?, ?)
        """, (employee_code, emp_id, punch_time, punch_date, source_device))
        conn.commit()
        conn.close()
        return True, "تم تسجيل البصمة ✅", emp_id
    except Exception as e:
        conn.close()
        return False, f"خطأ: {e}", None


# ============================================================
#         إعدادات جهاز البصمة (Device Settings)
# ============================================================
def get_device_settings():
    conn = get_connection()
    row = conn.execute("SELECT * FROM device_settings WHERE id=1").fetchone()
    conn.close()
    return row


def save_device_settings(ip: str, port: int, password: int, name: str, auto_listen: int = 0):
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM device_settings WHERE id=1").fetchone()
        if existing:
            conn.execute("""
                UPDATE device_settings SET
                    device_ip=?, device_port=?, device_password=?, device_name=?,
                    auto_listen=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=1
            """, (ip, int(port), int(password), name, int(auto_listen)))
        else:
            conn.execute("""
                INSERT INTO device_settings
                    (id, device_ip, device_port, device_password, device_name, auto_listen)
                VALUES (1,?,?,?,?,?)
            """, (ip, int(port), int(password), name, int(auto_listen)))
        conn.commit()
        return True
    except Exception as e:
        print(f"[Device Settings] خطأ: {e}")
        return False
    finally:
        conn.close()


def update_device_last_connected(timestamp: str):
    conn = get_connection()
    conn.execute("""
        UPDATE device_settings SET last_connected=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=1
    """, (timestamp,))
    conn.commit()
    conn.close()


def get_recent_live_punches(limit: int = 100):
    conn = get_connection()
    rows = conn.execute("""
        SELECT rp.*, e.name as employee_name
        FROM raw_punches rp
        LEFT JOIN employees e ON rp.employee_id = e.id
        ORDER BY rp.id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


# ============================================================
#         ✅ الموظفون المسحوبون من الجهاز (Device Users)
# ============================================================
def init_device_users_table():
    """إنشاء جدول device_users (يُستدعى تلقائياً من init_db)"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS device_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_uid INTEGER,
            user_id TEXT NOT NULL,
            name TEXT,
            privilege INTEGER DEFAULT 0,
            password TEXT,
            group_id TEXT,
            card INTEGER DEFAULT 0,
            device_ip TEXT,
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_du_user_id ON device_users(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_du_name ON device_users(name)")
    conn.commit()
    conn.close()


def save_pulled_device_users(users: list, device_ip: str = ""):
    """
    حفظ/تحديث قائمة الموظفين المسحوبين من الجهاز.
    - users: list of dicts { user_id, name, privilege, password, group_id, card, uid }
    - device_ip: عنوان الجهاز (للمرجعية)
    
    يستبدل البيانات القديمة ويحفظ الجديدة (بنفس user_id → update).
    Returns: (inserted, updated, failed)
    """
    if not users:
        return 0, 0, 0

    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    updated = 0
    failed = 0

    try:
        for u in users:
            user_id = str(u.get("user_id", "")).strip()
            if not user_id:
                failed += 1
                continue

            name = str(u.get("name", "") or "").strip()
            privilege = int(u.get("privilege", 0) or 0)
            password = str(u.get("password", "") or "")
            group_id = str(u.get("group_id", "") or "")
            card = int(u.get("card", 0) or 0)
            device_uid = u.get("uid")
            if device_uid is not None:
                try:
                    device_uid = int(device_uid)
                except (TypeError, ValueError):
                    device_uid = None

            existing = cur.execute(
                "SELECT id FROM device_users WHERE user_id=?", (user_id,)
            ).fetchone()

            if existing:
                cur.execute("""
                    UPDATE device_users SET
                        device_uid=?, name=?, privilege=?, password=?,
                        group_id=?, card=?, device_ip=?,
                        synced_at=CURRENT_TIMESTAMP
                    WHERE user_id=?
                """, (
                    device_uid, name, privilege, password,
                    group_id, card, device_ip, user_id,
                ))
                updated += 1
            else:
                cur.execute("""
                    INSERT INTO device_users
                        (device_uid, user_id, name, privilege, password,
                         group_id, card, device_ip)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    device_uid, user_id, name, privilege, password,
                    group_id, card, device_ip,
                ))
                inserted += 1

        conn.commit()
        return inserted, updated, failed
    except Exception as e:
        print(f"[Device Users] خطأ: {e}")
        conn.rollback()
        return inserted, updated, failed + 1
    finally:
        conn.close()


def get_device_users():
    """جلب كل الموظفين المسحوبين من الجهاز (مرتبين بالكود)"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM device_users
        ORDER BY user_id ASC
    """).fetchall()
    conn.close()
    return rows


def get_device_user(user_id: str):
    """جلب موظف واحد من الجهاز بالكود"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM device_users WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row


def get_unregistered_device_users():
    """
    جلب الموظفين الموجودين على الجهاز لكن غير مسجلين في النظام.
    (أي device_users.user_id ليس موجوداً في employees.code)
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT du.*
        FROM device_users du
        LEFT JOIN employees e ON du.user_id = e.code
        WHERE e.id IS NULL
        ORDER BY du.user_id ASC
    """).fetchall()
    conn.close()
    return rows


def get_registered_device_users():
    """
    جلب الموظفين الموجودين على الجهاز والمسجلين في النظام أيضاً.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT du.*, e.id as emp_id, e.name as emp_name
        FROM device_users du
        INNER JOIN employees e ON du.user_id = e.code
        ORDER BY du.user_id ASC
    """).fetchall()
    conn.close()
    return rows


def count_device_users():
    """عدد الموظفين المسحوبين من الجهاز"""
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as c FROM device_users").fetchone()
    conn.close()
    return row["c"] if row else 0


def count_unregistered_device_users():
    """عدد الموظفين على الجهاز غير المسجلين في النظام"""
    conn = get_connection()
    row = conn.execute("""
        SELECT COUNT(*) as c
        FROM device_users du
        LEFT JOIN employees e ON du.user_id = e.code
        WHERE e.id IS NULL
    """).fetchone()
    conn.close()
    return row["c"] if row else 0


def delete_device_user(user_id: str):
    """حذف موظف من قائمة الجهاز (لا يؤثر على الجهاز نفسه)"""
    conn = get_connection()
    conn.execute("DELETE FROM device_users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def delete_all_device_users():
    """حذف كل قائمة الموظفين المسحوبين من الجهاز"""
    conn = get_connection()
    conn.execute("DELETE FROM device_users")
    conn.commit()
    conn.close()


def get_last_device_sync_time():
    """وقت آخر سحب للموظفين من الجهاز"""
    conn = get_connection()
    row = conn.execute(
        "SELECT MAX(synced_at) as last_sync FROM device_users"
    ).fetchone()
    conn.close()
    return row["last_sync"] if row else None


# ============================================================
#                    تشغيل مباشر للاختبار
# ============================================================
if __name__ == "__main__":
    init_db()
    print("✅ Database initialized successfully")
    print(f"📁 File: {os.path.abspath(DB_NAME)}")
    print("\n📊 الجداول:")
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) as c FROM {t['name']}").fetchone()["c"]
        print(f"   • {t['name']:25s} → {count} سجل")
    conn.close()