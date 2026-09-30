import re
import csv
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QFrame, QGridLayout, QLineEdit,
    QFileDialog, QScrollArea, QDialog, QAbstractItemView,
    QSizePolicy, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt, QDate, QRegularExpression
from PySide6.QtGui import QColor, QFont, QRegularExpressionValidator

from database import (
    get_employees, get_employee, get_shift, get_shift_deductions,
    get_raw_punches_by_date, get_all_raw_punches_in_range,
    add_raw_punches_bulk, delete_all_raw_punches, count_raw_punches,
    get_attendance_override, save_attendance_override,
    delete_attendance_override, get_all_overrides_in_range,
    get_overrides_in_range,
    get_annual_leave_used, get_all_annual_leave_used,
    get_annual_leave_used_in_range, get_annual_leave_used_except_date,
)


# ============================================================
#     نظام ألوان مسطح وهادئ (تصميم برامج مكتبية / إدارية)
# ============================================================
BG          = "#eef0f3"
SURFACE     = "#ffffff"
SURFACE_2   = "#f8f9fa"
SURFACE_3   = "#f1f3f5"
BORDER      = "#d8dce1"
BORDER_2    = "#c3c9d0"
DIVIDER     = "#e8ebee"

TEXT        = "#1f2933"
TEXT_SEC    = "#4b5563"
TEXT_MUTED  = "#7b8794"

PRIMARY     = "#1f4e8c"
PRIMARY_HOV = "#1a4275"
PRIMARY_DK  = "#153561"
PRIMARY_BG  = "#e8eff8"
PRIMARY_BRD = "#b6c8e0"

SUCCESS     = "#2f7d4f"
SUCCESS_HOV = "#276a43"
SUCCESS_BG  = "#eaf4ee"
SUCCESS_BRD = "#b9d9c5"

DANGER      = "#b3372f"
DANGER_HOV  = "#992d26"
DANGER_BG   = "#fbeceb"
DANGER_BRD  = "#e6b9b5"

WARNING     = "#a86a12"
WARNING_HOV = "#8f590d"
WARNING_BG  = "#fbf3e4"
WARNING_BRD = "#e6cf9f"

INFO        = "#2a6f8f"
INFO_BG     = "#e9f2f6"
INFO_BRD    = "#b5d2df"

PURPLE      = "#5f4b8b"
PURPLE_BG   = "#efecf5"
PURPLE_BRD  = "#cfc6e0"

PINK        = "#9a3f62"
PINK_BG     = "#f7ecf0"
PINK_BRD    = "#e2bfcd"

GRAY        = "#616e7c"
GRAY_BG     = "#f0f2f4"
GRAY_BRD    = "#d8dce1"

ROW_ALT     = "#f8f9fa"
HEADER_BG   = "#f1f3f5"

FONT_FAMILY = "Segoe UI, Tahoma, Arial, sans-serif"

RADIUS = "4px"

ARABIC_DAYS = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
PY_WD_TO_AR = {5: 0, 6: 1, 0: 2, 1: 3, 2: 4, 3: 5, 4: 6}

OVERTIME_CUTOFF = "02:00"

DAY_STATUS_LABELS = {
    "auto":         "تلقائي",
    "present":      "حاضر",
    "absent":       "غائب",
    "annual_leave": "إجازة سنوية",
    "sick_leave":   "إجازة مرضية",
    "work_injury":  "إصابة عمل",
}

SICK_POLICY_LABELS = {
    "none":    "بدون خصم",
    "quarter": "خصم ربع يوم",
    "half":    "خصم نص يوم",
    "full":    "خصم يوم كامل",
}

SICK_POLICY_VALUES = {
    "none": 0.0,
    "quarter": 0.25,
    "half": 0.5,
    "full": 1.0,
}

# (النص، اللون، الخلفية، الحد، رمز) — الرمز فارغ عمداً (بدون أيقونات)
STATUS_STYLE = {
    "present":      ("حاضر",         SUCCESS, SUCCESS_BG, SUCCESS_BRD, ""),
    "absent":       ("غائب",         DANGER,  DANGER_BG,  DANGER_BRD,  ""),
    "annual_leave": ("إجازة سنوية",  INFO,    INFO_BG,    INFO_BRD,    ""),
    "sick_leave":   ("إجازة مرضية",  WARNING, WARNING_BG, WARNING_BRD, ""),
    "work_injury":  ("إصابة عمل",    PINK,    PINK_BG,    PINK_BRD,    ""),
    "weekly_holiday": ("راحة أسبوعية", GRAY, GRAY_BG, GRAY_BRD, ""),
}

NOTE_KINDS = {
    "info":    (INFO,    INFO_BG,    INFO_BRD),
    "success": (SUCCESS, SUCCESS_BG, SUCCESS_BRD),
    "danger":  (DANGER,  DANGER_BG,  DANGER_BRD),
    "warning": (WARNING, WARNING_BG, WARNING_BRD),
    "pink":    (PINK,    PINK_BG,    PINK_BRD),
}


def _fmt_num(v):
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return "0"
    return f"{fv:.0f}" if fv == int(fv) else f"{fv:.1f}"


def _badge_style(color, bg, brd, size=11, pad="3px 10px"):
    return f"""
        QLabel {{
            background:{bg}; color:{color};
            border:1px solid {brd}; padding:{pad};
            border-radius:3px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
    """


def _card_style(object_name):
    return f"""
        QFrame#{object_name} {{
            background:{SURFACE};
            border:1px solid {BORDER};
            border-radius:{RADIUS};
        }}
    """


def _table_style(item_padding="8px 8px"):
    return f"""
        QTableWidget {{
            background:{SURFACE}; border:none; color:{TEXT};
            font-size:12px; outline:none;
            selection-background-color:{PRIMARY_BG};
            selection-color:{TEXT}; gridline-color:{DIVIDER};
            font-family:{FONT_FAMILY};
            alternate-background-color:{ROW_ALT};
        }}
        QTableWidget::item {{
            padding:{item_padding}; border-bottom:1px solid {DIVIDER};
        }}
        QTableWidget::item:selected {{
            background:{PRIMARY_BG}; color:{TEXT};
        }}
        QHeaderView::section {{
            background:{HEADER_BG}; color:{TEXT_SEC};
            padding:10px 8px; border:none;
            border-bottom:1px solid {BORDER_2};
            border-left:1px solid {DIVIDER};
            font-weight:700; font-size:11px;
            font-family:{FONT_FAMILY};
        }}
        QScrollBar:vertical {{
            width:10px; background:{SURFACE_3};
            margin:0;
        }}
        QScrollBar::handle:vertical {{
            background:{BORDER_2}; border-radius:2px; min-height:40px;
            margin:2px;
        }}
        QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{ height:0; }}
        QScrollBar:horizontal {{
            height:10px; background:{SURFACE_3}; margin:0;
        }}
        QScrollBar::handle:horizontal {{
            background:{BORDER_2}; border-radius:2px; min-width:40px;
            margin:2px;
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{ width:0; }}
    """


def _primary_btn_style(size=12):
    return f"""
        QPushButton {{
            background:{PRIMARY}; color:white;
            border:1px solid {PRIMARY}; border-radius:{RADIUS};
            padding:0 18px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ background:{PRIMARY_HOV}; border-color:{PRIMARY_HOV}; }}
        QPushButton:pressed {{ background:{PRIMARY_DK}; border-color:{PRIMARY_DK}; }}
    """


def _secondary_btn_style(size=12):
    return f"""
        QPushButton {{
            background:{SURFACE}; color:{TEXT};
            border:1px solid {BORDER_2}; border-radius:{RADIUS};
            padding:0 18px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ background:{SURFACE_3}; border-color:{TEXT_MUTED}; }}
        QPushButton:pressed {{ background:{DIVIDER}; }}
    """


def _danger_btn_style(size=12):
    return f"""
        QPushButton {{
            background:{SURFACE}; color:{DANGER};
            border:1px solid {DANGER_BRD}; border-radius:{RADIUS};
            padding:0 16px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ background:{DANGER_BG}; border-color:{DANGER}; }}
        QPushButton:pressed {{ background:#f5d9d6; }}
    """


def _row_btn_style(size=11):
    return f"""
        QPushButton {{
            background:{SURFACE}; color:{PRIMARY};
            border:1px solid {PRIMARY_BRD}; border-radius:{RADIUS};
            padding:0 12px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ background:{PRIMARY_BG}; border-color:{PRIMARY}; }}
    """


# ============================================================
#                    Helpers: Time & Date
# ============================================================
def time_to_minutes(t: str) -> int:
    if not t:
        return 0
    try:
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return 0


def datetime_to_minutes(dt_str: str) -> int:
    if not dt_str:
        return 0
    try:
        time_part = dt_str.split(" ")[1] if " " in dt_str else dt_str
        parts = time_part.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return 0


def _parse_full_datetime(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def format_time_only(dt_str: str) -> str:
    if not dt_str:
        return "—"
    try:
        time_part = dt_str.split(" ")[1] if " " in dt_str else dt_str
        parts = time_part.split(":")
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    except (ValueError, IndexError):
        return dt_str


def format_minutes_ar(minutes: int) -> str:
    if minutes <= 0:
        return "—"
    h = minutes // 60
    m = minutes % 60
    if h > 0 and m > 0:
        return f"{h}س {m}د"
    if h > 0:
        return f"{h}س"
    return f"{m}د"


def format_overtime_ar(minutes: int) -> str:
    if minutes <= 0:
        return "—"
    return f"{minutes / 60:.2f}س"


def parse_datetime_flexible(s: str):
    if not s:
        return None
    s = str(s).strip()
    formats = [
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


# ============================================================
#   Helpers: جمع بصمات يوم عمل (يشمل فجر اليوم التالي)
# ============================================================
def _combine_punches_for_day(punches_by_emp_date, employee_id, date_str,
                             cutoff=OVERTIME_CUTOFF):
    cutoff_min = time_to_minutes(cutoff)
    by_date = punches_by_emp_date.get(employee_id, {})

    today_all = by_date.get(date_str, [])
    next_date = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    next_all = by_date.get(next_date, [])

    today_ok = [p for p in today_all if datetime_to_minutes(p["punch_time"]) > cutoff_min]
    next_ok = [p for p in next_all if datetime_to_minutes(p["punch_time"]) <= cutoff_min]

    return sorted(today_ok + next_ok, key=lambda x: x["punch_time"])


def get_punches_for_day(employee_id, date_str, cutoff=OVERTIME_CUTOFF):
    cutoff_min = time_to_minutes(cutoff)

    today_punches = [
        p for p in get_raw_punches_by_date(employee_id, date_str)
        if datetime_to_minutes(p["punch_time"]) > cutoff_min
    ]

    next_date = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    next_punches = [
        p for p in get_raw_punches_by_date(employee_id, next_date)
        if datetime_to_minutes(p["punch_time"]) <= cutoff_min
    ]

    return sorted(today_punches + next_punches, key=lambda x: x["punch_time"])


# ============================================================
#          قارئ ملف البصمة (Excel / CSV / TXT)
# ============================================================
def _read_text_with_encoding(file_path: str) -> str:
    with open(file_path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace")
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    sample = raw[:400]
    if b"\x00" in sample:
        try:
            return raw.decode("utf-16-le")
        except UnicodeDecodeError:
            try:
                return raw.decode("utf-16-be")
            except UnicodeDecodeError:
                pass
    for enc in ("utf-8", "cp1256", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _read_xlsx_rows(file_path: str):
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ImportError(
            "مكتبة openpyxl غير مثبتة.\n\n"
            "لتثبيتها: python -m pip install openpyxl"
        )
    wb = load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append(["" if v is None else str(v).strip() for v in row])
    wb.close()
    return rows


def _read_csv_rows(file_path: str):
    content = _read_text_with_encoding(file_path)
    rows = []
    for row in csv.reader(content.splitlines()):
        rows.append([cell.strip() for cell in row])
    return rows


def _is_header_row(cells):
    joined = " ".join(c.lower() for c in cells if c)
    return ("no." in joined or "no " in joined) and "date" in joined


def _extract_code_and_time(cells):
    time_idx = None
    for i, c in enumerate(cells):
        if not c:
            continue
        if re.search(r"\d{1,4}[/\-]\d{1,2}[/\-]\d{2,4}", str(c)) and \
           re.search(r"\d{1,2}:\d{2}", str(c)):
            time_idx = i
            break
    if time_idx is None or time_idx == 0:
        return None, None
    code = None
    for i in range(time_idx - 1, -1, -1):
        c = (cells[i] or "").strip()
        if c and re.fullmatch(r"\d+", str(c)):
            code = str(c)
            break
    if not code:
        return None, None
    dt = parse_datetime_flexible(str(cells[time_idx]))
    return code, dt


def parse_punch_file(file_path: str):
    records = []
    skipped = 0
    ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""

    if ext in ("xlsx", "xlsm", "xls"):
        rows = _read_xlsx_rows(file_path)
        for cells in rows:
            if not cells or not any(cells):
                continue
            if _is_header_row(cells):
                continue
            code, punch_time = _extract_code_and_time(cells)
            if code and punch_time:
                records.append({"employee_code": code, "punch_time": punch_time})
            else:
                skipped += 1
        return records, skipped

    if ext == "csv":
        rows = _read_csv_rows(file_path)
        for cells in rows:
            if not cells or not any(cells):
                continue
            if _is_header_row(cells):
                continue
            code, punch_time = _extract_code_and_time(cells)
            if code and punch_time:
                records.append({"employee_code": code, "punch_time": punch_time})
            else:
                skipped += 1
        return records, skipped

    content = _read_text_with_encoding(file_path)
    for line in content.splitlines():
        raw = line.rstrip("\r\n")
        if not raw.strip():
            continue
        if "\t" in raw:
            cells = [c.strip() for c in raw.split("\t")]
        elif re.search(r"\s{2,}", raw):
            cells = [c.strip() for c in re.split(r"\s{2,}", raw)]
        else:
            cells = raw.split()
        if _is_header_row(cells):
            continue
        code, punch_time = _extract_code_and_time(cells)
        if code and punch_time:
            records.append({"employee_code": code, "punch_time": punch_time})
        else:
            skipped += 1
    return records, skipped


# ============================================================
#                    Helpers: Deduction
# ============================================================
def compute_deduction_for_checkin(check_in_min: int, rules):
    for rule in rules:
        from_min = time_to_minutes(rule["from_time"])
        to_min = time_to_minutes(rule["to_time"])
        if from_min <= check_in_min <= to_min:
            dtype = rule["deduction_type"]
            if dtype == "minutes":
                v = int(rule["deduction_value"] or 0)
                return f"{v} دقيقة", v
            elif dtype == "quarter":
                return "ربع يوم", 0
            elif dtype == "half":
                return "نص يوم", 0
            elif dtype == "full":
                return "يوم كامل", 0
    return "—", 0


def compute_deduction_for_checkout(check_out_min: int, rules):
    for rule in rules:
        from_min = time_to_minutes(rule["from_time"])
        to_min = time_to_minutes(rule["to_time"])
        if from_min <= check_out_min <= to_min:
            dtype = rule["deduction_type"]
            if dtype == "minutes":
                v = int(rule["deduction_value"] or 0)
                return f"{v} دقيقة", v
            elif dtype == "quarter":
                return "ربع يوم", 0
            elif dtype == "half":
                return "نص يوم", 0
            elif dtype == "full":
                return "يوم كامل", 0
    return "—", 0


# ============================================================
#       حساب ملخص يوم واحد (مع دعم التعديلات اليدوية)
# ============================================================
def compute_day_stats(employee, shift, punches, override=None, is_working_day=True):
    result = {
        "is_working_day": is_working_day,
        "status": "no_shift",
        "day_type": "no_shift",
        "check_in": None,
        "check_out": None,
        "delay_min": 0,
        "early_leave_min": 0,
        "overtime_min": 0,
        "deduction_label": "—",
        "deduction_minutes": 0,
        "early_leave_deduction_label": "—",
        "early_leave_deduction_minutes": 0,
        "annual_leave_deduction": 0.0,
        "sick_leave_deduction": 0.0,
        "notes": "",
        "override_applied": False,
    }

    if not shift:
        if override and override["day_status"] in ("annual_leave", "sick_leave", "work_injury"):
            result["status"] = override["day_status"]
            result["day_type"] = override["day_status"]
            result["override_applied"] = True
            result["notes"] = override["notes"] or ""
            result["annual_leave_deduction"] = float(override["annual_leave_deduction"] or 0)
            result["sick_leave_deduction"] = float(override["sick_leave_deduction"] or 0)
        return result

    if not is_working_day:
        if override and override["day_status"] not in ("auto", "weekly_holiday"):
            result["status"] = override["day_status"]
            result["day_type"] = override["day_status"]
            result["override_applied"] = True
            result["notes"] = override["notes"] or ""
            result["check_in"] = override["check_in"]
            result["check_out"] = override["check_out"]
            result["annual_leave_deduction"] = float(override["annual_leave_deduction"] or 0)
            result["sick_leave_deduction"] = float(override["sick_leave_deduction"] or 0)
        else:
            result["status"] = "weekly_holiday"
            result["day_type"] = "weekly_holiday"
        return result

    def _calc_times(ci, co):
        delay = 0
        overtime = 0
        early_leave = 0
        ded_label = "—"
        ded_min = 0
        early_ded_label = "—"
        early_ded_min = 0

        shift_start = time_to_minutes(shift["start_time"])
        shift_end = time_to_minutes(shift["end_time"])

        if shift["shift_type"] == "evening" and shift_end <= shift_start:
            shift_end += 24 * 60

        rules = get_shift_deductions(shift["id"])

        ref_date = None
        ci_min = 0
        co_min = 0

        if ci:
            ci_dt = _parse_full_datetime(ci)
            if ci_dt is not None:
                ref_date = ci_dt.date()
                base = datetime.combine(ref_date, datetime.min.time())
                ci_min = int((ci_dt - base).total_seconds() // 60)
            else:
                ci_min = datetime_to_minutes(ci)

            delay = max(0, ci_min - shift_start)
            dl, dm = compute_deduction_for_checkin(ci_min, rules)
            ded_label = dl
            ded_min = dm

        if co:
            co_dt = _parse_full_datetime(co)
            if co_dt is not None:
                if ref_date is None:
                    ref_date = co_dt.date()
                base = datetime.combine(ref_date, datetime.min.time())
                co_min = int((co_dt - base).total_seconds() // 60)
            else:
                co_min = datetime_to_minutes(co)
                if shift["shift_type"] == "evening" and co_min < shift_start:
                    co_min += 24 * 60

            overtime = max(0, co_min - shift_end)
            early_leave = max(0, shift_end - co_min)

            cutoff_min = time_to_minutes(OVERTIME_CUTOFF)
            cutoff_abs = cutoff_min + 24 * 60
            if co_min > cutoff_abs:
                overtime = max(0, cutoff_abs - shift_end)

            if early_leave > 0:
                edl, edm = compute_deduction_for_checkout(co_min, rules)
                if edl != "—":
                    early_ded_label = edl
                    early_ded_min = edm

        return delay, overtime, early_leave, ded_label, ded_min, early_ded_label, early_ded_min

    if override:
        status = override["day_status"]
        result["override_applied"] = True
        result["notes"] = override["notes"] or ""
        result["annual_leave_deduction"] = float(override["annual_leave_deduction"] or 0)
        result["sick_leave_deduction"] = float(override["sick_leave_deduction"] or 0)

        if status == "auto":
            if override["check_in"] or override["check_out"]:
                ci = override["check_in"] or (punches[0]["punch_time"] if punches else None)
                co = override["check_out"] or (punches[-1]["punch_time"] if len(punches) > 1 else None)
                (delay, ot, early, dl, dm, edl, edm) = _calc_times(ci, co)
                result["status"] = "present"
                result["day_type"] = "present"
                result["check_in"] = ci
                result["check_out"] = co
                result["delay_min"] = delay
                result["early_leave_min"] = early
                result["overtime_min"] = ot
                result["deduction_label"] = dl
                result["deduction_minutes"] = dm
                result["early_leave_deduction_label"] = edl
                result["early_leave_deduction_minutes"] = edm
                return result

        elif status == "present":
            ci = override["check_in"] or (punches[0]["punch_time"] if punches else None)
            co = override["check_out"] or (punches[-1]["punch_time"] if len(punches) > 1 else None)
            (delay, ot, early, dl, dm, edl, edm) = _calc_times(ci, co)
            result["status"] = "present"
            result["day_type"] = "present"
            result["check_in"] = ci
            result["check_out"] = co
            result["delay_min"] = delay
            result["early_leave_min"] = early
            result["overtime_min"] = ot
            result["deduction_label"] = dl
            result["deduction_minutes"] = dm
            result["early_leave_deduction_label"] = edl
            result["early_leave_deduction_minutes"] = edm
            return result

        elif status == "absent":
            result["status"] = "absent"
            result["day_type"] = "absent"
            return result

        elif status == "annual_leave":
            result["status"] = "annual_leave"
            result["day_type"] = "annual_leave"
            return result

        elif status == "sick_leave":
            result["status"] = "sick_leave"
            result["day_type"] = "sick_leave"
            policy = shift["sick_leave_policy"] or "none"
            ded_value = SICK_POLICY_VALUES.get(policy, 0.0)
            result["sick_leave_deduction"] = ded_value
            if policy == "none":
                result["deduction_label"] = "بدون خصم"
            else:
                result["deduction_label"] = SICK_POLICY_LABELS.get(policy, policy)
            return result

        elif status == "work_injury":
            result["status"] = "work_injury"
            result["day_type"] = "work_injury"
            result["deduction_label"] = "بدون خصم"
            return result

        elif status == "weekly_holiday":
            result["status"] = "weekly_holiday"
            result["day_type"] = "weekly_holiday"
            return result

    if not punches:
        result["status"] = "absent"
        result["day_type"] = "absent"
        return result

    check_in = punches[0]["punch_time"]
    check_out = punches[-1]["punch_time"] if len(punches) > 1 else None
    (delay, ot, early, dl, dm, edl, edm) = _calc_times(check_in, check_out)

    result["status"] = "present"
    result["day_type"] = "present"
    result["check_in"] = check_in
    result["check_out"] = check_out
    result["delay_min"] = delay
    result["early_leave_min"] = early
    result["overtime_min"] = ot
    result["deduction_label"] = dl
    result["deduction_minutes"] = dm
    result["early_leave_deduction_label"] = edl
    result["early_leave_deduction_minutes"] = edm
    return result


def is_working_day_for_shift(shift, date_str: str) -> bool:
    if not shift:
        return False
    work_days = [int(d) for d in (shift["work_days"] or "").split(",") if d.isdigit()]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    ar_wd = PY_WD_TO_AR[dt.weekday()]
    return ar_wd in work_days


# ============================================================
#       حساب ملخص موظف (مع رصيد الإجازة السنوية)
# ============================================================
def compute_employee_summary(employee_id, from_date, to_date,
                             punches_by_emp_date=None,
                             overrides_by_emp_date=None,
                             annual_leave_used_map=None):
    emp = get_employee(employee_id)
    if not emp:
        return None

    shift = get_shift(emp["shift_id"]) if emp["shift_id"] else None

    initial_balance = float(emp["annual_leave_balance"] or 0)
    if annual_leave_used_map is not None:
        used_all_time = float(annual_leave_used_map.get(employee_id, 0.0))
    else:
        used_all_time = get_annual_leave_used(employee_id)
    remaining_balance = initial_balance - used_all_time

    start_d = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_d = datetime.strptime(to_date, "%Y-%m-%d").date()

    total_working = 0
    present = 0
    absent = 0
    annual_leaves = 0
    sick_leaves = 0
    work_injuries = 0
    weekly_holidays = 0
    total_delay = 0
    total_overtime = 0
    total_early_leave = 0
    total_ded_minutes = 0
    total_early_leave_rule_minutes = 0
    ded_full = 0
    ded_half = 0
    ded_quarter = 0
    total_sick_deduction = 0.0

    current = start_d
    while current <= end_d:
        date_str = current.isoformat()

        if overrides_by_emp_date is not None:
            override = overrides_by_emp_date.get(employee_id, {}).get(date_str)
        else:
            override = get_attendance_override(employee_id, date_str)

        is_wd = is_working_day_for_shift(shift, date_str)

        if not is_wd:
            weekly_holidays += 1
            current += timedelta(days=1)
            continue

        total_working += 1

        if punches_by_emp_date is not None:
            punches = _combine_punches_for_day(punches_by_emp_date, employee_id, date_str)
        else:
            punches = get_punches_for_day(employee_id, date_str)

        stats = compute_day_stats(emp, shift, punches, override=override, is_working_day=True)
        status = stats["status"]

        if status == "present":
            present += 1
            total_delay += stats["delay_min"]
            total_overtime += stats["overtime_min"]
            total_ded_minutes += stats["deduction_minutes"]
            total_early_leave += stats.get("early_leave_min", 0)
            total_early_leave_rule_minutes += stats.get("early_leave_deduction_minutes", 0)

            if stats["deduction_label"] == "يوم كامل":
                ded_full += 1
            elif stats["deduction_label"] == "نص يوم":
                ded_half += 1
            elif stats["deduction_label"] == "ربع يوم":
                ded_quarter += 1

            if stats.get("early_leave_deduction_label") == "يوم كامل":
                ded_full += 1
            elif stats.get("early_leave_deduction_label") == "نص يوم":
                ded_half += 1
            elif stats.get("early_leave_deduction_label") == "ربع يوم":
                ded_quarter += 1

        elif status == "absent":
            absent += 1
        elif status == "annual_leave":
            annual_leaves += 1
        elif status == "sick_leave":
            sick_leaves += 1
            total_sick_deduction += stats["sick_leave_deduction"]
        elif status == "work_injury":
            work_injuries += 1

        current += timedelta(days=1)

    ded_parts = []
    if ded_full:
        ded_parts.append(f"{ded_full} يوم")
    if ded_half:
        ded_parts.append(f"{ded_half} نص يوم")
    if ded_quarter:
        ded_parts.append(f"{ded_quarter} ربع يوم")
    if total_ded_minutes:
        ded_parts.append(f"{total_ded_minutes} دقيقة تأخير")
    if total_early_leave_rule_minutes:
        ded_parts.append(f"{total_early_leave_rule_minutes} دقيقة انصراف")
    if total_early_leave:
        ded_parts.append(f"انصراف مبكر: {total_early_leave} د")
    if total_sick_deduction:
        ded_parts.append(f"مرضية: {_fmt_num(total_sick_deduction)} يوم")
    ded_str = " + ".join(ded_parts) if ded_parts else "—"

    return {
        "employee_id": employee_id,
        "code": emp["code"],
        "name": emp["name"],
        "shift_name": shift["name"] if shift else "—",
        "shift_type": (
            "صباحي" if (shift and shift["shift_type"] == "morning")
            else ("مسائي" if shift else "—")
        ),
        "annual_leave_initial": initial_balance,
        "annual_leave_used_total": used_all_time,
        "annual_leave_remaining": remaining_balance,
        "annual_leave": remaining_balance,
        "present": present,
        "total_working": total_working,
        "absent": absent,
        "annual_leaves": annual_leaves,
        "sick_leaves": sick_leaves,
        "work_injuries": work_injuries,
        "weekly_holidays": weekly_holidays,
        "leave": annual_leaves + sick_leaves,
        "delay_str": format_minutes_ar(total_delay),
        "early_leave_str": format_minutes_ar(total_early_leave),
        "overtime_str": format_overtime_ar(total_overtime),
        "deduction_str": ded_str,
        "_total_delay_min": total_delay,
        "_total_early_leave_min": total_early_leave,
        "_total_overtime_min": total_overtime,
        "_total_sick_deduction": total_sick_deduction,
    }


# ============================================================
#                       صفحة الحضور
# ============================================================
class AttendancePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._summary_rows = []
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        today = QDate.currentDate()
        first = QDate(today.year(), today.month(), 1)
        if self.from_date.date() > today or self.from_date.date().year() < 2000:
            self.from_date.setDate(first)
        if self.to_date.date().year() < 2000:
            self.to_date.setDate(today)
        self._refresh_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())

        body = QWidget()
        body.setObjectName("attendanceBody")
        body.setStyleSheet(f"QWidget#attendanceBody {{ background:{BG}; }}")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 24)
        body_layout.setSpacing(16)

        body_layout.addWidget(self._build_stats())
        body_layout.addWidget(self._build_filters_card())
        body_layout.addWidget(self._build_table_card(), 1)
        root.addWidget(body, 1)

    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("attendanceTopbar")
        bar.setFixedHeight(60)
        bar.setStyleSheet(f"""
            QFrame#attendanceTopbar {{
                background:{SURFACE};
                border:none;
                border-bottom:1px solid {BORDER};
            }}
        """)

        h = QHBoxLayout(bar)
        h.setContentsMargins(24, 0, 24, 0)
        h.setSpacing(14)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("الحضور والانصراف")
        title.setStyleSheet(f"""
            QLabel {{
                color:{TEXT}; font-size:16px; font-weight:700;
                background:transparent; font-family:{FONT_FAMILY};
            }}
        """)
        title_box.addWidget(title)

        subtitle = QLabel("متابعة البصمات والتأخير والإضافي والخصومات")
        subtitle.setStyleSheet(
            f"QLabel {{ color:{TEXT_MUTED}; font-size:11px; background:transparent; }}"
        )
        title_box.addWidget(subtitle)
        h.addLayout(title_box)
        h.addStretch()

        self.punch_count_label = QLabel("0 بصمة")
        self.punch_count_label.setAlignment(Qt.AlignCenter)
        self.punch_count_label.setMinimumWidth(100)
        self.punch_count_label.setFixedHeight(28)
        self.punch_count_label.setStyleSheet(f"""
            QLabel {{
                background:{SURFACE_3};
                color:{TEXT_SEC};
                border:1px solid {BORDER};
                border-radius:{RADIUS}; padding:0 14px;
                font-size:11.5px; font-weight:600;
            }}
        """)
        h.addWidget(self.punch_count_label)
        return bar

    def _build_stats(self):
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.stat_employees = self._stat_card("إجمالي الموظفين", "0", TEXT)
        self.stat_present = self._stat_card("أيام الحضور", "0", SUCCESS)
        self.stat_delay = self._stat_card("إجمالي التأخير", "—", WARNING)
        self.stat_early = self._stat_card("الانصراف المبكر", "—", PINK)
        self.stat_overtime = self._stat_card("إجمالي الإضافي", "—", PURPLE)

        grid.addWidget(self.stat_employees, 0, 0)
        grid.addWidget(self.stat_present, 0, 1)
        grid.addWidget(self.stat_delay, 0, 2)
        grid.addWidget(self.stat_early, 0, 3)
        grid.addWidget(self.stat_overtime, 0, 4)

        for col in range(5):
            grid.setColumnStretch(col, 1)
        return wrap

    def _stat_card(self, title, value, color):
        card = QFrame()
        card.setObjectName("statCard")
        card.setMinimumHeight(74)
        card.setStyleSheet(_card_style("statCard"))

        v = QVBoxLayout(card)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(4)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; font-weight:600; "
            f"background:transparent; border:none;"
        )
        v.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:21px; color:{color}; font-weight:700; "
            f"background:transparent; border:none;"
        )
        v.addWidget(val)

        card._value_label = val
        return card

    def _build_filters_card(self):
        card = QFrame()
        card.setObjectName("filterCard")
        card.setStyleSheet(_card_style("filterCard"))

        outer = QVBoxLayout(card)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(12)

        head_title = QLabel("البحث والفلاتر")
        head_title.setStyleSheet(
            f"font-size:12.5px; font-weight:700; color:{TEXT}; "
            f"background:transparent; border:none;"
        )
        outer.addWidget(head_title)

        h = QHBoxLayout()
        h.setSpacing(12)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("ابحث بالكود أو الاسم...")
        self.code_input.setFixedHeight(34)
        self.code_input.setLayoutDirection(Qt.LeftToRight)
        self.code_input.setAlignment(Qt.AlignLeft)
        self.code_input.setStyleSheet(self._input_style())
        self.code_input.returnPressed.connect(self._refresh_table)

        code_wrap = self._labeled("كود الموظف", self.code_input)
        code_wrap.setMinimumWidth(180)
        h.addWidget(code_wrap, 2)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.from_date.setFixedHeight(34)
        self.from_date.setLayoutDirection(Qt.LeftToRight)
        self._style_date_edit(self.from_date)
        h.addWidget(self._labeled("من تاريخ", self.from_date), 2)

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setFixedHeight(34)
        self.to_date.setLayoutDirection(Qt.LeftToRight)
        self._style_date_edit(self.to_date)
        h.addWidget(self._labeled("إلى تاريخ", self.to_date), 2)

        btn_search = QPushButton("بحث")
        btn_search.setFixedHeight(34)
        btn_search.setMinimumWidth(90)
        btn_search.setCursor(Qt.PointingHandCursor)
        btn_search.setStyleSheet(self._primary_btn())
        btn_search.clicked.connect(self._refresh_table)

        btn_upload = QPushButton("رفع ملف بصمة")
        btn_upload.setFixedHeight(34)
        btn_upload.setMinimumWidth(110)
        btn_upload.setCursor(Qt.PointingHandCursor)
        btn_upload.setStyleSheet(self._secondary_btn())
        btn_upload.clicked.connect(self._upload_punches)

        btn_reset = QPushButton("إعادة تعيين")
        btn_reset.setFixedHeight(34)
        btn_reset.setMinimumWidth(100)
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setStyleSheet(self._secondary_btn())
        btn_reset.clicked.connect(self._reset_filters)

        btns_box = QHBoxLayout()
        btns_box.setSpacing(8)
        btns_box.addWidget(btn_search)
        btns_box.addWidget(btn_upload)
        btns_box.addWidget(btn_reset)

        btns_wrap = QWidget()
        btns_wrap.setStyleSheet("background:transparent;")
        bw = QVBoxLayout(btns_wrap)
        bw.setContentsMargins(0, 0, 0, 0)
        bw.setSpacing(5)
        spacer = QLabel("")
        spacer.setFixedHeight(15)
        bw.addWidget(spacer)
        bw.addLayout(btns_box)

        h.addWidget(btns_wrap)
        outer.addLayout(h)

        # ---- شريط أدوات إضافي: حذف كل البصمات ----
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER}; border:none;")
        outer.addWidget(line)

        tools_row = QHBoxLayout()
        tools_row.setSpacing(8)

        self.punch_total_label = QLabel("إجمالي البصمات في النظام: 0")
        self.punch_total_label.setStyleSheet(
            f"font-size:11.5px; color:{TEXT_MUTED}; background:transparent; "
            f"font-weight:600; border:none;"
        )
        tools_row.addWidget(self.punch_total_label)
        tools_row.addStretch()

        btn_delete_all = QPushButton("حذف جميع البصمات")
        btn_delete_all.setFixedHeight(30)
        btn_delete_all.setMinimumWidth(140)
        btn_delete_all.setCursor(Qt.PointingHandCursor)
        btn_delete_all.setToolTip("يحذف كل البصمات الخام من النظام نهائياً")
        btn_delete_all.setStyleSheet(self._danger_btn())
        btn_delete_all.clicked.connect(self._delete_all_punches)
        tools_row.addWidget(btn_delete_all)

        outer.addLayout(tools_row)

        return card

    def _input_style(self):
        return f"""
            QLineEdit {{
                background:{SURFACE}; border:1px solid {BORDER_2};
                border-radius:{RADIUS}; padding:0 10px;
                font-size:12.5px; color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QLineEdit:hover {{ border-color:{TEXT_MUTED}; }}
            QLineEdit:focus {{ border:1px solid {PRIMARY}; }}
        """

    def _labeled(self, text, widget):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(5)
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size:11px; font-weight:600; color:{TEXT_SEC}; "
            f"background:transparent; border:none;"
        )
        v.addWidget(lbl)
        v.addWidget(widget)
        return w

    def _style_date_edit(self, w):
        w.setStyleSheet(f"""
            QDateEdit {{
                background:{SURFACE}; border:1px solid {BORDER_2};
                border-radius:{RADIUS}; padding:0 10px;
                font-size:12.5px; color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QDateEdit:hover {{ border-color:{TEXT_MUTED}; }}
            QDateEdit:focus {{ border:1px solid {PRIMARY}; }}
            QDateEdit::drop-down {{ border:none; width:26px; }}
            QDateEdit::down-arrow {{
                image:none; width:0; height:0;
                border-left:4px solid transparent;
                border-right:4px solid transparent;
                border-top:5px solid {TEXT_MUTED};
                margin-right:8px;
            }}
        """)

    def _primary_btn(self):
        return _primary_btn_style(12)

    def _secondary_btn(self):
        return _secondary_btn_style(12)

    def _ghost_btn(self):
        return _secondary_btn_style(12)

    def _danger_btn(self):
        return _danger_btn_style(12)

    def _build_table_card(self):
        card = QFrame()
        card.setObjectName("tableCard")
        card.setStyleSheet(_card_style("tableCard"))

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head = QFrame()
        head.setObjectName("tableHead")
        head.setFixedHeight(52)
        head.setStyleSheet(f"""
            QFrame#tableHead {{
                background:{SURFACE};
                border:none;
                border-bottom:1px solid {BORDER};
                border-top-left-radius:{RADIUS};
                border-top-right-radius:{RADIUS};
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(18, 0, 18, 0)
        hl.setSpacing(12)

        hbox = QVBoxLayout()
        hbox.setSpacing(1)

        title = QLabel("سجل ملخص الحضور")
        title.setStyleSheet(
            f"font-size:13px; font-weight:700; color:{TEXT}; "
            f"background:transparent; border:none;"
        )
        hbox.addWidget(title)

        self.range_hint = QLabel("اختر الفترة ثم اضغط بحث")
        self.range_hint.setStyleSheet(
            f"font-size:10.5px; color:{TEXT_MUTED}; background:transparent; border:none;"
        )
        hbox.addWidget(self.range_hint)
        hl.addLayout(hbox)
        hl.addStretch()

        rows_caption = QLabel("عدد الموظفين")
        rows_caption.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; background:transparent; border:none;"
        )
        hl.addWidget(rows_caption)

        self.rows_badge = QLabel("0")
        self.rows_badge.setAlignment(Qt.AlignCenter)
        self.rows_badge.setMinimumWidth(40)
        self.rows_badge.setFixedHeight(24)
        self.rows_badge.setStyleSheet(f"""
            QLabel {{
                background:{SURFACE_3}; color:{TEXT_SEC};
                border:1px solid {BORDER};
                border-radius:3px; padding:0 10px;
                font-size:11.5px; font-weight:700;
            }}
        """)
        hl.addWidget(self.rows_badge)

        v.addWidget(head)

        self.table = QTableWidget(0, 14)
        self.table.setHorizontalHeaderLabels([
            "كود الموظف", "اسم الموظف", "نوع الشيفت", "الرصيد (متبقي/ابتدائي)",
            "الحضور", "الانصراف", "التأخير", "انصراف مبكر", "الإضافي",
            "الخصم", "سنوية", "مرضية", "إصابة", "تعديل"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(_table_style("8px 8px"))
        self.table.verticalHeader().setDefaultSectionSize(46)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 110)

        v.addWidget(self.table, 1)
        return card

    def _reset_filters(self):
        today = QDate.currentDate()
        first = QDate(today.year(), today.month(), 1)
        self.from_date.setDate(first)
        self.to_date.setDate(today)
        self.code_input.clear()
        self._refresh_table()

    def _refresh_table(self):
        from_d = self.from_date.date().toString("yyyy-MM-dd")
        to_d = self.to_date.date().toString("yyyy-MM-dd")

        if self.from_date.date() > self.to_date.date():
            QMessageBox.warning(self, "تنبيه", "تاريخ البداية بعد تاريخ النهاية")
            return

        code_filter = self.code_input.text().strip()

        to_d_ext = (datetime.strptime(to_d, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        all_punches_ext = get_all_raw_punches_in_range(from_d, to_d_ext)

        all_punches = [p for p in all_punches_ext if from_d <= p["punch_date"] <= to_d]

        punches_by_emp = {}
        for p in all_punches_ext:
            emp_id = p["employee_id"]
            if emp_id is None:
                continue
            punches_by_emp.setdefault(emp_id, {}).setdefault(p["punch_date"], []).append(p)
        for emp_id, by_date in punches_by_emp.items():
            for d, lst in by_date.items():
                lst.sort(key=lambda x: x["punch_time"])

        all_overrides = get_all_overrides_in_range(from_d, to_d)
        overrides_by_emp = {}
        for o in all_overrides:
            overrides_by_emp.setdefault(o["employee_id"], {})[o["date"]] = o

        annual_leave_used_map = get_all_annual_leave_used()

        employees = get_employees(include_inactive=False)
        if code_filter:
            cf = code_filter.lower()
            employees = [
                e for e in employees
                if cf in (e["code"] or "").lower()
                or cf in (e["name"] or "").lower()
            ]

        self._summary_rows = []
        for emp in employees:
            summary = compute_employee_summary(
                emp["id"], from_d, to_d,
                punches_by_emp_date=punches_by_emp,
                overrides_by_emp_date=overrides_by_emp,
                annual_leave_used_map=annual_leave_used_map,
            )
            if summary:
                self._summary_rows.append(summary)

        self._render_table()
        self._update_stats()

        self.range_hint.setText(
            f"الفترة: {from_d}  →  {to_d}"
            + (f"   ·   بحث: {code_filter}" if code_filter else "")
        )
        self.punch_count_label.setText(f"{len(all_punches)} بصمة")

        # تحديث عدّاد إجمالي البصمات في النظام
        try:
            self.punch_total_label.setText(
                f"إجمالي البصمات في النظام: {count_raw_punches()}"
            )
        except Exception:
            pass

    def _update_stats(self):
        total_emp = len(self._summary_rows)
        total_present = sum(r["present"] for r in self._summary_rows)
        total_delay = sum(r["_total_delay_min"] for r in self._summary_rows)
        total_early = sum(r["_total_early_leave_min"] for r in self._summary_rows)
        total_ot = sum(r["_total_overtime_min"] for r in self._summary_rows)

        self.stat_employees._value_label.setText(str(total_emp))
        self.stat_present._value_label.setText(str(total_present))
        self.stat_delay._value_label.setText(
            format_minutes_ar(total_delay) if total_delay > 0 else "0"
        )
        self.stat_early._value_label.setText(
            format_minutes_ar(total_early) if total_early > 0 else "0"
        )
        self.stat_overtime._value_label.setText(
            format_overtime_ar(total_ot) if total_ot > 0 else "0"
        )
        self.rows_badge.setText(str(total_emp))

    def _render_table(self):
        self.table.setRowCount(0)

        for i, r in enumerate(self._summary_rows):
            self.table.insertRow(i)

            code_item = QTableWidgetItem(r["code"])
            code_item.setTextAlignment(Qt.AlignCenter)
            code_item.setForeground(QColor(TEXT))
            f = code_item.font()
            f.setBold(True)
            code_item.setFont(f)
            self.table.setItem(i, 0, code_item)

            name_item = QTableWidgetItem(r["name"])
            name_item.setTextAlignment(Qt.AlignCenter)
            name_item.setForeground(QColor(TEXT))
            self.table.setItem(i, 1, name_item)

            self.table.setCellWidget(i, 2, self._badge_cell(
                r["shift_type"],
                SUCCESS if r["shift_type"] == "صباحي" else PURPLE,
                SUCCESS_BG if r["shift_type"] == "صباحي" else PURPLE_BG,
                SUCCESS_BRD if r["shift_type"] == "صباحي" else PURPLE_BRD,
            ))

            init_bal = r.get("annual_leave_initial", 0)
            rem_bal = r.get("annual_leave_remaining", init_bal)
            used_total = r.get("annual_leave_used_total", 0)

            leave_txt = f"{_fmt_num(rem_bal)} / {_fmt_num(init_bal)}"
            leave_item = QTableWidgetItem(leave_txt)
            leave_item.setTextAlignment(Qt.AlignCenter)

            if rem_bal <= 0:
                leave_color = DANGER
            elif rem_bal <= 3:
                leave_color = WARNING
            else:
                leave_color = INFO

            leave_item.setForeground(QColor(leave_color))
            leave_item.setToolTip(
                f"الرصيد الابتدائي: {_fmt_num(init_bal)} يوم\n"
                f"المستخدم: {_fmt_num(used_total)} يوم\n"
                f"المتبقي: {_fmt_num(rem_bal)} يوم"
            )
            self.table.setItem(i, 3, leave_item)

            present_txt = f"{r['present']}/{r['total_working']}"
            present_item = QTableWidgetItem(present_txt)
            present_item.setTextAlignment(Qt.AlignCenter)
            present_item.setForeground(QColor(SUCCESS if r['present'] > 0 else TEXT_MUTED))
            self.table.setItem(i, 4, present_item)

            out_item = QTableWidgetItem(str(r["present"]))
            out_item.setTextAlignment(Qt.AlignCenter)
            out_item.setForeground(QColor(TEXT))
            self.table.setItem(i, 5, out_item)

            delay_item = QTableWidgetItem(r["delay_str"])
            delay_item.setTextAlignment(Qt.AlignCenter)
            delay_item.setForeground(QColor(WARNING if r["_total_delay_min"] > 0 else TEXT_MUTED))
            self.table.setItem(i, 6, delay_item)

            early_item = QTableWidgetItem(r["early_leave_str"])
            early_item.setTextAlignment(Qt.AlignCenter)
            early_item.setForeground(QColor(PINK if r["_total_early_leave_min"] > 0 else TEXT_MUTED))
            early_item.setToolTip(
                f"إجمالي دقائق الانصراف المبكر: {r['_total_early_leave_min']}"
            )
            self.table.setItem(i, 7, early_item)

            ot_item = QTableWidgetItem(r["overtime_str"])
            ot_item.setTextAlignment(Qt.AlignCenter)
            ot_item.setForeground(QColor(PURPLE if r["_total_overtime_min"] > 0 else TEXT_MUTED))
            self.table.setItem(i, 8, ot_item)

            ded_item = QTableWidgetItem(r["deduction_str"])
            ded_item.setTextAlignment(Qt.AlignCenter)
            ded_item.setForeground(QColor(DANGER if r["deduction_str"] != "—" else TEXT_MUTED))
            self.table.setItem(i, 9, ded_item)

            ann_item = QTableWidgetItem(str(r["annual_leaves"]) if r["annual_leaves"] else "—")
            ann_item.setTextAlignment(Qt.AlignCenter)
            ann_item.setForeground(QColor(INFO if r["annual_leaves"] else TEXT_MUTED))
            self.table.setItem(i, 10, ann_item)

            sick_item = QTableWidgetItem(str(r["sick_leaves"]) if r["sick_leaves"] else "—")
            sick_item.setTextAlignment(Qt.AlignCenter)
            sick_item.setForeground(QColor(WARNING if r["sick_leaves"] else TEXT_MUTED))
            self.table.setItem(i, 11, sick_item)

            inj_item = QTableWidgetItem(str(r["work_injuries"]) if r["work_injuries"] else "—")
            inj_item.setTextAlignment(Qt.AlignCenter)
            inj_item.setForeground(QColor(PINK if r["work_injuries"] else TEXT_MUTED))
            self.table.setItem(i, 12, inj_item)

            edit_wrap = QWidget()
            edit_wrap.setStyleSheet("background:transparent;")
            el = QHBoxLayout(edit_wrap)
            el.setContentsMargins(4, 0, 4, 0)
            el.setAlignment(Qt.AlignCenter)

            btn_edit = QPushButton("تعديل")
            btn_edit.setFixedHeight(28)
            btn_edit.setMinimumWidth(66)
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setStyleSheet(_row_btn_style(11.5))
            btn_edit.clicked.connect(
                lambda _, emp_id=r["employee_id"]: self._open_detail(emp_id)
            )
            el.addWidget(btn_edit)
            self.table.setCellWidget(i, 13, edit_wrap)

    def _badge_cell(self, text, color, bg, brd):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setAlignment(Qt.AlignCenter)
        badge = QLabel(text)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(_badge_style(color, bg, brd, size=11, pad="3px 12px"))
        hl.addWidget(badge)
        return w

    def _upload_punches(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف البصمة", "",
            "كل الملفات المدعومة (*.xlsx *.xlsm *.xls *.csv *.txt *.dat);;"
            "Excel (*.xlsx *.xlsm *.xls);;CSV (*.csv);;"
            "نص (*.txt *.dat);;كل الملفات (*.*)"
        )
        if not file_path:
            return

        ans = QMessageBox.question(
            self, "تأكيد الاستيراد",
            "سيتم قراءة الملف وإضافة البصمات.\n"
            "سيتم تجاهل أي كود موظف غير مسجل في النظام.\n\n"
            "هل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if ans != QMessageBox.Yes:
            return

        try:
            records, parse_skipped = parse_punch_file(file_path)
        except ImportError as e:
            QMessageBox.critical(self, "مكتبة مفقودة", str(e))
            return
        except Exception as e:
            QMessageBox.critical(
                self, "خطأ في قراءة الملف",
                f"فشل قراءة الملف:\n\n{type(e).__name__}: {e}"
            )
            return

        if not records:
            ext = file_path.lower().rsplit(".", 1)[-1]
            QMessageBox.warning(
                self, "لا توجد بيانات صالحة",
                f"لم يتم العثور على بيانات صالحة في الملف.\n\n"
                f"نوع الملف: .{ext}\nسطور تم فحصها: {parse_skipped}"
            )
            return

        inserted, skipped_codes = add_raw_punches_bulk(records)
        self._refresh_table()

        msg = (
            f"تم استيراد {inserted} بصمة بنجاح\n"
            f"تم تجاهل {skipped_codes} بصمة (كود غير مسجل)\n"
            f"سطور تالفة: {parse_skipped}"
        )
        QMessageBox.information(self, "اكتمل الاستيراد", msg)

    def _delete_all_punches(self):
        """زر حذف جميع البصمات الخام من النظام (مع تأكد فعلي من الحذف)."""
        try:
            total = count_raw_punches()
        except Exception:
            total = 0

        if total == 0:
            QMessageBox.information(
                self, "لا توجد بصمات",
                "لا توجد أي بصمات في النظام حالياً لحذفها."
            )
            return

        ans = QMessageBox.warning(
            self, "تأكيد حذف جميع البصمات",
            f"سيتم حذف جميع البصمات الخام ({total} بصمة) نهائياً من النظام.\n\n"
            f"هذا الإجراء لا يمكن التراجع عنه.\n"
            f"تعديلات الحضور اليدوية لن تتأثر.\n\n"
            f"هل أنت متأكد من المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return

        # تأكيد ثاني للحماية
        ans2 = QMessageBox.critical(
            self, "تأكيد نهائي",
            f"هل تريد فعلاً حذف {total} بصمة نهائياً؟\n\n"
            f"اضغط Yes للحذف النهائي أو No للإلغاء.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if ans2 != QMessageBox.Yes:
            return

        # حذف فعلي
        try:
            delete_all_raw_punches()
        except Exception as e:
            QMessageBox.critical(
                self, "خطأ في الحذف",
                f"فشل حذف البصمات:\n\n{type(e).__name__}: {e}"
            )
            return

        # تحقق فعلي من الحذف
        try:
            remaining = count_raw_punches()
        except Exception:
            remaining = -1

        if remaining > 0:
            QMessageBox.warning(
                self, "لم يتم الحذف بالكامل",
                f"تم حذف {total - remaining} بصمة.\n"
                f"لكن لا زال هناك {remaining} بصمة في النظام.\n\n"
                f"الأسباب المحتملة:\n"
                f"• جهاز البصمة الحية شغّال وبيبعت بصمات جديدة.\n"
                f"• Auto-sync من الجهاز كل فترة قصيرة.\n"
                f"• نافذة تانية من التطبيق مفتوحة.\n\n"
                f"جرّب: اقفل جهاز البصمة / Auto-listen ثم أعد الحذف."
            )
        else:
            QMessageBox.information(
                self, "تم الحذف بالكامل",
                f"تم حذف جميع البصمات ({total} بصمة) بنجاح.\n"
                f"العدد المتبقي: 0"
            )

        self._refresh_table()

    def _open_detail(self, employee_id):
        from_d = self.from_date.date().toString("yyyy-MM-dd")
        to_d = self.to_date.date().toString("yyyy-MM-dd")
        dlg = AttendanceDetailDialog(employee_id, from_d, to_d, self)
        dlg.exec()
        self._refresh_table()


# ============================================================
#    Day Override Dialog
# ============================================================
class DayOverrideDialog(QDialog):
    def __init__(self, employee, shift, date_str, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.shift = shift
        self.date_str = date_str

        self.override = get_attendance_override(employee["id"], date_str)
        self.punches = get_punches_for_day(employee["id"], date_str)

        self.initial_balance = float(employee["annual_leave_balance"] or 0)
        self.used_before = get_annual_leave_used_except_date(
            employee["id"], date_str
        )
        self.remaining_before = self.initial_balance - self.used_before

        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle(f"تعديل يوم {date_str}")
        self.setMinimumWidth(700)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        # Header
        head = QFrame()
        head.setObjectName("dayHeader")
        head.setStyleSheet(_card_style("dayHeader"))
        hl = QHBoxLayout(head)
        hl.setContentsMargins(18, 14, 18, 14)
        hl.setSpacing(12)

        tbox = QVBoxLayout()
        tbox.setSpacing(3)

        wd = datetime.strptime(self.date_str, "%Y-%m-%d").weekday()
        day_name = ARABIC_DAYS[PY_WD_TO_AR[wd]]

        title = QLabel(f"{day_name}  ·  {self.date_str}")
        title.setStyleSheet(
            f"font-size:14.5px; font-weight:700; color:{TEXT}; "
            f"background:transparent; border:none;"
        )
        tbox.addWidget(title)

        sub = QLabel(
            f"{self.employee['name']}  ·  شيفت: "
            f"{self.shift['name'] if self.shift else '—'}"
        )
        sub.setStyleSheet(
            f"font-size:11.5px; color:{TEXT_MUTED}; background:transparent; border:none;"
        )
        tbox.addWidget(sub)
        hl.addLayout(tbox)
        hl.addStretch()

        rem = self.remaining_before
        if rem <= 0:
            b_color, b_bg, b_brd = DANGER, DANGER_BG, DANGER_BRD
        elif rem <= 3:
            b_color, b_bg, b_brd = WARNING, WARNING_BG, WARNING_BRD
        else:
            b_color, b_bg, b_brd = INFO, INFO_BG, INFO_BRD

        bal_badge = QLabel(
            f"رصيد الإجازة: {_fmt_num(rem)} / {_fmt_num(self.initial_balance)}"
        )
        bal_badge.setAlignment(Qt.AlignCenter)
        bal_badge.setStyleSheet(_badge_style(b_color, b_bg, b_brd, size=11.5, pad="5px 12px"))
        bal_badge.setToolTip(
            f"الابتدائي: {_fmt_num(self.initial_balance)} يوم\n"
            f"المستخدم: {_fmt_num(self.used_before)} يوم\n"
            f"المتبقي: {_fmt_num(rem)} يوم"
        )
        hl.addWidget(bal_badge)

        v.addWidget(head)

        # بصمات خام
        if self.punches:
            pbox = QFrame()
            pbox.setObjectName("rawPunches")
            pbox.setStyleSheet(f"""
                QFrame#rawPunches {{
                    background:{SURFACE_2};
                    border:1px solid {BORDER};
                    border-radius:{RADIUS};
                }}
            """)
            pb = QHBoxLayout(pbox)
            pb.setContentsMargins(14, 10, 14, 10)
            pb.setSpacing(8)

            times = "  ·  ".join(format_time_only(p["punch_time"]) for p in self.punches)
            lbl = QLabel(f"البصمات الخام:  {times}")
            lbl.setStyleSheet(
                f"font-size:11.5px; color:{TEXT_SEC}; "
                f"background:transparent; font-weight:600; border:none;"
            )
            pb.addWidget(lbl, 1)
            v.addWidget(pbox)

        type_lbl = QLabel("حالة اليوم")
        type_lbl.setStyleSheet(
            f"font-size:12px; font-weight:700; color:{TEXT}; background:transparent;"
        )
        v.addWidget(type_lbl)

        status_grid = QGridLayout()
        status_grid.setHorizontalSpacing(8)
        status_grid.setVerticalSpacing(8)

        self.status_checks = {}
        order = ["auto", "present", "absent", "annual_leave", "sick_leave", "work_injury"]

        for i, key in enumerate(order):
            cb = QCheckBox(DAY_STATUS_LABELS[key])
            cb.setCursor(Qt.PointingHandCursor)
            cb.setMinimumHeight(38)
            cb.setStyleSheet(self._status_cb_style(key))
            cb.toggled.connect(lambda checked, k=key: self._on_status_toggled(k, checked))
            self.status_checks[key] = cb
            row = i // 3
            col = i % 3
            status_grid.addWidget(cb, row, col)

        for c in range(3):
            status_grid.setColumnStretch(c, 1)

        v.addLayout(status_grid)

        self.time_box = QFrame()
        self.time_box.setObjectName("timeBox")
        self.time_box.setStyleSheet(f"""
            QFrame#timeBox {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)
        tb = QHBoxLayout(self.time_box)
        tb.setContentsMargins(16, 12, 16, 12)
        tb.setSpacing(12)

        self.ci_input = self._time_input("08:00")
        self.co_input = self._time_input("16:00")

        tb.addWidget(self._field("وقت الحضور", self.ci_input), 1)
        tb.addWidget(self._field("وقت الانصراف", self.co_input), 1)
        v.addWidget(self.time_box)

        self.info_box = QFrame()
        self.info_box.setObjectName("infoBox")
        si = QHBoxLayout(self.info_box)
        si.setContentsMargins(14, 10, 14, 10)
        si.setSpacing(8)

        self.info_lbl = QLabel("")
        self.info_lbl.setWordWrap(True)
        si.addWidget(self.info_lbl, 1)
        v.addWidget(self.info_box)

        notes_lbl = QLabel("ملاحظات")
        notes_lbl.setStyleSheet(
            f"font-size:12px; font-weight:700; color:{TEXT}; background:transparent;"
        )
        v.addWidget(notes_lbl)

        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(66)
        self.notes_input.setStyleSheet(f"""
            QTextEdit {{
                background:{SURFACE}; border:1px solid {BORDER_2};
                border-radius:{RADIUS}; padding:8px 10px;
                font-size:12px; color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QTextEdit:focus {{ border:1px solid {PRIMARY}; }}
        """)
        v.addWidget(self.notes_input)

        v.addStretch()

        btns = QHBoxLayout()
        btns.setSpacing(8)

        self.btn_delete = QPushButton("حذف التعديل")
        self.btn_delete.setFixedHeight(34)
        self.btn_delete.setMinimumWidth(120)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet(_danger_btn_style(12))
        self.btn_delete.clicked.connect(self._delete_override)
        btns.addWidget(self.btn_delete)

        btns.addStretch()

        btn_cancel = QPushButton("إلغاء")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setMinimumWidth(100)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(_secondary_btn_style(12))
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_save = QPushButton("حفظ")
        btn_save.setFixedHeight(34)
        btn_save.setMinimumWidth(120)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(_primary_btn_style(12))
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)

        v.addLayout(btns)

    def _status_cb_style(self, key):
        color_map = {
            "auto":         (PRIMARY, PRIMARY_BG, PRIMARY_BRD),
            "present":      (SUCCESS, SUCCESS_BG, SUCCESS_BRD),
            "absent":       (DANGER,  DANGER_BG,  DANGER_BRD),
            "annual_leave": (INFO,    INFO_BG,    INFO_BRD),
            "sick_leave":   (WARNING, WARNING_BG, WARNING_BRD),
            "work_injury":  (PINK,    PINK_BG,    PINK_BRD),
        }
        color, bg, brd = color_map.get(key, (PRIMARY, PRIMARY_BG, PRIMARY_BRD))
        return f"""
            QCheckBox {{
                background:{SURFACE};
                border:1px solid {BORDER_2};
                border-radius:{RADIUS};
                padding:8px 12px;
                font-size:12px;
                font-weight:600;
                color:{TEXT_SEC};
                spacing:8px;
                font-family:{FONT_FAMILY};
            }}
            QCheckBox:hover {{
                background:{SURFACE_3};
                border-color:{TEXT_MUTED};
            }}
            QCheckBox:checked {{
                background:{bg};
                border:1px solid {color};
                color:{color};
            }}
            QCheckBox::indicator {{
                width:14px; height:14px;
                border:1px solid {BORDER_2};
                border-radius:3px;
                background:white;
            }}
            QCheckBox::indicator:hover {{ border-color:{color}; }}
            QCheckBox::indicator:checked {{
                background:{color}; border-color:{color};
            }}
        """

    def _field(self, label, widget):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(5)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size:11px; font-weight:600; color:{TEXT_SEC}; "
            f"background:transparent; border:none;"
        )
        v.addWidget(lbl)
        v.addWidget(widget)
        return w

    def _time_input(self, default="08:00"):
        inp = QLineEdit()
        inp.setFixedHeight(36)
        inp.setLayoutDirection(Qt.LeftToRight)
        inp.setAlignment(Qt.AlignCenter)
        inp.setPlaceholderText("HH:mm")
        inp.setText(default)
        inp.setMaxLength(5)
        regex = QRegularExpression(r"^([01]\d|2[0-3]):([0-5]\d)$")
        inp.setValidator(QRegularExpressionValidator(regex))
        inp.setStyleSheet(f"""
            QLineEdit {{
                background:white; border:1px solid {BORDER_2};
                border-radius:{RADIUS}; padding:0 12px;
                font-size:13px; font-weight:600; color:{TEXT};
                letter-spacing:1px;
                font-family:{FONT_FAMILY};
            }}
            QLineEdit:focus {{ border:1px solid {PRIMARY}; }}
        """)
        return inp

    def _get_time_value(self, inp, fallback=None):
        t = inp.text().strip()
        if not t or ":" not in t:
            return fallback
        parts = t.split(":")
        try:
            h = int(parts[0]); m = int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}"
        except (ValueError, IndexError):
            pass
        return fallback

    def _on_status_toggled(self, key, checked):
        if checked:
            for k, cb in self.status_checks.items():
                if k != key and cb.isChecked():
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
        else:
            if not any(cb.isChecked() for cb in self.status_checks.values()):
                self.status_checks[key].blockSignals(True)
                self.status_checks[key].setChecked(True)
                self.status_checks[key].blockSignals(False)

        self._update_visibility(key)

    def _set_info(self, kind, text):
        color, bg, brd = NOTE_KINDS.get(kind, NOTE_KINDS["info"])
        self.info_box.setStyleSheet(f"""
            QFrame#infoBox {{
                background:{bg};
                border:1px solid {brd};
                border-radius:{RADIUS};
            }}
        """)
        self.info_lbl.setStyleSheet(
            f"font-size:11.5px; color:{color}; background:transparent; "
            f"font-weight:600; border:none; font-family:{FONT_FAMILY};"
        )
        self.info_lbl.setText(text)
        self.info_box.setVisible(True)

    def _update_visibility(self, key=None):
        if key is None:
            key = "auto"
            for k, cb in self.status_checks.items():
                if cb.isChecked():
                    key = k
                    break

        show_times = key in ("auto", "present")
        self.time_box.setVisible(show_times)

        policy = (self.shift["sick_leave_policy"] if self.shift else "none") or "none"
        policy_lbl = SICK_POLICY_LABELS.get(policy, policy)

        if key == "sick_leave":
            self._set_info(
                "warning",
                f"سيتم تطبيق سياسة المرضية من الشيفت: {policy_lbl}"
            )

        elif key == "annual_leave":
            init = self.initial_balance
            used = self.used_before
            rem = self.remaining_before

            txt = (
                f"الرصيد الابتدائي: {_fmt_num(init)} يوم   ·   "
                f"المستخدم سابقاً: {_fmt_num(used)}   ·   "
                f"المتبقي: {_fmt_num(rem)} يوم\n"
                f"سيتم خصم 1.0 يوم إضافي من الرصيد."
            )

            if rem < 1.0:
                txt += "\nتحذير: الرصيد المتبقي غير كافٍ."
                self._set_info("danger", txt)
            else:
                self._set_info("info", txt)

        elif key == "work_injury":
            self._set_info(
                "pink",
                "إصابة عمل: لا يوجد أي خصم — يُحتسب اليوم كحضور بإذن مسبق."
            )

        elif key == "absent":
            self._set_info(
                "danger",
                "غياب: لن يُحتسب اليوم كحضور وستُطبق قواعد الخصم من الشيفت."
            )

        elif key == "present":
            self._set_info(
                "success",
                "حاضر بأوقات مخصصة: سيتم استخدام الأوقات أدناه بدلاً من البصمة الخام، "
                "وسيتم حساب الانصراف المبكر تلقائياً لو الخروج قبل نهاية الشيفت."
            )

        else:
            self._set_info(
                "info",
                "تلقائي: يُحسب اليوم من البصمة (مع احتساب الانصراف المبكر)، "
                "ويمكنك تخصيص الأوقات إن أردت."
            )

    def _load_values(self):
        status = "auto"
        if self.override:
            status = self.override["day_status"] or "auto"

        if status in self.status_checks:
            cb = self.status_checks[status]
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)

        if self.override and self.override["check_in"]:
            self.ci_input.setText(format_time_only(self.override["check_in"]))
        elif self.punches:
            self.ci_input.setText(format_time_only(self.punches[0]["punch_time"]))

        if self.override and self.override["check_out"]:
            self.co_input.setText(format_time_only(self.override["check_out"]))
        elif len(self.punches) > 1:
            self.co_input.setText(format_time_only(self.punches[-1]["punch_time"]))

        if self.override:
            self.notes_input.setPlainText(self.override["notes"] or "")

        self.btn_delete.setVisible(bool(self.override))

        self._update_visibility(status)

    def _get_selected_status(self):
        for k, cb in self.status_checks.items():
            if cb.isChecked():
                return k
        return "auto"

    def _save(self):
        status = self._get_selected_status()

        ci = None
        co = None
        ann_ded = 0.0
        sick_ded = 0.0

        if status in ("present", "auto"):
            ci_t = self._get_time_value(self.ci_input)
            co_t = self._get_time_value(self.co_input)
            if status == "present" and not ci_t:
                QMessageBox.warning(self, "تنبيه", "أدخل وقت حضور صحيح")
                return
            if ci_t:
                ci = f"{self.date_str} {ci_t}:00"
            if co_t:
                if ci_t and co_t < ci_t:
                    next_date = (
                        datetime.strptime(self.date_str, "%Y-%m-%d") + timedelta(days=1)
                    ).strftime("%Y-%m-%d")
                    co = f"{next_date} {co_t}:00"
                else:
                    co = f"{self.date_str} {co_t}:00"

        if status == "annual_leave":
            if self.remaining_before < 1.0:
                ans = QMessageBox.question(
                    self, "تحذير: الرصيد غير كافٍ",
                    f"الرصيد المتبقي للموظف: {_fmt_num(self.remaining_before)} يوم.\n"
                    f"سيصبح بعد الحفظ: {_fmt_num(self.remaining_before - 1.0)} يوم (سالب).\n\n"
                    f"هل تريد المتابعة على أي حال؟",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if ans != QMessageBox.Yes:
                    return
            ann_ded = 1.0

        if status == "sick_leave":
            policy = (self.shift["sick_leave_policy"] if self.shift else "none") or "none"
            sick_ded = SICK_POLICY_VALUES.get(policy, 0.0)

        data = {
            "day_status": status,
            "check_in": ci,
            "check_out": co,
            "annual_leave_deduction": ann_ded,
            "sick_leave_deduction": sick_ded,
            "notes": self.notes_input.toPlainText().strip(),
        }

        ok, msg = save_attendance_override(self.employee["id"], self.date_str, data)
        if not ok:
            QMessageBox.critical(self, "خطأ", msg)
            return
        self.accept()

    def _delete_override(self):
        ans = QMessageBox.question(
            self, "تأكيد",
            f"حذف التعديل على يوم {self.date_str}؟\n"
            "سيتم الرجوع للحساب التلقائي من البصمات.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return
        delete_attendance_override(self.employee["id"], self.date_str)
        self.accept()


# ============================================================
#    Detail Dialog
# ============================================================
class AttendanceDetailDialog(QDialog):
    def __init__(self, employee_id, from_date, to_date, parent=None):
        super().__init__(parent)
        self.employee_id = employee_id
        self.from_date = from_date
        self.to_date = to_date

        emp = get_employee(employee_id)
        self.employee = emp
        self.shift = get_shift(emp["shift_id"]) if (emp and emp["shift_id"]) else None

        self.annual_initial = float(emp["annual_leave_balance"] or 0)
        self.annual_used = get_annual_leave_used(employee_id)
        self.annual_remaining = self.annual_initial - self.annual_used

        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle(f"تفاصيل الحضور — {emp['name'] if emp else ''}")
        self.setMinimumSize(1300, 760)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")

        self._build_ui()
        self._load_days()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        # Header
        head = QFrame()
        head.setObjectName("detailHeader")
        head.setStyleSheet(_card_style("detailHeader"))

        hl = QHBoxLayout(head)
        hl.setContentsMargins(20, 14, 20, 14)
        hl.setSpacing(12)

        tbox = QVBoxLayout()
        tbox.setSpacing(3)

        title = QLabel(f"{self.employee['name']}  ·  {self.employee['code']}")
        title.setStyleSheet(
            f"font-size:15px; font-weight:700; color:{TEXT}; "
            f"background:transparent; border:none;"
        )
        tbox.addWidget(title)

        sub = QLabel(f"الفترة: {self.from_date}  →  {self.to_date}")
        sub.setStyleSheet(
            f"font-size:11.5px; color:{TEXT_MUTED}; background:transparent; border:none;"
        )
        tbox.addWidget(sub)
        hl.addLayout(tbox)
        hl.addStretch()

        if self.shift:
            policy = self.shift["sick_leave_policy"] or "none"
            policy_lbl = SICK_POLICY_LABELS.get(policy, policy)
            shift_lbl = QLabel(
                f"الشيفت: {self.shift['name']}  ·  "
                f"{'صباحي' if self.shift['shift_type'] == 'morning' else 'مسائي'}  ·  "
                f"مرضية: {policy_lbl}"
            )
            shift_lbl.setStyleSheet(_badge_style(TEXT_SEC, SURFACE_3, BORDER, size=11.5, pad="5px 12px"))
            hl.addWidget(shift_lbl)

        if self.annual_remaining <= 0:
            bal_color, bal_bg, bal_brd = DANGER, DANGER_BG, DANGER_BRD
        elif self.annual_remaining <= 3:
            bal_color, bal_bg, bal_brd = WARNING, WARNING_BG, WARNING_BRD
        else:
            bal_color, bal_bg, bal_brd = INFO, INFO_BG, INFO_BRD

        bal_lbl = QLabel(
            f"رصيد الإجازة: {_fmt_num(self.annual_remaining)} / "
            f"{_fmt_num(self.annual_initial)}"
        )
        bal_lbl.setStyleSheet(_badge_style(bal_color, bal_bg, bal_brd, size=11.5, pad="5px 12px"))
        bal_lbl.setToolTip(
            f"الابتدائي: {_fmt_num(self.annual_initial)} يوم\n"
            f"المستخدم: {_fmt_num(self.annual_used)} يوم\n"
            f"المتبقي: {_fmt_num(self.annual_remaining)} يوم"
        )
        hl.addWidget(bal_lbl)

        v.addWidget(head)

        self._build_stats_row(v)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "التاريخ", "اليوم", "الحضور", "الانصراف",
            "التأخير", "انصراف مبكر", "الإضافي", "الخصم", "الحالة", "تعديل"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setStyleSheet(
            _table_style("7px 8px")
            + f"QTableWidget {{ border:1px solid {BORDER}; }}"
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(9, 100)
        self.table.verticalHeader().setDefaultSectionSize(42)
        v.addWidget(self.table, 1)

        footer = QFrame()
        footer.setObjectName("detailFooter")
        footer.setStyleSheet(_card_style("detailFooter"))

        fl = QHBoxLayout(footer)
        fl.setContentsMargins(18, 12, 18, 12)
        fl.setSpacing(12)

        self.totals_label = QLabel("")
        self.totals_label.setStyleSheet(
            f"font-size:11.5px; color:{TEXT_SEC}; background:transparent; "
            f"font-weight:600; border:none;"
        )
        fl.addWidget(self.totals_label, 1)

        btn_close = QPushButton("إغلاق")
        btn_close.setFixedHeight(34)
        btn_close.setMinimumWidth(110)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(_secondary_btn_style(12))
        btn_close.clicked.connect(self.accept)
        fl.addWidget(btn_close)
        v.addWidget(footer)

    def _build_stats_row(self, parent_layout):
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.card_present = self._mini_card("أيام الحضور", "0", SUCCESS)
        self.card_absent = self._mini_card("الغياب", "0", DANGER)
        self.card_annual = self._mini_card("إجازة سنوية", "0", INFO)
        self.card_sick = self._mini_card("إجازة مرضية", "0", WARNING)

        self.card_injury = self._mini_card("إصابة عمل", "0", PINK)
        self.card_weekly = self._mini_card("راحة أسبوعية", "0", GRAY)
        self.card_delay = self._mini_card("إجمالي التأخير", "0", WARNING)
        self.card_early = self._mini_card("الانصراف المبكر", "0", PINK)
        self.card_overtime = self._mini_card("إجمالي الإضافي", "0", PURPLE)

        grid.addWidget(self.card_present, 0, 0)
        grid.addWidget(self.card_absent, 0, 1)
        grid.addWidget(self.card_annual, 0, 2)
        grid.addWidget(self.card_sick, 0, 3)
        grid.addWidget(self.card_injury, 0, 4)

        grid.addWidget(self.card_weekly, 1, 0)
        grid.addWidget(self.card_delay, 1, 1)
        grid.addWidget(self.card_early, 1, 2)
        grid.addWidget(self.card_overtime, 1, 3)

        for c in range(5):
            grid.setColumnStretch(c, 1)

        parent_layout.addWidget(wrap)

    def _mini_card(self, title, value, color):
        card = QFrame()
        card.setObjectName("miniStat")
        card.setMinimumHeight(60)
        card.setStyleSheet(_card_style("miniStat"))

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 8, 14, 8)
        v.setSpacing(2)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:10.5px; color:{TEXT_MUTED}; font-weight:600; "
            f"background:transparent; border:none;"
        )
        v.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:17px; color:{color}; font-weight:700; "
            f"background:transparent; border:none;"
        )
        v.addWidget(val)

        card._value_label = val
        return card

    def _load_days(self):
        from_d = datetime.strptime(self.from_date, "%Y-%m-%d").date()
        to_d = datetime.strptime(self.to_date, "%Y-%m-%d").date()

        self.table.setRowCount(0)
        row_idx = 0

        total_present = 0
        total_absent = 0
        total_annual = 0
        total_sick = 0
        total_injury = 0
        total_weekly = 0
        total_delay = 0
        total_early = 0
        total_overtime = 0
        total_days = 0

        current = from_d
        while current <= to_d:
            date_str = current.isoformat()
            day_name = ARABIC_DAYS[PY_WD_TO_AR[current.weekday()]]
            total_days += 1

            is_wd = is_working_day_for_shift(self.shift, date_str)
            override = get_attendance_override(self.employee_id, date_str)

            if not is_wd:
                if override and override["day_status"] not in ("auto", "weekly_holiday"):
                    punches = get_punches_for_day(self.employee_id, date_str)
                    stats = compute_day_stats(
                        self.employee, self.shift, punches,
                        override=override, is_working_day=False
                    )
                    self.table.insertRow(row_idx)
                    self._render_day_row(row_idx, date_str, day_name, stats)
                    row_idx += 1
                    st = stats["status"]
                    if st == "present": total_present += 1
                    elif st == "absent": total_absent += 1
                    elif st == "annual_leave": total_annual += 1
                    elif st == "sick_leave": total_sick += 1
                    elif st == "work_injury": total_injury += 1
                else:
                    total_weekly += 1
                    self.table.insertRow(row_idx)
                    self._render_weekly_holiday_row(row_idx, date_str, day_name)
                    row_idx += 1
                current += timedelta(days=1)
                continue

            punches = get_punches_for_day(self.employee_id, date_str)
            stats = compute_day_stats(
                self.employee, self.shift, punches,
                override=override, is_working_day=True
            )

            st = stats["status"]
            if st == "present":
                total_present += 1
                total_delay += stats["delay_min"]
                total_early += stats.get("early_leave_min", 0)
                total_overtime += stats["overtime_min"]
            elif st == "absent":
                total_absent += 1
            elif st == "annual_leave":
                total_annual += 1
            elif st == "sick_leave":
                total_sick += 1
            elif st == "work_injury":
                total_injury += 1

            self.table.insertRow(row_idx)
            self._render_day_row(row_idx, date_str, day_name, stats)
            row_idx += 1
            current += timedelta(days=1)

        self.card_present._value_label.setText(str(total_present))
        self.card_absent._value_label.setText(str(total_absent))
        self.card_annual._value_label.setText(str(total_annual))
        self.card_sick._value_label.setText(str(total_sick))
        self.card_injury._value_label.setText(str(total_injury))
        self.card_weekly._value_label.setText(str(total_weekly))
        self.card_delay._value_label.setText(
            format_minutes_ar(total_delay) if total_delay > 0 else "0"
        )
        self.card_early._value_label.setText(
            format_minutes_ar(total_early) if total_early > 0 else "0"
        )
        self.card_overtime._value_label.setText(
            format_overtime_ar(total_overtime) if total_overtime > 0 else "0"
        )

        self.totals_label.setText(
            f"إجمالي الأيام: {total_days}   ·   "
            f"حضور: {total_present}   ·   غياب: {total_absent}   ·   "
            f"سنوية: {total_annual}   ·   مرضية: {total_sick}   ·   "
            f"إصابة: {total_injury}   ·   راحة: {total_weekly}   ·   "
            f"تأخير: {format_minutes_ar(total_delay)}   ·   "
            f"انصراف مبكر: {format_minutes_ar(total_early)}   ·   "
            f"إضافي: {format_overtime_ar(total_overtime)}"
        )

    def _status_badge_widget(self, text, color, bg, brd):
        badge_wrap = QWidget()
        badge_wrap.setStyleSheet("background:transparent;")
        bl = QHBoxLayout(badge_wrap)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setAlignment(Qt.AlignCenter)

        badge = QLabel(text)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(_badge_style(color, bg, brd, size=11, pad="3px 12px"))
        bl.addWidget(badge)
        return badge_wrap

    def _edit_button_widget(self, date_str, tooltip=None):
        edit_wrap = QWidget()
        edit_wrap.setStyleSheet("background:transparent;")
        el = QHBoxLayout(edit_wrap)
        el.setContentsMargins(2, 0, 2, 0)
        el.setAlignment(Qt.AlignCenter)

        btn_edit = QPushButton("تعديل")
        btn_edit.setFixedHeight(26)
        btn_edit.setMinimumWidth(66)
        btn_edit.setCursor(Qt.PointingHandCursor)
        if tooltip:
            btn_edit.setToolTip(tooltip)
        btn_edit.setStyleSheet(_row_btn_style(11))
        btn_edit.clicked.connect(lambda _, d=date_str: self._edit_day(d))
        el.addWidget(btn_edit)
        return edit_wrap

    def _render_weekly_holiday_row(self, row_idx, date_str, day_name):
        d_item = QTableWidgetItem(date_str)
        d_item.setTextAlignment(Qt.AlignCenter)
        d_item.setForeground(QColor(TEXT_MUTED))
        self.table.setItem(row_idx, 0, d_item)

        day_item = QTableWidgetItem(day_name)
        day_item.setTextAlignment(Qt.AlignCenter)
        day_item.setForeground(QColor(TEXT_MUTED))
        self.table.setItem(row_idx, 1, day_item)

        for c in range(2, 8):
            it = QTableWidgetItem("—")
            it.setTextAlignment(Qt.AlignCenter)
            it.setForeground(QColor(TEXT_MUTED))
            self.table.setItem(row_idx, c, it)

        self.table.setCellWidget(
            row_idx, 8,
            self._status_badge_widget("راحة أسبوعية", GRAY, GRAY_BG, GRAY_BRD)
        )
        self.table.setCellWidget(
            row_idx, 9,
            self._edit_button_widget(date_str, "تخصيص اليوم (اختياري)")
        )

    def _render_day_row(self, row_idx, date_str, day_name, stats):
        d_item = QTableWidgetItem(date_str)
        d_item.setTextAlignment(Qt.AlignCenter)
        d_item.setForeground(QColor(TEXT))
        self.table.setItem(row_idx, 0, d_item)

        day_item = QTableWidgetItem(day_name)
        day_item.setTextAlignment(Qt.AlignCenter)
        day_item.setForeground(QColor(TEXT_SEC))
        self.table.setItem(row_idx, 1, day_item)

        ci_txt = format_time_only(stats["check_in"]) if stats["check_in"] else "—"
        ci_item = QTableWidgetItem(ci_txt)
        ci_item.setTextAlignment(Qt.AlignCenter)
        ci_item.setForeground(QColor(SUCCESS if stats["check_in"] else TEXT_MUTED))
        self.table.setItem(row_idx, 2, ci_item)

        co_txt = format_time_only(stats["check_out"]) if stats["check_out"] else "—"
        co_item = QTableWidgetItem(co_txt)
        co_item.setTextAlignment(Qt.AlignCenter)
        co_item.setForeground(QColor(DANGER if stats["check_out"] else TEXT_MUTED))
        self.table.setItem(row_idx, 3, co_item)

        delay_item = QTableWidgetItem(format_minutes_ar(stats["delay_min"]))
        delay_item.setTextAlignment(Qt.AlignCenter)
        delay_item.setForeground(QColor(WARNING if stats["delay_min"] > 0 else TEXT_MUTED))
        self.table.setItem(row_idx, 4, delay_item)

        early_min = stats.get("early_leave_min", 0)
        early_item = QTableWidgetItem(format_minutes_ar(early_min))
        early_item.setTextAlignment(Qt.AlignCenter)
        early_item.setForeground(QColor(PINK if early_min > 0 else TEXT_MUTED))
        if early_min > 0 and stats.get("early_leave_deduction_label", "—") != "—":
            early_item.setToolTip(
                f"خصم من قواعد الشيفت: {stats['early_leave_deduction_label']}"
            )
        self.table.setItem(row_idx, 5, early_item)

        ot_item = QTableWidgetItem(format_overtime_ar(stats["overtime_min"]))
        ot_item.setTextAlignment(Qt.AlignCenter)
        ot_item.setForeground(QColor(PURPLE if stats["overtime_min"] > 0 else TEXT_MUTED))
        ot_item.setToolTip(
            f"الإضافي محسوب حتى الساعة {OVERTIME_CUTOFF} كحد أقصى"
        )
        self.table.setItem(row_idx, 6, ot_item)

        ded_parts = []
        if stats["deduction_label"] != "—":
            ded_parts.append(f"تأخير: {stats['deduction_label']}")
        if stats.get("early_leave_deduction_label", "—") != "—":
            ded_parts.append(f"انصراف: {stats['early_leave_deduction_label']}")
        ded_txt = " | ".join(ded_parts) if ded_parts else stats["deduction_label"]

        ded_item = QTableWidgetItem(ded_txt)
        ded_item.setTextAlignment(Qt.AlignCenter)
        show_ded = ded_txt not in ("—", "بدون خصم")
        ded_item.setForeground(QColor(DANGER if show_ded else TEXT_MUTED))
        self.table.setItem(row_idx, 7, ded_item)

        label_data = STATUS_STYLE.get(stats["status"], ("—", TEXT_MUTED, SURFACE_2, BORDER, ""))
        label_text, color, bg, brd, _unused = label_data

        text = label_text
        if stats["override_applied"]:
            text = f"{label_text}  (معدّل)"

        self.table.setCellWidget(
            row_idx, 8, self._status_badge_widget(text, color, bg, brd)
        )
        self.table.setCellWidget(row_idx, 9, self._edit_button_widget(date_str))

    def _edit_day(self, date_str):
        dlg = DayOverrideDialog(self.employee, self.shift, date_str, self)
        if dlg.exec() == QDialog.Accepted:
            self.annual_used = get_annual_leave_used(self.employee_id)
            self.annual_remaining = self.annual_initial - self.annual_used
            self._load_days()