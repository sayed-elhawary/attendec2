from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QStackedWidget, QGridLayout,
    QSizePolicy, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QPixmap, QIcon, QFont

from database import verify_user, create_user


# ============================================================
#     نظام ألوان مسطح وهادئ (نفس تصميم باقي التطبيق)
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

FONT_FAMILY = "Segoe UI, Tahoma, Arial, sans-serif"

RADIUS = "4px"


def _primary_btn_style(size=13):
    return f"""
        QPushButton {{
            background:{PRIMARY}; color:white;
            border:1px solid {PRIMARY}; border-radius:{RADIUS};
            padding:0 18px; font-weight:700; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ background:{PRIMARY_HOV}; border-color:{PRIMARY_HOV}; }}
        QPushButton:pressed {{ background:{PRIMARY_DK}; border-color:{PRIMARY_DK}; }}
    """


def _secondary_btn_style(size=13):
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


def _success_btn_style(size=13):
    return f"""
        QPushButton {{
            background:{SUCCESS}; color:white;
            border:1px solid {SUCCESS}; border-radius:{RADIUS};
            padding:0 18px; font-weight:700; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ background:{SUCCESS_HOV}; border-color:{SUCCESS_HOV}; }}
        QPushButton:pressed {{ background:#1f5f3c; border-color:#1f5f3c; }}
    """


def _link_btn_style(size=12):
    return f"""
        QPushButton {{
            background:transparent; color:{PRIMARY};
            border:none; border-radius:{RADIUS};
            padding:0 6px; font-weight:600; font-size:{size}px;
            font-family:{FONT_FAMILY};
        }}
        QPushButton:hover {{ color:{PRIMARY_HOV}; text-decoration:underline; }}
    """


def _input_style():
    return f"""
        QLineEdit {{
            background:{SURFACE}; border:1px solid {BORDER_2};
            border-radius:{RADIUS}; padding:0 12px;
            font-size:12.5px; color:{TEXT};
            font-family:{FONT_FAMILY};
        }}
        QLineEdit:hover {{ border-color:{TEXT_MUTED}; }}
        QLineEdit:focus {{ border:1px solid {PRIMARY}; }}
    """


def _field_label_style():
    return f"""
        QLabel {{
            font-size:11px;
            font-weight:700;
            color:{TEXT_SEC};
            background:transparent;
            font-family:{FONT_FAMILY};
        }}
    """


# ============================================================
#                  صفحة تسجيل الدخول
# ============================================================
class LoginPage(QWidget):
    logged_in = Signal(str)

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()

    # ========================================================
    #                    بناء الواجهة
    # ========================================================
    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # الجهة اليمنى: Branding
        outer.addWidget(self._build_brand_side(), 5)

        # الجهة اليسرى: نموذج الدخول
        outer.addWidget(self._build_form_side(), 4)

    # ----------------------------------------------------------
    #              الجهة اليمنى: الهوية البصرية
    # ----------------------------------------------------------
    def _build_brand_side(self):
        brand = QFrame()
        brand.setObjectName("brandSide")
        brand.setStyleSheet(f"""
            QFrame#brandSide {{
                background:{PRIMARY};
                border:none;
            }}
        """)

        layout = QVBoxLayout(brand)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)

        # Logo container
        logo_container = QFrame()
        logo_container.setFixedSize(180, 180)
        logo_container.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: {RADIUS};
            }}
        """)

        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(20, 20, 20, 20)
        logo_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("background:transparent; border:none;")

        # تحميل اللوجو من الملف
        try:
            pix = QPixmap("logo.png")
            if not pix.isNull():
                scaled = pix.scaled(
                    140, 140,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                logo_label.setPixmap(scaled)
            else:
                logo_label.setText("HR")
                logo_label.setStyleSheet(f"""
                    font-size:52px;
                    background:transparent;
                    color:white;
                    font-weight:700;
                    font-family:{FONT_FAMILY};
                    border:none;
                """)
        except Exception:
            logo_label.setText("HR")
            logo_label.setStyleSheet(f"""
                font-size:52px;
                background:transparent;
                color:white;
                font-weight:700;
                font-family:{FONT_FAMILY};
                border:none;
            """)

        logo_layout.addWidget(logo_label)
        layout.addWidget(logo_container, 0, Qt.AlignCenter)

        layout.addSpacing(24)

        # العنوان الرئيسي
        brand_title = QLabel("نظام الحضور والانصراف")
        brand_title.setAlignment(Qt.AlignCenter)
        brand_title.setStyleSheet(f"""
            QLabel {{
                color:white;
                font-size:26px;
                font-weight:700;
                background:transparent;
                font-family:{FONT_FAMILY};
                border:none;
            }}
        """)
        layout.addWidget(brand_title)

        # خط فاصل صغير
        line = QFrame()
        line.setFixedHeight(2)
        line.setFixedWidth(48)
        line.setStyleSheet("""
            background: rgba(255,255,255,0.45);
            border:none;
        """)
        layout.addWidget(line, 0, Qt.AlignCenter)

        # العنوان الفرعي
        brand_sub = QLabel("إدارة احترافية للحضور والانصراف والمرتبات")
        brand_sub.setAlignment(Qt.AlignCenter)
        brand_sub.setStyleSheet(f"""
            QLabel {{
                color: rgba(255,255,255,0.78);
                font-size:13px;
                background:transparent;
                font-weight:500;
                font-family:{FONT_FAMILY};
                border:none;
            }}
        """)
        layout.addWidget(brand_sub)

        layout.addSpacing(32)

        # قائمة الميزات — أرقام + نص (بدون أيقونات)
        features_items = [
            ("01", "تتبع البصمة والحضور"),
            ("02", "حساب المرتبات والخصومات"),
            ("03", "تقارير شاملة ودقيقة"),
        ]

        features_box = QVBoxLayout()
        features_box.setSpacing(8)

        for num, text in features_items:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.14);
                    border-radius: {RADIUS};
                }}
            """)
            rh = QHBoxLayout(row)
            rh.setContentsMargins(14, 10, 14, 10)
            rh.setSpacing(14)

            num_lbl = QLabel(num)
            num_lbl.setFixedSize(30, 30)
            num_lbl.setAlignment(Qt.AlignCenter)
            num_lbl.setStyleSheet(f"""
                QLabel {{
                    background: rgba(255,255,255,0.14);
                    color: white;
                    border: 1px solid rgba(255,255,255,0.22);
                    border-radius: {RADIUS};
                    font-size: 11.5px;
                    font-weight: 700;
                    font-family:{FONT_FAMILY};
                }}
            """)
            rh.addWidget(num_lbl)

            txt_lbl = QLabel(text)
            txt_lbl.setStyleSheet(f"""
                QLabel {{
                    color: rgba(255,255,255,0.92);
                    font-size: 12.5px;
                    font-weight: 600;
                    background: transparent;
                    font-family:{FONT_FAMILY};
                    border:none;
                }}
            """)
            rh.addWidget(txt_lbl)
            rh.addStretch()

            features_box.addWidget(row)

        layout.addLayout(features_box)
        layout.addStretch()

        # Footer
        footer = QLabel("جميع الحقوق محفوظة - 2026")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"""
            QLabel {{
                color: rgba(255,255,255,0.5);
                font-size: 11px;
                background: transparent;
                font-family:{FONT_FAMILY};
                border:none;
            }}
        """)
        layout.addWidget(footer)

        return brand

    # ----------------------------------------------------------
    #              الجهة اليسرى: الفورم
    # ----------------------------------------------------------
    def _build_form_side(self):
        container = QWidget()
        container.setObjectName("formSide")
        container.setStyleSheet(f"""
            QWidget#formSide {{
                background:{BG};
            }}
        """)

        outer_layout = QVBoxLayout(container)
        outer_layout.setContentsMargins(60, 40, 60, 40)
        outer_layout.setSpacing(0)
        outer_layout.setAlignment(Qt.AlignCenter)

        # البطاقة الرئيسية
        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(420)
        card.setStyleSheet(f"""
            QFrame#loginCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:{RADIUS};
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(0)

        # Stack للتبديل بين الدخول والتسجيل
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_form())
        self.stack.addWidget(self._build_register_form())
        card_layout.addWidget(self.stack)

        outer_layout.addWidget(card)
        return container

    # ========================================================
    #                نموذج تسجيل الدخول
    # ========================================================
    def _build_login_form(self):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header
        head = QVBoxLayout()
        head.setSpacing(6)

        title = QLabel("تسجيل الدخول")
        title.setStyleSheet(f"""
            font-size:22px;
            font-weight:700;
            color:{TEXT};
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        head.addWidget(title)

        sub = QLabel("مرحباً بك مجدداً — أدخل بياناتك للمتابعة")
        sub.setStyleSheet(f"""
            font-size:12px;
            color:{TEXT_MUTED};
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        head.addWidget(sub)

        v.addLayout(head)
        v.addSpacing(24)

        # حقل اسم المستخدم
        v.addWidget(self._field_label("اسم المستخدم"))
        v.addSpacing(6)
        self.login_user = self._input_field("أدخل اسم المستخدم")
        v.addWidget(self.login_user)

        v.addSpacing(14)

        # حقل كلمة المرور
        v.addWidget(self._field_label("كلمة المرور"))
        v.addSpacing(6)
        self.login_pass = self._input_field("أدخل كلمة المرور", password=True)
        v.addWidget(self.login_pass)

        v.addSpacing(12)

        # خيارات (تذكرني / نسيت كلمة المرور)
        options = QHBoxLayout()
        options.setSpacing(10)

        self.remember_cb = QCheckBox("تذكرني")
        self.remember_cb.setCursor(Qt.PointingHandCursor)
        self.remember_cb.setStyleSheet(self._checkbox_style())
        options.addWidget(self.remember_cb)
        options.addStretch()

        btn_forgot = QPushButton("نسيت كلمة المرور؟")
        btn_forgot.setCursor(Qt.PointingHandCursor)
        btn_forgot.setStyleSheet(_link_btn_style(11.5))
        options.addWidget(btn_forgot)

        v.addLayout(options)
        v.addSpacing(20)

        # زر الدخول
        btn_login = QPushButton("تسجيل الدخول")
        btn_login.setMinimumHeight(40)
        btn_login.setCursor(Qt.PointingHandCursor)
        btn_login.setStyleSheet(_primary_btn_style(13))
        btn_login.clicked.connect(self._do_login)
        v.addWidget(btn_login)

        v.addSpacing(14)

        # فاصل مع نص
        sep = QHBoxLayout()
        sep.setSpacing(10)
        line1 = QFrame()
        line1.setFixedHeight(1)
        line1.setStyleSheet(f"background:{BORDER}; border:none;")
        line2 = QFrame()
        line2.setFixedHeight(1)
        line2.setStyleSheet(f"background:{BORDER}; border:none;")
        sep_lbl = QLabel("ليس لديك حساب؟")
        sep_lbl.setStyleSheet(f"""
            font-size:11px;
            color:{TEXT_MUTED};
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        sep.addWidget(line1, 1)
        sep.addWidget(sep_lbl)
        sep.addWidget(line2, 1)
        v.addLayout(sep)

        v.addSpacing(14)

        # زر إنشاء حساب
        btn_go_register = QPushButton("إنشاء حساب جديد")
        btn_go_register.setMinimumHeight(40)
        btn_go_register.setCursor(Qt.PointingHandCursor)
        btn_go_register.setStyleSheet(_secondary_btn_style(13))
        btn_go_register.clicked.connect(self._go_to_register)
        v.addWidget(btn_go_register)

        v.addStretch()

        # ربط Enter
        self.login_pass._line_edit.returnPressed.connect(self._do_login)
        self.login_user._line_edit.returnPressed.connect(
            lambda: self.login_pass._line_edit.setFocus()
        )

        return w

    # ========================================================
    #                نموذج إنشاء حساب
    # ========================================================
    def _build_register_form(self):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header
        head = QVBoxLayout()
        head.setSpacing(6)

        title = QLabel("إنشاء حساب جديد")
        title.setStyleSheet(f"""
            font-size:22px;
            font-weight:700;
            color:{TEXT};
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        head.addWidget(title)

        sub = QLabel("سجّل حسابك للبدء في استخدام النظام")
        sub.setStyleSheet(f"""
            font-size:12px;
            color:{TEXT_MUTED};
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        head.addWidget(sub)

        v.addLayout(head)
        v.addSpacing(22)

        # اسم المستخدم
        v.addWidget(self._field_label("اسم المستخدم"))
        v.addSpacing(6)
        self.reg_user = self._input_field("اختر اسم مستخدم")
        v.addWidget(self.reg_user)

        v.addSpacing(12)

        # كلمة المرور
        v.addWidget(self._field_label("كلمة المرور"))
        v.addSpacing(6)
        self.reg_pass = self._input_field("اختر كلمة مرور قوية", password=True)
        v.addWidget(self.reg_pass)

        v.addSpacing(12)

        # تأكيد كلمة المرور
        v.addWidget(self._field_label("تأكيد كلمة المرور"))
        v.addSpacing(6)
        self.reg_pass2 = self._input_field("أعد كتابة كلمة المرور", password=True)
        v.addWidget(self.reg_pass2)

        v.addSpacing(20)

        # زر التسجيل
        btn_register = QPushButton("إنشاء الحساب")
        btn_register.setMinimumHeight(40)
        btn_register.setCursor(Qt.PointingHandCursor)
        btn_register.setStyleSheet(_success_btn_style(13))
        btn_register.clicked.connect(self._do_register)
        v.addWidget(btn_register)

        v.addSpacing(14)

        # فاصل
        sep = QHBoxLayout()
        sep.setSpacing(10)
        line1 = QFrame()
        line1.setFixedHeight(1)
        line1.setStyleSheet(f"background:{BORDER}; border:none;")
        line2 = QFrame()
        line2.setFixedHeight(1)
        line2.setStyleSheet(f"background:{BORDER}; border:none;")
        sep_lbl = QLabel("لديك حساب بالفعل؟")
        sep_lbl.setStyleSheet(f"""
            font-size:11px;
            color:{TEXT_MUTED};
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        sep.addWidget(line1, 1)
        sep.addWidget(sep_lbl)
        sep.addWidget(line2, 1)
        v.addLayout(sep)

        v.addSpacing(14)

        # زر الرجوع
        btn_back = QPushButton("العودة لتسجيل الدخول")
        btn_back.setMinimumHeight(40)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(_secondary_btn_style(13))
        btn_back.clicked.connect(self._go_to_login)
        v.addWidget(btn_back)

        v.addStretch()

        # Enter ينتقل بين الحقول وينفّذ التسجيل
        self.reg_user._line_edit.returnPressed.connect(
            lambda: self.reg_pass._line_edit.setFocus()
        )
        self.reg_pass._line_edit.returnPressed.connect(
            lambda: self.reg_pass2._line_edit.setFocus()
        )
        self.reg_pass2._line_edit.returnPressed.connect(self._do_register)

        return w

    # ========================================================
    #                عناصر مساعدة
    # ========================================================
    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(_field_label_style())
        return lbl

    def _input_field(self, placeholder, password=False):
        """حقل إدخال نظيف، مع زر إظهار/إخفاء نصي لكلمة المرور."""
        wrapper = QFrame()
        wrapper.setObjectName("inputWrap")
        wrapper.setFixedHeight(38)
        wrapper.setStyleSheet(f"""
            QFrame#inputWrap {{
                background:{SURFACE};
                border:1px solid {BORDER_2};
                border-radius:{RADIUS};
            }}
            QFrame#inputWrap:hover {{
                border-color:{TEXT_MUTED};
            }}
        """)

        h = QHBoxLayout(wrapper)
        h.setContentsMargins(12, 0, 8, 0)
        h.setSpacing(6)

        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFrame(False)
        if password:
            inp.setEchoMode(QLineEdit.Password)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background:transparent;
                border:none;
                padding:0;
                font-size:12.5px;
                color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
        """)
        h.addWidget(inp, 1)

        # زر إظهار/إخفاء كلمة المرور (نصي، بدون أيقونات)
        if password:
            toggle = QPushButton("عرض")
            toggle.setFixedHeight(24)
            toggle.setMinimumWidth(46)
            toggle.setCursor(Qt.PointingHandCursor)
            toggle.setCheckable(True)
            toggle.setToolTip("إظهار / إخفاء كلمة المرور")
            toggle.setStyleSheet(f"""
                QPushButton {{
                    background:transparent;
                    border:1px solid {BORDER};
                    border-radius:{RADIUS};
                    color:{TEXT_MUTED};
                    font-size:10.5px;
                    font-weight:600;
                    font-family:{FONT_FAMILY};
                    padding:0 8px;
                }}
                QPushButton:hover {{
                    border-color:{PRIMARY};
                    color:{PRIMARY};
                }}
                QPushButton:checked {{
                    background:{PRIMARY_BG};
                    border-color:{PRIMARY_BRD};
                    color:{PRIMARY};
                }}
            """)

            def _toggle_password(checked, field=inp, btn=toggle):
                if checked:
                    field.setEchoMode(QLineEdit.Normal)
                    btn.setText("إخفاء")
                else:
                    field.setEchoMode(QLineEdit.Password)
                    btn.setText("عرض")

            toggle.toggled.connect(_toggle_password)
            h.addWidget(toggle)

        # تخزين مرجع الحقل الفعلي
        wrapper._line_edit = inp
        return wrapper

    def _checkbox_style(self):
        return f"""
            QCheckBox {{
                font-size:11.5px;
                color:{TEXT_SEC};
                font-weight:600;
                background:transparent;
                spacing:7px;
                font-family:{FONT_FAMILY};
            }}
            QCheckBox::indicator {{
                width:15px;
                height:15px;
                border:1px solid {BORDER_2};
                border-radius:3px;
                background:white;
            }}
            QCheckBox::indicator:hover {{
                border-color:{PRIMARY};
            }}
            QCheckBox::indicator:checked {{
                background:{PRIMARY};
                border-color:{PRIMARY};
            }}
        """

    # ========================================================
    #                التنقل بين الفورم
    # ========================================================
    def _go_to_register(self):
        self.stack.setCurrentIndex(1)
        self.reg_user._line_edit.setFocus()

    def _go_to_login(self):
        self.stack.setCurrentIndex(0)
        self.login_user._line_edit.setFocus()

    # ========================================================
    #                    أحداث الدخول
    # ========================================================
    def _do_login(self):
        u = self.login_user._line_edit.text().strip()
        p = self.login_pass._line_edit.text()

        if not u or not p:
            QMessageBox.warning(self, "تنبيه", "أدخل اسم المستخدم وكلمة المرور")
            return

        if verify_user(u, p):
            self.logged_in.emit(u)
        else:
            QMessageBox.critical(self, "خطأ", "بيانات الدخول غير صحيحة")

    def _do_register(self):
        u = self.reg_user._line_edit.text().strip()
        p = self.reg_pass._line_edit.text()
        p2 = self.reg_pass2._line_edit.text()

        if not u or not p:
            QMessageBox.warning(self, "تنبيه", "املأ كل الحقول")
            return
        if len(u) < 3:
            QMessageBox.warning(self, "تنبيه", "اسم المستخدم يجب أن يكون 3 أحرف على الأقل")
            return
        if len(p) < 4:
            QMessageBox.warning(self, "تنبيه", "كلمة المرور يجب أن تكون 4 أحرف على الأقل")
            return
        if p != p2:
            QMessageBox.warning(self, "تنبيه", "كلمتا المرور غير متطابقتين")
            return

        ok, msg = create_user(u, p)
        if ok:
            QMessageBox.information(self, "تم", msg)

            # امسح حقول التسجيل
            self.reg_user._line_edit.clear()
            self.reg_pass._line_edit.clear()
            self.reg_pass2._line_edit.clear()

            # انتقل لتسجيل الدخول مع تعبئة اسم المستخدم
            self.stack.setCurrentIndex(0)
            self.login_user._line_edit.setText(u)
            self.login_pass._line_edit.setFocus()
        else:
            QMessageBox.critical(self, "خطأ", msg)