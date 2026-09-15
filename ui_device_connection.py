"""
صفحة ربط البصمة والاستماع التلقائي
- تتصل بجهاز ZKTeco عبر الشبكة
- تستمع للبصمات في الوقت الفعلي
- تسحب البصمات المُخزّنة في ذاكرة الجهاز خلال فترة محددة
- تضيفها مباشرة لجدول raw_punches (فقط للموظفين المسجّلين في النظام)
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
    QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QTime, Signal, QObject, QTimer
from PySide6.QtGui import QColor, QFont, QIcon

from database import (
    get_device_settings, save_device_settings,
    update_device_last_connected, add_live_punch,
    get_recent_live_punches, get_connection,
)


# ============================================================
#                نظام الألوان (Modern Pro)
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
#        إضافة بصمات آمنة (مع فلترة وتجاهل التكرار)
# ============================================================
def add_device_punches_safe(records, source="device_pull"):
    """
    إضافة بصمات من الجهاز بأمان:
    - تتجاهل الأكواد غير المسجّلة في النظام
    - تتجاهل التكرار (نفس الكود + نفس الوقت)

    Returns: (inserted, duplicates, unknown, total)
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
                unknown += 1
                continue

            emp_id = code_to_id.get(code)
            if emp_id is None:
                unknown += 1
                continue

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
                    f"✅ متصل بـ: {dev_name}  ·  S/N: {serial}"
                )
            except Exception:
                self.signals.log_message.emit("✅ متصل بالجهاز بنجاح")

            self.signals.status_changed.emit(
                "connected", f"متصل بـ {self.ip}:{self.port}"
            )

            try:
                update_device_last_connected(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            except Exception:
                pass

            self.signals.log_message.emit("🎧 بدء الاستماع للبصمات...")

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

                        if ok:
                            self.signals.punch_received.emit(
                                emp_code, punch_str, emp_name, "live"
                            )
                            self.signals.log_message.emit(
                                f"🔔 بصمة: {emp_code} ({emp_name}) @ {punch_str}"
                            )
                        else:
                            self.signals.log_message.emit(
                                f"⏭ تجاهل: {emp_code} — {msg}"
                            )

                except Exception as inner_e:
                    if self._stop_event.is_set():
                        break
                    self.signals.log_message.emit(
                        f"⚠️ خطأ مؤقت: {inner_e} — إعادة المحاولة..."
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
#       Thread سحب البصمات المخزّنة على الجهاز
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
                self.signals.log_message.emit(f"📡 الجهاز: {dev_name}")
            except Exception:
                pass

            self.signals.status_changed.emit("connected", "متصل — جاري سحب البصمات...")
            self.signals.log_message.emit(
                f"📥 جاري سحب البصمات من {self.from_date} إلى {self.to_date} ..."
            )

            all_atts = conn.get_attendance()
            total_from_device = len(all_atts) if all_atts else 0
            self.signals.log_message.emit(
                f"📊 إجمالي البصمات على الجهاز: {total_from_device}"
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
                f"⏱️  بصمات في الفترة المحددة: {in_range}"
            )

            inserted, duplicates, unknown, total = add_device_punches_safe(
                filtered, source="device_pull"
            )

            self.signals.log_message.emit(f"✅ تم إضافة {inserted} بصمة جديدة")
            if duplicates:
                self.signals.log_message.emit(
                    f"⏭️  مكررة (موجودة مسبقاً): {duplicates}"
                )
            if unknown:
                self.signals.log_message.emit(
                    f"⚠️  كود غير مسجّل في النظام: {unknown}"
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
            self.signals.log_message.emit(f"❌ خطأ في السحب: {e}")
        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:
                pass
            self.signals.finished.emit()


# ============================================================
#              Dialog: ملخص نتائج السحب
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

        # Header
        head = QFrame()
        head.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:0.5 {NAVY_2}, stop:1 {NAVY_3});
                border-radius:16px;
            }}
        """)
        apply_shadow(head, blur=20, y_offset=4, alpha=60)

        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 18, 22, 18)
        hl.setSpacing(16)

        ic = QLabel("📊")
        ic.setAlignment(Qt.AlignCenter)
        ic.setFixedSize(54, 54)
        ic.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                border:1px solid {NAVY_ACCENT};
                border-radius:15px; font-size:25px;
            }}
        """)
        hl.addWidget(ic)

        tbox = QVBoxLayout()
        tbox.setSpacing(4)
        title = QLabel("اكتمل سحب البصمات")
        title.setStyleSheet(
            "font-size:17px; font-weight:900; color:white; background:transparent;"
        )
        tbox.addWidget(title)
        sub = QLabel(
            f"📅  الفترة: {self.result.get('from_date','')}  →  {self.result.get('to_date','')}"
        )
        sub.setStyleSheet("font-size:11px; color:#9db3cf; background:transparent;")
        tbox.addWidget(sub)
        hl.addLayout(tbox)
        hl.addStretch()

        v.addWidget(head)

        # بطاقات النتائج - 3×2
        cards_grid = QGridLayout()
        cards_grid.setSpacing(14)

        c1 = self._mini_card("إجمالي على الجهاز",
                             str(self.result.get("total_from_device", 0)),
                             "💾", PRIMARY, PRIMARY_BG, PRIMARY_BRD)
        c2 = self._mini_card("في الفترة المحددة",
                             str(self.result.get("in_range", 0)),
                             "⏱", INFO, INFO_BG, INFO_BRD)
        c3 = self._mini_card("تم إضافتها للنظام",
                             str(self.result.get("inserted", 0)),
                             "✅", SUCCESS, SUCCESS_BG, SUCCESS_BRD)
        c4 = self._mini_card("مكررة (موجودة)",
                             str(self.result.get("duplicates", 0)),
                             "⏭", WARNING, WARNING_BG, WARNING_BRD)
        c5 = self._mini_card("كود غير مسجّل",
                             str(self.result.get("unknown", 0)),
                             "⚠️", DANGER, DANGER_BG, DANGER_BRD)

        cards_grid.addWidget(c1, 0, 0)
        cards_grid.addWidget(c2, 0, 1)
        cards_grid.addWidget(c3, 0, 2)
        cards_grid.addWidget(c4, 1, 0)
        cards_grid.addWidget(c5, 1, 1)

        for c in range(3):
            cards_grid.setColumnStretch(c, 1)

        v.addLayout(cards_grid)

        # ملاحظة
        note = QFrame()
        note.setStyleSheet(f"""
            QFrame {{
                background:{INFO_BG};
                border:1px solid {INFO_BRD};
                border-radius:11px;
            }}
        """)
        nl = QHBoxLayout(note)
        nl.setContentsMargins(16, 14, 16, 14)
        nl.setSpacing(10)

        note_ic = QLabel("💡")
        note_ic.setStyleSheet("font-size:16px; background:transparent;")
        nl.addWidget(note_ic)

        note_lbl = QLabel(
            "«كود غير مسجّل» يعني أن البصمة على الجهاز بكود غير موجود في النظام، "
            "فتم تجاهلها. البصمات المضافة الآن ظاهرة في صفحة «الحضور والانصراف» "
            "وفي القائمة أعلاه."
        )
        note_lbl.setStyleSheet(
            f"font-size:11.5px; color:{INFO}; background:transparent; font-weight:600;"
        )
        note_lbl.setWordWrap(True)
        nl.addWidget(note_lbl, 1)
        v.addWidget(note)

        # زر الإغلاق
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
                border-radius:11px; padding:0 28px;
                font-weight:900; font-size:13px;
            }}
            QPushButton:hover {{ background:{SUCCESS_HOV}; }}
        """)
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        v.addLayout(btns)

    def _mini_card(self, title, value, icon_text, color, bg, brd):
        card = QFrame()
        card.setMinimumHeight(84)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:13px;
            }}
            QFrame:hover {{ border:1.5px solid {brd}; }}
        """)
        apply_shadow(card, blur=10, y_offset=2, alpha=18)

        h = QHBoxLayout(card)
        h.setContentsMargins(14, 12, 14, 12)
        h.setSpacing(11)

        ic = QLabel(icon_text)
        ic.setFixedSize(44, 44)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"""
            QLabel {{
                background:{bg}; color:{color};
                border:1.5px solid {brd}; border-radius:12px;
                font-size:19px;
            }}
        """)
        h.addWidget(ic)

        v = QVBoxLayout()
        v.setSpacing(2)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:10px; color:{TEXT_MUTED}; font-weight:800;"
        )
        v.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:20px; color:{TEXT}; font-weight:900;"
        )
        v.addWidget(val)
        h.addLayout(v)
        h.addStretch()

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
        self._signals = DeviceSignals()
        self._pull_signals = PunchesPullSignals()
        self._connect_signals()
        self._connect_pull_signals()
        self._build_ui()
        self._load_settings()
        self._refresh_recent_punches()

    def _connect_signals(self):
        self._signals.punch_received.connect(self._on_punch_received)
        self._signals.status_changed.connect(self._on_status_changed)
        self._signals.log_message.connect(self._append_log)

    def _connect_pull_signals(self):
        self._pull_signals.result_ready.connect(self._on_pull_result)
        self._pull_signals.status_changed.connect(self._on_pull_status)
        self._pull_signals.log_message.connect(self._append_log)
        self._pull_signals.finished.connect(self._on_pull_finished)

    # ========================================================
    #                    بناء الواجهة
    # ========================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        # Scroll للمحتوى
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

        top_row = QHBoxLayout()
        top_row.setSpacing(18)
        top_row.addWidget(self._build_settings_card(), 5)
        top_row.addWidget(self._build_status_card(), 4)
        body_layout.addLayout(top_row)

        body_layout.addWidget(self._build_live_table_card())
        body_layout.addWidget(self._build_log_card())

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

    # ----------------------------------------------------------
    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("deviceTopbar")
        bar.setFixedHeight(96)
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
        h.setSpacing(18)

        # Icon container
        icon = QLabel("🔌")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(54, 54)
        icon.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_DK});
                border:1px solid {NAVY_ACCENT};
                border-radius:15px;
                font-size:24px;
            }}
        """)
        apply_shadow(icon, blur=14, y_offset=2, alpha=60)
        h.addWidget(icon)

        tbox = QVBoxLayout()
        tbox.setSpacing(4)
        title = QLabel("ربط جهاز البصمة")
        title.setStyleSheet(f"""
            QLabel {{
                color:white; font-size:22px; font-weight:900;
                background:transparent; font-family:{FONT_FAMILY};
                letter-spacing:0.3px;
            }}
        """)
        tbox.addWidget(title)

        sub = QLabel("ربط الجهاز • استماع مباشر • سحب البصمات المخزّنة خلال فترة")
        sub.setStyleSheet(
            "QLabel { color:#94a8c4; font-size:11px; background:transparent; }"
        )
        tbox.addWidget(sub)
        h.addLayout(tbox)
        h.addStretch()

        # Status pill
        self.topbar_status = QLabel("●  غير متصل")
        self.topbar_status.setAlignment(Qt.AlignCenter)
        self.topbar_status.setFixedHeight(38)
        self.topbar_status.setMinimumWidth(130)
        self.topbar_status.setStyleSheet(f"""
            QLabel {{
                background: rgba(148, 163, 184, 0.15);
                color:#cbd5e1;
                border:1px solid rgba(148, 163, 184, 0.35);
                border-radius:19px;
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
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=20, y_offset=4, alpha=25)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 20, 22, 20)
        v.setSpacing(16)

        # العنوان
        head = QHBoxLayout()
        head.setSpacing(12)

        hicon = QLabel("⚙️")
        hicon.setFixedSize(44, 44)
        hicon.setAlignment(Qt.AlignCenter)
        hicon.setStyleSheet(f"""
            QLabel {{
                background:{PRIMARY_BG}; color:{PRIMARY};
                border:1px solid {PRIMARY_BRD}; border-radius:12px;
                font-size:19px;
            }}
        """)
        head.addWidget(hicon)

        hbox = QVBoxLayout()
        hbox.setSpacing(2)
        ht = QLabel("إعدادات الجهاز")
        ht.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        hbox.addWidget(ht)
        hs = QLabel("أدخل IP ثم اربط — الاستماع المباشر يبدأ فوراً")
        hs.setStyleSheet(f"font-size:10.5px; color:{TEXT_MUTED};")
        hbox.addWidget(hs)
        head.addLayout(hbox)
        head.addStretch()
        v.addLayout(head)

        # الحقول
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(12)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.201")
        self.ip_input.setFixedHeight(44)
        self.ip_input.setLayoutDirection(Qt.LeftToRight)
        self.ip_input.setAlignment(Qt.AlignLeft)
        self._style_input(self.ip_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(4370)
        self.port_input.setFixedHeight(44)
        self.port_input.setLayoutDirection(Qt.LeftToRight)
        self.port_input.setAlignment(Qt.AlignLeft)
        self._style_spinbox(self.port_input)

        self.password_input = QSpinBox()
        self.password_input.setRange(0, 99999999)
        self.password_input.setValue(0)
        self.password_input.setFixedHeight(44)
        self.password_input.setLayoutDirection(Qt.LeftToRight)
        self.password_input.setAlignment(Qt.AlignLeft)
        self._style_spinbox(self.password_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("جهاز البصمة الرئيسي")
        self.name_input.setFixedHeight(44)
        self.name_input.setText("جهاز البصمة الرئيسي")
        self._style_input(self.name_input)

        g.addWidget(self._field("عنوان IP", self.ip_input), 0, 0)
        g.addWidget(self._field("المنفذ (Port)", self.port_input), 0, 1)
        g.addWidget(self._field("كلمة المرور (Password)", self.password_input), 1, 0)
        g.addWidget(self._field("اسم الجهاز", self.name_input), 1, 1)

        v.addLayout(g)

        # خيار الاستماع التلقائي
        self.auto_listen_cb = QCheckBox("الاستماع تلقائياً عند فتح التطبيق")
        self.auto_listen_cb.setCursor(Qt.PointingHandCursor)
        self.auto_listen_cb.setStyleSheet(f"""
            QCheckBox {{
                font-size:11.5px; font-weight:800; color:{TEXT_SEC};
                background:transparent; spacing:9px; padding:8px 0;
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

        # الأزرار
        btns = QHBoxLayout()
        btns.setSpacing(9)

        self.btn_connect = QPushButton("🔗  ربط الجهاز")
        self.btn_connect.setFixedHeight(46)
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                color:white; border:none;
                border-radius:11px; padding:0 24px;
                font-weight:900; font-size:12.5px;
            }}
            QPushButton:hover {{ background:{SUCCESS_HOV}; }}
        """)
        self.btn_connect.clicked.connect(self._on_connect)
        btns.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("⏹  إيقاف الاستماع")
        self.btn_disconnect.setFixedHeight(46)
        self.btn_disconnect.setCursor(Qt.PointingHandCursor)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{DANGER};
                border:1px solid {DANGER_BRD}; border-radius:11px;
                padding:0 24px; font-weight:800; font-size:12.5px;
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

        btn_save = QPushButton("💾  حفظ")
        btn_save.setFixedHeight(46)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{PRIMARY_DK};
                border:1px solid {PRIMARY_BRD}; border-radius:11px;
                padding:0 24px; font-weight:800; font-size:12.5px;
            }}
            QPushButton:hover {{ background:{PRIMARY_BG}; }}
        """)
        btn_save.clicked.connect(self._save_settings)
        btns.addWidget(btn_save)

        v.addLayout(btns)

        # ==================================================
        #  قسم سحب البصمات - بتصميم مميز
        # ==================================================
        pull_box = QFrame()
        pull_box.setObjectName("pullBox")
        pull_box.setStyleSheet(f"""
            QFrame#pullBox {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8fafc, stop:1 #eef2ff);
                border:1.5px solid {PRIMARY_BRD};
                border-radius:14px;
            }}
        """)
        pb = QVBoxLayout(pull_box)
        pb.setContentsMargins(18, 16, 18, 16)
        pb.setSpacing(14)

        # عنوان القسم
        ptitle_box = QHBoxLayout()
        ptitle_box.setSpacing(11)

        picon = QLabel("📥")
        picon.setFixedSize(38, 38)
        picon.setAlignment(Qt.AlignCenter)
        picon.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_DK});
                color:white;
                border-radius:11px;
                font-size:17px;
            }}
        """)
        ptitle_box.addWidget(picon)

        ptbox = QVBoxLayout()
        ptbox.setSpacing(2)
        pt = QLabel("سحب البصمات المخزّنة على الجهاز")
        pt.setStyleSheet(f"font-size:13px; font-weight:900; color:{TEXT};")
        ptbox.addWidget(pt)
        ps = QLabel("حدّد الفترة الزمنية — يُسحب فقط بصمات الموظفين المسجّلين في النظام")
        ps.setStyleSheet(f"font-size:10.5px; color:{TEXT_MUTED};")
        ptbox.addWidget(ps)
        ptitle_box.addLayout(ptbox)
        ptitle_box.addStretch()
        pb.addLayout(ptitle_box)

        # فلاتر التاريخ
        dates_row = QHBoxLayout()
        dates_row.setSpacing(12)

        self.pull_from_date = QDateEdit()
        self.pull_from_date.setCalendarPopup(True)
        self.pull_from_date.setDisplayFormat("yyyy-MM-dd")
        self.pull_from_date.setDate(QDate.currentDate().addDays(-30))
        self.pull_from_date.setFixedHeight(44)
        self.pull_from_date.setLayoutDirection(Qt.LeftToRight)
        self._style_date(self.pull_from_date)
        dates_row.addWidget(self._field("من تاريخ", self.pull_from_date), 1)

        self.pull_to_date = QDateEdit()
        self.pull_to_date.setCalendarPopup(True)
        self.pull_to_date.setDisplayFormat("yyyy-MM-dd")
        self.pull_to_date.setDate(QDate.currentDate())
        self.pull_to_date.setFixedHeight(44)
        self.pull_to_date.setLayoutDirection(Qt.LeftToRight)
        self._style_date(self.pull_to_date)
        dates_row.addWidget(self._field("إلى تاريخ", self.pull_to_date), 1)

        pb.addLayout(dates_row)

        # أزرار سريعة
        quick_row = QHBoxLayout()
        quick_row.setSpacing(7)

        quick_lbl = QLabel("⚡ فترة سريعة:")
        quick_lbl.setStyleSheet(
            f"font-size:11px; color:{TEXT_SEC}; font-weight:800; background:transparent;"
        )
        quick_row.addWidget(quick_lbl)

        btn_7d = self._quick_btn("آخر 7 أيام", 7)
        btn_30d = self._quick_btn("آخر 30 يوم", 30)
        btn_90d = self._quick_btn("آخر 90 يوم", 90)
        btn_this_month = self._quick_btn("هذا الشهر", None, "month")
        btn_all = self._quick_btn("كل البصمات", None, "all")

        quick_row.addWidget(btn_7d)
        quick_row.addWidget(btn_30d)
        quick_row.addWidget(btn_90d)
        quick_row.addWidget(btn_this_month)
        quick_row.addWidget(btn_all)
        quick_row.addStretch()

        pb.addLayout(quick_row)

        # زر السحب
        self.btn_pull_punches = QPushButton("📥  ابدأ سحب البصمات")
        self.btn_pull_punches.setFixedHeight(50)
        self.btn_pull_punches.setCursor(Qt.PointingHandCursor)
        self.btn_pull_punches.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PRIMARY}, stop:0.5 #4d6bff, stop:1 {PRIMARY_DK});
                color:white; border:none;
                border-radius:12px; padding:0 28px;
                font-weight:900; font-size:13.5px;
                font-family:{FONT_FAMILY};
                letter-spacing:0.3px;
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
        pb.addWidget(self.btn_pull_punches)

        v.addWidget(pull_box)

        return card

    def _quick_btn(self, text, days=None, mode=None):
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE};
                color:{TEXT_SEC};
                border:1px solid {BORDER};
                border-radius:16px;
                padding:0 14px;
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
                border-radius:11px;
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
    def _build_status_card(self):
        card = QFrame()
        card.setObjectName("statusCard")
        card.setStyleSheet(f"""
            QFrame#statusCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=20, y_offset=4, alpha=25)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 20, 22, 20)
        v.setSpacing(16)

        head = QHBoxLayout()
        head.setSpacing(12)

        hicon = QLabel("📡")
        hicon.setFixedSize(44, 44)
        hicon.setAlignment(Qt.AlignCenter)
        hicon.setStyleSheet(f"""
            QLabel {{
                background:{INFO_BG}; color:{INFO};
                border:1px solid {INFO_BRD}; border-radius:12px;
                font-size:19px;
            }}
        """)
        head.addWidget(hicon)

        hbox = QVBoxLayout()
        hbox.setSpacing(2)
        ht = QLabel("حالة الاتصال")
        ht.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        hbox.addWidget(ht)
        hs = QLabel("معلومات الجهاز والاستماع المباشر")
        hs.setStyleSheet(f"font-size:10.5px; color:{TEXT_MUTED};")
        hbox.addWidget(hs)
        head.addLayout(hbox)
        head.addStretch()
        v.addLayout(head)

        # Status box
        self.status_box = QFrame()
        self.status_box.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
        """)
        sb = QVBoxLayout(self.status_box)
        sb.setContentsMargins(20, 20, 20, 20)
        sb.setSpacing(10)

        self.status_icon = QLabel("⚪")
        self.status_icon.setAlignment(Qt.AlignCenter)
        self.status_icon.setStyleSheet("font-size:48px; background:transparent;")
        sb.addWidget(self.status_icon)

        self.status_label = QLabel("غير متصل")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            f"font-size:16px; font-weight:900; color:{TEXT_MUTED}; background:transparent;"
        )
        sb.addWidget(self.status_label)

        self.status_detail = QLabel("أدخل IP واضغط «ربط الجهاز»")
        self.status_detail.setAlignment(Qt.AlignCenter)
        self.status_detail.setWordWrap(True)
        self.status_detail.setStyleSheet(
            f"font-size:11.5px; color:{TEXT_MUTED}; background:transparent;"
        )
        sb.addWidget(self.status_detail)

        v.addWidget(self.status_box)

        # العدادات
        stats = QGridLayout()
        stats.setHorizontalSpacing(10)
        stats.setVerticalSpacing(10)

        self.cnt_today = self._mini_counter("بصمات اليوم", "0", "📅",
                                            PRIMARY, PRIMARY_BG, PRIMARY_BRD)
        self.cnt_total = self._mini_counter("إجمالي البصمات", "0", "📊",
                                            SUCCESS, SUCCESS_BG, SUCCESS_BRD)
        self.cnt_live = self._mini_counter("بصمات حية", "0", "🔴",
                                           DANGER, DANGER_BG, DANGER_BRD)

        stats.addWidget(self.cnt_today, 0, 0)
        stats.addWidget(self.cnt_total, 0, 1)
        stats.addWidget(self.cnt_live, 0, 2)
        for c in range(3):
            stats.setColumnStretch(c, 1)
        v.addLayout(stats)

        v.addStretch()
        return card

    # ----------------------------------------------------------
    def _build_live_table_card(self):
        card = QFrame()
        card.setObjectName("liveTableCard")
        card.setStyleSheet(f"""
            QFrame#liveTableCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=20, y_offset=4, alpha=25)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head = QFrame()
        head.setFixedHeight(72)
        head.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border-bottom:1px solid {DIVIDER};
                border-top-left-radius:16px;
                border-top-right-radius:16px;
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(12)

        hicon = QLabel("🔔")
        hicon.setFixedSize(40, 40)
        hicon.setAlignment(Qt.AlignCenter)
        hicon.setStyleSheet(f"""
            QLabel {{
                background:{WARNING_BG};
                border:1px solid {WARNING_BRD};
                border-radius:11px;
                font-size:18px;
            }}
        """)
        hl.addWidget(hicon)

        hbox = QVBoxLayout()
        hbox.setSpacing(2)
        title = QLabel("آخر البصمات المسجّلة في النظام")
        title.setStyleSheet(f"font-size:15px; font-weight:900; color:{TEXT};")
        hbox.addWidget(title)
        hint = QLabel("تُحدَّث تلقائياً عند وصول بصمة جديدة")
        hint.setStyleSheet(f"font-size:10.5px; color:{TEXT_MUTED};")
        hbox.addWidget(hint)
        hl.addLayout(hbox)
        hl.addStretch()

        btn_refresh = QPushButton("🔄  تحديث")
        btn_refresh.setFixedHeight(36)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1px solid {BORDER_2}; border-radius:10px;
                padding:0 16px; font-weight:800; font-size:11.5px;
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
        self.table.setMinimumHeight(260)
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
                letter-spacing:0.2px;
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
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=20, y_offset=4, alpha=25)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head = QFrame()
        head.setFixedHeight(60)
        head.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border-bottom:1px solid {DIVIDER};
                border-top-left-radius:16px;
                border-top-right-radius:16px;
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(12)

        hicon = QLabel("📝")
        hicon.setFixedSize(36, 36)
        hicon.setAlignment(Qt.AlignCenter)
        hicon.setStyleSheet(f"""
            QLabel {{
                background:{TEXT_SEC}15;
                border:1px solid {BORDER};
                border-radius:10px;
                font-size:16px;
            }}
        """)
        hl.addWidget(hicon)

        title = QLabel("سجل الأحداث")
        title.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        hl.addWidget(title)
        hl.addStretch()

        btn_clear = QPushButton("🗑  مسح السجل")
        btn_clear.setFixedHeight(32)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1px solid {BORDER}; border-radius:9px;
                padding:0 14px; font-weight:800; font-size:11px;
            }}
            QPushButton:hover {{ background:{SURFACE_2}; border-color:{BORDER_2}; }}
        """)
        btn_clear.clicked.connect(lambda: self.log_view.clear())
        hl.addWidget(btn_clear)

        v.addWidget(head)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(160)
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background:{SURFACE_2};
                border:none;
                border-bottom-left-radius:16px;
                border-bottom-right-radius:16px;
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
            f"background:transparent; letter-spacing:0.2px;"
        )
        v.addWidget(lbl)
        v.addWidget(widget)
        return w

    def _style_input(self, inp):
        inp.setStyleSheet(f"""
            QLineEdit {{
                background:{SURFACE_2}; border:1.5px solid {BORDER};
                border-radius:11px; padding:0 14px;
                font-size:12.5px; color:{TEXT};
            }}
            QLineEdit:hover {{ background:white; border-color:{BORDER_2}; }}
            QLineEdit:focus {{ background:white; border:1.5px solid {PRIMARY}; }}
        """)

    def _style_spinbox(self, sp):
        sp.setStyleSheet(f"""
            QSpinBox {{
                background:{SURFACE_2}; border:1.5px solid {BORDER};
                border-radius:11px; padding:0 14px;
                font-size:12.5px; color:{TEXT};
            }}
            QSpinBox:hover {{ background:white; border-color:{BORDER_2}; }}
            QSpinBox:focus {{ background:white; border:1.5px solid {PRIMARY}; }}
        """)

    def _mini_counter(self, title, value, icon_text, color, soft, brd):
        card = QFrame()
        card.setMinimumHeight(76)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:12px;
            }}
        """)

        h = QHBoxLayout(card)
        h.setContentsMargins(14, 12, 14, 12)
        h.setSpacing(10)

        ic = QLabel(icon_text)
        ic.setAlignment(Qt.AlignCenter)
        ic.setFixedSize(40, 40)
        ic.setStyleSheet(f"""
            QLabel {{
                background:{soft}; color:{color};
                border:1.5px solid {brd}; border-radius:11px;
                font-size:17px; font-weight:900;
            }}
        """)
        h.addWidget(ic)

        v = QVBoxLayout()
        v.setSpacing(2)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:10px; color:{TEXT_MUTED}; font-weight:800;"
        )
        v.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet(f"font-size:17px; color:{TEXT}; font-weight:900;")
        v.addWidget(val)

        h.addLayout(v)
        h.addStretch()
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
                    self._append_log(f"🕐 آخر اتصال: {s['last_connected']}")

                if s["auto_listen"] and s["device_ip"]:
                    QTimer.singleShot(1500, self._on_connect)
        except Exception as e:
            self._append_log(f"⚠️ لم يتم تحميل الإعدادات: {e}")

    def _save_settings(self):
        ip = self.ip_input.text().strip()
        port = self.port_input.value()
        pwd = self.password_input.value()
        name = self.name_input.text().strip() or "جهاز البصمة الرئيسي"
        auto = 1 if self.auto_listen_cb.isChecked() else 0

        try:
            save_device_settings(ip, port, pwd, name, auto)
            QMessageBox.information(self, "تم", "تم حفظ إعدادات الجهاز ✅")
            self._append_log("💾 تم حفظ الإعدادات")
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

        self._append_log(f"🔗 محاولة الاتصال بـ {ip}:{port} ...")

        self._thread = LiveListenerThread(ip, port, pwd, self._signals)
        self._thread.start()

        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)

    def _on_disconnect(self):
        if self._thread and self._thread.is_alive():
            self._append_log("⏹ طلب إيقاف الاستماع...")
            self._thread.stop()
            self._thread = None
        self._set_status("disconnected", "تم إيقاف الاستماع")

        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

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
            f"📅  من: {from_str}\n📅  إلى: {to_str}\n\n"
            f"سيتم إضافة بصمات الموظفين المسجّلين في النظام فقط.\n"
            f"هل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if ans != QMessageBox.Yes:
            return

        port = self.port_input.value()
        pwd = self.password_input.value()

        self._append_log(
            f"📥 بدء سحب البصمات من {ip}:{port} — "
            f"من {from_str} إلى {to_str} ..."
        )
        self.btn_pull_punches.setEnabled(False)
        self.btn_pull_punches.setText("⏳  جاري السحب...")

        self._pull_thread = PunchesPullThread(
            ip, port, pwd, from_str, to_str, self._pull_signals
        )
        self._pull_thread.start()

    def _on_pull_result(self, result):
        try:
            dlg = PullResultDialog(result, self)
            dlg.exec()
        except Exception as e:
            self._append_log(f"⚠️ فشل عرض النتائج: {e}")

        self._refresh_recent_punches()

    def _on_pull_status(self, status_type, message):
        self._append_log(f"[سحب] {message}")

    def _on_pull_finished(self):
        self.btn_pull_punches.setEnabled(True)
        self.btn_pull_punches.setText("📥  ابدأ سحب البصمات")
        self._refresh_recent_punches()

    # ========================================================
    #                  استقبال الإشارات
    # ========================================================
    def _on_punch_received(self, code, punch_time, name, source):
        self.table.insertRow(0)

        time_only = punch_time.split(" ")[1] if " " in punch_time else punch_time
        date_only = punch_time.split(" ")[0] if " " in punch_time else ""

        vals = [time_only, code, name or "—", date_only, "🔴 حي"]
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

        # تحديث topbar status
        if status_type == "connected":
            self.topbar_status.setText("●  متصل")
            self.topbar_status.setStyleSheet(f"""
                QLabel {{
                    background: rgba(5, 150, 105, 0.18);
                    color:#a7f3d0;
                    border:1px solid rgba(5, 150, 105, 0.4);
                    border-radius:19px;
                    padding:0 16px;
                    font-size:11.5px;
                    font-weight:800;
                }}
            """)
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
        elif status_type == "connecting":
            self.topbar_status.setText("●  جاري الاتصال")
            self.topbar_status.setStyleSheet(f"""
                QLabel {{
                    background: rgba(217, 119, 6, 0.18);
                    color:#fde68a;
                    border:1px solid rgba(217, 119, 6, 0.4);
                    border-radius:19px;
                    padding:0 16px;
                    font-size:11.5px;
                    font-weight:800;
                }}
            """)
        elif status_type == "disconnected":
            self.topbar_status.setText("●  غير متصل")
            self.topbar_status.setStyleSheet(f"""
                QLabel {{
                    background: rgba(148, 163, 184, 0.15);
                    color:#cbd5e1;
                    border:1px solid rgba(148, 163, 184, 0.35);
                    border-radius:19px;
                    padding:0 16px;
                    font-size:11.5px;
                    font-weight:800;
                }}
            """)
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
        elif status_type == "error":
            self.topbar_status.setText("●  خطأ")
            self.topbar_status.setStyleSheet(f"""
                QLabel {{
                    background: rgba(220, 38, 38, 0.18);
                    color:#fecaca;
                    border:1px solid rgba(220, 38, 38, 0.4);
                    border-radius:19px;
                    padding:0 16px;
                    font-size:11.5px;
                    font-weight:800;
                }}
            """)
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)

    def _set_status(self, status_type, message):
        if status_type == "connected":
            self.status_icon.setText("🟢")
            self.status_label.setText("متصل ويعمل")
            self.status_label.setStyleSheet(
                f"font-size:16px; font-weight:900; color:{SUCCESS}; background:transparent;"
            )
            self.status_detail.setText(message)
            self.status_box.setStyleSheet(f"""
                QFrame {{
                    background:{SUCCESS_BG};
                    border:1.5px solid {SUCCESS_BRD};
                    border-radius:14px;
                }}
            """)
        elif status_type == "connecting":
            self.status_icon.setText("🟡")
            self.status_label.setText("جاري الاتصال...")
            self.status_label.setStyleSheet(
                f"font-size:16px; font-weight:900; color:{WARNING}; background:transparent;"
            )
            self.status_detail.setText(message)
            self.status_box.setStyleSheet(f"""
                QFrame {{
                    background:{WARNING_BG};
                    border:1.5px solid {WARNING_BRD};
                    border-radius:14px;
                }}
            """)
        elif status_type == "error":
            self.status_icon.setText("🔴")
            self.status_label.setText("خطأ في الاتصال")
            self.status_label.setStyleSheet(
                f"font-size:16px; font-weight:900; color:{DANGER}; background:transparent;"
            )
            self.status_detail.setText(message)
            self.status_box.setStyleSheet(f"""
                QFrame {{
                    background:{DANGER_BG};
                    border:1.5px solid {DANGER_BRD};
                    border-radius:14px;
                }}
            """)
        else:
            self.status_icon.setText("⚪")
            self.status_label.setText("غير متصل")
            self.status_label.setStyleSheet(
                f"font-size:16px; font-weight:900; color:{TEXT_MUTED}; background:transparent;"
            )
            self.status_detail.setText(message or "أدخل IP واضغط «ربط الجهاز»")
            self.status_box.setStyleSheet(f"""
                QFrame {{
                    background:{SURFACE_2};
                    border:1px solid {BORDER};
                    border-radius:14px;
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
    #                  تحميل البصمات الأخيرة
    # ========================================================
    def _refresh_recent_punches(self):
        try:
            rows = get_recent_live_punches(limit=100)
        except Exception as e:
            self._append_log(f"⚠️ فشل تحميل البصمات: {e}")
            return

        self.table.setRowCount(0)
        for i, r in enumerate(rows):
            self.table.insertRow(i)
            punch_time = r["punch_time"] or ""
            time_only = punch_time.split(" ")[1] if " " in punch_time else punch_time
            date_only = punch_time.split(" ")[0] if " " in punch_time else ""

            src = r["source"] or "upload"
            src_map = {
                "live": "🔴 حي",
                "device_pull": "📥 مسحوب",
                "upload": "📤 مرفوع",
            }
            src_label = src_map.get(src, "📤 مرفوع")

            vals = [
                time_only,
                r["employee_code"] or "—",
                r["employee_name"] or "—",
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