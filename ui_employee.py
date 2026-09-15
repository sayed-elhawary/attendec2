from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QGridLayout, QScrollArea,
    QAbstractItemView, QFileDialog, QCheckBox, QDialog,
    QListWidget, QListWidgetItem, QMenu, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDoubleValidator, QColor, QDesktopServices, QAction
import os
import shutil
from pathlib import Path

from database import (
    add_employee, get_employees, get_shifts,
    delete_employee, update_employee, get_employee,
    toggle_employee_status,
    add_employee_file, get_employee_files, delete_employee_file,
)


# ============================================================
#                نظام الألوان الاحترافي (Modern Pro)
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

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def get_employee_folder(code: str) -> Path:
    folder = UPLOAD_DIR / code
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def apply_shadow(widget, blur=18, y_offset=2, alpha=20):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    effect.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(effect)
    return effect


# ============================================================
#                       صفحة الموظفين
# ============================================================
class EmployeePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._editing_id = None
        self._all_rows = []
        self._show_inactive = False
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_shifts()
        self._load_employees()

    # ========================================================
    #                    بناء الواجهة
    # ========================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())

        body = QWidget()
        body.setObjectName("employeeBody")
        body.setStyleSheet(f"QWidget#employeeBody {{ background:{BG}; }}")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(26, 22, 26, 26)
        body_layout.setSpacing(18)
        body_layout.addWidget(self._build_stats())

        content = QHBoxLayout()
        content.setSpacing(20)
        content.addWidget(self._build_table_card(), 7)
        content.addWidget(self._build_form_card(), 4)
        body_layout.addLayout(content, 1)
        root.addWidget(body, 1)

    # ----------------------------------------------------------
    #                       TOPBAR
    # ----------------------------------------------------------
    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("employeeTopbar")
        bar.setFixedHeight(96)
        bar.setStyleSheet(f"""
            QFrame#employeeTopbar {{
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
        icon = QLabel("👥")
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

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("إدارة الموظفين")
        title.setStyleSheet(f"""
            QLabel {{
                color:white; font-size:22px; font-weight:900;
                background:transparent; font-family:{FONT_FAMILY};
                letter-spacing:0.3px;
            }}
        """)
        title_box.addWidget(title)

        subtitle = QLabel("إدارة بيانات العاملين والرواتب والحالة الوظيفية من مكان واحد")
        subtitle.setStyleSheet(
            "QLabel { color:#94a8c4; font-size:11px; background:transparent; }"
        )
        title_box.addWidget(subtitle)
        h.addLayout(title_box)
        h.addStretch()

        # Count badge
        self.count_inline = QLabel("0 موظف")
        self.count_inline.setAlignment(Qt.AlignCenter)
        self.count_inline.setMinimumWidth(100)
        self.count_inline.setFixedHeight(38)
        self.count_inline.setStyleSheet(f"""
            QLabel {{
                background: rgba(59, 91, 253, 0.15);
                color:#c7d2fe;
                border:1px solid rgba(59, 91, 253, 0.35);
                border-radius:19px;
                padding:0 18px;
                font-size:11.5px;
                font-weight:800;
            }}
        """)
        h.addWidget(self.count_inline)

        # Search box
        search = QFrame()
        search.setFixedSize(340, 46)
        search.setObjectName("topSearch")
        search.setStyleSheet(f"""
            QFrame#topSearch {{
                background: rgba(255, 255, 255, 0.06);
                border:1px solid rgba(255, 255, 255, 0.12);
                border-radius:12px;
            }}
            QFrame#topSearch:hover {{
                background: rgba(255, 255, 255, 0.09);
                border:1px solid rgba(255, 255, 255, 0.18);
            }}
        """)
        sh = QHBoxLayout(search)
        sh.setContentsMargins(14, 0, 14, 0)
        sh.setSpacing(10)

        search_icon = QLabel("⌕")
        search_icon.setStyleSheet(
            "font-size:23px; color:#7c93b5; background:transparent; font-weight:900;"
        )
        sh.addWidget(search_icon)

        self.search = QLineEdit()
        self.search.setPlaceholderText("ابحث بالاسم أو الكود أو القسم...")
        self.search.setFrame(False)
        self.search.setStyleSheet("""
            QLineEdit {
                background:transparent;
                border:none;
                padding:0;
                color:white;
                font-size:12.5px;
                font-family: Segoe UI, Tahoma, Arial;
            }
        """)
        self.search.textChanged.connect(self._filter_table)
        sh.addWidget(self.search, 1)
        h.addWidget(search)
        return bar

    # ----------------------------------------------------------
    #                    بطاقات الإحصائيات
    # ----------------------------------------------------------
    def _build_stats(self):
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.stat_total = self._stat_card(
            "إجمالي الموظفين", "0", "👥",
            PRIMARY, PRIMARY_BG, PRIMARY_BRD, "سجل مسجّل"
        )
        self.stat_active = self._stat_card(
            "الموظفون النشطون", "0", "✓",
            SUCCESS, SUCCESS_BG, SUCCESS_BRD, "على رأس العمل"
        )
        self.stat_inactive = self._stat_card(
            "الموقوفون", "0", "⏸",
            WARNING, WARNING_BG, WARNING_BRD, "موقوف مؤقتاً"
        )
        self.stat_departments = self._stat_card(
            "الأقسام", "0", "▦",
            PURPLE, PURPLE_BG, PURPLE_BRD, "قسم/إدارة"
        )

        grid.addWidget(self.stat_total, 0, 0)
        grid.addWidget(self.stat_active, 0, 1)
        grid.addWidget(self.stat_inactive, 0, 2)
        grid.addWidget(self.stat_departments, 0, 3)

        for col in range(4):
            grid.setColumnStretch(col, 1)
        return wrap

    def _stat_card(self, title, value, icon_text, color, soft, border_color, unit):
        card = QFrame()
        card.setObjectName("statCard")
        card.setMinimumHeight(96)
        card.setStyleSheet(f"""
            QFrame#statCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
            QFrame#statCard:hover {{
                border:1.5px solid {border_color};
            }}
        """)
        apply_shadow(card, blur=16, y_offset=3, alpha=25)

        h = QHBoxLayout(card)
        h.setContentsMargins(18, 14, 18, 14)
        h.setSpacing(14)

        ic = QLabel(icon_text)
        ic.setAlignment(Qt.AlignCenter)
        ic.setFixedSize(52, 52)
        ic.setStyleSheet(f"""
            QLabel {{
                background:{soft};
                color:{color};
                border:1.5px solid {border_color};
                border-radius:14px;
                font-size:22px;
                font-weight:900;
            }}
        """)
        h.addWidget(ic)

        v = QVBoxLayout()
        v.setSpacing(2)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:10.5px; color:{TEXT_MUTED}; font-weight:800; "
            f"background:transparent; letter-spacing:0.3px;"
        )
        v.addWidget(lbl)

        # Value + unit
        vrow = QHBoxLayout()
        vrow.setSpacing(6)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:26px; color:{TEXT}; font-weight:900; background:transparent;"
        )
        vrow.addWidget(val)

        vrow.addStretch()

        un = QLabel(unit)
        un.setStyleSheet(f"""
            font-size:9.5px;
            color:{color};
            background:{soft};
            border:1px solid {border_color};
            border-radius:9px;
            padding:3px 8px;
            font-weight:800;
        """)
        vrow.addWidget(un)

        v.addLayout(vrow)
        h.addLayout(v)
        h.addStretch()

        card._value_label = val
        return card

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
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=20, y_offset=4, alpha=25)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header
        head = QFrame()
        head.setFixedHeight(80)
        head.setObjectName("tableHead")
        head.setStyleSheet(f"""
            QFrame#tableHead {{
                background:{SURFACE};
                border-bottom:1px solid {DIVIDER};
                border-top-left-radius:16px;
                border-top-right-radius:16px;
            }}
        """)

        hl = QHBoxLayout(head)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(14)

        hicon = QLabel("📋")
        hicon.setFixedSize(40, 40)
        hicon.setAlignment(Qt.AlignCenter)
        hicon.setStyleSheet(f"""
            QLabel {{
                background:{PRIMARY_BG};
                border:1px solid {PRIMARY_BRD};
                border-radius:11px;
                font-size:18px;
            }}
        """)
        hl.addWidget(hicon)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title = QLabel("سجل الموظفين")
        title.setStyleSheet(
            f"font-size:15px; font-weight:900; color:{TEXT}; background:transparent;"
        )
        title_box.addWidget(title)

        hint = QLabel("عرض وإدارة جميع الموظفين المسجلين في النظام")
        hint.setStyleSheet(f"font-size:10.5px; color:{TEXT_MUTED}; background:transparent;")
        title_box.addWidget(hint)
        hl.addLayout(title_box)
        hl.addStretch()

        self.chk_inactive = QCheckBox("إظهار الموقوفين")
        self.chk_inactive.setCursor(Qt.PointingHandCursor)
        self.chk_inactive.setStyleSheet(f"""
            QCheckBox {{
                font-size:11.5px;
                color:{TEXT_SEC};
                background:transparent;
                spacing:8px;
                padding:4px;
                font-weight:700;
            }}
            QCheckBox::indicator {{
                width:18px; height:18px;
                border:1.5px solid {BORDER_2};
                border-radius:5px;
                background:white;
            }}
            QCheckBox::indicator:hover {{ border-color:{PRIMARY}; }}
            QCheckBox::indicator:checked {{
                background:{PRIMARY};
                border-color:{PRIMARY};
            }}
        """)
        self.chk_inactive.toggled.connect(self._toggle_show_inactive)
        hl.addWidget(self.chk_inactive)

        self.count_badge = QLabel("0")
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setMinimumWidth(50)
        self.count_badge.setFixedHeight(32)
        self.count_badge.setStyleSheet(f"""
            QLabel {{
                background:{PRIMARY_BG};
                color:{PRIMARY};
                border:1px solid {PRIMARY_BRD};
                border-radius:16px;
                padding:0 15px;
                font-size:11.5px;
                font-weight:900;
            }}
        """)
        hl.addWidget(self.count_badge)
        v.addWidget(head)

        # Table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "الموظف", "القسم", "الأساسي", "الإجمالي",
            "البدلات", "الشيفت", "الحالة", "إجراءات"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background:{SURFACE};
                border:none;
                color:{TEXT};
                font-size:11.5px;
                outline:none;
                selection-background-color:{PRIMARY_BG};
                selection-color:{TEXT};
                gridline-color:transparent;
                font-family:{FONT_FAMILY};
            }}
            QTableWidget::item {{
                padding:8px;
                border-bottom:1px solid {DIVIDER};
            }}
            QTableWidget::item:selected {{
                background:{PRIMARY_BG};
                color:{TEXT};
            }}
            QTableWidget::item:alternate {{
                background:{ROW_ALT};
            }}
            QHeaderView::section {{
                background:{HEADER_BG};
                color:{TEXT_MUTED};
                padding:14px 10px;
                border:none;
                border-bottom:1px solid {BORDER};
                font-weight:900;
                font-size:10px;
                letter-spacing:0.3px;
            }}
            QScrollBar:vertical {{
                width:9px;
                background:transparent;
                margin:4px 2px 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2};
                border-radius:4px;
                min-height:40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background:{TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height:0;
            }}
        """)
        self.table.verticalHeader().setDefaultSectionSize(68)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 170)

        v.addWidget(self.table, 1)
        return card

    # ----------------------------------------------------------
    #                    بطاقة النموذج
    # ----------------------------------------------------------
    def _build_form_card(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background:transparent; border:none; }
            QScrollBar:vertical {
                width:9px; background:transparent; margin:2px 0;
            }
            QScrollBar::handle:vertical {
                background:#cbd5e1; border-radius:4px; min-height:40px;
            }
            QScrollBar::handle:vertical:hover { background:#94a3b8; }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height:0; }
        """)

        card = QFrame()
        card.setObjectName("formCard")
        card.setStyleSheet(f"""
            QFrame#formCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=20, y_offset=4, alpha=25)
        scroll.setWidget(card)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 22, 22, 22)
        v.setSpacing(16)

        # Form header
        head = QFrame()
        head.setObjectName("formHeader")
        head.setStyleSheet(f"""
            QFrame#formHeader {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:0.5 {NAVY_2}, stop:1 {NAVY_3});
                border-radius:14px;
            }}
        """)
        apply_shadow(head, blur=12, y_offset=2, alpha=45)

        hh = QHBoxLayout(head)
        hh.setContentsMargins(18, 14, 18, 14)
        hh.setSpacing(12)

        icon = QLabel("👤")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(46, 46)
        icon.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_DK});
                color:white;
                border-radius:13px;
                font-size:19px;
                font-weight:900;
            }}
        """)
        hh.addWidget(icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        self.form_title = QLabel("موظف جديد")
        self.form_title.setStyleSheet(
            "font-size:15.5px; font-weight:900; color:white; background:transparent;"
        )
        title_box.addWidget(self.form_title)

        self.form_subtitle = QLabel("إضافة سجل موظف جديد")
        self.form_subtitle.setStyleSheet(
            "font-size:10.5px; color:#9db3cf; background:transparent;"
        )
        title_box.addWidget(self.form_subtitle)
        hh.addLayout(title_box, 1)
        v.addWidget(head)

        # ============ Basic Data Section ============
        v.addWidget(self._section("البيانات الأساسية", PRIMARY, "👤"))
        g1 = self._grid()

        self.code = self._input("EMP-001", ltr=True)
        self.name = self._input("الاسم الكامل")
        self.dept = self._input("القسم / الإدارة")
        self.phone = self._input("01xxxxxxxxx", ltr=True)
        self.annual_leave = self._num()
        self.shift_combo = self._combo()

        g1.addWidget(self._field("الكود", self.code), 0, 0)
        g1.addWidget(self._field("الاسم", self.name), 0, 1)
        g1.addWidget(self._field("القسم", self.dept), 1, 0)
        g1.addWidget(self._field("الهاتف", self.phone), 1, 1)
        g1.addWidget(self._field("الشيفت", self.shift_combo), 2, 0)
        g1.addWidget(self._field("رصيد الإجازة", self.annual_leave), 2, 1)
        v.addLayout(g1)

        # ============ Salary Section ============
        v.addWidget(self._section("الراتب والبدلات", SUCCESS, "💰"))
        g2 = self._grid()

        self.base_salary = self._num()
        self.total_salary = self._num()
        self.incentive = self._num()
        self.meal = self._num()
        self.transport = self._num()
        self.expat = self._num()
        self.other = self._num()

        g2.addWidget(self._field("الأساسي", self.base_salary), 0, 0)
        g2.addWidget(self._field("الإجمالي", self.total_salary), 0, 1)
        g2.addWidget(self._field("الحافز", self.incentive), 1, 0)
        g2.addWidget(self._field("بدل وجبة", self.meal), 1, 1)
        g2.addWidget(self._field("بدل مواصلات", self.transport), 2, 0)
        g2.addWidget(self._field("بدل اغتراب", self.expat), 2, 1)
        g2.addWidget(self._field("بدلات أخرى", self.other), 3, 0)
        v.addLayout(g2)

        # ============ Insurance Section ============
        v.addWidget(self._section("التأمينات", INFO, "🛡"))
        g3 = self._grid()
        self.medical = self._num()
        self.social = self._num()
        g3.addWidget(self._field("تأمين طبي", self.medical), 0, 0)
        g3.addWidget(self._field("تأمين اجتماعي", self.social), 0, 1)
        v.addLayout(g3)

        v.addStretch(1)

        # Divider
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER};")
        v.addWidget(line)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(9)

        self.btn_files = QPushButton("📎  الملفات")
        self.btn_files.setFixedHeight(44)
        self.btn_files.setCursor(Qt.PointingHandCursor)
        self.btn_files.setStyleSheet(f"""
            QPushButton {{
                background:{INFO_BG};
                color:{INFO};
                border:1px solid {INFO_BRD};
                border-radius:11px;
                padding:0 18px;
                font-size:11.5px;
                font-weight:800;
            }}
            QPushButton:hover {{
                background:#cffafe;
                border-color:{INFO};
            }}
        """)
        self.btn_files.clicked.connect(self._open_files)
        self.btn_files.setVisible(False)
        btn_row.addWidget(self.btn_files)
        btn_row.addStretch()

        self.btn_cancel = QPushButton("إلغاء")
        self.btn_cancel.setFixedHeight(44)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE};
                color:{TEXT_SEC};
                border:1px solid {BORDER_2};
                border-radius:11px;
                padding:0 22px;
                font-size:11.5px;
                font-weight:800;
            }}
            QPushButton:hover {{
                background:{SURFACE_2};
                border-color:{TEXT_MUTED};
                color:{TEXT};
            }}
        """)
        self.btn_cancel.clicked.connect(self._cancel_form)
        self.btn_cancel.setVisible(False)

        self.btn_save = QPushButton("💾  حفظ الموظف")
        self.btn_save.setFixedHeight(44)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_HOV});
                color:white;
                border:none;
                border-radius:11px;
                padding:0 26px;
                font-size:12.5px;
                font-weight:900;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4d6bff, stop:1 {PRIMARY_HOV});
            }}
            QPushButton:pressed {{
                background:{PRIMARY_DK};
            }}
        """)
        self.btn_save.clicked.connect(self._save)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        v.addLayout(btn_row)

        return scroll

    # ----------------------------------------------------------
    #                    عناصر مساعدة
    # ----------------------------------------------------------
    def _section(self, text, color=PRIMARY, emoji=""):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 8, 0, 0)
        h.setSpacing(9)

        marker = QFrame()
        marker.setFixedSize(4, 20)
        marker.setStyleSheet(f"background:{color}; border-radius:2px;")
        h.addWidget(marker)

        if emoji:
            em = QLabel(emoji)
            em.setStyleSheet("font-size:14px; background:transparent;")
            h.addWidget(em)

        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size:12px; font-weight:900; color:{TEXT}; "
            f"background:transparent; letter-spacing:0.3px;"
        )
        h.addWidget(lbl)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER};")
        h.addWidget(line, 1)
        return w

    def _grid(self):
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(10)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        return g

    def _field(self, label_text, widget):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            f"font-size:10.5px; font-weight:800; color:{TEXT_SEC}; "
            f"background:transparent; letter-spacing:0.2px;"
        )
        v.addWidget(lbl)
        v.addWidget(widget)
        return w

    def _input(self, placeholder="", ltr=False):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(42)
        if ltr:
            inp.setLayoutDirection(Qt.LeftToRight)
            inp.setAlignment(Qt.AlignLeft)
        inp.setStyleSheet(self._input_qss())
        return inp

    def _num(self):
        inp = QLineEdit()
        inp.setValidator(QDoubleValidator(0, 100_000_000, 2))
        inp.setFixedHeight(42)
        inp.setText("0")
        inp.setLayoutDirection(Qt.LeftToRight)
        inp.setAlignment(Qt.AlignLeft)
        inp.setStyleSheet(self._input_qss())
        return inp

    def _input_qss(self):
        return f"""
            QLineEdit {{
                background:{SURFACE_2};
                border:1.5px solid {BORDER};
                border-radius:11px;
                padding:0 14px;
                font-size:12px;
                color:{TEXT};
                selection-background-color:{PRIMARY_BG};
                selection-color:{PRIMARY_DK};
                font-family:{FONT_FAMILY};
            }}
            QLineEdit:hover {{
                background:white;
                border-color:{BORDER_2};
            }}
            QLineEdit:focus {{
                background:white;
                border:1.5px solid {PRIMARY};
            }}
        """

    def _combo(self):
        c = QComboBox()
        c.setFixedHeight(42)
        c.setStyleSheet(f"""
            QComboBox {{
                background:{SURFACE_2};
                border:1.5px solid {BORDER};
                border-radius:11px;
                padding:0 14px;
                font-size:12px;
                color:{TEXT};
            }}
            QComboBox:hover {{
                border-color:{BORDER_2};
                background:white;
            }}
            QComboBox:focus {{
                border:1.5px solid {PRIMARY};
                background:white;
            }}
            QComboBox::drop-down {{
                border:none;
                width:30px;
            }}
            QComboBox::down-arrow {{
                image:none;
                width:0;
                height:0;
                border-left:4px solid transparent;
                border-right:4px solid transparent;
                border-top:5px solid {TEXT_MUTED};
                margin-right:10px;
            }}
            QComboBox QAbstractItemView {{
                background:white;
                border:1px solid {BORDER};
                border-radius:10px;
                padding:6px;
                selection-background-color:{PRIMARY_BG};
                selection-color:{PRIMARY};
                outline:none;
            }}
            QComboBox QAbstractItemView::item {{
                padding:9px 12px;
                border-radius:6px;
                min-height:22px;
            }}
        """)
        return c

    # ========================================================
    #                    Logic Helpers
    # ========================================================
    def _money(self, w):
        try:
            return float(w.text() or 0)
        except ValueError:
            return 0.0

    def _all_inputs(self):
        return [
            self.base_salary, self.total_salary, self.incentive,
            self.medical, self.social, self.meal, self.transport,
            self.expat, self.other, self.annual_leave,
        ]

    def _clear_form(self):
        self.code.clear()
        self.name.clear()
        self.dept.clear()
        self.phone.clear()
        for w in self._all_inputs():
            w.setText("0")
        if self.shift_combo.count():
            self.shift_combo.setCurrentIndex(0)

    def _cancel_form(self):
        self._editing_id = None
        self._clear_form()
        self.form_title.setText("موظف جديد")
        self.form_subtitle.setText("إضافة سجل موظف جديد")
        self.btn_save.setText("💾  حفظ الموظف")
        self.btn_cancel.setVisible(False)
        self.btn_files.setVisible(False)

    # ========================================================
    #                         Load
    # ========================================================
    def _load_shifts(self):
        current = self.shift_combo.currentData()
        self.shift_combo.clear()
        shifts = get_shifts()
        if not shifts:
            self.shift_combo.addItem("— لا توجد شيفتات —", None)
            return
        for s in shifts:
            type_ar = "صباحي" if s["shift_type"] == "morning" else "مسائي"
            self.shift_combo.addItem(f"{s['name']}  ·  {type_ar}", s["id"])
        if current is not None:
            idx = self.shift_combo.findData(current)
            if idx >= 0:
                self.shift_combo.setCurrentIndex(idx)

    def _load_employees(self):
        self._all_rows = get_employees(include_inactive=self._show_inactive)
        self._render_rows(self._all_rows)

        total = len(self._all_rows)
        active = sum(1 for r in self._all_rows if (r["active"] or 0) == 1)
        inactive = total - active
        departments = len({
            (r["department"] or "").strip()
            for r in self._all_rows
            if (r["department"] or "").strip()
        })

        self.count_badge.setText(str(total))
        self.count_inline.setText(f"{total} موظف")
        self.stat_total._value_label.setText(str(total))
        self.stat_active._value_label.setText(str(active))
        self.stat_inactive._value_label.setText(str(inactive))
        self.stat_departments._value_label.setText(str(departments))

    def _toggle_show_inactive(self, checked):
        self._show_inactive = checked
        self._load_employees()

    # ========================================================
    #                    Render Rows
    # ========================================================
    def _render_rows(self, rows):
        self.table.setRowCount(0)

        for i, r in enumerate(rows):
            self.table.insertRow(i)
            is_active = (r["active"] or 0) == 1

            # Employee cell (name + code)
            emp = QWidget()
            emp.setStyleSheet("background:transparent;")
            ev = QVBoxLayout(emp)
            ev.setContentsMargins(6, 3, 6, 3)
            ev.setSpacing(3)

            n = QLabel(r["name"] or "—")
            n.setStyleSheet(
                f"font-size:12.5px; font-weight:800; "
                f"color:{TEXT if is_active else TEXT_MUTED}; background:transparent;"
            )
            c = QLabel(r["code"] or "")
            c.setStyleSheet(
                f"font-size:10.5px; color:{TEXT_MUTED}; background:transparent;"
            )
            ev.addWidget(n)
            ev.addWidget(c)
            self.table.setCellWidget(i, 0, emp)

            allowances = (
                (r["meal_allowance"] or 0)
                + (r["transport_allowance"] or 0)
                + (r["expat_allowance"] or 0)
                + (r["other_allowances"] or 0)
            )

            cells = [
                (1, r["department"] or "—", TEXT_SEC),
                (2, f"{(r['base_salary'] or 0):,.0f}", TEXT),
                (3, f"{(r['total_salary'] or 0):,.0f}", SUCCESS),
                (4, f"{allowances:,.0f}", TEXT),
                (5, r["shift_name"] or "—", TEXT_SEC),
            ]

            for col, val, color in cells:
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor(color if is_active else TEXT_MUTED))
                self.table.setItem(i, col, item)

            # Status badge
            status = QWidget()
            status.setStyleSheet("background:transparent;")
            sl = QHBoxLayout(status)
            sl.setContentsMargins(0, 0, 0, 0)
            sl.setAlignment(Qt.AlignCenter)

            badge = QLabel("●  نشط" if is_active else "●  موقوف")
            badge.setAlignment(Qt.AlignCenter)
            if is_active:
                badge.setStyleSheet(f"""
                    background:{SUCCESS_BG};
                    color:{SUCCESS};
                    border:1px solid {SUCCESS_BRD};
                    padding:6px 14px;
                    border-radius:12px;
                    font-weight:800;
                    font-size:10.5px;
                """)
            else:
                badge.setStyleSheet(f"""
                    background:{DANGER_BG};
                    color:{DANGER};
                    border:1px solid {DANGER_BRD};
                    padding:6px 14px;
                    border-radius:12px;
                    font-weight:800;
                    font-size:10.5px;
                """)
            sl.addWidget(badge)
            self.table.setCellWidget(i, 6, status)

            # Actions
            actions = QWidget()
            actions.setStyleSheet("background:transparent;")
            al = QHBoxLayout(actions)
            al.setContentsMargins(2, 0, 2, 0)
            al.setSpacing(5)
            al.setAlignment(Qt.AlignCenter)

            btn_edit = self._icon_btn("✎", PRIMARY, PRIMARY_BG, PRIMARY_BRD, "تعديل الموظف")
            btn_edit.clicked.connect(lambda _, eid=r["id"]: self._edit(eid))

            btn_files = self._icon_btn("📎", INFO, INFO_BG, INFO_BRD, "ملفات الموظف")
            btn_files.clicked.connect(lambda _, eid=r["id"]: self._open_files_by_id(eid))

            if is_active:
                btn_toggle = self._icon_btn("⏸", WARNING, WARNING_BG, WARNING_BRD, "إيقاف الموظف")
            else:
                btn_toggle = self._icon_btn("▶", SUCCESS, SUCCESS_BG, SUCCESS_BRD, "تفعيل الموظف")
            btn_toggle.clicked.connect(lambda _, eid=r["id"]: self._toggle_status(eid))

            btn_del = self._icon_btn("✕", DANGER, DANGER_BG, DANGER_BRD, "حذف الموظف")
            btn_del.clicked.connect(lambda _, eid=r["id"]: self._delete(eid))

            al.addWidget(btn_edit)
            al.addWidget(btn_files)
            al.addWidget(btn_toggle)
            al.addWidget(btn_del)
            self.table.setCellWidget(i, 7, actions)

    def _icon_btn(self, text, color, hover_bg, border_color, tooltip=""):
        btn = QPushButton(text)
        btn.setFixedSize(34, 32)
        btn.setCursor(Qt.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE};
                color:{color};
                border:1px solid {BORDER_2};
                border-radius:9px;
                font-size:12.5px;
                font-weight:900;
            }}
            QPushButton:hover {{
                background:{hover_bg};
                border-color:{border_color};
            }}
            QPushButton:pressed {{
                background:{hover_bg};
            }}
        """)
        return btn

    def _filter_table(self, text):
        text = text.strip().lower()
        if not text:
            self._render_rows(self._all_rows)
            return
        filtered = [
            r for r in self._all_rows
            if text in (r["name"] or "").lower()
            or text in (r["code"] or "").lower()
            or text in (r["department"] or "").lower()
        ]
        self._render_rows(filtered)

    # ========================================================
    #                         Actions
    # ========================================================
    def _save(self):
        if not self.code.text().strip():
            QMessageBox.warning(self, "تنبيه", "أدخل كود الموظف")
            self.code.setFocus()
            return

        if not self.name.text().strip():
            QMessageBox.warning(self, "تنبيه", "أدخل اسم الموظف")
            self.name.setFocus()
            return

        if self.shift_combo.currentData() is None:
            QMessageBox.warning(self, "تنبيه", "أضف شيفت أولاً من صفحة الشيفتات")
            return

        data = {
            "code": self.code.text().strip(),
            "name": self.name.text().strip(),
            "department": self.dept.text().strip(),
            "phone": self.phone.text().strip(),
            "base_salary": self._money(self.base_salary),
            "total_salary": self._money(self.total_salary),
            "incentive": self._money(self.incentive),
            "medical_insurance": self._money(self.medical),
            "social_insurance": self._money(self.social),
            "meal_allowance": self._money(self.meal),
            "transport_allowance": self._money(self.transport),
            "expat_allowance": self._money(self.expat),
            "other_allowances": self._money(self.other),
            "annual_leave_balance": self._money(self.annual_leave),
            "shift_id": self.shift_combo.currentData(),
        }

        try:
            if self._editing_id is None:
                ok, msg = add_employee(data)
                if ok:
                    get_employee_folder(data["code"])
            else:
                ok, msg = update_employee(self._editing_id, data)
        except Exception as e:
            QMessageBox.critical(self, "خطأ غير متوقع", str(e))
            return

        if ok:
            QMessageBox.information(self, "تم", msg)
            self._cancel_form()
            self._load_employees()
        else:
            QMessageBox.critical(self, "خطأ", msg)

    def _edit(self, emp_id):
        try:
            r = get_employee(emp_id)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل جلب الموظف: {e}")
            return

        if not r:
            return

        self._editing_id = emp_id
        self.code.setText(r["code"] or "")
        self.name.setText(r["name"] or "")
        self.dept.setText(r["department"] or "")
        self.phone.setText(r["phone"] or "")
        self.base_salary.setText(str(r["base_salary"] or 0))
        self.total_salary.setText(str(r["total_salary"] or 0))
        self.incentive.setText(str(r["incentive"] or 0))
        self.medical.setText(str(r["medical_insurance"] or 0))
        self.social.setText(str(r["social_insurance"] or 0))
        self.meal.setText(str(r["meal_allowance"] or 0))
        self.transport.setText(str(r["transport_allowance"] or 0))
        self.expat.setText(str(r["expat_allowance"] or 0))
        self.other.setText(str(r["other_allowances"] or 0))
        self.annual_leave.setText(str(r["annual_leave_balance"] or 0))

        if r["shift_id"]:
            idx = self.shift_combo.findData(r["shift_id"])
            if idx >= 0:
                self.shift_combo.setCurrentIndex(idx)

        self.form_title.setText("✎  تعديل موظف")
        self.form_subtitle.setText(f"{r['name']}  ·  {r['code']}")
        self.btn_save.setText("💾  حفظ التعديلات")
        self.btn_cancel.setVisible(True)
        self.btn_files.setVisible(True)

    def _toggle_status(self, emp_id):
        r = get_employee(emp_id)
        if not r:
            return
        is_active = (r["active"] or 0) == 1
        action = "إيقاف" if is_active else "تفعيل"

        msg = QMessageBox(self)
        msg.setWindowTitle(f"{action} الموظف")
        msg.setText(f"هل تريد {action} الموظف «{r['name']}»؟")
        if not is_active:
            msg.setInformativeText("سيظهر الموظف في القوائم مرة أخرى.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.button(QMessageBox.Yes).setText(action)
        msg.button(QMessageBox.No).setText("إلغاء")

        if msg.exec() == QMessageBox.Yes:
            ok, m = toggle_employee_status(emp_id)
            if ok:
                self._load_employees()

    def _delete(self, emp_id):
        r = get_employee(emp_id)
        if not r:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("تأكيد الحذف")
        msg.setText(f"حذف الموظف «{r['name']}» نهائياً؟")
        msg.setInformativeText("⚠️ سيتم حذف الموظف من النظام، لكن ملفاته ستبقى في الفولدر.")
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.button(QMessageBox.Yes).setText("حذف نهائي")
        msg.button(QMessageBox.No).setText("إلغاء")
        msg.setDefaultButton(QMessageBox.No)

        if msg.exec() == QMessageBox.Yes:
            delete_employee(emp_id)
            self._load_employees()

    # ========================================================
    #                    Files Management
    # ========================================================
    def _open_files(self):
        if self._editing_id is None:
            return
        self._open_files_by_id(self._editing_id)

    def _open_files_by_id(self, emp_id):
        r = get_employee(emp_id)
        if not r:
            return
        dlg = EmployeeFilesDialog(emp_id, r["name"], r["code"], self)
        dlg.exec()


# ============================================================
#           Dialog لإدارة ملفات الموظف
# ============================================================
class EmployeeFilesDialog(QDialog):
    def __init__(self, employee_id, employee_name, employee_code, parent=None):
        super().__init__(parent)
        self.employee_id = employee_id
        self.employee_name = employee_name
        self.employee_code = employee_code
        self.folder = get_employee_folder(employee_code)

        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle(f"ملفات الموظف - {employee_name}")
        self.setMinimumSize(760, 600)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        # Header
        head = QFrame()
        head.setObjectName("filesHeader")
        head.setStyleSheet(f"""
            QFrame#filesHeader {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:0.5 {NAVY_2}, stop:1 {NAVY_3});
                border-radius:16px;
            }}
        """)
        apply_shadow(head, blur=20, y_offset=4, alpha=60)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 18, 22, 18)
        hl.setSpacing(14)

        icon = QLabel("📁")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(50, 50)
        icon.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_DK});
                border:1px solid {NAVY_ACCENT};
                border-radius:14px;
                font-size:22px;
            }}
        """)
        hl.addWidget(icon)

        tbox = QVBoxLayout()
        tbox.setSpacing(3)

        title = QLabel(f"ملفات: {self.employee_name}")
        title.setStyleSheet("font-size:16px; font-weight:900; color:white; background:transparent;")
        tbox.addWidget(title)

        sub = QLabel("إدارة مستندات وملفات الموظف")
        sub.setStyleSheet("font-size:10.5px; color:#9db3cf; background:transparent;")
        tbox.addWidget(sub)
        hl.addLayout(tbox)
        hl.addStretch()

        code_lbl = QLabel(f"كود: {self.employee_code}")
        code_lbl.setStyleSheet(f"""
            background: rgba(59, 91, 253, 0.15); color:#c7d2fe;
            padding:7px 15px; border-radius:13px;
            font-size:11.5px; font-weight:800;
            border:1px solid rgba(59, 91, 253, 0.35);
        """)
        hl.addWidget(code_lbl)
        v.addWidget(head)

        # Folder path
        path_box = QFrame()
        path_box.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:11px;
            }}
        """)
        pl = QHBoxLayout(path_box)
        pl.setContentsMargins(15, 11, 15, 11)
        pl.setSpacing(9)

        folder_icon = QLabel("📂")
        folder_icon.setStyleSheet("font-size:15px; background:transparent;")
        pl.addWidget(folder_icon)

        path_lbl = QLabel(f"{self.folder.absolute()}")
        path_lbl.setStyleSheet(
            f"font-size:11.5px; color:{TEXT_SEC}; background:transparent; "
            f"font-family: Consolas, monospace;"
        )
        path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        pl.addWidget(path_lbl, 1)
        v.addWidget(path_box)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(10)

        btn_upload = QPushButton("📤  رفع ملفات")
        btn_upload.setFixedHeight(42)
        btn_upload.setCursor(Qt.PointingHandCursor)
        btn_upload.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_HOV});
                color:white; border:none;
                border-radius:11px; padding:0 22px;
                font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4d6bff, stop:1 {PRIMARY_HOV});
            }}
        """)
        btn_upload.clicked.connect(self._upload)
        actions.addWidget(btn_upload)

        btn_scan = QPushButton("🖨  مسح ضوئي")
        btn_scan.setFixedHeight(42)
        btn_scan.setCursor(Qt.PointingHandCursor)
        btn_scan.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                color:white; border:none;
                border-radius:11px; padding:0 22px;
                font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{ background:{SUCCESS_HOV}; }}
        """)
        btn_scan.clicked.connect(self._scan)
        actions.addWidget(btn_scan)

        actions.addStretch()

        btn_open_folder = QPushButton("📂  فتح المجلد")
        btn_open_folder.setFixedHeight(42)
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1px solid {BORDER_2}; border-radius:11px;
                padding:0 20px; font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{
                background:{SURFACE_2};
                border-color:{TEXT_MUTED};
                color:{TEXT};
            }}
        """)
        btn_open_folder.clicked.connect(self._open_folder)
        actions.addWidget(btn_open_folder)

        v.addLayout(actions)

        # Files list
        self.list = QListWidget()
        self.list.setStyleSheet(f"""
            QListWidget {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:13px;
                padding:10px;
                font-size:12.5px;
                color:{TEXT};
                outline:none;
            }}
            QListWidget::item {{
                padding:14px 16px;
                border-radius:9px;
                border-bottom:1px solid {DIVIDER};
                margin:3px 0;
            }}
            QListWidget::item:selected {{
                background:{PRIMARY_BG};
                color:{PRIMARY_DK};
                border:1px solid {PRIMARY_BRD};
            }}
            QListWidget::item:hover {{
                background:{SURFACE_2};
            }}
        """)
        self.list.itemDoubleClicked.connect(self._open_file)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._file_menu)
        v.addWidget(self.list, 1)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        btn_close = QPushButton("إغلاق")
        btn_close.setFixedHeight(40)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1px solid {BORDER_2}; border-radius:11px;
                padding:0 28px; font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{
                background:{SURFACE_2};
                border-color:{TEXT_MUTED};
            }}
        """)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        v.addLayout(footer)

    def _refresh_list(self):
        self.list.clear()
        files = get_employee_files(self.employee_id)
        if not files:
            item = QListWidgetItem("— لا توجد ملفات بعد —")
            item.setForeground(QColor(TEXT_MUTED))
            item.setFlags(Qt.NoItemFlags)
            item.setTextAlignment(Qt.AlignCenter)
            self.list.addItem(item)
            return

        for f in files:
            size_kb = (f["file_size"] or 0) / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
            text = f"📄   {f['file_name']}     ·     {size_str}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, dict(f))
            self.list.addItem(item)

    def _upload(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "اختر ملفات لرفعها", "",
            "كل الملفات (*.*);;صور (*.png *.jpg *.jpeg *.bmp *.gif);;PDF (*.pdf)"
        )
        if not files:
            return

        count = 0
        for src in files:
            try:
                src_path = Path(src)
                dst = self.folder / src_path.name
                base = dst.stem
                suffix = dst.suffix
                counter = 1
                while dst.exists():
                    dst = self.folder / f"{base}_{counter}{suffix}"
                    counter += 1
                shutil.copy2(src, dst)
                add_employee_file(
                    employee_id=self.employee_id,
                    file_name=dst.name,
                    file_path=str(dst),
                    file_type=suffix,
                    file_size=dst.stat().st_size,
                )
                count += 1
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"فشل رفع {src}:\n{e}")

        if count:
            QMessageBox.information(self, "تم", f"تم رفع {count} ملف ✅")
            self._refresh_list()

    def _scan(self):
        try:
            scanner = ScanDialog(self.folder, self)
            if scanner.exec() == QDialog.Accepted and scanner.saved_file:
                p = Path(scanner.saved_file)
                add_employee_file(
                    employee_id=self.employee_id,
                    file_name=p.name,
                    file_path=str(p),
                    file_type=p.suffix,
                    file_size=p.stat().st_size,
                )
                self._refresh_list()
        except Exception as e:
            QMessageBox.critical(self, "خطأ في السكانر", str(e))

    def _open_file(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        path = data.get("file_path")
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "خطأ", "الملف غير موجود")

    def _file_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.UserRole)
        if not data:
            return

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.RightToLeft)
        menu.setStyleSheet(f"""
            QMenu {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:10px;
                padding:6px;
            }}
            QMenu::item {{
                padding:9px 24px 9px 16px;
                border-radius:7px;
                font-size:12px;
                color:{TEXT};
            }}
            QMenu::item:selected {{
                background:{PRIMARY_BG};
                color:{PRIMARY_DK};
            }}
            QMenu::separator {{
                height:1px;
                background:{DIVIDER};
                margin:5px 8px;
            }}
        """)

        act_open = QAction("📂  فتح", self)
        act_open.triggered.connect(lambda: self._open_file(item))

        act_del = QAction("🗑  حذف", self)
        act_del.triggered.connect(lambda: self._delete_file(data))

        menu.addAction(act_open)
        menu.addSeparator()
        menu.addAction(act_del)
        menu.exec(self.list.mapToGlobal(pos))

    def _delete_file(self, data):
        if QMessageBox.question(
            self, "تأكيد", f"حذف الملف «{data['file_name']}»؟"
        ) != QMessageBox.Yes:
            return

        path = delete_employee_file(data["id"])
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        self._refresh_list()

    def _open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.folder.absolute())))


# ============================================================
#           Dialog للمسح الضوئي
# ============================================================
class ScanDialog(QDialog):
    def __init__(self, target_folder: Path, parent=None):
        super().__init__(parent)
        self.target_folder = target_folder
        self.saved_file = None
        self.selected_path = None

        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("المسح الضوئي")
        self.setMinimumSize(620, 560)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")

        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

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
        hl.setContentsMargins(20, 16, 20, 16)
        hl.setSpacing(14)

        icon = QLabel("🖨")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(48, 48)
        icon.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_DK});
                border:1px solid {NAVY_ACCENT};
                border-radius:13px;
                font-size:21px;
            }}
        """)
        hl.addWidget(icon)

        tbox = QVBoxLayout()
        tbox.setSpacing(3)

        title = QLabel("المسح الضوئي / إضافة صورة")
        title.setStyleSheet("font-size:16px; font-weight:900; color:white; background:transparent;")
        tbox.addWidget(title)

        sub = QLabel("اختر صورة من الجهاز أو استخدم السكانر")
        sub.setStyleSheet("font-size:10.5px; color:#9db3cf; background:transparent;")
        tbox.addWidget(sub)
        hl.addLayout(tbox, 1)
        v.addWidget(head)

        # Info box
        info_box = QFrame()
        info_box.setStyleSheet(f"""
            QFrame {{
                background:{INFO_BG};
                border:1px solid {INFO_BRD};
                border-radius:11px;
            }}
        """)
        il = QHBoxLayout(info_box)
        il.setContentsMargins(15, 12, 15, 12)
        il.setSpacing(10)

        info_icon = QLabel("💡")
        info_icon.setStyleSheet("font-size:17px; background:transparent;")
        il.addWidget(info_icon)

        info = QLabel(
            "لسكانر حقيقي: ثبّت <b>pywin32</b> + <b>pillow</b> على ويندوز، "
            "أو <b>python-sane</b> على لينكس/ماك."
        )
        info.setStyleSheet(f"font-size:11.5px; color:{INFO}; background:transparent;")
        info.setWordWrap(True)
        il.addWidget(info, 1)
        v.addWidget(info_box)

        # Preview
        self.preview = QLabel("— لا توجد صورة —")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(240)
        self.preview.setStyleSheet(f"""
            background:{SURFACE};
            border:2px dashed {BORDER_2};
            border-radius:14px;
            color:{TEXT_MUTED};
            font-size:13px;
            font-weight:700;
        """)
        v.addWidget(self.preview, 1)

        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(10)

        btn_pick = QPushButton("📂  اختر صورة")
        btn_pick.setFixedHeight(44)
        btn_pick.setCursor(Qt.PointingHandCursor)
        btn_pick.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1px solid {BORDER_2}; border-radius:11px;
                padding:0 22px; font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{
                background:{SURFACE_2};
                border-color:{TEXT_MUTED};
                color:{TEXT};
            }}
        """)
        btn_pick.clicked.connect(self._pick_image)
        btns.addWidget(btn_pick)

        btn_scan_device = QPushButton("🖨  مسح من السكانر")
        btn_scan_device.setFixedHeight(44)
        btn_scan_device.setCursor(Qt.PointingHandCursor)
        btn_scan_device.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_HOV});
                color:white; border:none;
                border-radius:11px; padding:0 22px;
                font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4d6bff, stop:1 {PRIMARY_HOV});
            }}
        """)
        btn_scan_device.clicked.connect(self._scan_device)
        btns.addWidget(btn_scan_device)

        btns.addStretch()

        btn_save = QPushButton("💾  حفظ")
        btn_save.setFixedHeight(44)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                color:white; border:none;
                border-radius:11px; padding:0 28px;
                font-weight:900; font-size:12.5px;
            }}
            QPushButton:hover {{ background:{SUCCESS_HOV}; }}
        """)
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)

        btn_close = QPushButton("إلغاء")
        btn_close.setFixedHeight(44)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{TEXT_SEC};
                border:1px solid {BORDER_2}; border-radius:11px;
                padding:0 22px; font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{
                background:{SURFACE_2};
                border-color:{TEXT_MUTED};
            }}
        """)
        btn_close.clicked.connect(self.reject)
        btns.addWidget(btn_close)

        v.addLayout(btns)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "اختر صورة", "",
            "صور (*.png *.jpg *.jpeg *.bmp *.tiff);;كل الملفات (*.*)"
        )
        if path:
            self.selected_path = path
            self._show_preview(path)

    def _show_preview(self, path):
        try:
            from PySide6.QtGui import QPixmap
            pix = QPixmap(path)
            if not pix.isNull():
                scaled = pix.scaled(500, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview.setPixmap(scaled)
                self.preview.setStyleSheet(f"""
                    background:{SURFACE};
                    border:1px solid {BORDER};
                    border-radius:14px;
                """)
            else:
                self.preview.setText("⚠️ تعذر تحميل الصورة")
        except Exception as e:
            self.preview.setText(f"⚠️ {e}")

    def _scan_device(self):
        try:
            import win32com.client
            wia = win32com.client.Dispatch("WIA.CommonDialog")
            image = wia.ShowAcquireImage()
            if image:
                temp_path = self.target_folder / "scan_temp.jpg"
                img_bytes = image.FileData.BinaryData
                with open(temp_path, "wb") as f:
                    f.write(img_bytes)
                self.selected_path = str(temp_path)
                self._show_preview(str(temp_path))
                QMessageBox.information(self, "تم", "تم المسح الضوئي ✅")
                return
        except ImportError:
            pass
        except Exception as e:
            QMessageBox.warning(
                self, "تنبيه",
                f"لم يتم العثور على سكانر أو المكتبات المطلوبة.\n\n"
                f"لتشغيل السكانر:\n"
                f"• pip install pywin32 pillow  (ويندوز)\n"
                f"• pip install python-sane pillow  (لينكس)\n\n"
                f"تفاصيل: {e}"
            )
            return

        QMessageBox.information(
            self, "معلومة",
            "مكتبات السكانر غير مثبّتة.\n\n"
            "ثبّت:\n"
            "pip install pywin32 pillow\n\n"
            "أو استخدم «اختر صورة» حالياً."
        )

    def _save(self):
        if not self.selected_path:
            QMessageBox.warning(self, "تنبيه", "اختر صورة أو امسح ضوئياً أولاً")
            return
        try:
            src = Path(self.selected_path)
            if src.parent != self.target_folder:
                dst = self.target_folder / src.name
                base = dst.stem
                suffix = dst.suffix
                counter = 1
                while dst.exists():
                    dst = self.target_folder / f"{base}_{counter}{suffix}"
                    counter += 1
                shutil.copy2(src, dst)
            else:
                dst = src
            self.saved_file = str(dst)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الحفظ: {e}")