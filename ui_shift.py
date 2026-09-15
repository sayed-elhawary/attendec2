from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QFrame, QGridLayout, QGraphicsDropShadowEffect,
    QAbstractItemView, QDialog
)
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import (
    QDoubleValidator, QIntValidator, QColor, QRegularExpressionValidator
)
from database import (
    add_shift, get_shifts, get_shift, get_shift_deductions,
    update_shift, delete_shift
)


ARABIC_DAYS = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]

DEDUCTION_LABELS = {
    "minutes": "دقائق محددة",
    "quarter": "ربع يوم",
    "half": "نص يوم",
    "full": "يوم كامل",
}

SICK_LABELS = {
    "none": "بدون خصم",
    "quarter": "خصم ربع يوم",
    "half": "خصم نص يوم",
    "full": "خصم يوم كامل",
}

OT_LABELS = {
    1.0: "الساعة بساعة",
    1.5: "الساعة بساعة ونصف",
    2.0: "الساعة بساعتين",
}

# ============================================================
#                نظام الألوان الاحترافي
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

TIME_REGEX = QRegularExpression(r"^([01]\d|2[0-3]):([0-5]\d)$")


def apply_shadow(widget, blur=18, y_offset=2):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    effect.setColor(QColor(15, 23, 42, 15))
    widget.setGraphicsEffect(effect)
    return effect


# ============================================================
#                       صفحة الشيفتات
# ============================================================
class ShiftPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._deductions = []
        self._editing_id = None
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_shifts()

    # ========================================================
    #                    بناء الواجهة
    # ========================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        body = QWidget()
        body.setObjectName("shiftBody")
        body.setStyleSheet(f"QWidget#shiftBody {{ background:{BG}; }}")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(26, 22, 26, 26)
        body_layout.setSpacing(18)

        body_layout.addWidget(self._build_stats())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background:transparent; border:none; }}
            QScrollBar:vertical {{
                width:8px; background:transparent; margin:2px 0;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2}; border-radius:4px; min-height:36px;
            }}
            QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height:0; }}
        """)

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(18)

        top_row = QHBoxLayout()
        top_row.setSpacing(18)
        top_row.addWidget(self._build_main_card(), 5)
        top_row.addWidget(self._build_policies_card(), 3)
        cv.addLayout(top_row)

        cv.addWidget(self._build_days_card())
        cv.addWidget(self._build_deductions_card())
        cv.addWidget(self._build_save_row())
        cv.addWidget(self._build_shifts_table_card())

        scroll.setWidget(content)
        body_layout.addWidget(scroll, 1)
        root.addWidget(body, 1)

    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("shiftTopbar")
        bar.setFixedHeight(90)
        bar.setStyleSheet(f"""
            QFrame#shiftTopbar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:1 {NAVY_2});
                border:none;
            }}
        """)

        h = QHBoxLayout(bar)
        h.setContentsMargins(30, 0, 30, 0)
        h.setSpacing(18)

        icon = QLabel("🕐")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(50, 50)
        icon.setStyleSheet(f"""
            QLabel {{
                background:{NAVY_3};
                border:1px solid {NAVY_ACCENT};
                border-radius:14px;
                font-size:23px;
            }}
        """)
        h.addWidget(icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("إدارة الشيفتات")
        title.setStyleSheet(f"""
            QLabel {{
                color:white; font-size:21px; font-weight:800;
                background:transparent; font-family:{FONT_FAMILY};
            }}
        """)
        title_box.addWidget(title)

        subtitle = QLabel("إنشاء وتعديل الشيفتات وسياسات الحضور والخصومات")
        subtitle.setStyleSheet(
            "QLabel { color:#94a8c4; font-size:11px; background:transparent; }"
        )
        title_box.addWidget(subtitle)
        h.addLayout(title_box)
        h.addStretch()

        return bar

    def _build_stats(self):
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.stat_total = self._stat_card(
            "إجمالي الشيفتات", "0", "🕐", PRIMARY, PRIMARY_BG, PRIMARY_BRD
        )
        self.stat_morning = self._stat_card(
            "الشيفتات الصباحية", "0", "☀️", SUCCESS, SUCCESS_BG, SUCCESS_BRD
        )
        self.stat_evening = self._stat_card(
            "الشيفتات المسائية", "0", "🌙", PURPLE, PURPLE_BG, PURPLE_BRD
        )
        self.stat_hours = self._stat_card(
            "متوسط الساعات", "0", "⏱", INFO, INFO_BG, INFO_BRD
        )

        grid.addWidget(self.stat_total, 0, 0)
        grid.addWidget(self.stat_morning, 0, 1)
        grid.addWidget(self.stat_evening, 0, 2)
        grid.addWidget(self.stat_hours, 0, 3)

        for col in range(4):
            grid.setColumnStretch(col, 1)

        return wrap

    def _stat_card(self, title, value, icon_text, color, soft, border_color):
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
                border:1px solid {border_color};
            }}
        """)
        apply_shadow(card, blur=14, y_offset=2)

        h = QHBoxLayout(card)
        h.setContentsMargins(18, 14, 18, 14)
        h.setSpacing(14)

        ic = QLabel(icon_text)
        ic.setAlignment(Qt.AlignCenter)
        ic.setFixedSize(48, 48)
        ic.setStyleSheet(f"""
            QLabel {{
                background:{soft};
                color:{color};
                border:1px solid {border_color};
                border-radius:13px;
                font-size:20px;
                font-weight:900;
            }}
        """)
        h.addWidget(ic)

        v = QVBoxLayout()
        v.setSpacing(2)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size:10px; color:{TEXT_MUTED}; font-weight:800; "
            f"background:transparent; letter-spacing:0.3px;"
        )
        v.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size:24px; color:{TEXT}; font-weight:900; background:transparent;"
        )
        v.addWidget(val)

        h.addLayout(v)
        h.addStretch()
        card._value_label = val
        return card

    def _build_main_card(self):
        card = QFrame()
        card.setObjectName("mainCard")
        card.setStyleSheet(f"""
            QFrame#mainCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=3)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 22, 22, 22)
        v.setSpacing(16)

        v.addWidget(self._card_header(
            "📋", "بيانات الشيفت", "أدخل المعلومات الأساسية للشيفت", PRIMARY
        ))

        g = QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(14)

        self.shift_name = self._input("مثال: شيفت صباحي")
        self.shift_type = self._combo()

        self.work_hours = self._num_input("8")
        self.work_hours.setValidator(QDoubleValidator(0.5, 24, 2))
        self.work_hours.setText("8")

        self.start_time = self._time_input("08:00")
        self.end_time = self._time_input("16:00")

        self.shift_type.addItem("صباحي", "morning")
        self.shift_type.addItem("مسائي", "evening")
        self.shift_type.currentIndexChanged.connect(self._on_shift_type_changed)

        g.addWidget(self._field("اسم الشيفت", self.shift_name), 0, 0, 1, 2)
        g.addWidget(self._field("نوع الشيفت", self.shift_type), 0, 2)
        g.addWidget(self._field("عدد ساعات العمل", self.work_hours), 0, 3)

        g.addWidget(self._field("بداية الشيفت", self.start_time), 1, 0)
        g.addWidget(self._field("نهاية الشيفت", self.end_time), 1, 1)

        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(2, 1)
        g.setColumnStretch(3, 1)

        v.addLayout(g)

        self.shift_hint = QLabel("ℹ️  الشيفت الصباحي: الحضور والانصراف في نفس اليوم")
        self.shift_hint.setWordWrap(True)
        self.shift_hint.setStyleSheet(
            "color:#1e40af; background:#eff6ff; padding:12px; "
            "border-radius:10px; font-size:12px; font-weight:700; "
            "border:1px solid #bfdbfe;"
        )
        v.addWidget(self.shift_hint)

        v.addStretch()
        return card

    def _build_policies_card(self):
        card = QFrame()
        card.setObjectName("policiesCard")
        card.setStyleSheet(f"""
            QFrame#policiesCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=3)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 22, 22, 22)
        v.setSpacing(16)

        v.addWidget(self._card_header(
            "⚙️", "سياسات الحضور", "قواعد الإجازات والساعات الإضافية", SUCCESS
        ))

        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(14)

        self.sick_leave = self._combo()
        for key, label in SICK_LABELS.items():
            self.sick_leave.addItem(label, key)

        self.overtime_rate = self._combo()
        for rate, label in OT_LABELS.items():
            self.overtime_rate.addItem(label, rate)

        g.addWidget(self._field("الإجازة المرضية", self.sick_leave), 0, 0)
        g.addWidget(self._field("الساعات الإضافية", self.overtime_rate), 1, 0)
        g.setColumnStretch(0, 1)

        v.addLayout(g)
        v.addStretch()
        return card

    def _build_days_card(self):
        card = QFrame()
        card.setObjectName("daysCard")
        card.setStyleSheet(f"""
            QFrame#daysCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=3)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 20, 22, 20)
        v.setSpacing(14)

        v.addWidget(self._card_header(
            "📅", "أيام العمل", "اختر أيام العمل الأسبوعية للشيفت", INFO
        ))

        days_wrap = QWidget()
        days_wrap.setStyleSheet("background:transparent;")
        days_grid = QGridLayout(days_wrap)
        days_grid.setHorizontalSpacing(10)
        days_grid.setVerticalSpacing(10)

        self.day_checks = []
        for i, day in enumerate(ARABIC_DAYS):
            cb = QCheckBox(day)
            cb.setChecked(i < 5)
            cb.setCursor(Qt.PointingHandCursor)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    background:{SURFACE_2};
                    border:1px solid {BORDER};
                    border-radius:10px;
                    padding:10px 14px;
                    font-size:12px;
                    font-weight:800;
                    color:{TEXT_SEC};
                    spacing:8px;
                    min-width:90px;
                }}
                QCheckBox:hover {{
                    background:{PRIMARY_BG};
                    border-color:{PRIMARY_BRD};
                    color:{PRIMARY_DK};
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
            self.day_checks.append(cb)
            days_grid.addWidget(cb, 0, i)

        for i in range(len(ARABIC_DAYS)):
            days_grid.setColumnStretch(i, 1)

        v.addWidget(days_wrap)
        return card

    def _build_deductions_card(self):
        card = QFrame()
        card.setObjectName("dedCard")
        card.setStyleSheet(f"""
            QFrame#dedCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=3)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 20, 22, 20)
        v.setSpacing(14)

        v.addWidget(self._card_header(
            "⏰", "قواعد الخصم", "أضف قواعد الخصم على التأخير والانصراف المبكر", WARNING
        ))

        add_row = QFrame()
        add_row.setObjectName("dedAddRow")
        add_row.setStyleSheet(f"""
            QFrame#dedAddRow {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:12px;
            }}
        """)
        ar = QHBoxLayout(add_row)
        ar.setContentsMargins(16, 14, 16, 14)
        ar.setSpacing(12)

        self.ded_from = self._time_input("09:00")
        self.ded_to = self._time_input("10:00")

        self.ded_type = self._combo()
        for k, label in DEDUCTION_LABELS.items():
            self.ded_type.addItem(label, k)
        self.ded_type.currentIndexChanged.connect(self._on_ded_type_changed)

        self.ded_value = self._num_input("دقائق")
        self.ded_value.setValidator(QIntValidator(1, 480))
        self.ded_value.setVisible(False)

        ar.addWidget(self._field("من", self.ded_from), 2)
        ar.addWidget(self._field("إلى", self.ded_to), 2)
        ar.addWidget(self._field("نوع الخصم", self.ded_type), 2)
        ar.addWidget(self._field("القيمة", self.ded_value), 2)

        btn_add_ded = QPushButton("➕  إضافة")
        btn_add_ded.setFixedHeight(40)
        btn_add_ded.setMinimumWidth(110)
        btn_add_ded.setCursor(Qt.PointingHandCursor)
        btn_add_ded.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {WARNING}, stop:1 {WARNING_HOV});
                color:white; border:none;
                border-radius:10px; padding:0 18px;
                font-weight:900; font-size:12px;
            }}
            QPushButton:hover {{
                background:{WARNING_HOV};
            }}
        """)
        btn_add_ded.clicked.connect(self._add_deduction)

        btn_wrap = QWidget()
        btn_wrap.setStyleSheet("background:transparent;")
        bw = QVBoxLayout(btn_wrap)
        bw.setContentsMargins(0, 0, 0, 0)
        bw.setSpacing(6)
        spacer = QLabel("")
        spacer.setFixedHeight(14)
        bw.addWidget(spacer)
        bw.addWidget(btn_add_ded)

        ar.addWidget(btn_wrap, 1)
        v.addWidget(add_row)

        self.ded_table = QTableWidget(0, 5)
        self.ded_table.setHorizontalHeaderLabels(["من", "إلى", "النوع", "القيمة", ""])
        self.ded_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ded_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.ded_table.setColumnWidth(4, 70)
        self.ded_table.verticalHeader().setVisible(False)
        self.ded_table.setShowGrid(False)
        self.ded_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ded_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ded_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ded_table.setFocusPolicy(Qt.NoFocus)
        self.ded_table.setMinimumHeight(120)
        self.ded_table.setMaximumHeight(220)
        self.ded_table.verticalHeader().setDefaultSectionSize(44)
        self.ded_table.setStyleSheet(f"""
            QTableWidget {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:10px;
                color:{TEXT};
                font-size:11.5px;
                outline:none;
                gridline-color:transparent;
            }}
            QTableWidget::item {{
                padding:6px 8px;
                border-bottom:1px solid {DIVIDER};
            }}
            QTableWidget::item:selected {{
                background:{WARNING_BG};
                color:{TEXT};
            }}
            QHeaderView::section {{
                background:{HEADER_BG};
                color:{TEXT_MUTED};
                padding:10px 8px;
                border:none;
                border-bottom:1px solid {BORDER};
                font-weight:900;
                font-size:10px;
            }}
        """)
        v.addWidget(self.ded_table)
        return card

    def _build_save_row(self):
        wrap = QFrame()
        wrap.setObjectName("saveRow")
        wrap.setStyleSheet(f"""
            QFrame#saveRow {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NAVY}, stop:1 {NAVY_2});
                border-radius:14px;
            }}
        """)
        apply_shadow(wrap, blur=18, y_offset=3)

        h = QHBoxLayout(wrap)
        h.setContentsMargins(22, 16, 22, 16)
        h.setSpacing(14)

        self.save_icon = QLabel("💾")
        self.save_icon.setAlignment(Qt.AlignCenter)
        self.save_icon.setFixedSize(44, 44)
        self.save_icon.setStyleSheet(f"""
            QLabel {{
                background:{NAVY_3};
                border:1px solid {NAVY_ACCENT};
                border-radius:12px;
                font-size:20px;
            }}
        """)
        h.addWidget(self.save_icon)

        tbox = QVBoxLayout()
        tbox.setSpacing(2)

        self.save_title = QLabel("جاهز للحفظ؟")
        self.save_title.setStyleSheet(
            "font-size:14px; font-weight:900; color:white; background:transparent;"
        )
        tbox.addWidget(self.save_title)

        self.save_sub = QLabel("سيتم إضافة الشيفت الجديد إلى النظام فوراً")
        self.save_sub.setStyleSheet(
            "font-size:10px; color:#94a8c4; background:transparent;"
        )
        tbox.addWidget(self.save_sub)
        h.addLayout(tbox)
        h.addStretch()

        self.btn_cancel = QPushButton("إلغاء التعديل")
        self.btn_cancel.setFixedHeight(44)
        self.btn_cancel.setMinimumWidth(130)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background:{NAVY_3};
                color:#dbeafe;
                border:1px solid {NAVY_ACCENT};
                border-radius:10px;
                padding:0 20px;
                font-weight:800;
                font-size:12px;
            }}
            QPushButton:hover {{
                background:{NAVY_ACCENT};
                color:white;
            }}
        """)
        self.btn_cancel.clicked.connect(self._cancel_edit)
        self.btn_cancel.setVisible(False)
        h.addWidget(self.btn_cancel)

        btn_reset = QPushButton("إعادة تعيين")
        btn_reset.setFixedHeight(44)
        btn_reset.setMinimumWidth(120)
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setStyleSheet(f"""
            QPushButton {{
                background:{NAVY_3};
                color:#dbeafe;
                border:1px solid {NAVY_ACCENT};
                border-radius:10px;
                padding:0 20px;
                font-weight:800;
                font-size:12px;
            }}
            QPushButton:hover {{
                background:{NAVY_ACCENT};
                color:white;
            }}
        """)
        btn_reset.clicked.connect(self._reset_form)
        h.addWidget(btn_reset)

        self.btn_save = QPushButton("💾  حفظ الشيفت")
        self.btn_save.setFixedHeight(44)
        self.btn_save.setMinimumWidth(160)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SUCCESS}, stop:1 {SUCCESS_HOV});
                color:white;
                border:none;
                border-radius:10px;
                padding:0 26px;
                font-weight:900;
                font-size:13px;
            }}
            QPushButton:hover {{
                background:{SUCCESS_HOV};
            }}
            QPushButton:pressed {{
                background:#065f46;
            }}
        """)
        self.btn_save.clicked.connect(self._save_shift)
        h.addWidget(self.btn_save)

        return wrap

    def _build_shifts_table_card(self):
        card = QFrame()
        card.setObjectName("shiftsTableCard")
        card.setStyleSheet(f"""
            QFrame#shiftsTableCard {{
                background:{SURFACE};
                border:1px solid {BORDER};
                border-radius:16px;
            }}
        """)
        apply_shadow(card, blur=18, y_offset=3)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head = QFrame()
        head.setFixedHeight(76)
        head.setStyleSheet(f"""
            QFrame {{
                background:{SURFACE};
                border-bottom:1px solid {DIVIDER};
                border-top-left-radius:16px;
                border-top-right-radius:16px;
            }}
        """)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 0, 22, 0)
        hl.setSpacing(12)

        hbox = QVBoxLayout()
        hbox.setSpacing(3)

        title = QLabel("🗂  الشيفتات المسجلة")
        title.setStyleSheet(
            f"font-size:15px; font-weight:900; color:{TEXT}; background:transparent;"
        )
        hbox.addWidget(title)

        hint = QLabel("جميع الشيفتات المُضافة في النظام")
        hint.setStyleSheet(
            f"font-size:10px; color:{TEXT_MUTED}; background:transparent;"
        )
        hbox.addWidget(hint)
        hl.addLayout(hbox)
        hl.addStretch()

        self.shifts_count_badge = QLabel("0")
        self.shifts_count_badge.setAlignment(Qt.AlignCenter)
        self.shifts_count_badge.setMinimumWidth(44)
        self.shifts_count_badge.setFixedHeight(30)
        self.shifts_count_badge.setStyleSheet(f"""
            QLabel {{
                background:{PRIMARY_BG};
                color:{PRIMARY};
                border:1px solid {PRIMARY_BRD};
                border-radius:15px;
                padding:0 13px;
                font-size:11px;
                font-weight:900;
            }}
        """)
        hl.addWidget(self.shifts_count_badge)

        v.addWidget(head)

        # ✅ أضفنا عمودين: الإجراءات
        self.shifts_table = QTableWidget(0, 8)
        self.shifts_table.setHorizontalHeaderLabels(
            ["ID", "الاسم", "النوع", "الساعات", "من", "إلى", "أيام العمل", "إجراءات"]
        )
        self.shifts_table.verticalHeader().setVisible(False)
        self.shifts_table.setShowGrid(False)
        self.shifts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.shifts_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.shifts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shifts_table.setFocusPolicy(Qt.NoFocus)
        self.shifts_table.setAlternatingRowColors(True)
        self.shifts_table.setMinimumHeight(260)
        self.shifts_table.verticalHeader().setDefaultSectionSize(52)

        hh = self.shifts_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(7, QHeaderView.Fixed)
        self.shifts_table.setColumnWidth(0, 60)
        self.shifts_table.setColumnWidth(7, 170)

        self.shifts_table.setStyleSheet(f"""
            QTableWidget {{
                background:{SURFACE};
                border:none;
                color:{TEXT};
                font-size:11.5px;
                outline:none;
                selection-background-color:{PRIMARY_BG};
                selection-color:{TEXT};
                gridline-color:transparent;
            }}
            QTableWidget::item {{
                padding:6px 8px;
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
                padding:12px 8px;
                border:none;
                border-bottom:1px solid {BORDER};
                font-weight:900;
                font-size:10px;
                letter-spacing:0.2px;
            }}
            QScrollBar:vertical {{
                width:8px;
                background:transparent;
                margin:4px 2px 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_2};
                border-radius:4px;
                min-height:36px;
            }}
            QScrollBar::handle:vertical:hover {{
                background:{TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height:0;
            }}
        """)

        v.addWidget(self.shifts_table)
        return card

    # ========================================================
    #                    عناصر مساعدة
    # ========================================================
    def _card_header(self, emoji, title_text, subtitle_text, color):
        w = QFrame()
        w.setStyleSheet("background:transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)

        icon = QLabel(emoji)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(42, 42)
        icon.setStyleSheet(f"""
            QLabel {{
                background:{color}15;
                border:1px solid {color}40;
                border-radius:12px;
                font-size:18px;
            }}
        """)
        h.addWidget(icon)

        box = QVBoxLayout()
        box.setSpacing(2)

        t = QLabel(title_text)
        t.setStyleSheet(
            f"font-size:14px; font-weight:900; color:{TEXT}; background:transparent;"
        )
        box.addWidget(t)

        s = QLabel(subtitle_text)
        s.setStyleSheet(
            f"font-size:10px; color:{TEXT_MUTED}; background:transparent;"
        )
        box.addWidget(s)
        h.addLayout(box)
        h.addStretch()
        return w

    def _field(self, label_text, widget):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            f"font-size:10px; font-weight:800; color:{TEXT_SEC}; "
            f"background:transparent; letter-spacing:0.2px;"
        )
        v.addWidget(lbl)
        v.addWidget(widget)
        return w

    def _input(self, placeholder=""):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(42)
        inp.setStyleSheet(self._input_qss())
        return inp

    def _num_input(self, placeholder=""):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(42)
        inp.setLayoutDirection(Qt.LeftToRight)
        inp.setAlignment(Qt.AlignLeft)
        inp.setStyleSheet(self._input_qss())
        return inp

    def _time_input(self, default_value="08:00"):
        inp = QLineEdit()
        inp.setFixedHeight(42)
        inp.setLayoutDirection(Qt.LeftToRight)
        inp.setAlignment(Qt.AlignCenter)
        inp.setPlaceholderText("HH:mm")
        inp.setText(default_value)
        inp.setMaxLength(5)
        inp.setValidator(QRegularExpressionValidator(TIME_REGEX))
        inp.setStyleSheet(f"""
            QLineEdit {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:10px;
                padding:0 13px;
                font-size:13px;
                font-weight:800;
                color:{TEXT};
                letter-spacing:1px;
                selection-background-color:{PRIMARY_BG};
                selection-color:{PRIMARY_DK};
            }}
            QLineEdit:hover {{
                background:white;
                border-color:{BORDER_2};
            }}
            QLineEdit:focus {{
                background:white;
                border:1.5px solid {PRIMARY};
                padding:0 12.5px;
            }}
        """)
        return inp

    def _input_qss(self):
        return f"""
            QLineEdit {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:10px;
                padding:0 13px;
                font-size:12px;
                color:{TEXT};
                selection-background-color:{PRIMARY_BG};
                selection-color:{PRIMARY_DK};
            }}
            QLineEdit:hover {{
                background:white;
                border-color:{BORDER_2};
            }}
            QLineEdit:focus {{
                background:white;
                border:1.5px solid {PRIMARY};
                padding:0 12.5px;
            }}
        """

    def _combo(self):
        c = QComboBox()
        c.setFixedHeight(42)
        c.setStyleSheet(f"""
            QComboBox {{
                background:{SURFACE_2};
                border:1px solid {BORDER};
                border-radius:10px;
                padding:0 13px;
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
                margin-right:9px;
            }}
            QComboBox QAbstractItemView {{
                background:white;
                border:1px solid {BORDER};
                border-radius:9px;
                padding:6px;
                selection-background-color:{PRIMARY_BG};
                selection-color:{PRIMARY};
                outline:none;
            }}
            QComboBox QAbstractItemView::item {{
                padding:8px 11px;
                border-radius:6px;
                min-height:22px;
            }}
        """)
        return c

    def _get_time(self, field, fallback="08:00"):
        text = field.text().strip()
        if not text or ":" not in text:
            return fallback
        parts = text.split(":")
        if len(parts) != 2:
            return fallback
        h, m = parts
        try:
            h_i = int(h)
            m_i = int(m)
            if 0 <= h_i <= 23 and 0 <= m_i <= 59:
                return f"{h_i:02d}:{m_i:02d}"
        except ValueError:
            pass
        return fallback

    # ========================================================
    #                         Logic
    # ========================================================
    def _on_shift_type_changed(self, idx):
        if self.shift_type.currentData() == "morning":
            self.shift_hint.setText("ℹ️  الشيفت الصباحي: الحضور والانصراف في نفس اليوم")
            self.shift_hint.setStyleSheet(
                "color:#1e40af; background:#eff6ff; padding:12px; "
                "border-radius:10px; font-size:12px; font-weight:700; "
                "border:1px solid #bfdbfe;"
            )
        else:
            self.shift_hint.setText(
                "⚠️  الشيفت المسائي: الحضور في يوم والانصراف في اليوم التالي. "
                "سيتم احتساب بصمة الانصراف تلقائياً لليوم السابق."
            )
            self.shift_hint.setStyleSheet(
                "color:#b45309; background:#fffbeb; padding:12px; "
                "border-radius:10px; font-size:12px; font-weight:700; "
                "border:1px solid #fde68a;"
            )

    def _on_ded_type_changed(self, idx):
        self.ded_value.setVisible(self.ded_type.currentData() == "minutes")

    def _add_deduction(self):
        from_t = self._get_time(self.ded_from, "09:00")
        to_t = self._get_time(self.ded_to, "10:00")
        dtype = self.ded_type.currentData()

        try:
            value = int(self.ded_value.text() or 0) if dtype == "minutes" else 0
        except ValueError:
            value = 0

        if dtype == "minutes" and value <= 0:
            QMessageBox.warning(self, "تنبيه", "أدخل عدد الدقائق المطلوبة")
            return

        self._deductions.append({
            "from": from_t,
            "to": to_t,
            "type": dtype,
            "value": value,
        })
        self._refresh_ded_table()
        self.ded_value.clear()

    def _refresh_ded_table(self):
        self.ded_table.setRowCount(0)
        for i, d in enumerate(self._deductions):
            self.ded_table.insertRow(i)

            row_data = [
                d["from"],
                d["to"],
                DEDUCTION_LABELS[d["type"]],
                f"{d['value']} دقيقة" if d["type"] == "minutes" else "—",
            ]
            for c, v in enumerate(row_data):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor(TEXT))
                self.ded_table.setItem(i, c, item)

            btn_del_wrap = QWidget()
            btn_del_wrap.setStyleSheet("background:transparent;")
            bw = QHBoxLayout(btn_del_wrap)
            bw.setContentsMargins(6, 0, 6, 0)
            bw.setAlignment(Qt.AlignCenter)

            btn_del = QPushButton("🗑")
            btn_del.setFixedSize(30, 30)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setToolTip("حذف القاعدة")
            btn_del.setStyleSheet(f"""
                QPushButton {{
                    background:{SURFACE};
                    color:{DANGER};
                    border:1px solid {BORDER};
                    border-radius:8px;
                    font-size:12px;
                }}
                QPushButton:hover {{
                    background:{DANGER_BG};
                    border-color:{DANGER_BRD};
                }}
            """)
            btn_del.clicked.connect(lambda _, idx=i: self._remove_ded(idx))
            bw.addWidget(btn_del)
            self.ded_table.setCellWidget(i, 4, btn_del_wrap)

    def _remove_ded(self, idx):
        if 0 <= idx < len(self._deductions):
            del self._deductions[idx]
            self._refresh_ded_table()

    def _reset_form(self):
        """إعادة كل الحقول لحالتها الافتراضية"""
        self._editing_id = None
        self.shift_name.clear()
        self.shift_type.setCurrentIndex(0)
        self.work_hours.setText("8")
        self.start_time.setText("08:00")
        self.end_time.setText("16:00")
        self.sick_leave.setCurrentIndex(0)
        self.overtime_rate.setCurrentIndex(0)
        for i, cb in enumerate(self.day_checks):
            cb.setChecked(i < 5)
        self._deductions.clear()
        self._refresh_ded_table()
        self.ded_from.setText("09:00")
        self.ded_to.setText("10:00")
        self.ded_type.setCurrentIndex(0)
        self.ded_value.clear()

        # إرجاع زر الحفظ لحالته الأصلية
        self.save_icon.setText("💾")
        self.save_title.setText("جاهز للحفظ؟")
        self.save_sub.setText("سيتم إضافة الشيفت الجديد إلى النظام فوراً")
        self.btn_save.setText("💾  حفظ الشيفت")
        self.btn_cancel.setVisible(False)

    def _cancel_edit(self):
        self._reset_form()

    def _save_shift(self):
        name = self.shift_name.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "أدخل اسم الشيفت")
            self.shift_name.setFocus()
            return

        try:
            work_hours = float(self.work_hours.text() or 8)
        except ValueError:
            work_hours = 8

        days = ",".join(str(i) for i, cb in enumerate(self.day_checks) if cb.isChecked())
        if not days:
            QMessageBox.warning(self, "تنبيه", "اختر يوم عمل واحد على الأقل")
            return

        start_t = self._get_time(self.start_time, "08:00")
        end_t = self._get_time(self.end_time, "16:00")

        try:
            if self._editing_id is None:
                # إضافة جديدة
                add_shift(
                    name=name,
                    shift_type=self.shift_type.currentData(),
                    work_hours=work_hours,
                    start_time=start_t,
                    end_time=end_t,
                    sick_leave=self.sick_leave.currentData(),
                    overtime_rate=self.overtime_rate.currentData(),
                    work_days=days,
                    deductions=self._deductions,
                )
                QMessageBox.information(self, "تم", "تم حفظ الشيفت بنجاح ✅")
            else:
                # تعديل موجود
                update_shift(
                    self._editing_id,
                    name=name,
                    shift_type=self.shift_type.currentData(),
                    work_hours=work_hours,
                    start_time=start_t,
                    end_time=end_t,
                    sick_leave=self.sick_leave.currentData(),
                    overtime_rate=self.overtime_rate.currentData(),
                    work_days=days,
                    deductions=self._deductions,
                )
                QMessageBox.information(self, "تم", "تم تحديث الشيفت بنجاح ✅")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل حفظ الشيفت:\n{e}")
            return

        self._reset_form()
        self._load_shifts()

    def _load_shifts(self):
        rows = get_shifts()
        self.shifts_table.setRowCount(0)

        for i, r in enumerate(rows):
            self.shifts_table.insertRow(i)

            # ID
            id_item = QTableWidgetItem(str(r["id"]))
            id_item.setTextAlignment(Qt.AlignCenter)
            id_item.setForeground(QColor(TEXT_MUTED))
            self.shifts_table.setItem(i, 0, id_item)

            # الاسم
            name_item = QTableWidgetItem(r["name"])
            name_item.setTextAlignment(Qt.AlignCenter)
            name_item.setForeground(QColor(TEXT))
            self.shifts_table.setItem(i, 1, name_item)

            # النوع
            is_morning = r["shift_type"] == "morning"
            type_wrap = QWidget()
            type_wrap.setStyleSheet("background:transparent;")
            tw = QHBoxLayout(type_wrap)
            tw.setContentsMargins(0, 0, 0, 0)
            tw.setAlignment(Qt.AlignCenter)

            type_badge = QLabel("☀️ صباحي" if is_morning else "🌙 مسائي")
            type_badge.setAlignment(Qt.AlignCenter)
            if is_morning:
                type_badge.setStyleSheet(f"""
                    background:{SUCCESS_BG};
                    color:{SUCCESS};
                    border:1px solid {SUCCESS_BRD};
                    padding:5px 12px;
                    border-radius:11px;
                    font-weight:800;
                    font-size:10.5px;
                """)
            else:
                type_badge.setStyleSheet(f"""
                    background:{PURPLE_BG};
                    color:{PURPLE};
                    border:1px solid {PURPLE_BRD};
                    padding:5px 12px;
                    border-radius:11px;
                    font-weight:800;
                    font-size:10.5px;
                """)
            tw.addWidget(type_badge)
            self.shifts_table.setCellWidget(i, 2, type_wrap)

            # الساعات
            hrs_item = QTableWidgetItem(str(r["work_hours"]))
            hrs_item.setTextAlignment(Qt.AlignCenter)
            hrs_item.setForeground(QColor(TEXT))
            self.shifts_table.setItem(i, 3, hrs_item)

            # من / إلى
            from_item = QTableWidgetItem(r["start_time"])
            from_item.setTextAlignment(Qt.AlignCenter)
            from_item.setForeground(QColor(TEXT_SEC))
            self.shifts_table.setItem(i, 4, from_item)

            to_item = QTableWidgetItem(r["end_time"])
            to_item.setTextAlignment(Qt.AlignCenter)
            to_item.setForeground(QColor(TEXT_SEC))
            self.shifts_table.setItem(i, 5, to_item)

            # أيام العمل
            days_ar = ", ".join(
                ARABIC_DAYS[int(d)]
                for d in r["work_days"].split(",")
                if d and d.isdigit() and int(d) < len(ARABIC_DAYS)
            )
            days_item = QTableWidgetItem(days_ar or "—")
            days_item.setTextAlignment(Qt.AlignCenter)
            days_item.setForeground(QColor(TEXT_SEC))
            self.shifts_table.setItem(i, 6, days_item)

            # ✅ أزرار الإجراءات (تعديل + حذف)
            actions = QWidget()
            actions.setStyleSheet("background:transparent;")
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 0, 4, 0)
            al.setSpacing(6)
            al.setAlignment(Qt.AlignCenter)

            btn_edit = QPushButton("✎  تعديل")
            btn_edit.setFixedHeight(32)
            btn_edit.setMinimumWidth(85)
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setToolTip("تعديل الشيفت")
            btn_edit.setStyleSheet(f"""
                QPushButton {{
                    background:{SURFACE};
                    color:{PRIMARY};
                    border:1px solid {BORDER};
                    border-radius:8px;
                    padding:0 10px;
                    font-weight:800;
                    font-size:11px;
                }}
                QPushButton:hover {{
                    background:{PRIMARY_BG};
                    border-color:{PRIMARY_BRD};
                }}
            """)
            btn_edit.clicked.connect(lambda _, sid=r["id"]: self._edit_shift(sid))

            btn_del = QPushButton("🗑")
            btn_del.setFixedSize(32, 32)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setToolTip("حذف الشيفت")
            btn_del.setStyleSheet(f"""
                QPushButton {{
                    background:{SURFACE};
                    color:{DANGER};
                    border:1px solid {BORDER};
                    border-radius:8px;
                    font-size:12px;
                }}
                QPushButton:hover {{
                    background:{DANGER_BG};
                    border-color:{DANGER_BRD};
                }}
            """)
            btn_del.clicked.connect(lambda _, sid=r["id"]: self._delete_shift(sid))

            al.addWidget(btn_edit)
            al.addWidget(btn_del)
            self.shifts_table.setCellWidget(i, 7, actions)

        # تحديث الإحصائيات
        total = len(rows)
        morning = sum(1 for r in rows if r["shift_type"] == "morning")
        evening = total - morning
        avg_hours = (
            sum(float(r["work_hours"] or 0) for r in rows) / total if total else 0
        )

        self.shifts_count_badge.setText(str(total))
        self.stat_total._value_label.setText(str(total))
        self.stat_morning._value_label.setText(str(morning))
        self.stat_evening._value_label.setText(str(evening))
        self.stat_hours._value_label.setText(f"{avg_hours:.1f}")

    # ========================================================
    #                    تعديل الشيفت
    # ========================================================
    def _edit_shift(self, shift_id):
        """
        ✅ تحميل بيانات الشيفت + قواعده ووضعه في النموذج للتعديل.
        يعمل بدون فتح Dialog منفصل — يستخدم نفس النموذج الحالي.
        """
        shift = get_shift(shift_id)
        if not shift:
            QMessageBox.warning(self, "تنبيه", "الشيفت غير موجود")
            return

        # ضبط مؤشر التعديل
        self._editing_id = shift_id

        # اسم الشيفت
        self.shift_name.setText(shift["name"] or "")

        # نوع الشيفت
        type_idx = self.shift_type.findData(shift["shift_type"])
        if type_idx >= 0:
            self.shift_type.setCurrentIndex(type_idx)

        # ساعات العمل
        self.work_hours.setText(str(shift["work_hours"] or 8))

        # أوقات البداية والنهاية
        self.start_time.setText(shift["start_time"] or "08:00")
        self.end_time.setText(shift["end_time"] or "16:00")

        # سياسة المرضية
        sick_idx = self.sick_leave.findData(shift["sick_leave_policy"])
        if sick_idx >= 0:
            self.sick_leave.setCurrentIndex(sick_idx)

        # معدل الإضافي
        ot_idx = self.overtime_rate.findData(float(shift["overtime_rate"] or 1.0))
        if ot_idx >= 0:
            self.overtime_rate.setCurrentIndex(ot_idx)

        # أيام العمل
        days_set = set(
            int(d) for d in (shift["work_days"] or "").split(",")
            if d.isdigit()
        )
        for i, cb in enumerate(self.day_checks):
            cb.setChecked(i in days_set)

        # قواعد الخصم
        self._deductions = []
        ded_rows = get_shift_deductions(shift_id)
        for d in ded_rows:
            self._deductions.append({
                "from": d["from_time"],
                "to": d["to_time"],
                "type": d["deduction_type"],
                "value": int(d["deduction_value"] or 0),
            })
        self._refresh_ded_table()

        # تغيير واجهة زر الحفظ
        self.save_icon.setText("✎")
        self.save_title.setText(f"تعديل الشيفت #{shift_id}")
        self.save_sub.setText(
            f"تعديل بيانات «{shift['name']}» — سيتم حفظ التغييرات فوراً"
        )
        self.btn_save.setText("💾  حفظ التعديلات")
        self.btn_cancel.setVisible(True)

        # تحديث hint لو الشيفت مسائي
        self._on_shift_type_changed(0)

        # التمرير لأعلى الصفحة لرؤية النموذج
        try:
            # ابحث عن الـ ScrollArea الأب
            parent = self.parent()
            while parent and not isinstance(parent, QScrollArea):
                parent = parent.parent()
            # لا حاجة — المستخدم سيمرر يدوياً
        except Exception:
            pass

    # ========================================================
    #                    حذف الشيفت
    # ========================================================
    def _delete_shift(self, shift_id):
        shift = get_shift(shift_id)
        if not shift:
            QMessageBox.warning(self, "تنبيه", "الشيفت غير موجود")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("تأكيد الحذف")
        msg.setText(f"حذف الشيفت «{shift['name']}» نهائياً؟")
        msg.setInformativeText(
            "⚠️ سيتم حذف كل قواعد الخصم المرتبطة به.\n"
            "الموظفون المرتبطون بهذا الشيفت سيبقون بدون شيفت."
        )
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.button(QMessageBox.Yes).setText("حذف نهائي")
        msg.button(QMessageBox.No).setText("إلغاء")
        msg.setDefaultButton(QMessageBox.No)

        if msg.exec() == QMessageBox.Yes:
            try:
                delete_shift(shift_id)
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل حذف الشيفت:\n{e}")
                return

            QMessageBox.information(self, "تم", "تم حذف الشيفت بنجاح ✅")

            # لو كنا بنعدل نفس الشيفت، الصفحة تُعاد
            if self._editing_id == shift_id:
                self._reset_form()

            self._load_shifts()