import csv
import os
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QFrame, QGridLayout, QLineEdit,
    QFileDialog, QDialog, QAbstractItemView,
    QGraphicsDropShadowEffect, QTextEdit, QScrollArea
)
from PySide6.QtCore import Qt, QDate, QRegularExpression
from PySide6.QtGui import QColor, QFont, QRegularExpressionValidator, QPixmap

from database import (
    get_employees, get_employee, get_shift, get_shift_deductions,
    get_all_raw_punches_in_range, get_all_overrides_in_range,
    get_all_annual_leave_used, get_annual_leave_used,
    get_attendance_for_employee,
)
from ui_attendance import (
    compute_employee_summary, is_working_day_for_shift,
    format_minutes_ar, format_overtime_ar, _fmt_num,
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

PINK        = "#db2777"
PINK_BG     = "#fdf2f8"
PINK_BRD    = "#fbcfe8"

ROW_ALT     = "#fafbfc"
HEADER_BG   = "#f8fafc"

FONT_FAMILY = "Segoe UI, Tahoma, Arial, sans-serif"

# مسار اللوجو
LOGO_PATH = Path(__file__).parent / "logo.png"


def load_logo_pixmap(size: int = 54):
    """تحميل اللوجو من logo.png إن وُجد"""
    try:
        if LOGO_PATH.exists():
            pix = QPixmap(str(LOGO_PATH))
            if not pix.isNull():
                return pix.scaled(
                    size, size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
    except Exception:
        pass
    return None


def apply_shadow(widget, blur=20, y_offset=4, alpha=25):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    effect.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(effect)
    return effect


def fmt_money(v):
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def fmt_money_int(v):
    try:
        return f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return "0"


def _safe_get(summary, key, default=0):
    """قراءة آمنة من summary"""
    try:
        return summary.get(key, default) if summary else default
    except Exception:
        return default


# ============================================================
#                       صفحة المرتبات
# ============================================================
class PayrollPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._rows = []
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        today = QDate.currentDate()
        first = QDate(today.year(), today.month(), 1)
        if self.from_date.date().year() < 2000:
            self.from_date.setDate(first)
        if self.to_date.date().year() < 2000:
            self.to_date.setDate(today)
        self._refresh()

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
        body.setObjectName("payrollBody")
        body.setStyleSheet(f"QWidget#payrollBody {{ background:{BG}; }}")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(26, 22, 26, 26)
        body_layout.setSpacing(18)

        body_layout.addWidget(self._build_stats())
        body_layout.addWidget(self._build_filters_card())
        body_layout.addWidget(self._build_table_card(), 1)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

    # ----------------------------------------------------------
    #                       TOPBAR
    # ----------------------------------------------------------
    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("payrollTopbar")
        bar.setFixedHeight(76)
        bar.setStyleSheet(f"""
            QFrame#payrollTopbar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:0.5 {NAVY_2}, stop:1 {NAVY_3});
                border:none;
                border-bottom:1px solid #1e3a5f;
            }}
        """)

        h = QHBoxLayout(bar)
        h.setContentsMargins(30, 0, 30, 0)
        h.setSpacing(16)

        # اللوجو إن وُجد فقط
        pix = load_logo_pixmap(46)
        if pix is not None:
            icon = QLabel()
            icon.setAlignment(Qt.AlignCenter)
            icon.setFixedSize(50, 50)
            icon.setPixmap(pix)
            icon.setStyleSheet(f"""
                QLabel {{
                    background: {SURFACE};
                    border:1.5px solid {NAVY_ACCENT};
                    border-radius:12px;
                    padding:2px;
                }}
            """)
            apply_shadow(icon, blur=12, y_offset=2, alpha=60)
            h.addWidget(icon)

        title = QLabel("تقرير المرتبات")
        title.setStyleSheet(f"""
            QLabel {{
                color:white; font-size:20px; font-weight:900;
                background:transparent; font-family:{FONT_FAMILY};
            }}
        """)
        h.addWidget(title)
        h.addStretch()

        self.rows_badge = QLabel("0 موظف")
        self.rows_badge.setAlignment(Qt.AlignCenter)
        self.rows_badge.setMinimumWidth(110)
        self.rows_badge.setFixedHeight(34)
        self.rows_badge.setStyleSheet(f"""
            QLabel {{
                background: rgba(16, 185, 129, 0.15);
                color:#a7f3d0;
                border:1px solid rgba(16, 185, 129, 0.35);
                border-radius:17px; padding:0 16px;
                font-size:11.5px; font-weight:800;
            }}
        """)
        h.addWidget(self.rows_badge)

        return bar

    # ----------------------------------------------------------
    #                    بطاقات الإجماليات
    # ----------------------------------------------------------
    def _build_stats(self):
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.stat_employees = self._stat_card(
            "عدد الموظفين", "0",
            PRIMARY, PRIMARY_BG, PRIMARY_BRD, "موظف"
        )
        self.stat_days = self._stat_card(
            "إجمالي أيام العمل", "0",
            SUCCESS, SUCCESS_BG, SUCCESS_BRD, "يوم"
        )
        self.stat_overtime = self._stat_card(
            "إجمالي الإضافي", "0",
            PURPLE, PURPLE_BG, PURPLE_BRD, "ج.م"
        )
        self.stat_early = self._stat_card(
            "إجمالي الانصراف المبكر", "0",
            PINK, PINK_BG, PINK_BRD, "ج.م"
        )
        self.stat_net = self._stat_card(
            "إجمالي الصافي", "0",
            INFO, INFO_BG, INFO_BRD, "ج.م"
        )

        grid.addWidget(self.stat_employees, 0, 0)
        grid.addWidget(self.stat_days, 0, 1)
        grid.addWidget(self.stat_overtime, 0, 2)
        grid.addWidget(self.stat_early, 0, 3)
        grid.addWidget(self.stat_net, 0, 4)

        for c in range(5):
            grid.setColumnStretch(c, 1)
        return wrap

    def _stat_card(self, title, value, color, soft, border_color, unit):
        card = QFrame()
        card.setObjectName("statCard")
        card.setMinimumHeight(92)
        card.setStyleSheet(f"""
            QFrame#statCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
            QFrame#statCard:hover {{
                border:1.5px solid {border_color};
            }}
        """)
        apply_shadow(card, blur=14, y_offset=3, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)

        # العنوان
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; font-weight:700; "
            f"background:transparent; letter-spacing:0.2px;"
        )
        v.addWidget(lbl)

        # القيمة + الوحدة
        vrow = QHBoxLayout()
        vrow.setSpacing(8)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:24px; color:{TEXT}; font-weight:900; background:transparent;"
        )
        vrow.addWidget(val)
        vrow.addStretch()

        un = QLabel(unit)
        un.setStyleSheet(f"""
            font-size:9.5px;
            color:{color};
            background:{soft};
            border:1px solid {border_color};
            border-radius:8px;
            padding:3px 9px;
            font-weight:800;
        """)
        vrow.addWidget(un)

        v.addLayout(vrow)

        card._value_label = val
        return card

    # ----------------------------------------------------------
    #                    بطاقة الفلاتر
    # ----------------------------------------------------------
    def _build_filters_card(self):
        card = QFrame()
        card.setObjectName("filterCard")
        card.setStyleSheet(f"""
            QFrame#filterCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=16, y_offset=3, alpha=20)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(14)

        # العنوان
        head_title = QLabel("البحث والفلاتر")
        head_title.setStyleSheet(
            f"font-size:13px; font-weight:900; color:{TEXT}; background:transparent;"
        )
        outer.addWidget(head_title)

        # فاصل
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER}; border:none;")
        outer.addWidget(line)

        # الحقول
        h = QHBoxLayout()
        h.setSpacing(14)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ابحث بكود أو اسم الموظف...")
        self.search_input.setFixedHeight(44)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background:{SURFACE_2}; border:1.5px solid {BORDER};
                border-radius:10px; padding:0 14px;
                font-size:12.5px; color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QLineEdit:hover {{ background:white; border-color:{BORDER_2}; }}
            QLineEdit:focus {{ background:white; border:1.5px solid {PRIMARY}; }}
        """)
        self.search_input.returnPressed.connect(self._refresh)

        search_wrap = self._labeled("بحث (كود / اسم)", self.search_input)
        search_wrap.setMinimumWidth(240)
        h.addWidget(search_wrap, 3)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.from_date.setFixedHeight(44)
        self.from_date.setLayoutDirection(Qt.LeftToRight)
        self._style_date(self.from_date)
        h.addWidget(self._labeled("من تاريخ", self.from_date), 2)

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setFixedHeight(44)
        self.to_date.setLayoutDirection(Qt.LeftToRight)
        self._style_date(self.to_date)
        h.addWidget(self._labeled("إلى تاريخ", self.to_date), 2)

        # الأزرار
        btn_search = QPushButton("احسب")
        btn_search.setFixedHeight(44)
        btn_search.setMinimumWidth(120)
        btn_search.setCursor(Qt.PointingHandCursor)
        btn_search.setStyleSheet(self._gradient_btn(PRIMARY, PRIMARY_HOV))
        btn_search.clicked.connect(self._refresh)

        btn_export = QPushButton("تصدير CSV")
        btn_export.setFixedHeight(44)
        btn_export.setMinimumWidth(140)
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setStyleSheet(self._gradient_btn(SUCCESS, SUCCESS_HOV))
        btn_export.clicked.connect(self._export_csv)

        btn_reset = QPushButton("إعادة تعيين")
        btn_reset.setFixedHeight(44)
        btn_reset.setMinimumWidth(130)
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1.5px solid {BORDER_2}; border-radius:10px;
                padding:0 18px; font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{
                background:{SURFACE_2}; border-color:{TEXT_MUTED}; color:{TEXT};
            }}
        """)
        btn_reset.clicked.connect(self._reset_filters)

        btns = QHBoxLayout()
        btns.setSpacing(9)
        btns.addWidget(btn_search)
        btns.addWidget(btn_export)
        btns.addWidget(btn_reset)

        bw = QWidget()
        bw.setStyleSheet("background:transparent;")
        bwl = QVBoxLayout(bw)
        bwl.setContentsMargins(0, 0, 0, 0)
        bwl.setSpacing(6)
        sp = QLabel("")
        sp.setFixedHeight(16)
        bwl.addWidget(sp)
        bwl.addLayout(btns)

        h.addWidget(bw)
        outer.addLayout(h)

        return card

    def _labeled(self, text, widget):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size:10.5px; font-weight:800; color:{TEXT_SEC}; "
            f"background:transparent;"
        )
        v.addWidget(lbl)
        v.addWidget(widget)
        return w

    def _style_date(self, w):
        w.setStyleSheet(f"""
            QDateEdit {{
                background:{SURFACE_2}; border:1.5px solid {BORDER};
                border-radius:10px; padding:0 14px;
                font-size:12.5px; color:{TEXT}; font-weight:700;
            }}
            QDateEdit:hover {{ background:white; border-color:{BORDER_2}; }}
            QDateEdit:focus {{ background:white; border:1.5px solid {PRIMARY}; }}
            QDateEdit::drop-down {{ border:none; width:30px; }}
            QDateEdit::down-arrow {{
                image:none; width:0; height:0;
                border-left:4px solid transparent;
                border-right:4px solid transparent;
                border-top:5px solid {TEXT_MUTED};
                margin-right:10px;
            }}
        """)

    def _gradient_btn(self, c1, c2):
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {c1}, stop:1 {c2});
                color:white; border:none;
                border-radius:10px; padding:0 22px;
                font-weight:900; font-size:12.5px;
                font-family:{FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4d6bff, stop:1 {c2});
            }}
            QPushButton:pressed {{ background:{c2}; }}
        """

    # ----------------------------------------------------------
    #                    بطاقة الجدول
    # ----------------------------------------------------------
    def _build_table_card(self):
        card = QFrame()
        card.setObjectName("tableCard")
        card.setStyleSheet(f"""
            QFrame#tableCard {{
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

        title = QLabel("كشف المرتبات التفصيلي")
        title.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT};")
        hl.addWidget(title)
        hl.addStretch()

        hint = QLabel("انقر مرتين على أي صف لعرض التفاصيل")
        hint.setStyleSheet(f"font-size:10.5px; color:{TEXT_MUTED};")
        hl.addWidget(hint)
        v.addWidget(head)

        # 19 عمود
        self.table = QTableWidget(0, 19)
        self.table.setHorizontalHeaderLabels([
            "كود الموظف", "اسم الموظف", "الوظيفة",
            "أيام العمل", "الغياب", "خصم البدلات",
            "رصيد الإجازة", "إجازة سنوية", "خصم المرضية",
            "التأخيرات", "انصراف مبكر", "الإضافي",
            "تأمين طبي", "تأمين اجتماعي",
            "بدل وجبة", "بدل انتقال", "بدلات أخرى",
            "بدل انتماء", "الصافي"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(420)
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
                padding:14px 10px; border:none;
                border-bottom:1px solid {BORDER};
                font-weight:900; font-size:10px;
                letter-spacing:0.3px;
            }}
            QScrollBar:vertical {{
                width:9px; background:transparent;
                margin:4px 2px 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2}; border-radius:4px; min-height:40px;
            }}
            QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
            QScrollBar:horizontal {{
                height:9px; background:transparent;
                margin:0 4px 2px 4px;
            }}
            QScrollBar::handle:horizontal {{
                background:{BORDER_2}; border-radius:4px; min-width:40px;
            }}
            QScrollBar::handle:horizontal:hover {{ background:{TEXT_MUTED}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{ height:0; width:0; }}
        """)
        self.table.verticalHeader().setDefaultSectionSize(56)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 100)

        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)

        v.addWidget(self.table)
        return card

    # ========================================================
    #                    منطق الحساب
    # ========================================================
    def _reset_filters(self):
        today = QDate.currentDate()
        first = QDate(today.year(), today.month(), 1)
        self.from_date.setDate(first)
        self.to_date.setDate(today)
        self.search_input.clear()
        self._refresh()

    def _refresh(self):
        from_d = self.from_date.date().toString("yyyy-MM-dd")
        to_d = self.to_date.date().toString("yyyy-MM-dd")

        if self.from_date.date() > self.to_date.date():
            QMessageBox.warning(self, "تنبيه", "تاريخ البداية بعد تاريخ النهاية")
            return

        search = self.search_input.text().strip().lower()

        all_punches = get_all_raw_punches_in_range(from_d, to_d)
        punches_by_emp = {}
        for p in all_punches:
            emp_id = p["employee_id"]
            if emp_id is None:
                continue
            punches_by_emp.setdefault(emp_id, {}).setdefault(p["punch_date"], []).append(p)
        for by_date in punches_by_emp.values():
            for lst in by_date.values():
                lst.sort(key=lambda x: x["punch_time"])

        all_overrides = get_all_overrides_in_range(from_d, to_d)
        overrides_by_emp = {}
        for o in all_overrides:
            overrides_by_emp.setdefault(o["employee_id"], {})[o["date"]] = o

        annual_leave_used_map = get_all_annual_leave_used()

        employees = get_employees(include_inactive=False)
        if search:
            employees = [
                e for e in employees
                if search in (e["code"] or "").lower()
                or search in (e["name"] or "").lower()
            ]

        self._rows = []
        for emp in employees:
            row = self._compute_row(
                emp, from_d, to_d,
                punches_by_emp, overrides_by_emp, annual_leave_used_map
            )
            if row:
                self._rows.append(row)

        self._render_table()
        self._update_stats()

    def _compute_row(self, emp, from_d, to_d,
                     punches_by_emp, overrides_by_emp, annual_leave_used_map):
        """حساب صف مرتب واحد لموظف (مع الانصراف المبكر)"""
        summary = compute_employee_summary(
            emp["id"], from_d, to_d,
            punches_by_emp_date=punches_by_emp,
            overrides_by_emp_date=overrides_by_emp,
            annual_leave_used_map=annual_leave_used_map,
        )
        if not summary:
            return None

        shift = get_shift(emp["shift_id"]) if emp["shift_id"] else None

        # البيانات المالية
        base = float(emp["base_salary"] or 0)
        total_from_db = float(emp["total_salary"] or 0)
        incentive = float(emp["incentive"] or 0)
        meal = float(emp["meal_allowance"] or 0)
        transport = float(emp["transport_allowance"] or 0)
        other_allow = float(emp["other_allowances"] or 0)
        expat = float(emp["expat_allowance"] or 0)
        medical = float(emp["medical_insurance"] or 0)
        social = float(emp["social_insurance"] or 0)

        base_for_total = total_from_db if total_from_db > 0 else base
        total_salary = base_for_total + incentive

        allowances_total = meal + transport + other_allow + expat

        work_hours = float(shift["work_hours"]) if shift and shift["work_hours"] else 8.0
        ot_rate = float(shift["overtime_rate"]) if shift and shift["overtime_rate"] else 1.0

        daily = total_salary / 30.0 if total_salary else 0.0
        hourly = daily / work_hours if work_hours else 0.0

        # الخصومات
        absent_days = summary["absent"]
        absence_ded = absent_days * daily

        sick_ded_days = summary["_total_sick_deduction"]
        sick_ded_value = sick_ded_days * daily

        delay_min = summary["_total_delay_min"]
        delay_hours = delay_min / 60.0
        delay_ded = delay_hours * hourly

        early_min = _safe_get(summary, "_total_early_leave_min", 0)
        early_hours = early_min / 60.0
        early_ded = early_hours * hourly

        meal_ded_per_day = meal / 30.0 if meal else 0.0
        transport_ded_per_day = transport / 30.0 if transport else 0.0
        other_ded_per_day = other_allow / 30.0 if other_allow else 0.0
        expat_ded_per_day = expat / 30.0 if expat else 0.0

        meal_ded = meal_ded_per_day * absent_days
        transport_ded = transport_ded_per_day * absent_days
        other_ded = other_ded_per_day * absent_days
        expat_ded = expat_ded_per_day * absent_days

        allowances_ded_total = meal_ded + transport_ded + other_ded + expat_ded

        ot_min = summary["_total_overtime_min"]
        ot_hours = ot_min / 60.0
        ot_pay = ot_hours * hourly * ot_rate

        # الإجماليات
        gross = total_salary + allowances_total + ot_pay

        total_deductions = (
            absence_ded
            + allowances_ded_total
            + sick_ded_value
            + delay_ded
            + early_ded
            + medical
            + social
        )

        net = gross - total_deductions
        if net < 0:
            net = 0

        return {
            "employee_id": emp["id"],
            "code": emp["code"],
            "name": emp["name"],
            "department": emp["department"] or "—",
            "shift_name": shift["name"] if shift else "—",

            "total_working": summary["total_working"],
            "present": summary["present"],
            "absent": absent_days,
            "annual_leaves": summary["annual_leaves"],
            "sick_leaves": summary["sick_leaves"],
            "work_injuries": summary["work_injuries"],
            "weekly_holidays": summary["weekly_holidays"],

            "annual_initial": summary["annual_leave_initial"],
            "annual_used": summary["annual_leave_used_total"],
            "annual_remaining": summary["annual_leave_remaining"],

            "delay_min": delay_min,
            "delay_ded": delay_ded,
            "early_min": early_min,
            "early_hours": early_hours,
            "early_ded": early_ded,
            "ot_min": ot_min,
            "ot_hours": ot_hours,
            "ot_pay": ot_pay,
            "sick_ded_days": sick_ded_days,
            "sick_ded_value": sick_ded_value,
            "absence_ded": absence_ded,

            "meal_ded": meal_ded,
            "transport_ded": transport_ded,
            "other_ded": other_ded,
            "expat_ded": expat_ded,
            "allowances_ded_total": allowances_ded_total,

            "base": base,
            "total_salary": total_salary,
            "incentive": incentive,
            "allowances_total": allowances_total,
            "meal": meal,
            "transport": transport,
            "other_allow": other_allow,
            "expat": expat,
            "medical": medical,
            "social": social,

            "hourly": hourly,
            "daily": daily,
            "work_hours": work_hours,
            "ot_rate": ot_rate,

            "gross": gross,
            "total_deductions": total_deductions,
            "net": net,
        }

    # ========================================================
    #                    عرض الجدول
    # ========================================================
    def _render_table(self):
        self.table.setRowCount(0)

        for i, r in enumerate(self._rows):
            self.table.insertRow(i)

            # 0: كود
            c0 = QTableWidgetItem(str(r["code"]))
            c0.setTextAlignment(Qt.AlignCenter)
            c0.setForeground(QColor(TEXT))
            f = c0.font(); f.setBold(True); c0.setFont(f)
            self.table.setItem(i, 0, c0)

            # 1: اسم
            c1 = QTableWidgetItem(r["name"])
            c1.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            c1.setForeground(QColor(TEXT))
            self.table.setItem(i, 1, c1)

            # 2: الوظيفة
            c2 = QTableWidgetItem(r["department"])
            c2.setTextAlignment(Qt.AlignCenter)
            c2.setForeground(QColor(TEXT_SEC))
            self.table.setItem(i, 2, c2)

            # 3: أيام العمل
            c3 = QTableWidgetItem(f"{r['present']}/{r['total_working']}")
            c3.setTextAlignment(Qt.AlignCenter)
            c3.setForeground(QColor(SUCCESS if r['present'] > 0 else TEXT_MUTED))
            self.table.setItem(i, 3, c3)

            # 4: الغياب
            c4 = QTableWidgetItem(str(r["absent"]) if r["absent"] else "—")
            c4.setTextAlignment(Qt.AlignCenter)
            c4.setForeground(QColor(DANGER if r["absent"] else TEXT_MUTED))
            if r["absent"]:
                c4.setToolTip(
                    f"أيام الغياب: {r['absent']}\n"
                    f"السعر اليومي: {fmt_money(r['daily'])}\n"
                    f"خصم الغياب: {fmt_money(r['absence_ded'])} ج.م"
                )
            self.table.setItem(i, 4, c4)

            # 5: خصم البدلات
            if r["allowances_ded_total"] > 0:
                c5 = QTableWidgetItem(fmt_money_int(r["allowances_ded_total"]))
                c5.setTextAlignment(Qt.AlignCenter)
                c5.setForeground(QColor(PINK))
                c5.setToolTip(
                    f"خصم البدلات بنسبة أيام الغياب ({r['absent']} يوم):\n"
                    f"────────────────\n"
                    f"بدل وجبة: {fmt_money(r['meal_ded'])}\n"
                    f"بدل انتقال: {fmt_money(r['transport_ded'])}\n"
                    f"بدلات أخرى: {fmt_money(r['other_ded'])}\n"
                    f"بدل انتماء: {fmt_money(r['expat_ded'])}\n"
                    f"────────────────\n"
                    f"الإجمالي: {fmt_money(r['allowances_ded_total'])} ج.م"
                )
            else:
                c5 = QTableWidgetItem("—")
                c5.setTextAlignment(Qt.AlignCenter)
                c5.setForeground(QColor(TEXT_MUTED))
            self.table.setItem(i, 5, c5)

            # 6: رصيد الإجازة
            rem = r["annual_remaining"]
            init = r["annual_initial"]
            c6 = QTableWidgetItem(f"{_fmt_num(rem)} / {_fmt_num(init)}")
            c6.setTextAlignment(Qt.AlignCenter)
            if rem <= 0:
                c6.setForeground(QColor(DANGER))
            elif rem <= 3:
                c6.setForeground(QColor(WARNING))
            else:
                c6.setForeground(QColor(INFO))
            c6.setToolTip(
                f"الابتدائي: {_fmt_num(init)}\n"
                f"المستخدم: {_fmt_num(r['annual_used'])}\n"
                f"المتبقي: {_fmt_num(rem)}"
            )
            self.table.setItem(i, 6, c6)

            # 7: الإجازة السنوية
            c7 = QTableWidgetItem(str(r["annual_leaves"]) if r["annual_leaves"] else "—")
            c7.setTextAlignment(Qt.AlignCenter)
            c7.setForeground(QColor(INFO if r["annual_leaves"] else TEXT_MUTED))
            self.table.setItem(i, 7, c7)

            # 8: خصم المرضية
            if r["sick_ded_value"] > 0:
                c8 = QTableWidgetItem(fmt_money_int(r["sick_ded_value"]))
                c8.setForeground(QColor(WARNING))
                c8.setToolTip(
                    f"أيام الخصم: {_fmt_num(r['sick_ded_days'])} يوم\n"
                    f"السعر اليومي: {fmt_money(r['daily'])}\n"
                    f"القيمة: {fmt_money(r['sick_ded_value'])} ج.م"
                )
            else:
                c8 = QTableWidgetItem("—")
                c8.setForeground(QColor(TEXT_MUTED))
            c8.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 8, c8)

            # 9: التأخيرات
            if r["delay_ded"] > 0:
                c9 = QTableWidgetItem(fmt_money_int(r["delay_ded"]))
                c9.setForeground(QColor(DANGER))
                c9.setToolTip(
                    f"دقائق التأخير: {r['delay_min']:.0f}\n"
                    f"({format_minutes_ar(int(r['delay_min']))})\n"
                    f"سعر الساعة: {fmt_money(r['hourly'])}\n"
                    f"القيمة: {fmt_money(r['delay_ded'])} ج.م"
                )
            else:
                c9 = QTableWidgetItem("—")
                c9.setForeground(QColor(TEXT_MUTED))
            c9.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 9, c9)

            # 10: الانصراف المبكر
            if r["early_ded"] > 0:
                c10 = QTableWidgetItem(fmt_money_int(r["early_ded"]))
                c10.setForeground(QColor(PINK))
                f10 = c10.font(); f10.setBold(True); c10.setFont(f10)
                c10.setToolTip(
                    f"دقائق الانصراف المبكر: {r['early_min']:.0f}\n"
                    f"({format_minutes_ar(int(r['early_min']))})\n"
                    f"سعر الساعة: {fmt_money(r['hourly'])}\n"
                    f"القيمة: {fmt_money(r['early_ded'])} ج.م"
                )
            else:
                c10 = QTableWidgetItem("—")
                c10.setForeground(QColor(TEXT_MUTED))
            c10.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 10, c10)

            # 11: الإضافي
            if r["ot_pay"] > 0:
                c11 = QTableWidgetItem(fmt_money_int(r["ot_pay"]))
                c11.setForeground(QColor(PURPLE))
                f11 = c11.font(); f11.setBold(True); c11.setFont(f11)
                c11.setToolTip(
                    f"ساعات الإضافي: {r['ot_hours']:.2f}\n"
                    f"سعر الساعة: {fmt_money(r['hourly'])}\n"
                    f"المعدل: ×{r['ot_rate']}\n"
                    f"القيمة: {fmt_money(r['ot_pay'])} ج.م"
                )
            else:
                c11 = QTableWidgetItem("—")
                c11.setForeground(QColor(TEXT_MUTED))
            c11.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 11, c11)

            # 12: تأمين طبي
            c12 = QTableWidgetItem(fmt_money_int(r["medical"]) if r["medical"] else "—")
            c12.setTextAlignment(Qt.AlignCenter)
            c12.setForeground(QColor(TEXT if r["medical"] else TEXT_MUTED))
            self.table.setItem(i, 12, c12)

            # 13: تأمين اجتماعي
            c13 = QTableWidgetItem(fmt_money_int(r["social"]) if r["social"] else "—")
            c13.setTextAlignment(Qt.AlignCenter)
            c13.setForeground(QColor(TEXT if r["social"] else TEXT_MUTED))
            self.table.setItem(i, 13, c13)

            # 14: بدل وجبة
            c14 = QTableWidgetItem(fmt_money_int(r["meal"]) if r["meal"] else "—")
            c14.setTextAlignment(Qt.AlignCenter)
            c14.setForeground(QColor(SUCCESS if r["meal"] else TEXT_MUTED))
            self.table.setItem(i, 14, c14)

            # 15: بدل انتقال
            c15 = QTableWidgetItem(fmt_money_int(r["transport"]) if r["transport"] else "—")
            c15.setTextAlignment(Qt.AlignCenter)
            c15.setForeground(QColor(SUCCESS if r["transport"] else TEXT_MUTED))
            self.table.setItem(i, 15, c15)

            # 16: بدلات أخرى
            c16 = QTableWidgetItem(fmt_money_int(r["other_allow"]) if r["other_allow"] else "—")
            c16.setTextAlignment(Qt.AlignCenter)
            c16.setForeground(QColor(SUCCESS if r["other_allow"] else TEXT_MUTED))
            self.table.setItem(i, 16, c16)

            # 17: بدل انتماء
            c17 = QTableWidgetItem(fmt_money_int(r["expat"]) if r["expat"] else "—")
            c17.setTextAlignment(Qt.AlignCenter)
            c17.setForeground(QColor(SUCCESS if r["expat"] else TEXT_MUTED))
            self.table.setItem(i, 17, c17)

            # 18: الصافي
            net_wrap = QWidget()
            net_wrap.setStyleSheet("background:transparent;")
            nl = QHBoxLayout(net_wrap)
            nl.setContentsMargins(4, 0, 4, 0)
            nl.setAlignment(Qt.AlignCenter)

            net_lbl = QLabel(fmt_money_int(r["net"]) + " ج.م")
            net_lbl.setAlignment(Qt.AlignCenter)
            net_lbl.setStyleSheet(f"""
                background:{SUCCESS_BG}; color:{SUCCESS};
                border:1.5px solid {SUCCESS_BRD};
                padding:6px 14px; border-radius:10px;
                font-weight:900; font-size:12px;
                font-family:{FONT_FAMILY};
            """)
            net_lbl.setToolTip(
                f"الإجمالي (أساسي + حافز): {fmt_money(r['total_salary'])}\n"
                f"البدلات الكاملة: +{fmt_money(r['allowances_total'])}\n"
                f"الإضافي: +{fmt_money(r['ot_pay'])}\n"
                f"═════════════\n"
                f"خصم غياب: -{fmt_money(r['absence_ded'])}\n"
                f"خصم بدلات: -{fmt_money(r['allowances_ded_total'])}\n"
                f"خصم مرضية: -{fmt_money(r['sick_ded_value'])}\n"
                f"خصم تأخير: -{fmt_money(r['delay_ded'])}\n"
                f"خصم انصراف مبكر: -{fmt_money(r['early_ded'])}\n"
                f"طبي + اجتماعي: -{fmt_money(r['medical'] + r['social'])}\n"
                f"═════════════\n"
                f"الصافي: {fmt_money(r['net'])} ج.م"
            )
            nl.addWidget(net_lbl)
            self.table.setCellWidget(i, 18, net_wrap)

    def _update_stats(self):
        total = len(self._rows)
        total_days = sum(r["present"] for r in self._rows)
        total_ot = sum(r["ot_pay"] for r in self._rows)
        total_early = sum(r["early_ded"] for r in self._rows)
        total_net = sum(r["net"] for r in self._rows)

        self.stat_employees._value_label.setText(str(total))
        self.stat_days._value_label.setText(str(total_days))
        self.stat_overtime._value_label.setText(fmt_money_int(total_ot))
        self.stat_early._value_label.setText(fmt_money_int(total_early))
        self.stat_net._value_label.setText(fmt_money_int(total_net))
        self.rows_badge.setText(f"{total} موظف")

    # ========================================================
    #                    تصدير CSV
    # ========================================================
    def _export_csv(self):
        if not self._rows:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات للتصدير")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ كشف المرتبات", "payroll.csv", "CSV (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow([
                    "كود الموظف", "اسم الموظف", "الوظيفة",
                    "أيام العمل", "الغياب", "خصم البدلات",
                    "رصيد الإجازة", "إجازة سنوية", "خصم المرضية",
                    "التأخيرات", "انصراف مبكر", "الإضافي",
                    "تأمين طبي", "تأمين اجتماعي",
                    "بدل وجبة", "بدل انتقال", "بدلات أخرى",
                    "بدل انتماء", "الصافي",
                ])
                for r in self._rows:
                    w.writerow([
                        r["code"], r["name"], r["department"],
                        f"{r['present']}/{r['total_working']}", r["absent"],
                        f"{fmt_money_int(r['allowances_ded_total'])}",
                        f"{_fmt_num(r['annual_remaining'])}/{_fmt_num(r['annual_initial'])}",
                        r["annual_leaves"],
                        f"{fmt_money_int(r['sick_ded_value'])}",
                        f"{fmt_money_int(r['delay_ded'])}",
                        f"{fmt_money_int(r['early_ded'])}",
                        f"{fmt_money_int(r['ot_pay'])}",
                        f"{fmt_money_int(r['medical'])}",
                        f"{fmt_money_int(r['social'])}",
                        f"{fmt_money_int(r['meal'])}",
                        f"{fmt_money_int(r['transport'])}",
                        f"{fmt_money_int(r['other_allow'])}",
                        f"{fmt_money_int(r['expat'])}",
                        f"{fmt_money_int(r['net'])}",
                    ])
            QMessageBox.information(self, "تم", f"تم التصدير:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل التصدير:\n{e}")

    # ========================================================
    #                    نافذة التفاصيل
    # ========================================================
    def _on_row_double_clicked(self, item):
        row_idx = item.row()
        if 0 <= row_idx < len(self._rows):
            dlg = PayrollDetailDialog(
                self._rows[row_idx],
                self.from_date.date().toString("yyyy-MM-dd"),
                self.to_date.date().toString("yyyy-MM-dd"),
                self,
            )
            dlg.exec()


# ============================================================
#              Dialog: تفاصيل المرتب لموظف
# ============================================================
class PayrollDetailDialog(QDialog):
    def __init__(self, row, from_date, to_date, parent=None):
        super().__init__(parent)
        self.row = row
        self.from_date = from_date
        self.to_date = to_date

        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle(f"تفاصيل المرتب — {row['name']}")
        self.setMinimumSize(1180, 800)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")

        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

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

        content = QWidget()
        content.setStyleSheet(f"background:{BG};")
        v = QVBoxLayout(content)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        # ============ Header ============
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
        title = QLabel(f"{self.row['name']}  ·  {self.row['code']}")
        title.setStyleSheet(
            "font-size:16px; font-weight:900; color:white; background:transparent;"
        )
        tbox.addWidget(title)
        sub = QLabel(
            f"الفترة: {self.from_date}  →  {self.to_date}      "
            f"الوظيفة: {self.row['department']}      "
            f"الشيفت: {self.row['shift_name']}"
        )
        sub.setStyleSheet("font-size:11px; color:#9db3cf; background:transparent;")
        sub.setWordWrap(True)
        tbox.addWidget(sub)
        hl.addLayout(tbox)
        hl.addStretch()

        net_lbl = QLabel(f"{fmt_money_int(self.row['net'])} ج.م")
        net_lbl.setAlignment(Qt.AlignCenter)
        net_lbl.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {SUCCESS_BG}, stop:1 #d1fae5);
            color:{SUCCESS};
            padding:10px 24px; border-radius:12px;
            font-size:16px; font-weight:900;
            border:1.5px solid {SUCCESS_BRD};
        """)
        hl.addWidget(net_lbl)

        v.addWidget(head)

        # ============ Summary Cards ============
        self._build_summary_section(v)

        # ============ Details ============
        self._build_details_section(v)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # ============ Footer ============
        footer = QFrame()
        footer.setStyleSheet(f"background:{SURFACE}; border-top:1px solid {BORDER};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(22, 12, 22, 12)
        fl.addStretch()

        btn_close = QPushButton("إغلاق")
        btn_close.setFixedHeight(42)
        btn_close.setMinimumWidth(140)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1.5px solid {BORDER_2}; border-radius:10px;
                padding:0 26px; font-weight:800; font-size:12.5px;
            }}
            QPushButton:hover {{
                background:{SURFACE_2}; border-color:{TEXT_MUTED};
                color:{TEXT};
            }}
        """)
        btn_close.clicked.connect(self.accept)
        fl.addWidget(btn_close)
        outer.addWidget(footer)

    def _build_summary_section(self, parent_layout):
        r = self.row

        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        cards_data = [
            ("أيام العمل", f"{r['present']}/{r['total_working']}",
             PRIMARY, PRIMARY_BG, PRIMARY_BRD),
            ("الغياب", str(r["absent"]),
             DANGER, DANGER_BG, DANGER_BRD),
            ("رصيد الإجازة",
             f"{_fmt_num(r['annual_remaining'])}/{_fmt_num(r['annual_initial'])}",
             INFO, INFO_BG, INFO_BRD),
            ("إجازة بالفترة", str(r["annual_leaves"]),
             INFO, INFO_BG, INFO_BRD),
            ("إجازة مرضية", str(r["sick_leaves"]),
             WARNING, WARNING_BG, WARNING_BRD),
            ("إصابة عمل", str(r["work_injuries"]),
             PINK, PINK_BG, PINK_BRD),
            ("التأخير", format_minutes_ar(int(r["delay_min"])),
             WARNING, WARNING_BG, WARNING_BRD),
            ("انصراف مبكر", format_minutes_ar(int(r["early_min"])),
             PINK, PINK_BG, PINK_BRD),
            ("الإضافي", f"{r['ot_hours']:.2f} س",
             PURPLE, PURPLE_BG, PURPLE_BRD),
        ]

        for i, (t, val, color, bg, brd) in enumerate(cards_data):
            card = QFrame()
            card.setMinimumHeight(72)
            card.setStyleSheet(f"""
                QFrame {{
                    background:{SURFACE};
                    border:1px solid {BORDER};
                    border-radius:12px;
                }}
                QFrame:hover {{
                    border:1.5px solid {brd};
                }}
            """)
            apply_shadow(card, blur=10, y_offset=2, alpha=18)

            v = QVBoxLayout(card)
            v.setContentsMargins(14, 12, 14, 12)
            v.setSpacing(4)

            lbl = QLabel(t)
            lbl.setStyleSheet(
                f"font-size:10.5px; color:{TEXT_MUTED}; font-weight:700;"
            )
            v.addWidget(lbl)

            vv = QLabel(val)
            vv.setStyleSheet(
                f"font-size:17px; color:{color}; font-weight:900;"
            )
            v.addWidget(vv)

            grid.addWidget(card, i // 5, i % 5)

        for c in range(5):
            grid.setColumnStretch(c, 1)

        parent_layout.addWidget(wrap)

    def _build_details_section(self, parent_layout):
        r = self.row

        earnings = [
            ("الإجمالي (أساسي + حافز)", r["total_salary"]),
            ("بدل وجبة", r["meal"]),
            ("بدل انتقال", r["transport"]),
            ("بدلات أخرى", r["other_allow"]),
            ("بدل انتماء", r["expat"]),
            ("الإضافي", r["ot_pay"]),
        ]

        allowances_ded_breakdown = [
            ("خصم بدل وجبة", r["meal_ded"]),
            ("خصم بدل انتقال", r["transport_ded"]),
            ("خصم بدلات أخرى", r["other_ded"]),
            ("خصم بدل انتماء", r["expat_ded"]),
        ]

        deductions = [
            ("خصم الغياب (من الإجمالي)", r["absence_ded"]),
            ("خصم الإجازة المرضية", r["sick_ded_value"]),
            ("خصم التأخير", r["delay_ded"]),
            ("خصم الانصراف المبكر", r["early_ded"]),
            ("تأمين طبي", r["medical"]),
            ("تأمين اجتماعي", r["social"]),
        ]

        grid = QHBoxLayout()
        grid.setSpacing(16)

        earn_card = self._make_section_card(
            "الاستحقاقات", earnings, SUCCESS, SUCCESS_BG, SUCCESS_BRD,
            total_label="إجمالي الاستحقاقات", total_value=r["gross"],
            extra_items=[
                ("الراتب الأساسي", r["base"]),
                ("الحافز", r["incentive"]),
            ],
            extra_title="تفصيل الراتب الإجمالي"
        )
        grid.addWidget(earn_card, 1)

        ded_card = self._make_section_card(
            "الخصومات", deductions, DANGER, DANGER_BG, DANGER_BRD,
            total_label="إجمالي الخصومات", total_value=r["total_deductions"],
            extra_items=allowances_ded_breakdown,
            extra_title="خصم البدلات (بنسبة الغياب)"
        )
        grid.addWidget(ded_card, 1)

        net_card = self._make_net_card(r)
        grid.addWidget(net_card, 1)

        parent_layout.addLayout(grid, 1)

    def _make_section_card(self, title, items, color, bg, brd,
                           total_label="", total_value=0,
                           extra_items=None, extra_title=""):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=14, y_offset=3, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(12)

        head = QLabel(title)
        head.setStyleSheet(f"""
            font-size:13px; font-weight:900; color:{color};
            background:{bg}; border:1.5px solid {brd};
            padding:10px 14px; border-radius:10px;
        """)
        head.setAlignment(Qt.AlignCenter)
        v.addWidget(head)

        for label, value in items:
            if value <= 0 and label not in ("الإجمالي (أساسي + حافز)",):
                continue

            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background:{SURFACE_2};
                    border:1px solid {BORDER};
                    border-radius:9px;
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(6)

            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size:11.5px; color:{TEXT_SEC}; font-weight:700;")
            rl.addWidget(lbl)
            rl.addStretch()

            val = QLabel(fmt_money(value))
            val.setStyleSheet(f"font-size:12px; color:{color}; font-weight:900;")
            rl.addWidget(val)

            v.addWidget(row)

        if extra_items:
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background:{DIVIDER};")
            v.addWidget(sep)

            if extra_title:
                et = QLabel(extra_title)
                et.setStyleSheet(f"""
                    font-size:10.5px;
                    color:{TEXT_MUTED};
                    font-weight:800;
                    background:transparent;
                    padding:4px 0;
                """)
                v.addWidget(et)

            for label, value in extra_items:
                row = QFrame()
                row.setStyleSheet("background:transparent;")
                rl = QHBoxLayout(row)
                rl.setContentsMargins(8, 4, 8, 4)
                rl.setSpacing(6)

                lbl = QLabel(label)
                lbl.setStyleSheet(
                    f"font-size:10.5px; color:{TEXT_MUTED}; font-weight:600;"
                )
                rl.addWidget(lbl)
                rl.addStretch()

                val = QLabel(fmt_money_int(value))
                val.setStyleSheet(
                    f"font-size:10.5px; color:{TEXT_SEC}; font-weight:800;"
                )
                rl.addWidget(val)

                v.addWidget(row)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{brd};")
        v.addWidget(line)

        total = QFrame()
        total.setStyleSheet(f"""
            QFrame {{
                background:{bg};
                border:1.5px solid {brd};
                border-radius:9px;
            }}
        """)
        tl = QHBoxLayout(total)
        tl.setContentsMargins(14, 12, 14, 12)

        tlbl = QLabel(total_label)
        tlbl.setStyleSheet(f"font-size:12.5px; color:{color}; font-weight:900;")
        tl.addWidget(tlbl)
        tl.addStretch()

        tval = QLabel(fmt_money(total_value))
        tval.setStyleSheet(f"font-size:15px; color:{color}; font-weight:900;")
        tl.addWidget(tval)

        v.addWidget(total)
        v.addStretch()
        return card

    def _make_net_card(self, r):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                border-radius:14px;
            }}
        """)
        apply_shadow(card, blur=16, y_offset=4, alpha=50)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 26, 22, 26)
        v.setSpacing(12)

        lbl = QLabel("صافي المرتب")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "font-size:13px; color:#d1fae5; background:transparent; font-weight:800;"
        )
        v.addWidget(lbl)

        val = QLabel(f"{fmt_money(r['net'])}")
        val.setAlignment(Qt.AlignCenter)
        val.setStyleSheet(
            "font-size:28px; color:white; background:transparent; font-weight:900;"
        )
        v.addWidget(val)

        cur = QLabel("ج.م")
        cur.setAlignment(Qt.AlignCenter)
        cur.setStyleSheet(
            "font-size:12px; color:#d1fae5; background:transparent; font-weight:700;"
        )
        v.addWidget(cur)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background:rgba(255,255,255,0.25);")
        v.addWidget(line)

        info_lines = [
            ("الإجمالي (أساسي+حافز)", r["total_salary"]),
            ("البدلات الكاملة", r["allowances_total"]),
            ("الإضافي", r["ot_pay"]),
            ("خصم البدلات", r["allowances_ded_total"]),
            ("خصم التأخير", r["delay_ded"]),
            ("خصم انصراف مبكر", r["early_ded"]),
            ("الخصومات الإجمالية", r["total_deductions"]),
        ]
        for lb, vl in info_lines:
            row = QHBoxLayout()
            l1 = QLabel(lb)
            l1.setStyleSheet(
                "font-size:10.5px; color:#d1fae5; background:transparent;"
            )
            row.addWidget(l1)
            row.addStretch()
            l2 = QLabel(fmt_money_int(vl))
            l2.setStyleSheet(
                "font-size:10.5px; color:white; background:transparent; font-weight:800;"
            )
            row.addWidget(l2)
            v.addLayout(row)

        v.addSpacing(6)

        daily_row = QHBoxLayout()
        d1 = QLabel("السعر اليومي")
        d1.setStyleSheet(
            "font-size:10.5px; color:#d1fae5; background:transparent;"
        )
        daily_row.addWidget(d1)
        daily_row.addStretch()
        d2 = QLabel(fmt_money(r["daily"]))
        d2.setStyleSheet(
            "font-size:10.5px; color:white; background:transparent; font-weight:800;"
        )
        daily_row.addWidget(d2)
        v.addLayout(daily_row)

        hourly_row = QHBoxLayout()
        h1 = QLabel("سعر الساعة")
        h1.setStyleSheet(
            "font-size:10.5px; color:#d1fae5; background:transparent;"
        )
        hourly_row.addWidget(h1)
        hourly_row.addStretch()
        h2 = QLabel(fmt_money(r["hourly"]))
        h2.setStyleSheet(
            "font-size:10.5px; color:white; background:transparent; font-weight:800;"
        )
        hourly_row.addWidget(h2)
        v.addLayout(hourly_row)

        v.addStretch()
        return card