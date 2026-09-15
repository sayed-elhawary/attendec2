from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QStackedWidget, QGridLayout,
    QGraphicsDropShadowEffect, QSizePolicy, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QPixmap, QIcon, QFont

from database import verify_user, create_user


# ============================================================
#                نظام الألوان
# ============================================================
BG          = "#f1f5f9"
SURFACE     = "#ffffff"
SURFACE_2   = "#f8fafc"
BORDER      = "#e2e8f0"
BORDER_2    = "#cbd5e1"

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
DANGER_BG   = "#fef2f2"
DANGER_BRD  = "#fecaca"

FONT_FAMILY = "Segoe UI, Tahoma, Arial, sans-serif"


def apply_shadow(widget, blur=30, y_offset=8, alpha=40):
    """ظل ناعم احترافي"""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    effect.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(effect)
    return effect


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

        # الجهة اليمنى: Branding (اللوجو + العنوان)
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
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {NAVY},
                    stop:0.5 {NAVY_2},
                    stop:1 {NAVY_3});
                border:none;
            }}
        """)

        layout = QVBoxLayout(brand)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignCenter)

        # Logo container
        logo_container = QFrame()
        logo_container.setFixedSize(220, 220)
        logo_container.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.06);
                border: 2px solid rgba(255,255,255,0.12);
                border-radius: 30px;
            }
        """)
        apply_shadow(logo_container, blur=40, y_offset=10, alpha=60)

        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(24, 24, 24, 24)
        logo_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("background:transparent;")

        # ✅ تحميل اللوجو من الملف
        try:
            pix = QPixmap("logo.png")
            if not pix.isNull():
                scaled = pix.scaled(
                    170, 170,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                logo_label.setPixmap(scaled)
            else:
                logo_label.setText("⏱")
                logo_label.setStyleSheet(
                    "font-size:80px; background:transparent; color:white;"
                )
        except Exception:
            logo_label.setText("⏱")
            logo_label.setStyleSheet(
                "font-size:80px; background:transparent; color:white;"
            )

        logo_layout.addWidget(logo_label)
        layout.addWidget(logo_container, 0, Qt.AlignCenter)

        layout.addSpacing(20)

        # العنوان الرئيسي
        brand_title = QLabel("نظام الحضور والانصراف")
        brand_title.setAlignment(Qt.AlignCenter)
        brand_title.setStyleSheet(f"""
            QLabel {{
                color:white;
                font-size:32px;
                font-weight:900;
                background:transparent;
                font-family:{FONT_FAMILY};
                letter-spacing:0.5px;
            }}
        """)
        layout.addWidget(brand_title)

        # خط فاصل صغير
        line = QFrame()
        line.setFixedHeight(3)
        line.setFixedWidth(80)
        line.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {PRIMARY}, stop:1 #60a5fa);
            border-radius:2px;
        """)
        layout.addWidget(line, 0, Qt.AlignCenter)

        # العنوان الفرعي
        brand_sub = QLabel("إدارة احترافية للحضور والانصراف والمرتبات")
        brand_sub.setAlignment(Qt.AlignCenter)
        brand_sub.setStyleSheet("""
            QLabel {
                color:#94a8c4;
                font-size:14px;
                background:transparent;
                font-weight:500;
                letter-spacing:0.3px;
            }
        """)
        layout.addWidget(brand_sub)

        layout.addSpacing(30)

        # شارات الميزات
        features = QHBoxLayout()
        features.setSpacing(14)
        features.setAlignment(Qt.AlignCenter)

        feat_items = [
            ("🕐", "تتبع البصمة"),
            ("💰", "حساب المرتبات"),
            ("📊", "تقارير شاملة"),
        ]

        for icon, text in feat_items:
            box = QFrame()
            box.setStyleSheet("""
                QFrame {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 12px;
                }
            """)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(16, 12, 16, 12)
            bl.setSpacing(4)
            bl.setAlignment(Qt.AlignCenter)

            ic = QLabel(icon)
            ic.setAlignment(Qt.AlignCenter)
            ic.setStyleSheet("font-size:22px; background:transparent;")
            bl.addWidget(ic)

            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("""
                color:#dbeafe;
                font-size:11px;
                background:transparent;
                font-weight:600;
            """)
            bl.addWidget(lbl)

            features.addWidget(box)

        layout.addLayout(features)
        layout.addStretch()

        # Footer
        footer = QLabel("© 2026 · جميع الحقوق محفوظة")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            color:#64748b;
            font-size:10px;
            background:transparent;
            letter-spacing:0.5px;
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
        card.setFixedWidth(440)
        card.setStyleSheet(f"""
            QFrame#loginCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:20px;
            }}
        """)
        apply_shadow(card, blur=40, y_offset=12, alpha=30)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
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
            font-size:26px;
            font-weight:900;
            color:{TEXT};
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        head.addWidget(title)

        sub = QLabel("مرحباً بك مجدداً — أدخل بياناتك للمتابعة")
        sub.setStyleSheet(f"""
            font-size:12.5px;
            color:{TEXT_MUTED};
            background:transparent;
        """)
        head.addWidget(sub)

        v.addLayout(head)
        v.addSpacing(28)

        # حقل اسم المستخدم
        v.addWidget(self._field_label("اسم المستخدم"))
        self.login_user = self._input_with_icon("👤", "أدخل اسم المستخدم")
        v.addWidget(self.login_user)

        v.addSpacing(16)

        # حقل كلمة المرور
        v.addWidget(self._field_label("كلمة المرور"))
        self.login_pass = self._input_with_icon(
            "🔒", "أدخل كلمة المرور", password=True
        )
        v.addWidget(self.login_pass)

        v.addSpacing(12)

        # خيارات (تذكرني)
        options = QHBoxLayout()
        options.setSpacing(10)

        self.remember_cb = QCheckBox("تذكرني")
        self.remember_cb.setCursor(Qt.PointingHandCursor)
        self.remember_cb.setStyleSheet(f"""
            QCheckBox {{
                font-size:11.5px;
                color:{TEXT_SEC};
                font-weight:600;
                background:transparent;
                spacing:7px;
            }}
            QCheckBox::indicator {{
                width:16px;
                height:16px;
                border:1.5px solid {BORDER_2};
                border-radius:5px;
                background:white;
            }}
            QCheckBox::indicator:hover {{
                border-color:{PRIMARY};
            }}
            QCheckBox::indicator:checked {{
                background:{PRIMARY};
                border-color:{PRIMARY};
            }}
        """)
        options.addWidget(self.remember_cb)
        options.addStretch()

        forgot = QLabel("نسيت كلمة المرور؟")
        forgot.setStyleSheet(f"""
            font-size:11.5px;
            color:{PRIMARY};
            font-weight:700;
            background:transparent;
        """)
        forgot.setCursor(Qt.PointingHandCursor)
        options.addWidget(forgot)

        v.addLayout(options)
        v.addSpacing(24)

        # زر الدخول
        btn_login = QPushButton("🔓   تسجيل الدخول")
        btn_login.setMinimumHeight(48)
        btn_login.setCursor(Qt.PointingHandCursor)
        btn_login.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_HOV});
                color:white;
                border:none;
                border-radius:12px;
                font-size:14px;
                font-weight:900;
                font-family:{FONT_FAMILY};
                padding:0 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 {PRIMARY_HOV});
            }}
            QPushButton:pressed {{
                background:{PRIMARY_DK};
            }}
        """)
        btn_login.clicked.connect(self._do_login)
        v.addWidget(btn_login)

        v.addSpacing(14)

        # فاصل مع نص
        sep = QHBoxLayout()
        sep.setSpacing(10)
        line1 = QFrame(); line1.setFixedHeight(1); line1.setStyleSheet(f"background:{BORDER};")
        line2 = QFrame(); line2.setFixedHeight(1); line2.setStyleSheet(f"background:{BORDER};")
        sep_lbl = QLabel("ليس لديك حساب؟")
        sep_lbl.setStyleSheet(f"font-size:11px; color:{TEXT_MUTED}; background:transparent;")
        sep.addWidget(line1, 1)
        sep.addWidget(sep_lbl)
        sep.addWidget(line2, 1)
        v.addLayout(sep)

        v.addSpacing(14)

        # زر إنشاء حساب
        btn_go_register = QPushButton("✨   إنشاء حساب جديد")
        btn_go_register.setMinimumHeight(46)
        btn_go_register.setCursor(Qt.PointingHandCursor)
        btn_go_register.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE};
                color:{PRIMARY_DK};
                border:1.5px solid {PRIMARY_BRD};
                border-radius:12px;
                font-size:13px;
                font-weight:800;
                font-family:{FONT_FAMILY};
                padding:0 20px;
            }}
            QPushButton:hover {{
                background:{PRIMARY_BG};
                border-color:{PRIMARY};
            }}
            QPushButton:pressed {{
                background:{PRIMARY_BRD};
            }}
        """)
        btn_go_register.clicked.connect(self._go_to_register)
        v.addWidget(btn_go_register)

        v.addStretch()

        # ✅ الإصلاح: استخدم _line_edit للوصول لحقل الإدخال الفعلي
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
            font-size:24px;
            font-weight:900;
            color:{TEXT};
            background:transparent;
            font-family:{FONT_FAMILY};
        """)
        head.addWidget(title)

        sub = QLabel("سجّل حسابك للبدء في استخدام النظام")
        sub.setStyleSheet(f"""
            font-size:12.5px;
            color:{TEXT_MUTED};
            background:transparent;
        """)
        head.addWidget(sub)

        v.addLayout(head)
        v.addSpacing(24)

        # اسم المستخدم
        v.addWidget(self._field_label("اسم المستخدم"))
        self.reg_user = self._input_with_icon("👤", "اختر اسم مستخدم")
        v.addWidget(self.reg_user)
        v.addSpacing(14)

        # كلمة المرور
        v.addWidget(self._field_label("كلمة المرور"))
        self.reg_pass = self._input_with_icon(
            "🔒", "اختر كلمة مرور قوية", password=True
        )
        v.addWidget(self.reg_pass)
        v.addSpacing(14)

        # تأكيد كلمة المرور
        v.addWidget(self._field_label("تأكيد كلمة المرور"))
        self.reg_pass2 = self._input_with_icon(
            "🔒", "أعد كتابة كلمة المرور", password=True
        )
        v.addWidget(self.reg_pass2)
        v.addSpacing(22)

        # زر التسجيل
        btn_register = QPushButton("✅   إنشاء الحساب")
        btn_register.setMinimumHeight(48)
        btn_register.setCursor(Qt.PointingHandCursor)
        btn_register.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                color:white;
                border:none;
                border-radius:12px;
                font-size:14px;
                font-weight:900;
                font-family:{FONT_FAMILY};
                padding:0 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 {SUCCESS_HOV});
            }}
            QPushButton:pressed {{
                background:#065f46;
            }}
        """)
        btn_register.clicked.connect(self._do_register)
        v.addWidget(btn_register)

        v.addSpacing(14)

        # فاصل
        sep = QHBoxLayout()
        sep.setSpacing(10)
        line1 = QFrame(); line1.setFixedHeight(1); line1.setStyleSheet(f"background:{BORDER};")
        line2 = QFrame(); line2.setFixedHeight(1); line2.setStyleSheet(f"background:{BORDER};")
        sep_lbl = QLabel("لديك حساب بالفعل؟")
        sep_lbl.setStyleSheet(f"font-size:11px; color:{TEXT_MUTED}; background:transparent;")
        sep.addWidget(line1, 1)
        sep.addWidget(sep_lbl)
        sep.addWidget(line2, 1)
        v.addLayout(sep)

        v.addSpacing(14)

        # زر الرجوع
        btn_back = QPushButton("←   العودة لتسجيل الدخول")
        btn_back.setMinimumHeight(46)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE};
                color:{TEXT_SEC};
                border:1.5px solid {BORDER_2};
                border-radius:12px;
                font-size:13px;
                font-weight:800;
                font-family:{FONT_FAMILY};
                padding:0 20px;
            }}
            QPushButton:hover {{
                background:{SURFACE_2};
                border-color:{TEXT_MUTED};
                color:{TEXT};
            }}
        """)
        btn_back.clicked.connect(self._go_to_login)
        v.addWidget(btn_back)

        v.addStretch()

        # ✅ الإصلاح: استخدم _line_edit
        self.reg_pass2._line_edit.returnPressed.connect(self._do_register)

        return w

    # ========================================================
    #                عناصر مساعدة
    # ========================================================
    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            font-size:11.5px;
            font-weight:800;
            color:{TEXT_SEC};
            background:transparent;
            font-family:{FONT_FAMILY};
            letter-spacing:0.2px;
            padding-bottom:2px;
        """)
        return lbl

    def _input_with_icon(self, icon, placeholder, password=False):
        """حقل إدخال بأيقونة داخلية على اليمين (RTL)"""
        wrapper = QFrame()
        wrapper.setObjectName("inputWrap")
        wrapper.setFixedHeight(48)
        wrapper.setStyleSheet(f"""
            QFrame#inputWrap {{
                background:{SURFACE_2};
                border:1.5px solid {BORDER};
                border-radius:11px;
            }}
            QFrame#inputWrap:hover {{
                background:white;
                border-color:{BORDER_2};
            }}
        """)

        h = QHBoxLayout(wrapper)
        h.setContentsMargins(14, 0, 14, 0)
        h.setSpacing(10)

        # الأيقونة (يسار في RTL يعني تظهر على يمين الحقل بصريًا)
        ic = QLabel(icon)
        ic.setFixedSize(24, 24)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"""
            font-size:15px;
            background:transparent;
            color:{TEXT_MUTED};
        """)
        h.addWidget(ic)

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
                font-size:13px;
                color:{TEXT};
                font-family:{FONT_FAMILY};
            }}
            QLineEdit::placeholder {{
                color:{TEXT_MUTED};
            }}
        """)
        h.addWidget(inp, 1)

        # زر إظهار/إخفاء كلمة المرور (فقط للحقول السرية)
        if password:
            toggle = QPushButton("👁")
            toggle.setFixedSize(26, 26)
            toggle.setCursor(Qt.PointingHandCursor)
            toggle.setCheckable(True)
            toggle.setToolTip("إظهار / إخفاء كلمة المرور")
            toggle.setStyleSheet(f"""
                QPushButton {{
                    background:transparent;
                    border:none;
                    color:{TEXT_MUTED};
                    font-size:14px;
                    border-radius:6px;
                }}
                QPushButton:hover {{
                    background:{PRIMARY_BG};
                    color:{PRIMARY};
                }}
                QPushButton:checked {{
                    color:{PRIMARY};
                }}
            """)

            def _toggle_password(checked, field=inp, btn=toggle):
                if checked:
                    field.setEchoMode(QLineEdit.Normal)
                    btn.setText("🙈")
                else:
                    field.setEchoMode(QLineEdit.Password)
                    btn.setText("👁")

            toggle.toggled.connect(_toggle_password)
            h.addWidget(toggle)

        # تخزين مرجع الحقل الفعلي داخل wrapper
        wrapper._line_edit = inp
        return wrapper

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