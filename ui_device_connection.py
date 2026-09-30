"""
صفحة ربط البصمة والاستماع التلقائي
- تتصل بجهاز ZKTeco عبر الشبكة
- تسحب قائمة الموظفين من الجهاز (بأسمائهم)
- تستمع للبصمات في الوقت الفعلي
- تسحب جميع البصمات المخزّنة (حتى لو الكود مش مسجل في النظام)
"""

import threading
import time
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QGridLayout, QSpinBox, QCheckBox,
    QAbstractItemView, QGraphicsDropShadowEffect, QTextEdit,
    QDialog, QComboBox, QScrollArea, QDialogButtonBox, QDateEdit,
    QSizePolicy, QTabWidget
)
from PySide6.QtCore import Qt, QDate, QTime, Signal, QObject, QTimer
from PySide6.QtGui import QColor, QFont, QIcon

from database import (
    get_device_settings, save_device_settings,
    update_device_last_connected, add_live_punch,
    get_recent_live_punches, get_connection,
    # ✅ جديد — قائمة موظفي الجهاز
    save_pulled_device_users, get_device_users,
    get_unregistered_device_users, get_registered_device_users,
    count_device_users, count_unregistered_device_users,
    get_last_device_sync_time, delete_all_device_users,
)


# ============================================================
#                نظام الألوان
# ============================================================
BG          = "#f1f5f9"
BG_2        = "#eef2f7"
SURFACE     = "#ffffff"
SURFACE_2   = "#f8fafc"
SURFACE_3   = "#f1f5f9"
BORDER      = "#e2e8f0"
BORDER_2    = "#cbd5e1"
DIVIDER     = "#eef2f7"

TEXT        = "#0f172a"
TEXT_SEC    = "#475569"
TEXT_MUTED  = "#94a3b8"

NAVY        = "#0b1729"
NAVY_2      = "#132a4a"
NAVY_3      = "#1e3a5f"
NAVY_ACCENT = "#1e40af"

PRIMARY     = "#2563eb"
PRIMARY_HOV = "#1d4ed8"
PRIMARY_DK  = "#1e40af"
PRIMARY_BG  = "#eff6ff"
PRIMARY_BRD = "#bfdbfe"

SUCCESS     = "#059669"
SUCCESS_HOV = "#047857"
SUCCESS_BG  = "#ecfdf5"
SUCCESS_BRD = "#a7f3d0"

DANGER      = "#dc2626"
DANGER_HOV  = "#b91c1c"
DANGER_BG   = "#fef2f2"
DANGER_BRD  = "#fecaca"

WARNING     = "#d97706"
WARNING_HOV = "#b45309"
WARNING_BG  = "#fffbeb"
WARNING_BRD = "#fde68a"

INFO        = "#0891b2"
INFO_BG     = "#ecfeff"
INFO_BRD    = "#a5f3fc"

PURPLE      = "#7c3aed"
PURPLE_BG   = "#f5f3ff"
PURPLE_BRD  = "#ddd6fe"

ROW_ALT     = "#fafbfc"
HEADER_BG   = "#f8fafc"

FONT_FAMILY = "Segoe UI, Tahoma, Arial, sans-serif"


def apply_shadow(widget, blur=20, y_offset=4, alpha=25):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    effect.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(effect)
    return effect


# ============================================================
#    ✅ حفظ جميع البصمات (بدون فلترة الأكواد غير المسجلة)
# ============================================================
def add_device_punches_all(records, source="device_pull"):
    """
    إضافة جميع البصمات — لا نتجاهل أي كود:
    - الأكواد المسجّلة في النظام → employee_id = id الموظف
    - الأكواد غير المسجّلة → employee_id = NULL (محفوظة للمراجعة لاحقاً)
    - التكرار (نفس الكود + نفس الوقت) → يُتجاهل فقط لمنع التكرار

    Returns: (inserted, duplicates, unknown_codes, total)
    """
    if not records:
        return 0, 0, 0, 0

    conn = get_connection()
    cur = conn.cursor()

    emp_rows = cur.execute("SELECT id, code FROM employees").fetchall()
    code_to_id = {r["code"]: r["id"] for r in emp_rows}

    inserted = 0
    duplicates = 0
    unknown = 0

    try:
        for rec in records:
            code = str(rec.get("employee_code", "")).strip()
            punch_time = rec.get("punch_time")

            if not code or not punch_time:
                continue

            emp_id = code_to_id.get(code)
            if emp_id is None:
                unknown += 1  # نعدّها لكن لا نتجاهلها

            dup = cur.execute(
                "SELECT id FROM raw_punches WHERE employee_code=? AND punch_time=?",
                (code, punch_time)
            ).fetchone()

            if dup:
                duplicates += 1
                continue

            punch_date = punch_time.split(" ")[0]
            cur.execute("""
                INSERT INTO raw_punches
                    (employee_code, employee_id, punch_time, punch_date, source)
                VALUES (?, ?, ?, ?, ?)
            """, (code, emp_id, punch_time, punch_date, source))
            inserted += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[Device Punches] خطأ: {e}")
    finally:
        conn.close()

    return inserted, duplicates, unknown, len(records)


# للتوافق مع الكود القديم إن استُخدم
def add_device_punches_safe(records, source="device_pull"):
    return add_device_punches_all(records, source=source)


# ============================================================
#        Signals
# ============================================================
class DeviceSignals(QObject):
    punch_received = Signal(str, str, str, str)
    status_changed = Signal(str, str)
    connection_lost = Signal(str)
    log_message = Signal(str)


class PunchesPullSignals(QObject):
    result_ready = Signal(dict)
    status_changed = Signal(str, str)
    log_message = Signal(str)
    finished = Signal()


# ✅ جديد — Signals لسحب قائمة الموظفين
class UsersPullSignals(QObject):
    result_ready = Signal(dict)
    status_changed = Signal(str, str)
    log_message = Signal(str)
    finished = Signal()


# ============================================================
#              Thread الاستماع للبصمة
# ============================================================
class LiveListenerThread(threading.Thread):
    def __init__(self, ip, port, password, signals):
        super().__init__(daemon=True)
        self.ip = ip
        self.port = int(port)
        self.password = int(password)
        self.signals = signals
        self._stop_event = threading.Event()
        self._zk = None
        self._conn = None

    def stop(self):
        self._stop_event.set()
        try:
            if self._conn:
                self._conn.disconnect()
        except Exception:
            pass

    def run(self):
        try:
            from zk import ZK
        except ImportError:
            self.signals.status_changed.emit(
                "error",
                "مكتبة pyzk غير مثبتة.\nشغّل: python -m pip install pyzk"
            )
            return

        try:
            self.signals.status_changed.emit(
                "connecting", f"جاري الاتصال بـ {self.ip}:{self.port} ..."
            )
            self._zk = ZK(
                self.ip, port=self.port, timeout=10,
                password=self.password, force_udp=False, ommit_ping=True,
            )
            self._conn = self._zk.connect()

            try:
                dev_name = self._conn.get_device_name()
                serial = self._conn.get_serialnumber()
                self.signals.log_message.emit(
                    f"متصل بـ: {dev_name}  ·  S/N: {serial}"
                )
            except Exception:
                self.signals.log_message.emit("متصل بالجهاز بنجاح")

            self.signals.status_changed.emit(
                "connected", f"متصل بـ {self.ip}:{self.port}"
            )

            try:
                update_device_last_connected(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            except Exception:
                pass

            self.signals.log_message.emit("بدء الاستماع للبصمات...")

            while not self._stop_event.is_set():
                try:
                    for attendance in self._conn.live_capture():
                        if self._stop_event.is_set():
                            break
                        if attendance is None:
                            continue

                        emp_code = str(attendance.user_id).strip()
                        punch_ts = attendance.timestamp
                        if hasattr(punch_ts, "strftime"):
                            punch_str = punch_ts.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            punch_str = str(punch_ts)

                        ok, msg, emp_id = add_live_punch(
                            emp_code, punch_str, source_device="live"
                        )

                        emp_name = ""
                        if emp_id:
                            try:
                                from database import get_employee
                                e = get_employee(emp_id)
                                if e:
                                    emp_name = e["name"] or ""
                            except Exception:
                                pass

                        # لو الكود مش مسجل — نجيب الاسم من device_users
                        if not emp_name:
                            try:
                                from database import get_device_user
                                du = get_device_user(emp_code)
                                if du and du["name"]:
                                    emp_name = f"{du['name']} (غير مسجل)"
                            except Exception:
                                pass

                        if ok:
                            self.signals.punch_received.emit(
                                emp_code, punch_str, emp_name, "live"
                            )
                            self.signals.log_message.emit(
                                f"بصمة: {emp_code} ({emp_name or 'غير معروف'}) @ {punch_str}"
                            )
                        else:
                            self.signals.log_message.emit(
                                f"تجاهل: {emp_code} — {msg}"
                            )

                except Exception as inner_e:
                    if self._stop_event.is_set():
                        break
                    self.signals.log_message.emit(
                        f"خطأ مؤقت: {inner_e} — إعادة المحاولة..."
                    )
                    time.sleep(3)
                    try:
                        if self._conn:
                            self._conn.disconnect()
                    except Exception:
                        pass
                    try:
                        self._conn = self._zk.connect()
                        self.signals.status_changed.emit(
                            "connected", "تم إعادة الاتصال"
                        )
                    except Exception as reconn_e:
                        self.signals.status_changed.emit(
                            "error", f"فشل إعادة الاتصال: {reconn_e}"
                        )
                        return

        except Exception as e:
            self.signals.status_changed.emit("error", f"فشل الاتصال: {e}")
        finally:
            try:
                if self._conn:
                    self._conn.disconnect()
            except Exception:
                pass
            self.signals.status_changed.emit("disconnected", "تم قطع الاتصال")


# ============================================================
#       Thread سحب البصمات (جميع البصمات بدون فلترة)
# ============================================================
class PunchesPullThread(threading.Thread):
    def __init__(self, ip, port, password, from_date, to_date, signals):
        super().__init__(daemon=True)
        self.ip = ip
        self.port = int(port)
        self.password = int(password)
        self.from_date = from_date
        self.to_date = to_date
        self.signals = signals

    def run(self):
        conn = None
        try:
            from zk import ZK
        except ImportError:
            self.signals.status_changed.emit(
                "error",
                "مكتبة pyzk غير مثبتة.\nشغّل: python -m pip install pyzk"
            )
            self.signals.finished.emit()
            return

        try:
            self.signals.status_changed.emit(
                "connecting", f"جاري الاتصال بـ {self.ip}:{self.port} ..."
            )
            zk = ZK(
                self.ip, port=self.port, timeout=60,
                password=self.password, force_udp=False, ommit_ping=True,
            )
            conn = zk.connect()

            try:
                dev_name = conn.get_device_name()
                self.signals.log_message.emit(f"الجهاز: {dev_name}")
            except Exception:
                pass

            self.signals.status_changed.emit("connected", "متصل — جاري سحب البصمات...")
            self.signals.log_message.emit(
                f"جاري سحب البصمات من {self.from_date} إلى {self.to_date} ..."
            )

            all_atts = conn.get_attendance()
            total_from_device = len(all_atts) if all_atts else 0
            self.signals.log_message.emit(
                f"إجمالي البصمات على الجهاز: {total_from_device}"
            )

            from_dt = datetime.strptime(self.from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(self.to_date, "%Y-%m-%d") + timedelta(days=1)

            filtered = []
            for att in (all_atts or []):
                try:
                    ts = att.timestamp
                    if not hasattr(ts, "strftime"):
                        continue
                    if ts < from_dt or ts >= to_dt:
                        continue

                    emp_code = str(att.user_id).strip()
                    punch_str = ts.strftime("%Y-%m-%d %H:%M:%S")

                    filtered.append({
                        "employee_code": emp_code,
                        "punch_time": punch_str,
                    })
                except Exception:
                    continue

            in_range = len(filtered)
            self.signals.log_message.emit(
                f"بصمات في الفترة المحددة: {in_range}"
            )

            # ✅ الحفظ الآن يشمل كل الأكواد (المسجّلة وغير المسجّلة)
            inserted, duplicates, unknown, total = add_device_punches_all(
                filtered, source="device_pull"
            )

            self.signals.log_message.emit(f"تم إضافة {inserted} بصمة جديدة")
            if duplicates:
                self.signals.log_message.emit(
                    f"مكررة (موجودة مسبقاً): {duplicates}"
                )
            if unknown:
                self.signals.log_message.emit(
                    f"أكواد غير مسجّلة في النظام: {unknown} (تم حفظ بصماتها)"
                )

            result = {
                "total_from_device": total_from_device,
                "in_range": in_range,
                "inserted": inserted,
                "duplicates": duplicates,
                "unknown": unknown,
                "from_date": self.from_date,
                "to_date": self.to_date,
            }

            self.signals.result_ready.emit(result)
            self.signals.status_changed.emit("done", "تم السحب بنجاح")

        except Exception as e:
            self.signals.status_changed.emit("error", f"فشل السحب: {e}")
            self.signals.log_message.emit(f"خطأ في السحب: {e}")
        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:
                pass
            self.signals.finished.emit()


# ============================================================
#       ✅ Thread جديد: سحب قائمة الموظفين من الجهاز
# ============================================================
class UsersPullThread(threading.Thread):
    """يسحب قائمة الموظفين (users) من ذاكرة الجهاز بأسمائهم وأكوادهم."""

    def __init__(self, ip, port, password, signals):
        super().__init__(daemon=True)
        self.ip = ip
        self.port = int(port)
        self.password = int(password)
        self.signals = signals

    def run(self):
        conn = None
        try:
            from zk import ZK
        except ImportError:
            self.signals.status_changed.emit(
                "error",
                "مكتبة pyzk غير مثبتة.\nشغّل: python -m pip install pyzk"
            )
            self.signals.finished.emit()
            return

        try:
            self.signals.status_changed.emit(
                "connecting", f"جاري الاتصال بـ {self.ip}:{self.port} ..."
            )
            zk = ZK(
                self.ip, port=self.port, timeout=60,
                password=self.password, force_udp=False, ommit_ping=True,
            )
            conn = zk.connect()

            try:
                dev_name = conn.get_device_name()
                self.signals.log_message.emit(f"الجهاز: {dev_name}")
            except Exception:
                pass

            self.signals.status_changed.emit(
                "connected", "متصل — جاري سحب قائمة الموظفين..."
            )

            users = conn.get_users()
            self.signals.log_message.emit(
                f"عدد الموظفين على الجهاز: {len(users) if users else 0}"
            )

            device_users = []
            for u in (users or []):
                try:
                    device_users.append({
                        "uid": getattr(u, "uid", None),
                        "user_id": str(getattr(u, "user_id", "")).strip(),
                        "name": str(getattr(u, "name", "") or "").strip(),
                        "privilege": int(getattr(u, "privilege", 0) or 0),
                        "password": str(getattr(u, "password", "") or ""),
                        "group_id": str(getattr(u, "group_id", "") or ""),
                        "card": int(getattr(u, "card", 0) or 0),
                    })
                except Exception:
                    continue

            inserted, updated, failed = save_pulled_device_users(
                device_users, device_ip=self.ip
            )

            self.signals.log_message.emit(
                f"تم حفظ {inserted} موظف جديد + تحديث {updated} موظف"
            )

            # نحسب عدد غير المسجلين في النظام
            try:
                from database import count_unregistered_device_users
                unregistered = count_unregistered_device_users()
            except Exception:
                unregistered = 0

            result = {
                "total_from_device": len(device_users),
                "inserted": inserted,
                "updated": updated,
                "failed": failed,
                "unregistered": unregistered,
            }

            self.signals.result_ready.emit(result)
            self.signals.status_changed.emit("done", "تم سحب قائمة الموظفين بنجاح")

        except Exception as e:
            self.signals.status_changed.emit("error", f"فشل السحب: {e}")
            self.signals.log_message.emit(f"خطأ في سحب الموظفين: {e}")
        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:
                pass
            self.signals.finished.emit()


# ============================================================
#              Dialog: ملخص نتائج سحب البصمات
# ============================================================
class PullResultDialog(QDialog):
    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("نتيجة سحب البصمات")
        self.setMinimumWidth(640)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")

        self.result = result or {}
        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(18)

        head = QFrame()
        head.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:0.5 {NAVY_2}, stop:1 {NAVY_3});
                border-radius:14px;
            }}
        """)
        apply_shadow(head, blur=20, y_offset=4, alpha=60)

        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 18, 22, 18)
        hl.setSpacing(16)

        tbox = QVBoxLayout()
        tbox.setSpacing(4)
        title = QLabel("اكتمل سحب البصمات")
        title.setStyleSheet(
            "font-size:17px; font-weight:900; color:white; background:transparent;"
        )
        tbox.addWidget(title)
        sub = QLabel(
            f"الفترة: {self.result.get('from_date','')}  →  {self.result.get('to_date','')}"
        )
        sub.setStyleSheet("font-size:11px; color:#9db3cf; background:transparent;")
        tbox.addWidget(sub)
        hl.addLayout(tbox)
        hl.addStretch()

        v.addWidget(head)

        cards_grid = QGridLayout()
        cards_grid.setSpacing(14)

        c1 = self._mini_card("إجمالي على الجهاز",
                             str(self.result.get("total_from_device", 0)),
                             PRIMARY, PRIMARY_BG, PRIMARY_BRD)
        c2 = self._mini_card("في الفترة المحددة",
                             str(self.result.get("in_range", 0)),
                             INFO, INFO_BG, INFO_BRD)
        c3 = self._mini_card("تم إضافتها للنظام",
                             str(self.result.get("inserted", 0)),
                             SUCCESS, SUCCESS_BG, SUCCESS_BRD)
        c4 = self._mini_card("مكررة (موجودة)",
                             str(self.result.get("duplicates", 0)),
                             WARNING, WARNING_BG, WARNING_BRD)
        c5 = self._mini_card("أكواد غير مسجّلة",
                             str(self.result.get("unknown", 0)),
                             DANGER, DANGER_BG, DANGER_BRD)

        cards_grid.addWidget(c1, 0, 0)
        cards_grid.addWidget(c2, 0, 1)
        cards_grid.addWidget(c3, 0, 2)
        cards_grid.addWidget(c4, 1, 0)
        cards_grid.addWidget(c5, 1, 1)

        for c in range(3):
            cards_grid.setColumnStretch(c, 1)

        v.addLayout(cards_grid)

        note = QFrame()
        note.setStyleSheet(f"""
            QFrame {{
                background:{INFO_BG};
                border:1px solid {INFO_BRD};
                border-radius:10px;
            }}
        """)
        nl = QHBoxLayout(note)
        nl.setContentsMargins(16, 14, 16, 14)
        nl.setSpacing(10)

        note_lbl = QLabel(
            "تم حفظ جميع البصمات في النظام — حتى بصمات الأكواد غير المسجّلة. "
            "بصمات الأكواد غير المسجّلة تُخزَّن بـ employee_id فارغ، ويمكنك "
            "رؤيتها في جدول البصمات الأخيرة لاحقاً."
        )
        note_lbl.setStyleSheet(
            f"font-size:11.5px; color:{INFO}; background:transparent; font-weight:600;"
        )
        note_lbl.setWordWrap(True)
        nl.addWidget(note_lbl, 1)
        v.addWidget(note)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_close = QPushButton("حسناً")
        btn_close.setFixedHeight(44)
        btn_close.setMinimumWidth(150)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                color:white; border:none;
                border-radius:10px; padding:0 28px;
                font-weight:900; font-size:13px;
            }}
            QPushButton:hover {{ background:{SUCCESS_HOV}; }}
        """)
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        v.addLayout(btns)

    def _mini_card(self, title, value, color, bg, brd):
        card = QFrame()
        card.setMinimumHeight(80)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:12px;
            }}
            QFrame:hover {{ border:1.5px solid {brd}; }}
        """)
        apply_shadow(card, blur=10, y_offset=2, alpha=18)

        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(4)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:10.5px; color:{TEXT_MUTED}; font-weight:800;"
        )
        v.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:22px; color:{color}; font-weight:900;"
        )
        v.addWidget(val)

        return card


# ============================================================
#   ✅ Dialog: ملخص سحب قائمة الموظفين من الجهاز
# ============================================================
class UsersPullResultDialog(QDialog):
    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("نتيجة سحب قائمة الموظفين")
        self.setMinimumWidth(600)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")
        self.result = result or {}
        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(18)

        head = QFrame()
        head.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:0.5 {NAVY_2}, stop:1 {NAVY_3});
                border-radius:14px;
            }}
        """)
        apply_shadow(head, blur=20, y_offset=4, alpha=60)

        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 18, 22, 18)

        title = QLabel("اكتمل سحب قائمة الموظفين من الجهاز")
        title.setStyleSheet(
            "font-size:16px; font-weight:900; color:white; background:transparent;"
        )
        hl.addWidget(title)
        hl.addStretch()
        v.addWidget(head)

        cards_grid = QGridLayout()
        cards_grid.setSpacing(14)

        c1 = self._mini_card("على الجهاز",
                             str(self.result.get("total_from_device", 0)),
                             PRIMARY, PRIMARY_BG, PRIMARY_BRD)
        c2 = self._mini_card("جديد",
                             str(self.result.get("inserted", 0)),
                             SUCCESS, SUCCESS_BG, SUCCESS_BRD)
        c3 = self._mini_card("محدَّث",
                             str(self.result.get("updated", 0)),
                             INFO, INFO_BG, INFO_BRD)
        c4 = self._mini_card("غير مسجّل في النظام",
                             str(self.result.get("unregistered", 0)),
                             WARNING, WARNING_BG, WARNING_BRD)

        cards_grid.addWidget(c1, 0, 0)
        cards_grid.addWidget(c2, 0, 1)
        cards_grid.addWidget(c3, 1, 0)
        cards_grid.addWidget(c4, 1, 1)

        for c in range(2):
            cards_grid.setColumnStretch(c, 1)

        v.addLayout(cards_grid)

        note = QFrame()
        note.setStyleSheet(f"""
            QFrame {{
                background:{INFO_BG};
                border:1px solid {INFO_BRD};
                border-radius:10px;
            }}
        """)
        nl = QHBoxLayout(note)
        nl.setContentsMargins(16, 14, 16, 14)
        note_lbl = QLabel(
            "تم سحب أسماء الموظفين من الجهاز. افتح قسم «الموظفون على الجهاز» "
            "لمعرفة الأكواد غير المسجّلة في النظام وتسجيلها إن أردت."
        )
        note_lbl.setStyleSheet(
            f"font-size:11.5px; color:{INFO}; background:transparent; font-weight:600;"
        )
        note_lbl.setWordWrap(True)
        nl.addWidget(note_lbl, 1)
        v.addWidget(note)

        btns = QHBoxLayout()
        btns.addStretch()
        btn = QPushButton("حسناً")
        btn.setFixedHeight(42)
        btn.setMinimumWidth(140)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                color:white; border:none;
                border-radius:10px; padding:0 26px;
                font-weight:900; font-size:13px;
            }}
            QPushButton:hover {{ background:{SUCCESS_HOV}; }}
        """)
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        v.addLayout(btns)

    def _mini_card(self, title, value, color, bg, brd):
        card = QFrame()
        card.setMinimumHeight(80)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:12px;
            }}
            QFrame:hover {{ border:1.5px solid {brd}; }}
        """)
        apply_shadow(card, blur=10, y_offset=2, alpha=18)

        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(4)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:10.5px; color:{TEXT_MUTED}; font-weight:800;"
        )
        v.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:22px; color:{color}; font-weight:900;"
        )
        v.addWidget(val)

        return card


# ============================================================
#                   صفحة ربط البصمة
# ============================================================
class DeviceConnectionPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._thread = None
        self._pull_thread = None
        self._users_thread = None
        self._signals = DeviceSignals()
        self._pull_signals = PunchesPullSignals()
        self._users_signals = UsersPullSignals()
        self._connect_signals()
        self._connect_pull_signals()
        self._connect_users_signals()
        self._build_ui()
        self._load_settings()
        self._refresh_recent_punches()
        self._refresh_device_users()

    def _connect_signals(self):
        self._signals.punch_received.connect(self._on_punch_received)
        self._signals.status_changed.connect(self._on_status_changed)
        self._signals.log_message.connect(self._append_log)

    def _connect_pull_signals(self):
        self._pull_signals.result_ready.connect(self._on_pull_result)
        self._pull_signals.status_changed.connect(self._on_pull_status)
        self._pull_signals.log_message.connect(self._append_log)
        self._pull_signals.finished.connect(self._on_pull_finished)

    def _connect_users_signals(self):
        self._users_signals.result_ready.connect(self._on_users_result)
        self._users_signals.status_changed.connect(self._on_users_status)
        self._users_signals.log_message.connect(self._append_log)
        self._users_signals.finished.connect(self._on_users_finished)

    # ========================================================
    #                    بناء الواجهة
    # ========================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background:{BG}; border:none; }}
            QScrollBar:vertical {{
                width:9px; background:transparent; margin:2px;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2}; border-radius:4px; min-height:40px;
            }}
            QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height:0; }}
        """)

        body = QWidget()
        body.setObjectName("deviceBody")
        body.setStyleSheet(f"QWidget#deviceBody {{ background:{BG}; }}")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(26, 22, 26, 26)
        body_layout.setSpacing(18)

        body_layout.addWidget(self._build_settings_card())
        body_layout.addWidget(self._build_status_card())
        # ✅ قسم جديد: قائمة الموظفين على الجهاز
        body_layout.addWidget(self._build_device_users_card())
        body_layout.addWidget(self._build_pull_card())
        body_layout.addWidget(self._build_live_table_card())
        body_layout.addWidget(self._build_log_card())

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("deviceTopbar")
        bar.setFixedHeight(76)
        bar.setStyleSheet(f"""
            QFrame#deviceTopbar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:0.5 {NAVY_2}, stop:1 {NAVY_3});
                border:none;
                border-bottom:1px solid #1e3a5f;
            }}
        """)

        h = QHBoxLayout(bar)
        h.setContentsMargins(30, 0, 30, 0)
        h.setSpacing(16)

        title = QLabel("ربط جهاز البصمة")
        title.setStyleSheet(f"""
            QLabel {{
                color:white; font-size:20px; font-weight:900;
                background:transparent; font-family:{FONT_FAMILY};
            }}
        """)
        h.addWidget(title)
        h.addStretch()

        self.topbar_status = QLabel("غير متصل")
        self.topbar_status.setAlignment(Qt.AlignCenter)
        self.topbar_status.setFixedHeight(34)
        self.topbar_status.setMinimumWidth(120)
        self.topbar_status.setStyleSheet(f"""
            QLabel {{
                background: rgba(148, 163, 184, 0.15);
                color:#cbd5e1;
                border:1px solid rgba(148, 163, 184, 0.35);
                border-radius:17px;
                padding:0 16px;
                font-size:11.5px;
                font-weight:800;
            }}
        """)
        h.addWidget(self.topbar_status)

        return bar

    # ----------------------------------------------------------
    def _build_settings_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setStyleSheet(f"""
            QFrame#settingsCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=4, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(16)

        ht = QLabel("إعدادات الجهاز")
        ht.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        v.addWidget(ht)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER}; border:none;")
        v.addWidget(line)

        g = QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(14)
        for c in range(4):
            g.setColumnStretch(c, 1)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.201")
        self.ip_input.setFixedHeight(46)
        self.ip_input.setLayoutDirection(Qt.LeftToRight)
        self.ip_input.setAlignment(Qt.AlignLeft)
        self._style_input(self.ip_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(4370)
        self.port_input.setFixedHeight(46)
        self.port_input.setLayoutDirection(Qt.LeftToRight)
        self.port_input.setAlignment(Qt.AlignLeft)
        self._style_spinbox(self.port_input)

        self.password_input = QSpinBox()
        self.password_input.setRange(0, 99999999)
        self.password_input.setValue(0)
        self.password_input.setFixedHeight(46)
        self.password_input.setLayoutDirection(Qt.LeftToRight)
        self.password_input.setAlignment(Qt.AlignLeft)
        self._style_spinbox(self.password_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("جهاز البصمة الرئيسي")
        self.name_input.setFixedHeight(46)
        self.name_input.setText("جهاز البصمة الرئيسي")
        self._style_input(self.name_input)

        g.addWidget(self._field("عنوان IP", self.ip_input), 0, 0)
        g.addWidget(self._field("المنفذ (Port)", self.port_input), 0, 1)
        g.addWidget(self._field("كلمة المرور (Password)", self.password_input), 0, 2)
        g.addWidget(self._field("اسم الجهاز", self.name_input), 0, 3)

        v.addLayout(g)

        self.auto_listen_cb = QCheckBox("الاستماع تلقائياً عند فتح التطبيق")
        self.auto_listen_cb.setCursor(Qt.PointingHandCursor)
        self.auto_listen_cb.setStyleSheet(f"""
            QCheckBox {{
                font-size:12px; font-weight:800; color:{TEXT_SEC};
                background:transparent; spacing:9px; padding:6px 0;
            }}
            QCheckBox::indicator {{
                width:18px; height:18px;
                border:1.5px solid {BORDER_2};
                border-radius:5px; background:white;
            }}
            QCheckBox::indicator:hover {{ border-color:{PRIMARY}; }}
            QCheckBox::indicator:checked {{
                background:{PRIMARY}; border-color:{PRIMARY};
            }}
        """)
        v.addWidget(self.auto_listen_cb)

        btns = QHBoxLayout()
        btns.setSpacing(10)

        self.btn_connect = QPushButton("ربط الجهاز")
        self.btn_connect.setFixedHeight(46)
        self.btn_connect.setMinimumWidth(170)
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                color:white; border:none;
                border-radius:10px; padding:0 26px;
                font-weight:900; font-size:13px;
            }}
            QPushButton:hover {{ background:{SUCCESS_HOV}; }}
            QPushButton:disabled {{
                background:{SURFACE_2}; color:{TEXT_MUTED};
                border:1px solid {BORDER};
            }}
        """)
        self.btn_connect.clicked.connect(self._on_connect)
        btns.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("إيقاف الاستماع")
        self.btn_disconnect.setFixedHeight(46)
        self.btn_disconnect.setMinimumWidth(170)
        self.btn_disconnect.setCursor(Qt.PointingHandCursor)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{DANGER};
                border:1.5px solid {DANGER_BRD}; border-radius:10px;
                padding:0 26px; font-weight:800; font-size:13px;
            }}
            QPushButton:hover:enabled {{ background:{DANGER_BG}; }}
            QPushButton:disabled {{
                background:{SURFACE_2}; color:{TEXT_MUTED};
                border-color:{BORDER};
            }}
        """)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        btns.addWidget(self.btn_disconnect)

        btns.addStretch()

        btn_save = QPushButton("حفظ الإعدادات")
        btn_save.setFixedHeight(46)
        btn_save.setMinimumWidth(170)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{PRIMARY_DK};
                border:1.5px solid {PRIMARY_BRD}; border-radius:10px;
                padding:0 26px; font-weight:800; font-size:13px;
            }}
            QPushButton:hover {{ background:{PRIMARY_BG}; }}
        """)
        btn_save.clicked.connect(self._save_settings)
        btns.addWidget(btn_save)

        v.addLayout(btns)

        return card

    # ----------------------------------------------------------
    def _build_status_card(self):
        card = QFrame()
        card.setObjectName("statusCard")
        card.setStyleSheet(f"""
            QFrame#statusCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=4, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(16)

        ht = QLabel("حالة الاتصال")
        ht.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        v.addWidget(ht)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER}; border:none;")
        v.addWidget(line)

        self.status_box = QFrame()
        self.status_box.setMinimumHeight(110)
        self.status_box.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:12px;
            }}
        """)
        sb = QHBoxLayout(self.status_box)
        sb.setContentsMargins(24, 18, 24, 18)
        sb.setSpacing(20)

        self.status_dot = QFrame()
        self.status_dot.setFixedSize(14, 14)
        self.status_dot.setStyleSheet(
            f"background:{TEXT_MUTED}; border-radius:7px; border:none;"
        )

        dot_wrap = QVBoxLayout()
        dot_wrap.addStretch()
        dot_wrap.addWidget(self.status_dot, 0, Qt.AlignCenter)
        dot_wrap.addStretch()

        dot_container = QWidget()
        dot_container.setStyleSheet("background:transparent;")
        dot_container.setLayout(dot_wrap)
        dot_container.setFixedWidth(60)
        sb.addWidget(dot_container)

        status_text = QVBoxLayout()
        status_text.setSpacing(6)

        self.status_label = QLabel("غير متصل")
        self.status_label.setStyleSheet(
            f"font-size:18px; font-weight:900; color:{TEXT_MUTED}; "
            f"background:transparent; border:none;"
        )
        status_text.addWidget(self.status_label)

        self.status_detail = QLabel("أدخل IP واضغط «ربط الجهاز» لبدء الاستماع")
        self.status_detail.setWordWrap(True)
        self.status_detail.setStyleSheet(
            f"font-size:12px; color:{TEXT_MUTED}; background:transparent; border:none;"
        )
        status_text.addWidget(self.status_detail)

        sb.addLayout(status_text, 1)

        v.addWidget(self.status_box)

        stats = QHBoxLayout()
        stats.setSpacing(12)

        self.cnt_today = self._mini_counter("بصمات اليوم", "0",
                                            PRIMARY, PRIMARY_BG, PRIMARY_BRD)
        self.cnt_total = self._mini_counter("إجمالي البصمات", "0",
                                            SUCCESS, SUCCESS_BG, SUCCESS_BRD)
        self.cnt_live = self._mini_counter("بصمات حية (هذه الجلسة)", "0",
                                           DANGER, DANGER_BG, DANGER_BRD)

        stats.addWidget(self.cnt_today)
        stats.addWidget(self.cnt_total)
        stats.addWidget(self.cnt_live)
        v.addLayout(stats)

        return card

    # ----------------------------------------------------------
    #   ✅ قسم جديد: الموظفون على الجهاز
    # ----------------------------------------------------------
    def _build_device_users_card(self):
        card = QFrame()
        card.setObjectName("deviceUsersCard")
        card.setStyleSheet(f"""
            QFrame#deviceUsersCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=4, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(16)

        # العنوان + الأزرار
        head = QHBoxLayout()
        head.setSpacing(12)

        ht = QLabel("الموظفون على الجهاز")
        ht.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        head.addWidget(ht)
        head.addStretch()

        # سطر معلومات آخر مزامنة
        self.users_sync_label = QLabel("لم تتم المزامنة بعد")
        self.users_sync_label.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; background:transparent; "
            f"font-weight:700; padding-right:6px;"
        )
        head.addWidget(self.users_sync_label)

        v.addLayout(head)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER}; border:none;")
        v.addWidget(line)

        # بطاقات إحصائية صغيرة
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.du_total = self._mini_counter("إجمالي على الجهاز", "0",
                                           PRIMARY, PRIMARY_BG, PRIMARY_BRD)
        self.du_registered = self._mini_counter("مسجّل في النظام", "0",
                                                SUCCESS, SUCCESS_BG, SUCCESS_BRD)
        self.du_unregistered = self._mini_counter("غير مسجّل", "0",
                                                  WARNING, WARNING_BG, WARNING_BRD)
        stats_row.addWidget(self.du_total)
        stats_row.addWidget(self.du_registered)
        stats_row.addWidget(self.du_unregistered)
        v.addLayout(stats_row)

        # أزرار التحكم
        btns_row = QHBoxLayout()
        btns_row.setSpacing(10)

        self.btn_pull_users = QPushButton("سحب قائمة الموظفين من الجهاز")
        self.btn_pull_users.setFixedHeight(46)
        self.btn_pull_users.setMinimumWidth(240)
        self.btn_pull_users.setCursor(Qt.PointingHandCursor)
        self.btn_pull_users.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_DK});
                color:white; border:none;
                border-radius:10px; padding:0 26px;
                font-weight:900; font-size:13px;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOV}; }}
            QPushButton:disabled {{
                background:{SURFACE_2}; color:{TEXT_MUTED};
                border:1px solid {BORDER};
            }}
        """)
        self.btn_pull_users.clicked.connect(self._on_pull_users)
        btns_row.addWidget(self.btn_pull_users)

        # فلتر
        self.users_filter = QComboBox()
        self.users_filter.setFixedHeight(46)
        self.users_filter.setMinimumWidth(200)
        self.users_filter.addItem("الكل", "all")
        self.users_filter.addItem("غير مسجّل في النظام فقط", "unregistered")
        self.users_filter.addItem("مسجّل في النظام فقط", "registered")
        self.users_filter.setStyleSheet(f"""
            QComboBox {{
                background:{SURFACE_2}; border:1.5px solid {BORDER};
                border-radius:10px; padding:0 14px;
                font-size:12.5px; color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QComboBox:hover {{ background:white; border-color:{BORDER_2}; }}
            QComboBox:focus {{ background:white; border:1.5px solid {PRIMARY}; }}
            QComboBox::drop-down {{ border:none; width:26px; }}
            QComboBox::down-arrow {{
                image:none; width:0; height:0;
                border-left:4px solid transparent;
                border-right:4px solid transparent;
                border-top:5px solid {TEXT_MUTED};
                margin-right:8px;
            }}
            QComboBox QAbstractItemView {{
                background:white;
                border:1px solid {BORDER};
                padding:4px;
                selection-background-color:{PRIMARY_BG};
                selection-color:{PRIMARY};
                outline:none;
            }}
            QComboBox QAbstractItemView::item {{
                padding:7px 10px; min-height:22px;
            }}
        """)
        self.users_filter.currentIndexChanged.connect(
            lambda _: self._refresh_device_users()
        )
        btns_row.addWidget(self.users_filter)

        btns_row.addStretch()

        btn_clear_users = QPushButton("حذف القائمة المحفوظة")
        btn_clear_users.setFixedHeight(46)
        btn_clear_users.setMinimumWidth(170)
        btn_clear_users.setCursor(Qt.PointingHandCursor)
        btn_clear_users.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{DANGER};
                border:1.5px solid {DANGER_BRD}; border-radius:10px;
                padding:0 26px; font-weight:800; font-size:13px;
            }}
            QPushButton:hover {{ background:{DANGER_BG}; }}
        """)
        btn_clear_users.clicked.connect(self._clear_device_users)
        btns_row.addWidget(btn_clear_users)

        v.addLayout(btns_row)

        # الجدول
        self.users_table = QTableWidget(0, 4)
        self.users_table.setHorizontalHeaderLabels([
            "كود الموظف على الجهاز", "الاسم على الجهاز",
            "الحالة في النظام", "البصمات المسجّلة"
        ])
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.setShowGrid(False)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.setFocusPolicy(Qt.NoFocus)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setMinimumHeight(260)
        self.users_table.setStyleSheet(f"""
            QTableWidget {{
                background:{SURFACE}; border:none; color:{TEXT};
                font-size:11.5px; outline:none;
                selection-background-color:{PRIMARY_BG};
                selection-color:{TEXT}; gridline-color:transparent;
                font-family:{FONT_FAMILY};
            }}
            QTableWidget::item {{
                padding:10px 8px; border-bottom:1px solid {DIVIDER};
            }}
            QTableWidget::item:selected {{
                background:{PRIMARY_BG}; color:{TEXT};
            }}
            QTableWidget::item:alternate {{ background:{ROW_ALT}; }}
            QHeaderView::section {{
                background:{HEADER_BG}; color:{TEXT_MUTED};
                padding:12px 8px; border:none;
                border-bottom:1px solid {BORDER};
                font-weight:900; font-size:10.5px;
            }}
            QScrollBar:vertical {{
                width:9px; background:transparent; margin:2px;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2}; border-radius:4px; min-height:40px;
            }}
            QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        hh = self.users_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        self.users_table.verticalHeader().setDefaultSectionSize(46)
        v.addWidget(self.users_table)

        return card

    # ----------------------------------------------------------
    def _build_pull_card(self):
        card = QFrame()
        card.setObjectName("pullCard")
        card.setStyleSheet(f"""
            QFrame#pullCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8fafc, stop:1 #eef2ff);
                border:1.5px solid {PRIMARY_BRD};
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=4, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(16)

        ht = QLabel("سحب البصمات المخزّنة على الجهاز")
        ht.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        v.addWidget(ht)

        sub = QLabel(
            "يتم سحب جميع البصمات (بما فيها أكواد غير مسجّلة في النظام) وحفظها كاملة"
        )
        sub.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; background:transparent;"
        )
        sub.setWordWrap(True)
        v.addWidget(sub)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{PRIMARY_BRD}; border:none;")
        v.addWidget(line)

        dates_row = QHBoxLayout()
        dates_row.setSpacing(14)

        self.pull_from_date = QDateEdit()
        self.pull_from_date.setCalendarPopup(True)
        self.pull_from_date.setDisplayFormat("yyyy-MM-dd")
        self.pull_from_date.setDate(QDate.currentDate().addDays(-30))
        self.pull_from_date.setFixedHeight(46)
        self.pull_from_date.setLayoutDirection(Qt.LeftToRight)
        self._style_date(self.pull_from_date)
        dates_row.addWidget(self._field("من تاريخ", self.pull_from_date), 1)

        self.pull_to_date = QDateEdit()
        self.pull_to_date.setCalendarPopup(True)
        self.pull_to_date.setDisplayFormat("yyyy-MM-dd")
        self.pull_to_date.setDate(QDate.currentDate())
        self.pull_to_date.setFixedHeight(46)
        self.pull_to_date.setLayoutDirection(Qt.LeftToRight)
        self._style_date(self.pull_to_date)
        dates_row.addWidget(self._field("إلى تاريخ", self.pull_to_date), 1)

        v.addLayout(dates_row)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)

        quick_lbl = QLabel("فترة سريعة:")
        quick_lbl.setStyleSheet(
            f"font-size:11.5px; color:{TEXT_SEC}; font-weight:800; background:transparent;"
        )
        quick_row.addWidget(quick_lbl)

        quick_row.addWidget(self._quick_btn("آخر 7 أيام", 7))
        quick_row.addWidget(self._quick_btn("آخر 30 يوم", 30))
        quick_row.addWidget(self._quick_btn("آخر 90 يوم", 90))
        quick_row.addWidget(self._quick_btn("هذا الشهر", None, "month"))
        quick_row.addWidget(self._quick_btn("كل البصمات", None, "all"))
        quick_row.addStretch()

        v.addLayout(quick_row)

        self.btn_pull_punches = QPushButton("ابدأ سحب البصمات")
        self.btn_pull_punches.setFixedHeight(52)
        self.btn_pull_punches.setCursor(Qt.PointingHandCursor)
        self.btn_pull_punches.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PRIMARY}, stop:0.5 #4d6bff, stop:1 {PRIMARY_DK});
                color:white; border:none;
                border-radius:11px; padding:0 28px;
                font-weight:900; font-size:14px;
                font-family:{FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PRIMARY_HOV}, stop:0.5 {PRIMARY}, stop:1 {PRIMARY_DK});
            }}
            QPushButton:pressed {{ background:{PRIMARY_DK}; }}
            QPushButton:disabled {{
                background:{SURFACE_2}; color:{TEXT_MUTED};
                border:1px solid {BORDER};
            }}
        """)
        self.btn_pull_punches.clicked.connect(self._on_pull_punches)
        v.addWidget(self.btn_pull_punches)

        return card

    def _quick_btn(self, text, days=None, mode=None):
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE};
                color:{TEXT_SEC};
                border:1px solid {BORDER};
                border-radius:17px;
                padding:0 16px;
                font-size:11px;
                font-weight:800;
            }}
            QPushButton:hover {{
                background:{PRIMARY_BG};
                border-color:{PRIMARY_BRD};
                color:{PRIMARY_DK};
            }}
        """)

        def on_click():
            today = QDate.currentDate()
            if mode == "month":
                first = QDate(today.year(), today.month(), 1)
                self.pull_from_date.setDate(first)
                self.pull_to_date.setDate(today)
            elif mode == "all":
                self.pull_from_date.setDate(QDate(2020, 1, 1))
                self.pull_to_date.setDate(today)
            elif days is not None:
                self.pull_from_date.setDate(today.addDays(-days))
                self.pull_to_date.setDate(today)

        btn.clicked.connect(on_click)
        return btn

    def _style_date(self, w):
        w.setStyleSheet(f"""
            QDateEdit {{
                background:white;
                border:1.5px solid {BORDER};
                border-radius:10px;
                padding:0 14px;
                font-size:12.5px;
                color:{TEXT};
                font-weight:700;
            }}
            QDateEdit:hover {{ border-color:{BORDER_2}; }}
            QDateEdit:focus {{ border:1.5px solid {PRIMARY}; }}
            QDateEdit::drop-down {{ border:none; width:30px; }}
            QDateEdit::down-arrow {{
                image:none; width:0; height:0;
                border-left:4px solid transparent;
                border-right:4px solid transparent;
                border-top:5px solid {TEXT_MUTED};
                margin-right:10px;
            }}
        """)

    # ----------------------------------------------------------
    def _build_live_table_card(self):
        card = QFrame()
        card.setObjectName("liveTableCard")
        card.setStyleSheet(f"""
            QFrame#liveTableCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=4, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head = QFrame()
        head.setFixedHeight(60)
        head.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border-bottom:1px solid {DIVIDER};
                border-top-left-radius:14px;
                border-top-right-radius:14px;
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 0, 22, 0)
        hl.setSpacing(12)

        title = QLabel("آخر البصمات المسجّلة في النظام")
        title.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        hl.addWidget(title)
        hl.addStretch()

        btn_refresh = QPushButton("تحديث")
        btn_refresh.setFixedHeight(34)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1px solid {BORDER_2}; border-radius:9px;
                padding:0 18px; font-weight:800; font-size:11.5px;
            }}
            QPushButton:hover {{ background:{SURFACE_2}; border-color:{TEXT_MUTED}; }}
        """)
        btn_refresh.clicked.connect(self._refresh_recent_punches)
        hl.addWidget(btn_refresh)

        v.addWidget(head)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "الوقت", "كود الموظف", "اسم الموظف", "التاريخ", "المصدر"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(280)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background:{SURFACE}; border:none; color:{TEXT};
                font-size:11.5px; outline:none;
                selection-background-color:{PRIMARY_BG};
                selection-color:{TEXT}; gridline-color:transparent;
                font-family:{FONT_FAMILY};
            }}
            QTableWidget::item {{
                padding:10px 8px; border-bottom:1px solid {DIVIDER};
            }}
            QTableWidget::item:selected {{
                background:{PRIMARY_BG}; color:{TEXT};
            }}
            QTableWidget::item:alternate {{ background:{ROW_ALT}; }}
            QHeaderView::section {{
                background:{HEADER_BG}; color:{TEXT_MUTED};
                padding:12px 8px; border:none;
                border-bottom:1px solid {BORDER};
                font-weight:900; font-size:10.5px;
            }}
            QScrollBar:vertical {{
                width:9px; background:transparent; margin:2px;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2}; border-radius:4px; min-height:40px;
            }}
            QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(46)
        v.addWidget(self.table)

        return card

    # ----------------------------------------------------------
    def _build_log_card(self):
        card = QFrame()
        card.setObjectName("logCard")
        card.setStyleSheet(f"""
            QFrame#logCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=4, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head = QFrame()
        head.setFixedHeight(56)
        head.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border-bottom:1px solid {DIVIDER};
                border-top-left-radius:14px;
                border-top-right-radius:14px;
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 0, 22, 0)
        hl.setSpacing(12)

        title = QLabel("سجل الأحداث")
        title.setStyleSheet(f"font-size:13.5px; font-weight:900; color:{TEXT};")
        hl.addWidget(title)
        hl.addStretch()

        btn_clear = QPushButton("مسح السجل")
        btn_clear.setFixedHeight(32)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1px solid {BORDER}; border-radius:9px;
                padding:0 16px; font-weight:800; font-size:11px;
            }}
            QPushButton:hover {{ background:{SURFACE_2}; border-color:{BORDER_2}; }}
        """)
        btn_clear.clicked.connect(lambda: self.log_view.clear())
        hl.addWidget(btn_clear)

        v.addWidget(head)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(180)
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background:{SURFACE_2};
                border:none;
                border-bottom-left-radius:14px;
                border-bottom-right-radius:14px;
                padding:12px 16px;
                font-family: Consolas, monospace;
                font-size:11.5px;
                color:{TEXT_SEC};
                line-height:1.6;
            }}
        """)
        v.addWidget(self.log_view)

        return card

    # ========================================================
    #                  عناصر مساعدة
    # ========================================================
    def _field(self, label, widget):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(7)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size:10.5px; font-weight:800; color:{TEXT_SEC}; "
            f"background:transparent;"
        )
        v.addWidget(lbl)
        v.addWidget(widget)
        return w

    def _style_input(self, inp):
        inp.setStyleSheet(f"""
            QLineEdit {{
                background:{SURFACE_2}; border:1.5px solid {BORDER};
                border-radius:10px; padding:0 14px;
                font-size:12.5px; color:{TEXT};
            }}
            QLineEdit:hover {{ background:white; border-color:{BORDER_2}; }}
            QLineEdit:focus {{ background:white; border:1.5px solid {PRIMARY}; }}
        """)

    def _style_spinbox(self, sp):
        sp.setStyleSheet(f"""
            QSpinBox {{
                background:{SURFACE_2}; border:1.5px solid {BORDER};
                border-radius:10px; padding:0 14px;
                font-size:12.5px; color:{TEXT};
            }}
            QSpinBox:hover {{ background:white; border-color:{BORDER_2}; }}
            QSpinBox:focus {{ background:white; border:1.5px solid {PRIMARY}; }}
        """)

    def _mini_counter(self, title, value, color, soft, brd):
        card = QFrame()
        card.setMinimumHeight(78)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:11px;
            }}
            QFrame:hover {{ border-color:{brd}; }}
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(4)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:10.5px; color:{TEXT_MUTED}; font-weight:800; background:transparent;"
        )
        v.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:22px; color:{color}; font-weight:900; background:transparent;"
        )
        v.addWidget(val)

        card._value_label = val
        return card

    # ========================================================
    #                  تحميل/حفظ الإعدادات
    # ========================================================
    def _load_settings(self):
        try:
            s = get_device_settings()
            if s:
                self.ip_input.setText(s["device_ip"] or "")
                self.port_input.setValue(int(s["device_port"] or 4370))
                self.password_input.setValue(int(s["device_password"] or 0))
                self.name_input.setText(s["device_name"] or "جهاز البصمة الرئيسي")
                self.auto_listen_cb.setChecked(bool(s["auto_listen"]))

                if s["last_connected"]:
                    self._append_log(f"آخر اتصال: {s['last_connected']}")

                if s["auto_listen"] and s["device_ip"]:
                    QTimer.singleShot(1500, self._on_connect)
        except Exception as e:
            self._append_log(f"لم يتم تحميل الإعدادات: {e}")

    def _save_settings(self):
        ip = self.ip_input.text().strip()
        port = self.port_input.value()
        pwd = self.password_input.value()
        name = self.name_input.text().strip() or "جهاز البصمة الرئيسي"
        auto = 1 if self.auto_listen_cb.isChecked() else 0

        try:
            save_device_settings(ip, port, pwd, name, auto)
            QMessageBox.information(self, "تم", "تم حفظ إعدادات الجهاز")
            self._append_log("تم حفظ الإعدادات")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الحفظ:\n{e}")

    # ========================================================
    #                  الاتصال/القطع
    # ========================================================
    def _on_connect(self):
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "تنبيه", "أدخل عنوان IP للجهاز")
            self.ip_input.setFocus()
            return

        if self._thread and self._thread.is_alive():
            QMessageBox.information(self, "معلوم", "الاستماع يعمل بالفعل")
            return

        port = self.port_input.value()
        pwd = self.password_input.value()

        try:
            save_device_settings(
                ip, port, pwd,
                self.name_input.text().strip() or "جهاز البصمة الرئيسي",
                1 if self.auto_listen_cb.isChecked() else 0,
            )
        except Exception:
            pass

        self._append_log(f"محاولة الاتصال بـ {ip}:{port} ...")

        self._thread = LiveListenerThread(ip, port, pwd, self._signals)
        self._thread.start()

        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)

    def _on_disconnect(self):
        if self._thread and self._thread.is_alive():
            self._append_log("طلب إيقاف الاستماع...")
            self._thread.stop()
            self._thread = None
        self._set_status("disconnected", "تم إيقاف الاستماع")

        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    # ========================================================
    #   ✅ سحب قائمة الموظفين من الجهاز
    # ========================================================
    def _on_pull_users(self):
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "تنبيه", "أدخل عنوان IP للجهاز")
            self.ip_input.setFocus()
            return

        if self._users_thread and self._users_thread.is_alive():
            QMessageBox.information(self, "معلوم", "جاري السحب بالفعل")
            return

        port = self.port_input.value()
        pwd = self.password_input.value()

        self._append_log(f"بدء سحب قائمة الموظفين من {ip}:{port} ...")
        self.btn_pull_users.setEnabled(False)
        self.btn_pull_users.setText("جاري السحب...")

        self._users_thread = UsersPullThread(ip, port, pwd, self._users_signals)
        self._users_thread.start()

    def _on_users_result(self, result):
        try:
            dlg = UsersPullResultDialog(result, self)
            dlg.exec()
        except Exception as e:
            self._append_log(f"فشل عرض النتائج: {e}")
        self._refresh_device_users()

    def _on_users_status(self, status_type, message):
        self._append_log(f"[موظفون] {message}")

    def _on_users_finished(self):
        self.btn_pull_users.setEnabled(True)
        self.btn_pull_users.setText("سحب قائمة الموظفين من الجهاز")
        self._refresh_device_users()

    # ========================================================
    #        سحب البصمات من الجهاز
    # ========================================================
    def _on_pull_punches(self):
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "تنبيه", "أدخل عنوان IP للجهاز")
            self.ip_input.setFocus()
            return

        if self._pull_thread and self._pull_thread.is_alive():
            QMessageBox.information(self, "معلوم", "جاري السحب بالفعل")
            return

        fd = self.pull_from_date.date()
        td = self.pull_to_date.date()
        if fd > td:
            QMessageBox.warning(self, "تنبيه", "تاريخ البداية بعد تاريخ النهاية")
            return

        from_str = fd.toString("yyyy-MM-dd")
        to_str = td.toString("yyyy-MM-dd")

        ans = QMessageBox.question(
            self, "تأكيد سحب البصمات",
            f"سيتم سحب البصمات من الجهاز خلال الفترة:\n\n"
            f"من: {from_str}\nإلى: {to_str}\n\n"
            f"ملاحظة: تُحفظ جميع البصمات بما فيها أكواد غير مسجّلة بالنظام.\n"
            f"هل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if ans != QMessageBox.Yes:
            return

        port = self.port_input.value()
        pwd = self.password_input.value()

        self._append_log(
            f"بدء سحب البصمات من {ip}:{port} — "
            f"من {from_str} إلى {to_str} ..."
        )
        self.btn_pull_punches.setEnabled(False)
        self.btn_pull_punches.setText("جاري السحب...")

        self._pull_thread = PunchesPullThread(
            ip, port, pwd, from_str, to_str, self._pull_signals
        )
        self._pull_thread.start()

    def _on_pull_result(self, result):
        try:
            dlg = PullResultDialog(result, self)
            dlg.exec()
        except Exception as e:
            self._append_log(f"فشل عرض النتائج: {e}")

        self._refresh_recent_punches()

    def _on_pull_status(self, status_type, message):
        self._append_log(f"[سحب] {message}")

    def _on_pull_finished(self):
        self.btn_pull_punches.setEnabled(True)
        self.btn_pull_punches.setText("ابدأ سحب البصمات")
        self._refresh_recent_punches()

    # ========================================================
    #                  استقبال الإشارات
    # ========================================================
    def _on_punch_received(self, code, punch_time, name, source):
        self.table.insertRow(0)

        time_only = punch_time.split(" ")[1] if " " in punch_time else punch_time
        date_only = punch_time.split(" ")[0] if " " in punch_time else ""

        vals = [time_only, code, name or "—", date_only, "حي"]
        for c, v in enumerate(vals):
            item = QTableWidgetItem(str(v))
            item.setTextAlignment(Qt.AlignCenter)
            if c == 0:
                item.setForeground(QColor(SUCCESS))
                f = item.font(); f.setBold(True); item.setFont(f)
            elif c == 1:
                item.setForeground(QColor(PRIMARY))
                f = item.font(); f.setBold(True); item.setFont(f)
            elif c == 4:
                item.setForeground(QColor(DANGER))
                f = item.font(); f.setBold(True); item.setFont(f)
            else:
                item.setForeground(QColor(TEXT))
            self.table.setItem(0, c, item)

        while self.table.rowCount() > 200:
            self.table.removeRow(self.table.rowCount() - 1)

        try:
            cur = int(self.cnt_live._value_label.text() or "0")
            self.cnt_live._value_label.setText(str(cur + 1))
        except Exception:
            pass

        self._refresh_counters()

    def _on_status_changed(self, status_type, message):
        self._set_status(status_type, message)
        self._append_log(f"[{status_type}] {message}")

        if status_type == "connected":
            self.topbar_status.setText("متصل")
            self.topbar_status.setStyleSheet(f"""
                QLabel {{
                    background: rgba(5, 150, 105, 0.18);
                    color:#a7f3d0;
                    border:1px solid rgba(5, 150, 105, 0.4);
                    border-radius:17px;
                    padding:0 16px;
                    font-size:11.5px;
                    font-weight:800;
                }}
            """)
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
        elif status_type == "connecting":
            self.topbar_status.setText("جاري الاتصال")
            self.topbar_status.setStyleSheet(f"""
                QLabel {{
                    background: rgba(217, 119, 6, 0.18);
                    color:#fde68a;
                    border:1px solid rgba(217, 119, 6, 0.4);
                    border-radius:17px;
                    padding:0 16px;
                    font-size:11.5px;
                    font-weight:800;
                }}
            """)
        elif status_type == "disconnected":
            self.topbar_status.setText("غير متصل")
            self.topbar_status.setStyleSheet(f"""
                QLabel {{
                    background: rgba(148, 163, 184, 0.15);
                    color:#cbd5e1;
                    border:1px solid rgba(148, 163, 184, 0.35);
                    border-radius:17px;
                    padding:0 16px;
                    font-size:11.5px;
                    font-weight:800;
                }}
            """)
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
        elif status_type == "error":
            self.topbar_status.setText("خطأ")
            self.topbar_status.setStyleSheet(f"""
                QLabel {{
                    background: rgba(220, 38, 38, 0.18);
                    color:#fecaca;
                    border:1px solid rgba(220, 38, 38, 0.4);
                    border-radius:17px;
                    padding:0 16px;
                    font-size:11.5px;
                    font-weight:800;
                }}
            """)
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)

    def _set_status(self, status_type, message):
        if status_type == "connected":
            self.status_dot.setStyleSheet(
                f"background:{SUCCESS}; border-radius:7px; border:none;"
            )
            self.status_label.setText("متصل ويعمل")
            self.status_label.setStyleSheet(
                f"font-size:18px; font-weight:900; color:{SUCCESS}; "
                f"background:transparent; border:none;"
            )
            self.status_detail.setText(message)
            self.status_box.setStyleSheet(f"""
                QFrame {{
                    background:{SUCCESS_BG};
                    border:1.5px solid {SUCCESS_BRD};
                    border-radius:12px;
                }}
            """)
        elif status_type == "connecting":
            self.status_dot.setStyleSheet(
                f"background:{WARNING}; border-radius:7px; border:none;"
            )
            self.status_label.setText("جاري الاتصال...")
            self.status_label.setStyleSheet(
                f"font-size:18px; font-weight:900; color:{WARNING}; "
                f"background:transparent; border:none;"
            )
            self.status_detail.setText(message)
            self.status_box.setStyleSheet(f"""
                QFrame {{
                    background:{WARNING_BG};
                    border:1.5px solid {WARNING_BRD};
                    border-radius:12px;
                }}
            """)
        elif status_type == "error":
            self.status_dot.setStyleSheet(
                f"background:{DANGER}; border-radius:7px; border:none;"
            )
            self.status_label.setText("خطأ في الاتصال")
            self.status_label.setStyleSheet(
                f"font-size:18px; font-weight:900; color:{DANGER}; "
                f"background:transparent; border:none;"
            )
            self.status_detail.setText(message)
            self.status_box.setStyleSheet(f"""
                QFrame {{
                    background:{DANGER_BG};
                    border:1.5px solid {DANGER_BRD};
                    border-radius:12px;
                }}
            """)
        else:
            self.status_dot.setStyleSheet(
                f"background:{TEXT_MUTED}; border-radius:7px; border:none;"
            )
            self.status_label.setText("غير متصل")
            self.status_label.setStyleSheet(
                f"font-size:18px; font-weight:900; color:{TEXT_MUTED}; "
                f"background:transparent; border:none;"
            )
            self.status_detail.setText(
                message or "أدخل IP واضغط «ربط الجهاز» لبدء الاستماع"
            )
            self.status_box.setStyleSheet(f"""
                QFrame {{
                    background:{SURFACE_2};
                    border:1px solid {BORDER};
                    border-radius:12px;
                }}
            """)

    def _append_log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {text}"
        self.log_view.append(line)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    # ========================================================
    #   ✅ تحديث جدول الموظفين على الجهاز
    # ========================================================
    def _refresh_device_users(self):
        try:
            filter_key = self.users_filter.currentData() or "all"
            if filter_key == "unregistered":
                rows = get_unregistered_device_users()
            elif filter_key == "registered":
                rows = get_registered_device_users()
            else:
                rows = get_device_users()
        except Exception as e:
            self._append_log(f"فشل تحميل قائمة الموظفين: {e}")
            return

        self.users_table.setRowCount(0)

        for i, u in enumerate(rows):
            self.users_table.insertRow(i)

            # كود الموظف
            code_item = QTableWidgetItem(str(u["user_id"] or "—"))
            code_item.setTextAlignment(Qt.AlignCenter)
            code_item.setForeground(QColor(TEXT))
            f = code_item.font(); f.setBold(True); code_item.setFont(f)
            self.users_table.setItem(i, 0, code_item)

            # الاسم
            name_item = QTableWidgetItem(str(u["name"] or "—"))
            name_item.setTextAlignment(Qt.AlignCenter)
            name_item.setForeground(QColor(TEXT_SEC))
            self.users_table.setItem(i, 1, name_item)

            # الحالة
            is_registered = "emp_id" in u.keys() if hasattr(u, "keys") else False
            if is_registered:
                status_item = QTableWidgetItem("مسجّل")
                status_item.setForeground(QColor(SUCCESS))
            else:
                status_item = QTableWidgetItem("غير مسجّل")
                status_item.setForeground(QColor(WARNING))
            status_item.setTextAlignment(Qt.AlignCenter)
            f = status_item.font(); f.setBold(True); status_item.setFont(f)
            self.users_table.setItem(i, 2, status_item)

            # عدد البصمات المسجّلة لهذا الكود
            try:
                conn = get_connection()
                row_cnt = conn.execute(
                    "SELECT COUNT(*) as c FROM raw_punches WHERE employee_code=?",
                    (str(u["user_id"]),)
                ).fetchone()
                conn.close()
                cnt = row_cnt["c"] if row_cnt else 0
            except Exception:
                cnt = 0

            cnt_item = QTableWidgetItem(str(cnt))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            if cnt > 0:
                cnt_item.setForeground(QColor(PRIMARY))
                f = cnt_item.font(); f.setBold(True); cnt_item.setFont(f)
            else:
                cnt_item.setForeground(QColor(TEXT_MUTED))
            self.users_table.setItem(i, 3, cnt_item)

        # تحديث الإحصائيات
        try:
            total = count_device_users()
            unreg = count_unregistered_device_users()
            reg = total - unreg
            self.du_total._value_label.setText(str(total))
            self.du_registered._value_label.setText(str(reg))
            self.du_unregistered._value_label.setText(str(unreg))

            last_sync = get_last_device_sync_time()
            if last_sync:
                self.users_sync_label.setText(f"آخر مزامنة: {last_sync}")
            else:
                self.users_sync_label.setText("لم تتم المزامنة بعد")
        except Exception:
            pass

    def _clear_device_users(self):
        ans = QMessageBox.question(
            self, "تأكيد",
            "سيتم حذف قائمة الموظفين المحفوظة محلياً.\n"
            "الجهاز نفسه لن يتأثر.\n\n"
            "هل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return
        try:
            delete_all_device_users()
            self._append_log("تم حذف قائمة الموظفين المحفوظة")
            self._refresh_device_users()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الحذف:\n{e}")

    # ========================================================
    #                  تحميل البصمات الأخيرة
    # ========================================================
    def _refresh_recent_punches(self):
        try:
            rows = get_recent_live_punches(limit=100)
        except Exception as e:
            self._append_log(f"فشل تحميل البصمات: {e}")
            return

        # نجمع أكواد الأجهزة مرة واحدة
        try:
            device_users_map = {
                str(u["user_id"]): u["name"]
                for u in get_device_users()
            }
        except Exception:
            device_users_map = {}

        self.table.setRowCount(0)
        for i, r in enumerate(rows):
            self.table.insertRow(i)
            punch_time = r["punch_time"] or ""
            time_only = punch_time.split(" ")[1] if " " in punch_time else punch_time
            date_only = punch_time.split(" ")[0] if " " in punch_time else ""

            src = r["source"] or "upload"
            src_map = {
                "live": "حي",
                "device_pull": "مسحوب",
                "upload": "مرفوع",
            }
            src_label = src_map.get(src, "مرفوع")

            # لو مش مسجل بالاسم من employees → نجيب اسمه من الجهاز
            emp_name = r["employee_name"] or ""
            if not emp_name:
                code = r["employee_code"] or ""
                dev_name = device_users_map.get(code, "")
                if dev_name:
                    emp_name = f"{dev_name} (غير مسجل)"
                else:
                    emp_name = "—"

            vals = [
                time_only,
                r["employee_code"] or "—",
                emp_name,
                date_only,
                src_label,
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                if c == 1:
                    item.setForeground(QColor(PRIMARY))
                    f = item.font(); f.setBold(True); item.setFont(f)
                elif c == 4 and src == "live":
                    item.setForeground(QColor(DANGER))
                    f = item.font(); f.setBold(True); item.setFont(f)
                elif c == 4 and src == "device_pull":
                    item.setForeground(QColor(INFO))
                    f = item.font(); f.setBold(True); item.setFont(f)
                else:
                    item.setForeground(QColor(TEXT) if c != 4 else QColor(TEXT_MUTED))
                self.table.setItem(i, c, item)

        self._refresh_counters()

    def _refresh_counters(self):
        try:
            from database import count_raw_punches
            total = count_raw_punches()
            self.cnt_total._value_label.setText(str(total))

            today = datetime.now().strftime("%Y-%m-%d")
            conn = get_connection()
            row = conn.execute(
                "SELECT COUNT(*) as c FROM raw_punches WHERE punch_date=?",
                (today,),
            ).fetchone()
            conn.close()
            self.cnt_today._value_label.setText(str(row["c"] if row else 0))
        except Exception:
            pass

    # ========================================================
    #                  إغلاق الصفحة
    # ========================================================
    def closeEvent(self, event):
        if self._thread and self._thread.is_alive():
            self._thread.stop()
        super().closeEvent(event)