from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QGridLayout, QScrollArea,
    QAbstractItemView, QFileDialog, QCheckBox, QDialog,
    QListWidget, QListWidgetItem, QMenu, QStackedWidget
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
#     نظام ألوان مسطح وهادئ
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
WARNING_BG  = "#fbf3e4"
WARNING_BRD = "#e6cf9f"

INFO        = "#2a6f8f"
INFO_BG     = "#e9f2f6"
INFO_BRD    = "#b5d2df"

PURPLE      = "#5f4b8b"
PURPLE_BG   = "#efecf5"
PURPLE_BRD  = "#cfc6e0"

ROW_ALT     = "#f8f9fa"
HEADER_BG   = "#f1f3f5"

FONT_FAMILY = "Segoe UI, Tahoma, Arial, sans-serif"
RADIUS = "4px"

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def get_employee_folder(code: str) -> Path:
    folder = UPLOAD_DIR / code
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ============================================================
#                     Helpers (Styles)
# ============================================================
def _card_style(object_name):
    return f"""
        QFrame#{object_name} {{
            background:{SURFACE};
            border:1px solid {BORDER};
            border-radius:{RADIUS};
        }}
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


def _success_btn_style(size=12):
    return f"""
        QPushButton {{
            background:{SUCCESS}; color:white;
            border:1px solid {SUCCESS}; border-radius:{RADIUS};
            padding:0 18px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ background:{SUCCESS_HOV}; border-color:{SUCCESS_HOV}; }}
        QPushButton:pressed {{ background:#1f5f3c; }}
    """


def _badge_style(color, bg, brd, size=11, pad="3px 10px"):
    return f"""
        QLabel {{
            background:{bg}; color:{color};
            border:1px solid {brd}; padding:{pad};
            border-radius:3px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
    """


def _input_qss():
    return f"""
        QLineEdit {{
            background:{SURFACE}; border:1px solid {BORDER_2};
            border-radius:{RADIUS}; padding:0 12px;
            font-size:12.5px; color:{TEXT};
            selection-background-color:{PRIMARY_BG};
            selection-color:{PRIMARY_DK};
            font-family:{FONT_FAMILY};
        }}
        QLineEdit:hover {{ border-color:{TEXT_MUTED}; }}
        QLineEdit:focus {{ border:1px solid {PRIMARY}; }}
    """


def _scroll_qss():
    return f"""
        QScrollArea {{ background:transparent; border:none; }}
        QScrollBar:vertical {{
            width:10px; background:{SURFACE_3}; margin:0;
        }}
        QScrollBar::handle:vertical {{
            background:{BORDER_2}; border-radius:2px;
            min-height:40px; margin:2px;
        }}
        QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{ height:0; }}
    """


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

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"QStackedWidget {{ background:{BG}; }}")

        self.list_page = self._build_list_page()
        self.form_page = self._build_form_page()

        self.stack.addWidget(self.list_page)
        self.stack.addWidget(self.form_page)

        root.addWidget(self.stack, 1)

    # ----------------------------------------------------------
    #                       TOPBAR
    # ----------------------------------------------------------
    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("employeeTopbar")
        bar.setFixedHeight(58)
        bar.setStyleSheet(f"""
            QFrame#employeeTopbar {{
                background:{SURFACE};
                border:none;
                border-bottom:1px solid {BORDER};
            }}
        """)

        h = QHBoxLayout(bar)
        h.setContentsMargins(24, 0, 24, 0)
        h.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        title = QLabel("إدارة الموظفين")
        title.setStyleSheet(f"""
            QLabel {{
                color:{TEXT}; font-size:15px; font-weight:700;
                background:transparent; font-family:{FONT_FAMILY};
                border:none;
            }}
        """)
        title_box.addWidget(title)

        subtitle = QLabel("إدارة بيانات العاملين والرواتب والحالة الوظيفية")
        subtitle.setStyleSheet(
            f"QLabel {{ color:{TEXT_MUTED}; font-size:11px; background:transparent; "
            f"font-family:{FONT_FAMILY}; border:none; }}"
        )
        title_box.addWidget(subtitle)
        h.addLayout(title_box)
        h.addStretch()

        self.count_inline = QLabel("0 موظف")
        self.count_inline.setAlignment(Qt.AlignCenter)
        self.count_inline.setMinimumWidth(90)
        self.count_inline.setFixedHeight(28)
        self.count_inline.setStyleSheet(f"""
            QLabel {{
                background:{SURFACE_3};
                color:{TEXT_SEC};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
                padding:0 14px;
                font-size:11.5px;
                font-weight:600;
                font-family:{FONT_FAMILY};
            }}
        """)
        h.addWidget(self.count_inline)
        return bar

    # ----------------------------------------------------------
    #               صفحة القائمة (الإحصائيات + الجدول)
    # ----------------------------------------------------------
    def _build_list_page(self):
        page = QWidget()
        page.setObjectName("listPage")
        page.setStyleSheet(f"QWidget#listPage {{ background:{BG}; }}")
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 20, 24, 24)
        v.setSpacing(16)
        v.addWidget(self._build_stats())
        v.addWidget(self._build_table_card(), 1)
        return page

    def _build_stats(self):
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.stat_total = self._stat_card(
            "إجمالي الموظفين", "0",
            PRIMARY, PRIMARY_BG, PRIMARY_BRD, "سجل مسجّل"
        )
        self.stat_active = self._stat_card(
            "الموظفون النشطون", "0",
            SUCCESS, SUCCESS_BG, SUCCESS_BRD, "على رأس العمل"
        )
        self.stat_inactive = self._stat_card(
            "الموقوفون", "0",
            WARNING, WARNING_BG, WARNING_BRD, "موقوف مؤقتاً"
        )
        self.stat_departments = self._stat_card(
            "الأقسام", "0",
            PURPLE, PURPLE_BG, PURPLE_BRD, "قسم/إدارة"
        )

        grid.addWidget(self.stat_total, 0, 0)
        grid.addWidget(self.stat_active, 0, 1)
        grid.addWidget(self.stat_inactive, 0, 2)
        grid.addWidget(self.stat_departments, 0, 3)

        for col in range(4):
            grid.setColumnStretch(col, 1)
        return wrap

    def _stat_card(self, title, value, color, soft, border_color, unit):
        card = QFrame()
        card.setObjectName("statCard")
        card.setMinimumHeight(88)
        card.setStyleSheet(f"""
            QFrame#statCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
            QFrame#statCard:hover {{
                border:1px solid {border_color};
            }}
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; font-weight:600; "
            f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
        )
        top.addWidget(lbl)
        top.addStretch()

        un = QLabel(unit)
        un.setStyleSheet(_badge_style(color, soft, border_color, size=10, pad="2px 8px"))
        top.addWidget(un)

        v.addLayout(top)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:24px; color:{TEXT}; font-weight:700; "
            f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
        )
        v.addWidget(val)
        v.addStretch()

        card._value_label = val
        return card

    # ----------------------------------------------------------
    #              بطاقة الجدول (بعرض كامل)
    # ----------------------------------------------------------
    def _build_table_card(self):
        card = QFrame()
        card.setObjectName("tableCard")
        card.setStyleSheet(_card_style("tableCard"))

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header bar with title + search + filters + add button
        head = QFrame()
        head.setFixedHeight(64)
        head.setObjectName("tableHead")
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
        hl.setSpacing(14)

        # Title
        tbox = QVBoxLayout()
        tbox.setSpacing(1)

        title = QLabel("سجل الموظفين")
        title.setStyleSheet(
            f"font-size:13.5px; font-weight:700; color:{TEXT}; "
            f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
        )
        tbox.addWidget(title)

        hint = QLabel("عرض وإدارة جميع الموظفين المسجلين في النظام")
        hint.setStyleSheet(
            f"font-size:10.5px; color:{TEXT_MUTED}; background:transparent; "
            f"font-family:{FONT_FAMILY}; border:none;"
        )
        tbox.addWidget(hint)
        hl.addLayout(tbox)
        hl.addStretch()

        # Search
        search = QFrame()
        search.setFixedSize(280, 36)
        search.setObjectName("topSearch")
        search.setStyleSheet(f"""
            QFrame#topSearch {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
            QFrame#topSearch:hover {{ border:1px solid {BORDER_2}; }}
        """)
        sh = QHBoxLayout(search)
        sh.setContentsMargins(12, 0, 12, 0)
        sh.setSpacing(8)

        icon = QLabel("⌕")
        icon.setStyleSheet(
            f"font-size:16px; color:{TEXT_MUTED}; background:transparent; "
            f"font-weight:600; border:none;"
        )
        sh.addWidget(icon)

        self.search = QLineEdit()
        self.search.setPlaceholderText("ابحث بالاسم أو الكود أو القسم...")
        self.search.setFrame(False)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background:transparent; border:none; padding:0;
                color:{TEXT}; font-size:12.5px;
                font-family:{FONT_FAMILY};
            }}
        """)
        self.search.textChanged.connect(self._filter_table)
        sh.addWidget(self.search, 1)
        hl.addWidget(search)

        # Show inactive checkbox
        self.chk_inactive = QCheckBox("إظهار الموقوفين")
        self.chk_inactive.setCursor(Qt.PointingHandCursor)
        self.chk_inactive.setStyleSheet(f"""
            QCheckBox {{
                font-size:11.5px; color:{TEXT_SEC};
                background:transparent; spacing:7px;
                padding:4px; font-weight:600;
                font-family:{FONT_FAMILY};
            }}
            QCheckBox::indicator {{
                width:15px; height:15px;
                border:1px solid {BORDER_2};
                border-radius:3px;
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

        # Count badge
        self.count_badge = QLabel("0")
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setMinimumWidth(44)
        self.count_badge.setFixedHeight(26)
        self.count_badge.setStyleSheet(f"""
            QLabel {{
                background:{SURFACE_3}; color:{TEXT_SEC};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
                padding:0 12px;
                font-size:11.5px; font-weight:600;
                font-family:{FONT_FAMILY};
            }}
        """)
        hl.addWidget(self.count_badge)

        # Add new button
        btn_add = QPushButton("+  موظف جديد")
        btn_add.setFixedHeight(36)
        btn_add.setMinimumWidth(140)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(_primary_btn_style(12))
        btn_add.clicked.connect(self._new_employee)
        hl.addWidget(btn_add)

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
                font-size:12px;
                outline:none;
                selection-background-color:{PRIMARY_BG};
                selection-color:{TEXT};
                gridline-color:{DIVIDER};
                font-family:{FONT_FAMILY};
                alternate-background-color:{ROW_ALT};
            }}
            QTableWidget::item {{
                padding:8px;
                border-bottom:1px solid {DIVIDER};
            }}
            QTableWidget::item:selected {{
                background:{PRIMARY_BG};
                color:{TEXT};
            }}
            QTableWidget::item:hover {{ background:{SURFACE_2}; }}
            QHeaderView::section {{
                background:{HEADER_BG};
                color:{TEXT_SEC};
                padding:10px 8px;
                border:none;
                border-bottom:1px solid {BORDER_2};
                border-left:1px solid {DIVIDER};
                font-weight:700;
                font-size:11px;
                font-family:{FONT_FAMILY};
            }}
            QScrollBar:vertical {{
                width:10px;
                background:{SURFACE_3};
                margin:0;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2};
                border-radius:2px;
                min-height:40px;
                margin:2px;
            }}
            QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        self.table.verticalHeader().setDefaultSectionSize(58)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 170)

        v.addWidget(self.table, 1)
        return card

    # ----------------------------------------------------------
    #              صفحة النموذج (كاملة)
    # ----------------------------------------------------------
    def _build_form_page(self):
        page = QWidget()
        page.setObjectName("formPage")
        page.setStyleSheet(f"QWidget#formPage {{ background:{BG}; }}")
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 20, 24, 24)
        v.setSpacing(16)

        # Top header bar
        head = QFrame()
        head.setObjectName("formTopbar")
        head.setStyleSheet(f"""
            QFrame#formTopbar {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(18, 14, 18, 14)
        hl.setSpacing(14)

        btn_back = QPushButton("→  العودة للقائمة")
        btn_back.setFixedHeight(36)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(_secondary_btn_style(12))
        btn_back.clicked.connect(self._cancel_form)
        hl.addWidget(btn_back)

        divider = QFrame()
        divider.setFixedSize(1, 30)
        divider.setStyleSheet(f"background:{DIVIDER}; border:none;")
        hl.addWidget(divider)

        tbox = QVBoxLayout()
        tbox.setSpacing(2)

        self.form_title = QLabel("موظف جديد")
        self.form_title.setStyleSheet(
            f"font-size:15px; font-weight:700; color:{TEXT}; "
            f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
        )
        tbox.addWidget(self.form_title)

        self.form_subtitle = QLabel("إضافة سجل موظف جديد")
        self.form_subtitle.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; background:transparent; "
            f"font-family:{FONT_FAMILY}; border:none;"
        )
        tbox.addWidget(self.form_subtitle)
        hl.addLayout(tbox)
        hl.addStretch()

        self.btn_files = QPushButton("ملفات الموظف")
        self.btn_files.setFixedHeight(36)
        self.btn_files.setCursor(Qt.PointingHandCursor)
        self.btn_files.setStyleSheet(f"""
            QPushButton {{
                background:{INFO_BG};
                color:{INFO};
                border:1px solid {INFO_BRD};
                border-radius:{RADIUS};
                padding:0 18px;
                font-size:12px;
                font-weight:600;
                font-family:{FONT_FAMILY};
            }}
            QPushButton:hover {{
                background:#d9e9f0;
                border-color:{INFO};
            }}
        """)
        self.btn_files.clicked.connect(self._open_files)
        self.btn_files.setVisible(False)
        hl.addWidget(self.btn_files)

        v.addWidget(head)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(_scroll_qss())

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        cl = QHBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(16)

        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        left_col.addWidget(self._section_card("البيانات الأساسية", PRIMARY, "basic"))
        left_col.addWidget(self._section_card("التأمينات", INFO, "insurance"))
        left_col.addStretch()

        # Right column
        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        right_col.addWidget(self._section_card("الراتب والبدلات", SUCCESS, "salary"))
        right_col.addStretch()

        cl.addLayout(left_col, 1)
        cl.addLayout(right_col, 1)

        scroll.setWidget(content)
        v.addWidget(scroll, 1)

        # Footer with save/cancel
        footer = QFrame()
        footer.setObjectName("formFooter")
        footer.setStyleSheet(f"""
            QFrame#formFooter {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(18, 12, 18, 12)
        fl.setSpacing(10)
        fl.addStretch()

        self.btn_cancel = QPushButton("إلغاء")
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setMinimumWidth(120)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(_secondary_btn_style(12))
        self.btn_cancel.clicked.connect(self._cancel_form)

        self.btn_save = QPushButton("حفظ الموظف")
        self.btn_save.setFixedHeight(40)
        self.btn_save.setMinimumWidth(170)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet(_primary_btn_style(12))
        self.btn_save.clicked.connect(self._save)

        fl.addWidget(self.btn_cancel)
        fl.addWidget(self.btn_save)
        v.addWidget(footer)

        return page

    def _section_card(self, title, color, key):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setStyleSheet(f"""
            QFrame#sectionCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 18, 20, 20)
        v.setSpacing(14)

        # Section header
        h = QHBoxLayout()
        h.setSpacing(9)

        marker = QFrame()
        marker.setFixedSize(3, 16)
        marker.setStyleSheet(f"background:{color}; border:none; border-radius:2px;")
        h.addWidget(marker)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:12.5px; font-weight:700; color:{TEXT}; "
            f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
        )
        h.addWidget(lbl)
        h.addStretch()
        v.addLayout(h)

        # Fields grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        if key == "basic":
            self.code = self._input("EMP-001", ltr=True)
            self.name = self._input("الاسم الكامل")
            self.dept = self._input("القسم / الإدارة")
            self.phone = self._input("01xxxxxxxxx", ltr=True)
            self.shift_combo = self._combo()
            self.annual_leave = self._num()

            grid.addWidget(self._field("الكود", self.code), 0, 0)
            grid.addWidget(self._field("الاسم", self.name), 0, 1)
            grid.addWidget(self._field("القسم", self.dept), 1, 0)
            grid.addWidget(self._field("الهاتف", self.phone), 1, 1)
            grid.addWidget(self._field("الشيفت", self.shift_combo), 2, 0)
            grid.addWidget(self._field("رصيد الإجازة", self.annual_leave), 2, 1)

        elif key == "salary":
            self.base_salary = self._num()
            self.total_salary = self._num()
            self.incentive = self._num()
            self.meal = self._num()
            self.transport = self._num()
            self.expat = self._num()
            self.other = self._num()

            grid.addWidget(self._field("الأساسي", self.base_salary), 0, 0)
            grid.addWidget(self._field("الإجمالي", self.total_salary), 0, 1)
            grid.addWidget(self._field("الحافز", self.incentive), 1, 0)
            grid.addWidget(self._field("بدل وجبة", self.meal), 1, 1)
            grid.addWidget(self._field("بدل مواصلات", self.transport), 2, 0)
            grid.addWidget(self._field("بدل اغتراب", self.expat), 2, 1)
            grid.addWidget(self._field("بدلات أخرى", self.other), 3, 0)

        elif key == "insurance":
            self.medical = self._num()
            self.social = self._num()

            grid.addWidget(self._field("تأمين طبي", self.medical), 0, 0)
            grid.addWidget(self._field("تأمين اجتماعي", self.social), 0, 1)

        v.addLayout(grid)
        return card

    # ----------------------------------------------------------
    #                    عناصر مساعدة
    # ----------------------------------------------------------
    def _field(self, label_text, widget):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(5)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            f"font-size:11px; font-weight:600; color:{TEXT_SEC}; "
            f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
        )
        v.addWidget(lbl)
        v.addWidget(widget)
        return w

    def _input(self, placeholder="", ltr=False):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(36)
        if ltr:
            inp.setLayoutDirection(Qt.LeftToRight)
            inp.setAlignment(Qt.AlignLeft)
        inp.setStyleSheet(_input_qss())
        return inp

    def _num(self):
        inp = QLineEdit()
        inp.setValidator(QDoubleValidator(0, 100_000_000, 2))
        inp.setFixedHeight(36)
        inp.setText("0")
        inp.setLayoutDirection(Qt.LeftToRight)
        inp.setAlignment(Qt.AlignLeft)
        inp.setStyleSheet(_input_qss())
        return inp

    def _combo(self):
        c = QComboBox()
        c.setFixedHeight(36)
        c.setStyleSheet(f"""
            QComboBox {{
                background:{SURFACE};
                border:1px solid {BORDER_2};
                border-radius:{RADIUS};
                padding:0 12px;
                font-size:12.5px;
                color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QComboBox:hover {{ border-color:{TEXT_MUTED}; }}
            QComboBox:focus {{ border:1px solid {PRIMARY}; }}
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
                border-radius:{RADIUS};
                padding:4px;
                selection-background-color:{PRIMARY_BG};
                selection-color:{PRIMARY};
                outline:none;
            }}
            QComboBox QAbstractItemView::item {{
                padding:7px 10px;
                border-radius:3px;
                min-height:20px;
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

    def _new_employee(self):
        self._editing_id = None
        self._clear_form()
        self._load_shifts()
        self.form_title.setText("موظف جديد")
        self.form_subtitle.setText("إضافة سجل موظف جديد")
        self.btn_save.setText("حفظ الموظف")
        self.btn_files.setVisible(False)
        self.stack.setCurrentWidget(self.form_page)

    def _cancel_form(self):
        self._editing_id = None
        self._clear_form()
        self.stack.setCurrentWidget(self.list_page)

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

            # Employee cell
            emp = QWidget()
            emp.setStyleSheet("background:transparent;")
            ev = QVBoxLayout(emp)
            ev.setContentsMargins(6, 3, 6, 3)
            ev.setSpacing(2)

            n = QLabel(r["name"] or "—")
            n.setStyleSheet(
                f"font-size:12.5px; font-weight:700; "
                f"color:{TEXT if is_active else TEXT_MUTED}; "
                f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
            )
            c = QLabel(r["code"] or "")
            c.setStyleSheet(
                f"font-size:10.5px; color:{TEXT_MUTED}; "
                f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
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

            badge = QLabel("نشط" if is_active else "موقوف")
            badge.setAlignment(Qt.AlignCenter)
            if is_active:
                badge.setStyleSheet(_badge_style(SUCCESS, SUCCESS_BG, SUCCESS_BRD, size=11, pad="3px 12px"))
            else:
                badge.setStyleSheet(_badge_style(DANGER, DANGER_BG, DANGER_BRD, size=11, pad="3px 12px"))
            sl.addWidget(badge)
            self.table.setCellWidget(i, 6, status)

            # Actions
            actions = QWidget()
            actions.setStyleSheet("background:transparent;")
            al = QHBoxLayout(actions)
            al.setContentsMargins(2, 0, 2, 0)
            al.setSpacing(5)
            al.setAlignment(Qt.AlignCenter)

            btn_edit = self._icon_btn("تعديل", PRIMARY, "تعديل الموظف")
            btn_edit.clicked.connect(lambda _, eid=r["id"]: self._edit(eid))

            btn_files = self._icon_btn("ملفات", INFO, "ملفات الموظف")
            btn_files.clicked.connect(lambda _, eid=r["id"]: self._open_files_by_id(eid))

            if is_active:
                btn_toggle = self._icon_btn("إيقاف", WARNING, "إيقاف الموظف")
            else:
                btn_toggle = self._icon_btn("تفعيل", SUCCESS, "تفعيل الموظف")
            btn_toggle.clicked.connect(lambda _, eid=r["id"]: self._toggle_status(eid))

            btn_del = self._icon_btn("حذف", DANGER, "حذف الموظف")
            btn_del.clicked.connect(lambda _, eid=r["id"]: self._delete(eid))

            al.addWidget(btn_edit)
            al.addWidget(btn_files)
            al.addWidget(btn_toggle)
            al.addWidget(btn_del)
            self.table.setCellWidget(i, 7, actions)

    def _icon_btn(self, text, color, tooltip=""):
        btn = QPushButton(text)
        btn.setFixedHeight(26)
        btn.setMinimumWidth(50)
        btn.setCursor(Qt.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE};
                color:{color};
                border:1px solid {BORDER_2};
                border-radius:{RADIUS};
                padding:0 10px;
                font-size:11px;
                font-weight:600;
                font-family:{FONT_FAMILY};
            }}
            QPushButton:hover {{
                background:{SURFACE_3};
                border-color:{color};
            }}
            QPushButton:pressed {{ background:{SURFACE_2}; }}
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
        self._load_shifts()
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

        self.form_title.setText("تعديل موظف")
        self.form_subtitle.setText(f"{r['name']}  ·  {r['code']}")
        self.btn_save.setText("حفظ التعديلات")
        self.btn_files.setVisible(True)
        self.stack.setCurrentWidget(self.form_page)

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
        msg.setInformativeText("سيتم حذف الموظف من النظام، لكن ملفاته ستبقى في الفولدر.")
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
        self.setMinimumSize(740, 580)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 22, 22, 22)
        v.setSpacing(14)

        head = QFrame()
        head.setObjectName("filesHeader")
        head.setStyleSheet(f"""
            QFrame#filesHeader {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(18, 14, 18, 14)
        hl.setSpacing(12)

        tbox = QVBoxLayout()
        tbox.setSpacing(2)

        title = QLabel(f"ملفات: {self.employee_name}")
        title.setStyleSheet(
            f"font-size:15px; font-weight:700; color:{TEXT}; "
            f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
        )
        tbox.addWidget(title)

        sub = QLabel("إدارة مستندات وملفات الموظف")
        sub.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; background:transparent; "
            f"font-family:{FONT_FAMILY}; border:none;"
        )
        tbox.addWidget(sub)
        hl.addLayout(tbox)
        hl.addStretch()

        code_lbl = QLabel(f"كود: {self.employee_code}")
        code_lbl.setStyleSheet(_badge_style(TEXT_SEC, SURFACE_3, BORDER, size=11, pad="4px 12px"))
        hl.addWidget(code_lbl)
        v.addWidget(head)

        path_box = QFrame()
        path_box.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)
        pl = QHBoxLayout(path_box)
        pl.setContentsMargins(14, 10, 14, 10)
        pl.setSpacing(8)

        path_lbl = QLabel(f"{self.folder.absolute()}")
        path_lbl.setStyleSheet(
            f"font-size:11px; color:{TEXT_SEC}; background:transparent; "
            f"font-family: Consolas, monospace; border:none;"
        )
        path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        pl.addWidget(path_lbl, 1)
        v.addWidget(path_box)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        btn_upload = QPushButton("رفع ملفات")
        btn_upload.setFixedHeight(36)
        btn_upload.setCursor(Qt.PointingHandCursor)
        btn_upload.setStyleSheet(_primary_btn_style(12))
        btn_upload.clicked.connect(self._upload)
        actions.addWidget(btn_upload)

        btn_scan = QPushButton("مسح ضوئي")
        btn_scan.setFixedHeight(36)
        btn_scan.setCursor(Qt.PointingHandCursor)
        btn_scan.setStyleSheet(_success_btn_style(12))
        btn_scan.clicked.connect(self._scan)
        actions.addWidget(btn_scan)

        actions.addStretch()

        btn_open_folder = QPushButton("فتح المجلد")
        btn_open_folder.setFixedHeight(36)
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.setStyleSheet(_secondary_btn_style(12))
        btn_open_folder.clicked.connect(self._open_folder)
        actions.addWidget(btn_open_folder)

        v.addLayout(actions)

        self.list = QListWidget()
        self.list.setStyleSheet(f"""
            QListWidget {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
                padding:6px;
                font-size:12.5px;
                color:{TEXT};
                outline:none;
                font-family:{FONT_FAMILY};
            }}
            QListWidget::item {{
                padding:12px 14px;
                border-radius:{RADIUS};
                border-bottom:1px solid {DIVIDER};
                margin:2px 0;
            }}
            QListWidget::item:selected {{
                background:{PRIMARY_BG};
                color:{PRIMARY_DK};
                border:1px solid {PRIMARY_BRD};
            }}
            QListWidget::item:hover {{ background:{SURFACE_2}; }}
        """)
        self.list.itemDoubleClicked.connect(self._open_file)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._file_menu)
        v.addWidget(self.list, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        btn_close = QPushButton("إغلاق")
        btn_close.setFixedHeight(36)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(_secondary_btn_style(12))
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
            text = f"{f['file_name']}          {size_str}"
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
            QMessageBox.information(self, "تم", f"تم رفع {count} ملف")
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
                border-radius:{RADIUS};
                padding:4px;
            }}
            QMenu::item {{
                padding:8px 22px 8px 14px;
                border-radius:3px;
                font-size:12px;
                color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QMenu::item:selected {{
                background:{PRIMARY_BG};
                color:{PRIMARY_DK};
            }}
            QMenu::separator {{
                height:1px;
                background:{DIVIDER};
                margin:4px 6px;
            }}
        """)

        act_open = QAction("فتح", self)
        act_open.triggered.connect(lambda: self._open_file(item))

        act_del = QAction("حذف", self)
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
        self.setMinimumSize(600, 540)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")

        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 22, 22, 22)
        v.setSpacing(14)

        head = QFrame()
        head.setObjectName("scanHeader")
        head.setStyleSheet(f"""
            QFrame#scanHeader {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(18, 14, 18, 14)
        hl.setSpacing(12)

        tbox = QVBoxLayout()
        tbox.setSpacing(2)

        title = QLabel("المسح الضوئي / إضافة صورة")
        title.setStyleSheet(
            f"font-size:15px; font-weight:700; color:{TEXT}; "
            f"background:transparent; font-family:{FONT_FAMILY}; border:none;"
        )
        tbox.addWidget(title)

        sub = QLabel("اختر صورة من الجهاز أو استخدم السكانر")
        sub.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; background:transparent; "
            f"font-family:{FONT_FAMILY}; border:none;"
        )
        tbox.addWidget(sub)
        hl.addLayout(tbox, 1)
        v.addWidget(head)

        info_box = QFrame()
        info_box.setStyleSheet(f"""
            QFrame {{
                background:{INFO_BG};
                border:1px solid {INFO_BRD};
                border-radius:{RADIUS};
            }}
        """)
        il = QHBoxLayout(info_box)
        il.setContentsMargins(14, 11, 14, 11)
        il.setSpacing(10)

        info = QLabel(
            "لسكانر حقيقي: ثبّت <b>pywin32</b> + <b>pillow</b> على ويندوز، "
            "أو <b>python-sane</b> على لينكس/ماك."
        )
        info.setStyleSheet(
            f"font-size:11.5px; color:{INFO}; background:transparent; "
            f"font-family:{FONT_FAMILY}; border:none;"
        )
        info.setWordWrap(True)
        il.addWidget(info, 1)
        v.addWidget(info_box)

        self.preview = QLabel("— لا توجد صورة —")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(220)
        self.preview.setStyleSheet(f"""
            background:{SURFACE};
            border:2px dashed {BORDER_2};
            border-radius:{RADIUS};
            color:{TEXT_MUTED};
            font-size:13px;
            font-weight:600;
            font-family:{FONT_FAMILY};
        """)
        v.addWidget(self.preview, 1)

        btns = QHBoxLayout()
        btns.setSpacing(8)

        btn_pick = QPushButton("اختر صورة")
        btn_pick.setFixedHeight(36)
        btn_pick.setCursor(Qt.PointingHandCursor)
        btn_pick.setStyleSheet(_secondary_btn_style(12))
        btn_pick.clicked.connect(self._pick_image)
        btns.addWidget(btn_pick)

        btn_scan_device = QPushButton("مسح من السكانر")
        btn_scan_device.setFixedHeight(36)
        btn_scan_device.setCursor(Qt.PointingHandCursor)
        btn_scan_device.setStyleSheet(_primary_btn_style(12))
        btn_scan_device.clicked.connect(self._scan_device)
        btns.addWidget(btn_scan_device)

        btns.addStretch()

        btn_save = QPushButton("حفظ")
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(_success_btn_style(12))
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)

        btn_close = QPushButton("إلغاء")
        btn_close.setFixedHeight(36)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(_secondary_btn_style(12))
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
                scaled = pix.scaled(480, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview.setPixmap(scaled)
                self.preview.setStyleSheet(f"""
                    background:{SURFACE};
                    border:1px solid {BORDER};
                    border-radius:{RADIUS};
                """)
            else:
                self.preview.setText("تعذر تحميل الصورة")
        except Exception as e:
            self.preview.setText(f"خطأ: {e}")

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
                QMessageBox.information(self, "تم", "تم المسح الضوئي")
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