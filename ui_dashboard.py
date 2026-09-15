import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QStackedWidget, QFrame, QButtonGroup, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGridLayout,
    QGraphicsDropShadowEffect, QScrollArea
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
#                نظام الألوان
# ============================================================
BG          = "#f1f5f9"
SURFACE     = "#ffffff"
SURFACE_2   = "#f8fafc"
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
SUCCESS_BG  = "#ecfdf5"
SUCCESS_BRD = "#a7f3d0"

DANGER      = "#dc2626"
DANGER_BG   = "#fef2f2"
DANGER_BRD  = "#fecaca"

WARNING     = "#d97706"
WARNING_BG  = "#fffbeb"
WARNING_BRD = "#fde68a"

INFO        = "#0891b2"
INFO_BG     = "#ecfeff"
INFO_BRD    = "#a5f3fc"

PURPLE      = "#7c3aed"
PURPLE_BG   = "#f5f3ff"
PURPLE_BRD  = "#ddd6fe"

FONT_FAMILY = "Segoe UI, Tahoma, Arial, sans-serif"


def apply_shadow(widget, blur=20, y_offset=4, alpha=35):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    effect.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(effect)
    return effect


# ============================================================
#              Dialog: تغيير كلمة المرور
# ============================================================
class ChangePasswordDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تغيير كلمة المرور")
        self.setFixedWidth(460)
        self.setStyleSheet(f"QDialog {{ background:{BG}; }}")
        self.username = username

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        # Header
        head = QFrame()
        head.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:1 {NAVY_2});
                border-radius:12px;
            }}
        """)
        apply_shadow(head, blur=14, y_offset=3)

        hh = QHBoxLayout(head)
        hh.setContentsMargins(16, 14, 16, 14)
        hh.setSpacing(12)

        icon = QLabel("🔒")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(42, 42)
        icon.setStyleSheet(f"""
            QLabel {{
                background:{NAVY_3}; color:white;
                border:1px solid {NAVY_ACCENT}; border-radius:11px;
                font-size:18px;
            }}
        """)
        hh.addWidget(icon)

        tbox = QVBoxLayout()
        tbox.setSpacing(2)
        t = QLabel("تغيير كلمة المرور")
        t.setStyleSheet(
            "font-size:15px; font-weight:900; color:white; background:transparent;"
        )
        tbox.addWidget(t)
        s = QLabel(f"المستخدم: {username}")
        s.setStyleSheet(
            "font-size:10px; color:#9db3cf; background:transparent;"
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

        v.addSpacing(8)

        # أزرار
        btns = QHBoxLayout()
        btns.setSpacing(9)

        btn_cancel = QPushButton("إلغاء")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE}; color:{TEXT_SEC};
                border:1px solid {BORDER}; border-radius:10px;
                padding:0 22px; font-weight:800; font-size:12px;
            }}
            QPushButton:hover {{
                background:{SURFACE_2}; border-color:{BORDER_2};
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btns.addStretch()

        btn_save = QPushButton("💾  حفظ")
        btn_save.setFixedHeight(42)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 #047857);
                color:white; border:none;
                border-radius:10px; padding:0 26px;
                font-weight:900; font-size:12px;
            }}
            QPushButton:hover {{ background:#047857; }}
        """)
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)

        v.addLayout(btns)

    def _password_input(self, placeholder):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setEchoMode(QLineEdit.Password)
        inp.setFixedHeight(42)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background:{SURFACE_2}; border:1px solid {BORDER};
                border-radius:10px; padding:0 13px;
                font-size:12px; color:{TEXT};
            }}
            QLineEdit:focus {{ background:white; border:1.5px solid {PRIMARY}; }}
        """)
        return inp

    def _field(self, label, widget):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size:11px; font-weight:800; color:{TEXT_SEC}; background:transparent;"
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
        sidebar.setFixedWidth(272)
        sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {NAVY}, stop:0.5 {NAVY_2}, stop:1 {NAVY_3});
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
        menu_lbl.setStyleSheet("""
            color:#64748b;
            font-size:10px;
            font-weight:800;
            letter-spacing:1.5px;
            padding:0 26px;
            background:transparent;
        """)
        v.addWidget(menu_lbl)
        v.addSpacing(10)

        # Buttons (بدون badges)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.stack = QStackedWidget()

        pages_list = [
            ("🏠", "لوحة التحكم",       self._make_home()),
            ("🕐", "الشيفتات",          ShiftPage()),
            ("👥", "الموظفين",          EmployeePage()),
            ("✅", "الحضور والانصراف",   AttendancePage()),
            ("💰", "المرتبات",          PayrollPage()),
            ("🔌", "ربط البصمة",        DeviceConnectionPage()),
        ]

        for icon, label, widget in pages_list:
            self._add_sidebar_btn(v, icon, label, widget)

        v.addStretch()

        # Actions at bottom
        v.addWidget(self._divider())
        v.addSpacing(10)

        btn_pw = self._make_action_btn("🔒", "تغيير كلمة المرور")
        btn_pw.clicked.connect(self._open_change_pw)
        v.addWidget(btn_pw)

        btn_logout = self._make_action_btn("🚪", "تسجيل الخروج", danger=True)
        btn_logout.clicked.connect(self._logout)
        v.addWidget(btn_logout)

        v.addSpacing(12)

        # Footer
        footer = QLabel("v1.0  ·  © 2026")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            color:#475569;
            font-size:9.5px;
            background:transparent;
            padding:10px;
            letter-spacing:0.5px;
        """)
        v.addWidget(footer)

        return sidebar

    def _divider(self):
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet("background:rgba(255,255,255,0.06); margin:0 20px;")
        return d

    def _build_logo_section(self):
        wrap = QFrame()
        wrap.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(22, 24, 22, 20)
        wl.setSpacing(12)

        # Logo container
        logo_container = QFrame()
        logo_container.setFixedSize(84, 84)
        logo_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255,255,255,0.10),
                    stop:1 rgba(255,255,255,0.03));
                border: 1.5px solid rgba(255,255,255,0.14);
                border-radius: 22px;
            }
        """)
        apply_shadow(logo_container, blur=20, y_offset=4, alpha=60)

        lc_layout = QVBoxLayout(logo_container)
        lc_layout.setContentsMargins(8, 8, 8, 8)
        lc_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("background:transparent;")

        try:
            if os.path.exists("logo.png"):
                pix = QPixmap("logo.png")
                if not pix.isNull():
                    scaled = pix.scaled(
                        66, 66, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    logo_label.setPixmap(scaled)
                else:
                    logo_label.setText("⏱")
                    logo_label.setStyleSheet(
                        "font-size:42px; background:transparent; color:white;"
                    )
            else:
                logo_label.setText("⏱")
                logo_label.setStyleSheet(
                    "font-size:42px; background:transparent; color:white;"
                )
        except Exception:
            logo_label.setText("⏱")
            logo_label.setStyleSheet(
                "font-size:42px; background:transparent; color:white;"
            )

        lc_layout.addWidget(logo_label)
        wl.addWidget(logo_container, 0, Qt.AlignCenter)

        # الاسم
        title = QLabel("نظام الحضور")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color:white;
            font-size:17px;
            font-weight:900;
            background:transparent;
            letter-spacing:0.5px;
        """)
        wl.addWidget(title)

        sub = QLabel("والانصراف والمرتبات")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("""
            color:#94a8c4;
            font-size:10.5px;
            background:transparent;
            letter-spacing:0.3px;
            font-weight:500;
        """)
        wl.addWidget(sub)

        return wrap

    def _build_user_card(self):
        wrap = QFrame()
        wrap.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(16, 16, 16, 16)
        wl.setSpacing(0)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
            }
        """)

        h = QHBoxLayout(card)
        h.setContentsMargins(12, 11, 12, 11)
        h.setSpacing(11)

        # Avatar
        avatar = QLabel(self.username[0].upper() if self.username else "؟")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(40, 40)
        avatar.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {PRIMARY}, stop:1 #3b82f6);
                color:white;
                border-radius:20px;
                font-size:16px;
                font-weight:900;
            }}
        """)
        h.addWidget(avatar)

        # Info
        v = QVBoxLayout()
        v.setSpacing(2)

        name_lbl = QLabel(self.username)
        name_lbl.setStyleSheet("""
            color:white;
            font-size:12.5px;
            font-weight:800;
            background:transparent;
        """)
        v.addWidget(name_lbl)

        role_lbl = QLabel("●  مسجل الدخول")
        role_lbl.setStyleSheet("""
            color:#4ade80;
            font-size:9.5px;
            background:transparent;
            font-weight:700;
        """)
        v.addWidget(role_lbl)

        h.addLayout(v)
        h.addStretch()

        wl.addWidget(card)
        return wrap

    def _add_sidebar_btn(self, layout, icon, label, widget):
        """إضافة زر جانبي (بدون badge رقمي)"""
        btn = QPushButton()
        btn.setObjectName("sidebar_btn")
        btn.setCheckable(True)
        btn.setMinimumHeight(48)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(self._sidebar_btn_style())

        h = QHBoxLayout(btn)
        h.setContentsMargins(18, 0, 16, 0)
        h.setSpacing(10)

        ic = QLabel(icon)
        ic.setFixedSize(22, 22)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("""
            font-size:15px;
            background:transparent;
            color:inherit;
        """)
        ic.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        h.addWidget(ic)

        txt = QLabel(label)
        txt.setStyleSheet(f"""
            background:transparent;
            color:#cbd5e1;
            font-size:12.5px;
            font-weight:700;
            font-family:{FONT_FAMILY};
        """)
        txt.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        h.addWidget(txt, 1)

        btn._icon_label = ic
        btn._text_label = txt

        self.btn_group.addButton(btn)
        self._buttons[label] = btn

        layout.addWidget(btn)
        self.stack.addWidget(widget)
        self._pages[label] = widget

        btn.clicked.connect(lambda _, l=label: self._switch_page(l))
        btn.toggled.connect(lambda checked, b=btn: self._update_btn_style(b, checked))

    def _sidebar_btn_style(self):
        return f"""
            QPushButton {{
                background:transparent;
                border:none;
                border-radius:11px;
                margin:3px 14px;
                text-align:right;
                font-family:{FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.07);
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_HOV});
            }}
        """

    def _update_btn_style(self, btn, checked):
        if not hasattr(btn, "_icon_label"):
            return

        if checked:
            btn._icon_label.setStyleSheet("""
                font-size:15px;
                background:transparent;
                color:white;
            """)
            btn._text_label.setStyleSheet(f"""
                background:transparent;
                color:white;
                font-size:12.5px;
                font-weight:900;
                font-family:{FONT_FAMILY};
            """)
        else:
            btn._icon_label.setStyleSheet("""
                font-size:15px;
                background:transparent;
                color:inherit;
            """)
            btn._text_label.setStyleSheet(f"""
                background:transparent;
                color:#cbd5e1;
                font-size:12.5px;
                font-weight:700;
                font-family:{FONT_FAMILY};
            """)

    def _make_action_btn(self, icon, label, danger=False):
        btn = QPushButton()
        btn.setMinimumHeight(44)
        btn.setCursor(Qt.PointingHandCursor)

        if danger:
            color = "#f87171"
            hover_bg = "rgba(239,68,68,0.12)"
            hover_color = "#fca5a5"
        else:
            color = "#cbd5e1"
            hover_bg = "rgba(255,255,255,0.07)"
            hover_color = "white"

        btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent;
                border:none;
                border-radius:10px;
                margin:2px 14px;
                text-align:right;
            }}
            QPushButton:hover {{
                background:{hover_bg};
            }}
        """)

        h = QHBoxLayout(btn)
        h.setContentsMargins(18, 0, 16, 0)
        h.setSpacing(10)

        ic = QLabel(icon)
        ic.setFixedSize(22, 22)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"""
            font-size:15px;
            background:transparent;
            color:{color};
        """)
        ic.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        h.addWidget(ic)

        txt = QLabel(label)
        txt.setStyleSheet(f"""
            background:transparent;
            color:{color};
            font-size:12.5px;
            font-weight:700;
            font-family:{FONT_FAMILY};
        """)
        txt.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        h.addWidget(txt, 1)

        def enter(e):
            ic.setStyleSheet(f"font-size:15px; background:transparent; color:{hover_color};")
            txt.setStyleSheet(f"""
                background:transparent;
                color:{hover_color};
                font-size:12.5px;
                font-weight:800;
                font-family:{FONT_FAMILY};
            """)

        def leave(e):
            ic.setStyleSheet(f"font-size:15px; background:transparent; color:{color};")
            txt.setStyleSheet(f"""
                background:transparent;
                color:{color};
                font-size:12.5px;
                font-weight:700;
                font-family:{FONT_FAMILY};
            """)

        btn.enterEvent = enter
        btn.leaveEvent = leave

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
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border-bottom:1px solid {BORDER};
            }}
        """)
        apply_shadow(bar, blur=14, y_offset=2, alpha=15)

        h = QHBoxLayout(bar)
        h.setContentsMargins(32, 0, 32, 0)
        h.setSpacing(16)

        # breadcrumb
        crumb_box = QVBoxLayout()
        crumb_box.setSpacing(2)

        crumb = QLabel("🏠  الرئيسية  ›  لوحة التحكم")
        crumb.setStyleSheet(f"""
            color:{TEXT_MUTED};
            font-size:10.5px;
            font-weight:700;
            background:transparent;
            letter-spacing:0.3px;
        """)
        crumb_box.addWidget(crumb)
        self._crumb_label = crumb

        # Page title
        self.page_title = QLabel("لوحة التحكم")
        self.page_title.setStyleSheet(f"""
            font-size:17px;
            font-weight:900;
            color:{TEXT};
            background:transparent;
            letter-spacing:0.2px;
        """)
        crumb_box.addWidget(self.page_title)

        h.addLayout(crumb_box)

        h.addStretch()

        # Status indicator (متصل)
        status_lbl = QLabel("●  متصل")
        status_lbl.setAlignment(Qt.AlignCenter)
        status_lbl.setFixedHeight(32)
        status_lbl.setStyleSheet("""
            QLabel {
                background:#ecfdf5;
                color:#059669;
                border:1px solid #a7f3d0;
                border-radius:16px;
                padding:0 14px;
                font-size:11px;
                font-weight:800;
            }
        """)
        h.addWidget(status_lbl)

        # Divider
        dv = QFrame()
        dv.setFixedWidth(1)
        dv.setFixedHeight(30)
        dv.setStyleSheet(f"background:{BORDER};")
        h.addWidget(dv)

        # User badge
        user_badge = QLabel(f"👤   {self.username}")
        user_badge.setAlignment(Qt.AlignCenter)
        user_badge.setFixedHeight(38)
        user_badge.setStyleSheet(f"""
            QLabel {{
                background:{PRIMARY_BG};
                color:{PRIMARY_DK};
                border:1px solid {PRIMARY_BRD};
                border-radius:19px;
                padding:0 18px;
                font-size:12px;
                font-weight:800;
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
            icons_map = {
                "لوحة التحكم": "🏠",
                "الشيفتات": "🕐",
                "الموظفين": "👥",
                "الحضور والانصراف": "✅",
                "المرتبات": "💰",
                "ربط البصمة": "🔌",
            }
            icon = icons_map.get(label, "🏠")
            if hasattr(self, "_crumb_label"):
                self._crumb_label.setText(f"🏠  الرئيسية  ›  {icon} {label}")

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
                width:9px; background:transparent; margin:2px;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2}; border-radius:4px; min-height:40px;
            }}
            QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height:0; }}
        """)

        w = QWidget()
        w.setStyleSheet(f"background:{BG};")
        v = QVBoxLayout(w)
        v.setContentsMargins(30, 26, 30, 30)
        v.setSpacing(22)

        # ====== إحصائيات ======
        v.addWidget(self._section_header("📊", "نظرة عامة", "إحصائيات سريعة عن النظام"))

        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        emp_count = self._safe_count(get_employees, [])
        shift_count = self._safe_count(get_shifts, [])
        punch_count = self._safe_count(count_raw_punches, 0)
        override_count = self._safe_count(count_all_overrides, 0)

        stats = [
            ("👥", "الموظفين",         emp_count,      PRIMARY, PRIMARY_BG, PRIMARY_BRD, "موظف نشط"),
            ("🕐", "الشيفتات",         shift_count,    SUCCESS, SUCCESS_BG, SUCCESS_BRD, "شيفت مسجّل"),
            ("📌", "البصمات المسجلة",  punch_count,    WARNING, WARNING_BG, WARNING_BRD, "بصمة إجمالية"),
            ("✎",  "تعديلات الحضور",   override_count, PURPLE,  PURPLE_BG,  PURPLE_BRD, "تعديل يدوي"),
        ]

        for i, (icon, label, value, color, bg, brd, unit) in enumerate(stats):
            card = self._make_stat_card(icon, label, value, color, bg, brd, unit)
            stats_grid.addWidget(card, 0, i)

        for c in range(4):
            stats_grid.setColumnStretch(c, 1)

        v.addLayout(stats_grid)

        # ====== إجراءات سريعة ======
        v.addWidget(self._section_header("⚡", "إجراءات سريعة", "انتقل مباشرة إلى الصفحات الرئيسية"))

        actions_grid = QGridLayout()
        actions_grid.setSpacing(16)

        actions = [
            ("🕐", "إنشاء شيفت جديد",   "أضف شيفتاً واربط الموظفين به",  PRIMARY, PRIMARY_BG, PRIMARY_BRD, "الشيفتات"),
            ("👥", "إضافة موظف",       "سجّل موظفاً جديداً بالنظام",    SUCCESS, SUCCESS_BG, SUCCESS_BRD, "الموظفين"),
            ("✅", "تسجيل حضور",       "سجّل بصمة حضور أو انصراف",     WARNING, WARNING_BG, WARNING_BRD, "الحضور والانصراف"),
            ("🔌", "ربط جهاز البصمة",   "استمع للبصمات فور حدوثها",     INFO,    INFO_BG,    INFO_BRD,    "ربط البصمة"),
            ("💰", "عرض المرتبات",     "احسب مرتبات الموظفين",          PURPLE,  PURPLE_BG,  PURPLE_BRD,  "المرتبات"),
        ]

        for i, (icon, title, desc, color, bg, brd, target) in enumerate(actions):
            card = self._make_action_card(icon, title, desc, color, bg, brd, target)
            actions_grid.addWidget(card, i // 3, i % 3)

        for c in range(3):
            actions_grid.setColumnStretch(c, 1)

        v.addLayout(actions_grid)

        # ====== دليل البداية ======
        v.addWidget(self._section_header("💡", "دليل البداية السريعة", "خطوات العمل بالترتيب"))

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

    def _section_header(self, icon, title, subtitle):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(2, 8, 2, 0)
        h.setSpacing(11)

        ic = QLabel(icon)
        ic.setFixedSize(36, 36)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"""
            QLabel {{
                background:{PRIMARY_BG};
                border:1px solid {PRIMARY_BRD};
                border-radius:10px;
                font-size:16px;
            }}
        """)
        h.addWidget(ic)

        v = QVBoxLayout()
        v.setSpacing(1)

        t = QLabel(title)
        t.setStyleSheet(f"""
            font-size:15px;
            font-weight:900;
            color:{TEXT};
            background:transparent;
        """)
        v.addWidget(t)

        s = QLabel(subtitle)
        s.setStyleSheet(f"""
            font-size:11px;
            color:{TEXT_MUTED};
            background:transparent;
        """)
        v.addWidget(s)

        h.addLayout(v)
        h.addStretch()

        return w

    def _make_stat_card(self, icon, label, value, color, bg, brd, unit):
        card = QFrame()
        card.setMinimumHeight(140)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
            QFrame:hover {{
                border:1.5px solid {brd};
            }}
        """)
        apply_shadow(card, blur=14, y_offset=3, alpha=22)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 20, 22, 20)
        v.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(12)

        ic = QLabel(icon)
        ic.setFixedSize(48, 48)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"""
            QLabel {{
                background:{bg};
                color:{color};
                border:1px solid {brd};
                border-radius:13px;
                font-size:21px;
                font-weight:900;
            }}
        """)
        top.addWidget(ic)
        top.addStretch()

        v.addLayout(top)

        val = QLabel(str(value))
        val.setStyleSheet(f"""
            font-size:32px;
            font-weight:900;
            color:{TEXT};
            background:transparent;
            letter-spacing:-0.5px;
        """)
        v.addWidget(val)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"""
            font-size:12px;
            color:{TEXT_SEC};
            background:transparent;
            font-weight:800;
        """)
        bottom.addWidget(lbl)

        bottom.addStretch()

        un = QLabel(unit)
        un.setStyleSheet(f"""
            font-size:10px;
            color:{color};
            background:{bg};
            border:1px solid {brd};
            border-radius:9px;
            padding:3px 9px;
            font-weight:800;
        """)
        bottom.addWidget(un)

        v.addLayout(bottom)

        return card

    def _make_action_card(self, icon, title, desc, color, bg, brd, target_page):
        card = QFrame()
        card.setMinimumHeight(140)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
            QFrame:hover {{
                background:{bg};
                border:1.5px solid {brd};
            }}
        """)
        apply_shadow(card, blur=12, y_offset=3, alpha=20)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 20, 22, 20)
        v.setSpacing(10)

        ic = QLabel(icon)
        ic.setFixedSize(46, 46)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"""
            QLabel {{
                background:{bg};
                border:1px solid {brd};
                border-radius:13px;
                font-size:19px;
            }}
        """)
        v.addWidget(ic)

        t = QLabel(title)
        t.setStyleSheet(f"""
            font-size:14.5px;
            font-weight:900;
            color:{TEXT};
            background:transparent;
        """)
        v.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet(f"""
            font-size:11px;
            color:{TEXT_MUTED};
            background:transparent;
        """)
        d.setWordWrap(True)
        v.addWidget(d)

        v.addStretch()

        arrow = QLabel("فتح الصفحة   ←")
        arrow.setStyleSheet(f"""
            color:{color};
            font-size:11px;
            font-weight:900;
            background:transparent;
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
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=14, y_offset=3, alpha=20)

        v = QVBoxLayout(card)
        v.setContentsMargins(26, 22, 26, 22)
        v.setSpacing(14)

        steps = [
            ("1", "أنشئ شيفت جديد",
             "اذهب إلى صفحة الشيفتات وحدّد أوقات العمل، أيام العمل، سياسة المرضية، والساعات الإضافية.",
             PRIMARY),
            ("2", "أضف الموظفين",
             "من صفحة الموظفين، سجّل بيانات كل موظف (كود، اسم، راتب، بدلات، تأمينات) واربطه بالشيفت.",
             SUCCESS),
            ("3", "اربط جهاز البصمة",
             "من صفحة «ربط البصمة»، أدخل IP الجهاز وفعّل «الاستماع التلقائي» لاستقبال البصمات فوراً.",
             INFO),
            ("4", "تابع الحضور والانصراف",
             "استعرض البصمات، عدّل الأيام، أضف إجازات، وتحقق من التأخير والإضافي والخصومات.",
             WARNING),
            ("5", "اعرض المرتبات",
             "احسب مرتبات الموظفين لكل فترة، اعرض التفاصيل، وصدّر الكشف كـ CSV.",
             PURPLE),
        ]

        for num, title, desc, color in steps:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background:{SURFACE_2};
                    border:1px solid {DIVIDER};
                    border-radius:12px;
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(16, 14, 16, 14)
            rl.setSpacing(16)

            badge = QLabel(num)
            badge.setFixedSize(38, 38)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(f"""
                QLabel {{
                    background:{color};
                    color:white;
                    border-radius:19px;
                    font-size:15px;
                    font-weight:900;
                }}
            """)
            rl.addWidget(badge)

            txt = QVBoxLayout()
            txt.setSpacing(3)
            tt = QLabel(title)
            tt.setStyleSheet(f"""
                font-size:13px;
                font-weight:900;
                color:{TEXT};
                background:transparent;
            """)
            txt.addWidget(tt)
            dd = QLabel(desc)
            dd.setStyleSheet(f"""
                font-size:11.5px;
                color:{TEXT_SEC};
                background:transparent;
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