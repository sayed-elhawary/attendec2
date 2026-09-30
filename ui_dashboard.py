import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QStackedWidget, QFrame, QButtonGroup, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGridLayout,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

from ui_shift import ShiftPage
from ui_employee import EmployeePage
from ui_attendance import AttendancePage
from ui_payroll import PayrollPage
from ui_device_connection import DeviceConnectionPage
from database import (
    change_password, get_employees, get_shifts,
    count_raw_punches, count_all_overrides,
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
WARNING_BG  = "#fbf3e4"
WARNING_BRD = "#e6cf9f"

INFO        = "#2a6f8f"
INFO_BG     = "#e9f2f6"
INFO_BRD    = "#b5d2df"

PURPLE      = "#5f4b8b"
PURPLE_BG   = "#efecf5"
PURPLE_BRD  = "#cfc6e0"

GRAY        = "#616e7c"
GRAY_BG     = "#f0f2f4"
GRAY_BRD    = "#d8dce1"

FONT_FAMILY = "Segoe UI, Tahoma, Arial, sans-serif"

RADIUS = "4px"


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
            padding:0 16px; font-weight:600; font-size:{size}px;
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
            padding:0 16px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ background:{SURFACE_3}; border-color:{TEXT_MUTED}; }}
        QPushButton:pressed {{ background:{DIVIDER}; }}
    """


# ============================================================
#              Dialog: تغيير كلمة المرور
# ============================================================
class ChangePasswordDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تغيير كلمة المرور")
        self.setFixedWidth(440)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")
        self.username = username

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 22, 22, 22)
        v.setSpacing(14)

        # Header
        head = QFrame()
        head.setObjectName("pwHeader")
        head.setStyleSheet(_card_style("pwHeader"))

        hh = QHBoxLayout(head)
        hh.setContentsMargins(16, 12, 16, 12)
        hh.setSpacing(12)

        tbox = QVBoxLayout()
        tbox.setSpacing(2)

        t = QLabel("تغيير كلمة المرور")
        t.setStyleSheet(
            f"font-size:15px; font-weight:700; color:{TEXT}; "
            f"background:transparent; border:none;"
        )
        tbox.addWidget(t)

        s = QLabel(f"المستخدم: {username}")
        s.setStyleSheet(
            f"font-size:11px; color:{TEXT_MUTED}; background:transparent; border:none;"
        )
        tbox.addWidget(s)
        hh.addLayout(tbox)
        hh.addStretch()
        v.addWidget(head)

        # الحقول
        self.old = self._password_input("كلمة المرور الحالية")
        self.new = self._password_input("كلمة المرور الجديدة")
        self.new2 = self._password_input("تأكيد كلمة المرور الجديدة")

        v.addWidget(self._field("كلمة المرور الحالية", self.old))
        v.addWidget(self._field("كلمة المرور الجديدة", self.new))
        v.addWidget(self._field("تأكيد كلمة المرور", self.new2))

        v.addSpacing(6)

        # أزرار
        btns = QHBoxLayout()
        btns.setSpacing(8)

        btn_cancel = QPushButton("إلغاء")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(_secondary_btn_style(12))
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btns.addStretch()

        btn_save = QPushButton("حفظ")
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(_primary_btn_style(12))
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)

        v.addLayout(btns)

    def _password_input(self, placeholder):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setEchoMode(QLineEdit.Password)
        inp.setFixedHeight(36)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background:{SURFACE}; border:1px solid {BORDER_2};
                border-radius:{RADIUS}; padding:0 12px;
                font-size:12.5px; color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QLineEdit:hover {{ border-color:{TEXT_MUTED}; }}
            QLineEdit:focus {{ border:1px solid {PRIMARY}; }}
        """)
        return inp

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

    def _save(self):
        if not self.old.text() or not self.new.text():
            QMessageBox.warning(self, "تنبيه", "املأ كل الحقول")
            return
        if self.new.text() != self.new2.text():
            QMessageBox.warning(self, "تنبيه", "كلمتا المرور غير متطابقتين")
            return
        if len(self.new.text()) < 4:
            QMessageBox.warning(self, "تنبيه", "كلمة المرور يجب أن تكون 4 أحرف على الأقل")
            return

        ok, msg = change_password(self.username, self.old.text(), self.new.text())
        if ok:
            QMessageBox.information(self, "تم", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "خطأ", msg)


# ============================================================
#                       Dashboard
# ============================================================
class Dashboard(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setLayoutDirection(Qt.RightToLeft)
        self._pages = {}
        self._buttons = {}
        self._build_ui()

    # ========================================================
    #                    بناء الواجهة
    # ========================================================
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_main_area(), 1)

    # ----------------------------------------------------------
    #                    Sidebar
    # ----------------------------------------------------------
    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background:{PRIMARY};
                border:none;
            }}
        """)

        v = QVBoxLayout(sidebar)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Logo Section
        v.addWidget(self._build_logo_section())

        # Divider
        v.addWidget(self._divider())

        # User card
        v.addWidget(self._build_user_card())

        # Divider
        v.addWidget(self._divider())

        # Menu label
        v.addSpacing(14)
        menu_lbl = QLabel("القائمة الرئيسية")
        menu_lbl.setStyleSheet(f"""
            color: rgba(255,255,255,0.55);
            font-size:10.5px;
            font-weight:700;
            letter-spacing:1px;
            padding:0 22px;
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        v.addWidget(menu_lbl)
        v.addSpacing(10)

        # Buttons
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.stack = QStackedWidget()

        pages_list = [
            ("لوحة التحكم",       self._make_home()),
            ("الشيفتات",          ShiftPage()),
            ("الموظفين",          EmployeePage()),
            ("الحضور والانصراف",  AttendancePage()),
            ("المرتبات",          PayrollPage()),
            ("ربط البصمة",        DeviceConnectionPage()),
        ]

        for label, widget in pages_list:
            self._add_sidebar_btn(v, label, widget)

        v.addStretch()

        # Actions at bottom
        v.addWidget(self._divider())
        v.addSpacing(10)

        btn_pw = self._make_action_btn("تغيير كلمة المرور")
        btn_pw.clicked.connect(self._open_change_pw)
        v.addWidget(btn_pw)

        btn_logout = self._make_action_btn("تسجيل الخروج", danger=True)
        btn_logout.clicked.connect(self._logout)
        v.addWidget(btn_logout)

        v.addSpacing(10)

        # Footer
        footer = QLabel("v1.0  -  2026")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"""
            color: rgba(255,255,255,0.4);
            font-size:10px;
            background:transparent;
            padding:10px;
            letter-spacing:0.5px;
            font-family:{FONT_FAMILY};
        """)
        v.addWidget(footer)

        return sidebar

    def _divider(self):
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet(
            "background: rgba(255,255,255,0.1); border:none;"
        )
        return d

    def _build_logo_section(self):
        wrap = QFrame()
        wrap.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(20, 22, 20, 18)
        wl.setSpacing(10)

        # Logo container
        logo_container = QFrame()
        logo_container.setFixedSize(72, 72)
        logo_container.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: {RADIUS};
            }}
        """)

        lc_layout = QVBoxLayout(logo_container)
        lc_layout.setContentsMargins(6, 6, 6, 6)
        lc_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("background:transparent; border:none;")

        try:
            if os.path.exists("logo.png"):
                pix = QPixmap("logo.png")
                if not pix.isNull():
                    scaled = pix.scaled(
                        56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    logo_label.setPixmap(scaled)
                else:
                    logo_label.setText("HR")
                    logo_label.setStyleSheet(f"""
                        font-size:22px;
                        background:transparent;
                        color:white;
                        font-weight:700;
                        font-family:{FONT_FAMILY};
                        border:none;
                    """)
            else:
                logo_label.setText("HR")
                logo_label.setStyleSheet(f"""
                    font-size:22px;
                    background:transparent;
                    color:white;
                    font-weight:700;
                    font-family:{FONT_FAMILY};
                    border:none;
                """)
        except Exception:
            logo_label.setText("HR")
            logo_label.setStyleSheet(f"""
                font-size:22px;
                background:transparent;
                color:white;
                font-weight:700;
                font-family:{FONT_FAMILY};
                border:none;
            """)

        lc_layout.addWidget(logo_label)
        wl.addWidget(logo_container, 0, Qt.AlignCenter)

        # الاسم
        title = QLabel("نظام الحضور")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            color:white;
            font-size:15px;
            font-weight:700;
            background:transparent;
            letter-spacing:0.3px;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        wl.addWidget(title)

        sub = QLabel("والانصراف والمرتبات")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"""
            color: rgba(255,255,255,0.62);
            font-size:10.5px;
            background:transparent;
            letter-spacing:0.2px;
            font-weight:500;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        wl.addWidget(sub)

        return wrap

    def _build_user_card(self):
        wrap = QFrame()
        wrap.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(14, 14, 14, 14)
        wl.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: {RADIUS};
            }}
        """)

        h = QHBoxLayout(card)
        h.setContentsMargins(10, 9, 10, 9)
        h.setSpacing(10)

        # Avatar
        avatar = QLabel(self.username[0].upper() if self.username else "؟")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(34, 34)
        avatar.setStyleSheet(f"""
            QLabel {{
                background: rgba(255,255,255,0.15);
                color:white;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: {RADIUS};
                font-size:14px;
                font-weight:700;
                font-family:{FONT_FAMILY};
            }}
        """)
        h.addWidget(avatar)

        # Info
        v = QVBoxLayout()
        v.setSpacing(1)

        name_lbl = QLabel(self.username)
        name_lbl.setStyleSheet(f"""
            color:white;
            font-size:12px;
            font-weight:700;
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        v.addWidget(name_lbl)

        role_lbl = QLabel("مسجل الدخول")
        role_lbl.setStyleSheet(f"""
            color: rgba(255,255,255,0.62);
            font-size:10px;
            background:transparent;
            font-weight:500;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        v.addWidget(role_lbl)

        h.addLayout(v)
        h.addStretch()

        wl.addWidget(card)
        return wrap

    def _add_sidebar_btn(self, layout, label, widget):
        """إضافة زر جانبي مع تباعد واضح بين الأزرار."""
        # فراغ قبل الزر لجعل التباعد أوضح
        spacer = QWidget()
        spacer.setFixedHeight(4)
        spacer.setStyleSheet("background:transparent;")
        layout.addWidget(spacer)

        btn = QPushButton(label)
        btn.setObjectName("sidebar_btn")
        btn.setCheckable(True)
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(self._sidebar_btn_style())

        self.btn_group.addButton(btn)
        self._buttons[label] = btn

        layout.addWidget(btn)
        self.stack.addWidget(widget)
        self._pages[label] = widget

        btn.clicked.connect(lambda _, l=label: self._switch_page(l))
        btn.toggled.connect(
            lambda checked, b=btn: self._update_btn_style(b, checked)
        )

    def _sidebar_btn_style(self):
        """نمط الأزرار العادية (غير محددة) — مع Hover واضح وتباعد جيد."""
        return f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-left: 3px solid transparent;
                border-radius: {RADIUS};
                margin: 3px 14px;
                padding: 0 16px;
                text-align: right;
                font-family: {FONT_FAMILY};
                font-size: 12.5px;
                font-weight: 600;
                color: rgba(255,255,255,0.85);
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.14);
                color: white;
                font-weight: 700;
            }}
        """

    def _update_btn_style(self, btn, checked):
        """تحديث لون الزر عند التحديد — مع شريط جانبي أبيض."""
        if checked:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.18);
                    border: none;
                    border-left: 3px solid white;
                    border-radius: {RADIUS};
                    margin: 3px 14px;
                    padding: 0 16px;
                    text-align: right;
                    font-family: {FONT_FAMILY};
                    font-size: 12.5px;
                    font-weight: 700;
                    color: white;
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.24);
                }}
            """)
        else:
            btn.setStyleSheet(self._sidebar_btn_style())

    def _make_action_btn(self, label, danger=False):
        """زر أسفل الـ sidebar (تغيير كلمة المرور / الخروج) — بنفس التباعد."""
        btn = QPushButton(label)
        btn.setMinimumHeight(38)
        btn.setCursor(Qt.PointingHandCursor)

        if danger:
            color = "rgba(255,180,175,0.95)"
            hover_bg = "rgba(255,255,255,0.14)"
            hover_color = "white"
        else:
            color = "rgba(255,255,255,0.85)"
            hover_bg = "rgba(255,255,255,0.14)"
            hover_color = "white"

        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-left: 3px solid transparent;
                border-radius: {RADIUS};
                margin: 3px 14px;
                padding: 0 16px;
                text-align: right;
                font-family: {FONT_FAMILY};
                font-size: 12.5px;
                font-weight: 600;
                color: {color};
            }}
            QPushButton:hover {{
                background: {hover_bg};
                color: {hover_color};
                font-weight: 700;
            }}
        """)
        return btn

    # ----------------------------------------------------------
    #                    Main Area
    # ----------------------------------------------------------
    def _build_main_area(self):
        wrap = QWidget()
        wrap.setStyleSheet(f"background:{BG};")
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        v.addWidget(self._build_topbar())
        v.addWidget(self.stack, 1)

        default = "لوحة التحكم"
        if default in self._buttons:
            self._buttons[default].setChecked(True)
            self.stack.setCurrentWidget(self._pages[default])
            self._update_topbar_title(default)

        return wrap

    def _build_topbar(self):
        bar = QFrame()
        bar.setFixedHeight(58)
        bar.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:none;
                border-bottom:1px solid {BORDER};
            }}
        """)

        h = QHBoxLayout(bar)
        h.setContentsMargins(26, 0, 26, 0)
        h.setSpacing(14)

        # breadcrumb
        crumb_box = QVBoxLayout()
        crumb_box.setSpacing(1)

        crumb = QLabel("الرئيسية  /  لوحة التحكم")
        crumb.setStyleSheet(f"""
            color:{TEXT_MUTED};
            font-size:10.5px;
            font-weight:600;
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        crumb_box.addWidget(crumb)
        self._crumb_label = crumb

        # Page title
        self.page_title = QLabel("لوحة التحكم")
        self.page_title.setStyleSheet(f"""
            font-size:15px;
            font-weight:700;
            color:{TEXT};
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        crumb_box.addWidget(self.page_title)

        h.addLayout(crumb_box)
        h.addStretch()

        # Status indicator
        status_lbl = QLabel("متصل")
        status_lbl.setAlignment(Qt.AlignCenter)
        status_lbl.setFixedHeight(26)
        status_lbl.setStyleSheet(f"""
            QLabel {{
                background:{SUCCESS_BG};
                color:{SUCCESS};
                border:1px solid {SUCCESS_BRD};
                border-radius:{RADIUS};
                padding:0 12px;
                font-size:11px;
                font-weight:600;
                font-family:{FONT_FAMILY};
            }}
        """)
        h.addWidget(status_lbl)

        # Divider
        dv = QFrame()
        dv.setFixedWidth(1)
        dv.setFixedHeight(24)
        dv.setStyleSheet(f"background:{BORDER};")
        h.addWidget(dv)

        # User badge
        user_badge = QLabel(self.username)
        user_badge.setAlignment(Qt.AlignCenter)
        user_badge.setFixedHeight(30)
        user_badge.setStyleSheet(f"""
            QLabel {{
                background:{SURFACE_3};
                color:{TEXT};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
                padding:0 14px;
                font-size:11.5px;
                font-weight:600;
                font-family:{FONT_FAMILY};
            }}
        """)
        h.addWidget(user_badge)

        return bar

    def _switch_page(self, label):
        widget = self._pages.get(label)
        if widget:
            self.stack.setCurrentWidget(widget)
            self._update_topbar_title(label)

    def _update_topbar_title(self, label):
        if hasattr(self, "page_title"):
            self.page_title.setText(label)
            if hasattr(self, "_crumb_label"):
                self._crumb_label.setText(f"الرئيسية  /  {label}")

    # ========================================================
    #                لوحة التحكم (Home Page)
    # ========================================================
    def _make_home(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background:{BG}; border:none; }}
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
        """)

        w = QWidget()
        w.setStyleSheet(f"background:{BG};")
        v = QVBoxLayout(w)
        v.setContentsMargins(26, 22, 26, 26)
        v.setSpacing(18)

        # ====== إحصائيات ======
        v.addWidget(self._section_header("نظرة عامة", "إحصائيات سريعة عن النظام"))

        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)

        emp_count = self._safe_count(get_employees, [])
        shift_count = self._safe_count(get_shifts, [])
        punch_count = self._safe_count(count_raw_punches, 0)
        override_count = self._safe_count(count_all_overrides, 0)

        stats = [
            ("الموظفين",         emp_count,      PRIMARY, PRIMARY_BG, PRIMARY_BRD, "موظف نشط"),
            ("الشيفتات",         shift_count,    SUCCESS, SUCCESS_BG, SUCCESS_BRD, "شيفت مسجّل"),
            ("البصمات المسجلة",  punch_count,    WARNING, WARNING_BG, WARNING_BRD, "بصمة إجمالية"),
            ("تعديلات الحضور",   override_count, PURPLE,  PURPLE_BG,  PURPLE_BRD, "تعديل يدوي"),
        ]

        for i, (label, value, color, bg, brd, unit) in enumerate(stats):
            card = self._make_stat_card(label, value, color, bg, brd, unit)
            stats_grid.addWidget(card, 0, i)

        for c in range(4):
            stats_grid.setColumnStretch(c, 1)

        v.addLayout(stats_grid)

        # ====== إجراءات سريعة ======
        v.addWidget(self._section_header("إجراءات سريعة", "انتقل مباشرة إلى الصفحات الرئيسية"))

        actions_grid = QGridLayout()
        actions_grid.setSpacing(12)

        actions = [
            ("إنشاء شيفت جديد",   "أضف شيفتاً واربط الموظفين به",  PRIMARY, PRIMARY_BG, PRIMARY_BRD, "الشيفتات"),
            ("إضافة موظف",       "سجّل موظفاً جديداً بالنظام",    SUCCESS, SUCCESS_BG, SUCCESS_BRD, "الموظفين"),
            ("تسجيل حضور",       "سجّل بصمة حضور أو انصراف",     WARNING, WARNING_BG, WARNING_BRD, "الحضور والانصراف"),
            ("ربط جهاز البصمة",   "استمع للبصمات فور حدوثها",     INFO,    INFO_BG,    INFO_BRD,    "ربط البصمة"),
            ("عرض المرتبات",     "احسب مرتبات الموظفين",          PURPLE,  PURPLE_BG,  PURPLE_BRD,  "المرتبات"),
        ]

        for i, (title, desc, color, bg, brd, target) in enumerate(actions):
            card = self._make_action_card(title, desc, color, bg, brd, target)
            actions_grid.addWidget(card, i // 3, i % 3)

        for c in range(3):
            actions_grid.setColumnStretch(c, 1)

        v.addLayout(actions_grid)

        # ====== دليل البداية ======
        v.addWidget(self._section_header("دليل البداية السريعة", "خطوات العمل بالترتيب"))

        info_card = self._make_guide_card()
        v.addWidget(info_card)

        v.addStretch()

        scroll.setWidget(w)
        return scroll

    def _safe_count(self, fn, default):
        try:
            result = fn()
            if isinstance(result, (list, tuple)):
                return len(result)
            return int(result)
        except Exception:
            return default

    def _section_header(self, title, subtitle):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(2, 6, 2, 0)
        h.setSpacing(10)

        # شريط عمودي صغير على اليمين (RTL)
        bar = QFrame()
        bar.setFixedSize(3, 30)
        bar.setStyleSheet(f"""
            QFrame {{
                background:{PRIMARY};
                border:none;
                border-radius:2px;
            }}
        """)
        h.addWidget(bar)

        v = QVBoxLayout()
        v.setSpacing(1)

        t = QLabel(title)
        t.setStyleSheet(f"""
            font-size:14px;
            font-weight:700;
            color:{TEXT};
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        v.addWidget(t)

        s = QLabel(subtitle)
        s.setStyleSheet(f"""
            font-size:11px;
            color:{TEXT_MUTED};
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        v.addWidget(s)

        h.addLayout(v)
        h.addStretch()

        return w

    def _make_stat_card(self, label, value, color, bg, brd, unit):
        card = QFrame()
        card.setMinimumHeight(112)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
            QFrame:hover {{
                border:1px solid {brd};
            }}
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        # Top row: label + unit
        top = QHBoxLayout()
        top.setSpacing(8)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"""
            font-size:11.5px;
            color:{TEXT_MUTED};
            background:transparent;
            font-weight:600;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        top.addWidget(lbl)
        top.addStretch()

        un = QLabel(unit)
        un.setStyleSheet(f"""
            font-size:10px;
            color:{color};
            background:{bg};
            border:1px solid {brd};
            border-radius:{RADIUS};
            padding:2px 8px;
            font-weight:600;
            font-family:{FONT_FAMILY};
        """)
        top.addWidget(un)

        v.addLayout(top)

        # Value
        val = QLabel(str(value))
        val.setStyleSheet(f"""
            font-size:28px;
            font-weight:700;
            color:{TEXT};
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        v.addWidget(val)

        v.addStretch()

        return card

    def _make_action_card(self, title, desc, color, bg, brd, target_page):
        card = QFrame()
        card.setMinimumHeight(112)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
            QFrame:hover {{
                background:{bg};
                border:1px solid {brd};
            }}
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(6)

        t = QLabel(title)
        t.setStyleSheet(f"""
            font-size:13.5px;
            font-weight:700;
            color:{TEXT};
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        v.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet(f"""
            font-size:11px;
            color:{TEXT_MUTED};
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
        """)
        d.setWordWrap(True)
        v.addWidget(d)

        v.addStretch()

        # Footer مع خط فاصل وسهم نصي
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{DIVIDER}; border:none;")
        v.addWidget(sep)

        arrow = QLabel("فتح الصفحة  ←")
        arrow.setStyleSheet(f"""
            color:{color};
            font-size:11px;
            font-weight:700;
            background:transparent;
            font-family:{FONT_FAMILY};
            border:none;
            padding-top:4px;
        """)
        v.addWidget(arrow)

        def _on_click(event, page=target_page):
            if page in self._buttons:
                self._buttons[page].setChecked(True)
                self._switch_page(page)

        card.mousePressEvent = _on_click
        return card

    def _make_guide_card(self):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(10)

        steps = [
            ("01", "أنشئ شيفت جديد",
             "اذهب إلى صفحة الشيفتات وحدّد أوقات العمل، أيام العمل، سياسة المرضية، والساعات الإضافية.",
             PRIMARY),
            ("02", "أضف الموظفين",
             "من صفحة الموظفين، سجّل بيانات كل موظف (كود، اسم، راتب، بدلات، تأمينات) واربطه بالشيفت.",
             SUCCESS),
            ("03", "اربط جهاز البصمة",
             "من صفحة «ربط البصمة»، أدخل IP الجهاز وفعّل «الاستماع التلقائي» لاستقبال البصمات فوراً.",
             INFO),
            ("04", "تابع الحضور والانصراف",
             "استعرض البصمات، عدّل الأيام، أضف إجازات، وتحقق من التأخير والإضافي والخصومات.",
             WARNING),
            ("05", "اعرض المرتبات",
             "احسب مرتبات الموظفين لكل فترة، اعرض التفاصيل، وصدّر الكشف كـ CSV.",
             PURPLE),
        ]

        for num, title, desc, color in steps:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background:{SURFACE_2};
                    border:1px solid {DIVIDER};
                    border-radius:{RADIUS};
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)
            rl.setSpacing(14)

            badge = QLabel(num)
            badge.setFixedSize(34, 34)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(f"""
                QLabel {{
                    background:{color};
                    color:white;
                    border:1px solid {color};
                    border-radius:{RADIUS};
                    font-size:12px;
                    font-weight:700;
                    font-family:{FONT_FAMILY};
                }}
            """)
            rl.addWidget(badge)

            txt = QVBoxLayout()
            txt.setSpacing(3)
            tt = QLabel(title)
            tt.setStyleSheet(f"""
                font-size:12.5px;
                font-weight:700;
                color:{TEXT};
                background:transparent;
                font-family:{FONT_FAMILY};
                border:none;
            """)
            txt.addWidget(tt)
            dd = QLabel(desc)
            dd.setStyleSheet(f"""
                font-size:11px;
                color:{TEXT_SEC};
                background:transparent;
                font-family:{FONT_FAMILY};
                border:none;
            """)
            dd.setWordWrap(True)
            txt.addWidget(dd)
            rl.addLayout(txt, 1)

            v.addWidget(row)

        return card

    # ========================================================
    #                Actions
    # ========================================================
    def _open_change_pw(self):
        ChangePasswordDialog(self.username, self).exec()

    def _logout(self):
        reply = QMessageBox.question(
            self, "تسجيل الخروج",
            f"هل تريد تسجيل الخروج من حساب «{self.username}»؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.window().close()