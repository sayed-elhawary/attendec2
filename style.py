APP_STYLE = """
/* ==================== GLOBAL ==================== */
* {
    font-family: 'Segoe UI', 'Tahoma', 'Arial';
    outline: none;
}
QWidget {
    background-color: #f0f2f5;
    color: #1e293b;
    font-size: 13px;
}

/* ==================== INPUTS ==================== */
QLineEdit, QComboBox, QDateEdit, QTimeEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 24px;
    font-size: 13px;
    selection-background-color: #3b82f6;
    selection-color: white;
}
QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QTimeEdit:hover {
    border-color: #cbd5e1;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border-color: #3b82f6;
    background-color: #ffffff;
}
QLineEdit:disabled, QComboBox:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
}

/* ============ إخفاء أسهم الـ SpinBox بالكامل ============ */
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 24px;
    font-size: 13px;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 0px;
    height: 0px;
    border: none;
}

/* ============ إخفاء سهم الـ ComboBox ============ */
QComboBox::drop-down {
    border: none;
    width: 0px;
}
QComboBox::down-arrow {
    image: none;
    border: none;
    width: 0;
    height: 0;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #eff6ff;
    selection-color: #1e40af;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 4px;
    min-height: 24px;
}

/* ============ إخفاء أسهم الـ Date/Time Edit ============ */
QDateEdit::up-button, QDateEdit::down-button,
QTimeEdit::up-button, QTimeEdit::down-button {
    width: 0px;
    height: 0px;
    border: none;
}
QDateEdit::drop-down, QTimeEdit::drop-down {
    border: none;
    width: 24px;
}
QDateEdit::down-arrow, QTimeEdit::down-arrow {
    image: none;
    border: none;
}

/* ==================== BUTTONS ==================== */
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 600;
    min-height: 24px;
}
QPushButton:hover { background-color: #2563eb; }
QPushButton:pressed { background-color: #1d4ed8; }
QPushButton:disabled {
    background-color: #cbd5e1;
    color: #f1f5f9;
}
QPushButton#success {
    background-color: #10b981;
    color: #ffffff;
}
QPushButton#success:hover { background-color: #059669; }
QPushButton#danger {
    background-color: #ef4444;
    color: #ffffff;
}
QPushButton#danger:hover { background-color: #dc2626; }
QPushButton#secondary {
    background-color: #64748b;
    color: #ffffff;
}
QPushButton#secondary:hover { background-color: #475569; }
QPushButton#ghost {
    background-color: transparent;
    color: #3b82f6;
    border: 1.5px solid #3b82f6;
}
QPushButton#ghost:hover {
    background-color: #eff6ff;
}

/* ==================== LABELS ==================== */
QLabel {
    background: transparent;
}
QLabel#title {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
}
QLabel#subtitle {
    font-size: 14px;
    color: #64748b;
}
QLabel#field_label {
    font-size: 13px;
    font-weight: 600;
    color: #334155;
    background: transparent;
}
QLabel#hint {
    font-size: 12px;
    color: #64748b;
    background: transparent;
}

/* ==================== CARDS ==================== */
QFrame#card {
    background-color: #ffffff;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
}
QFrame#card_white {
    background-color: #ffffff;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
}
QFrame#stat_card {
    background-color: #ffffff;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
}
QFrame#sidebar {
    background-color: #0f172a;
    border-radius: 0;
}
QFrame#divider {
    background-color: #e2e8f0;
    max-height: 1px;
    min-height: 1px;
}

/* ==================== GROUPBOX (بشكل Card) ==================== */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    margin-top: 16px;
    padding: 18px 14px 14px 14px;
    font-size: 14px;
    font-weight: 700;
    color: #0f172a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    right: 18px;
    top: 4px;
    padding: 2px 10px;
    color: #3b82f6;
    background-color: #ffffff;
    font-size: 13px;
    font-weight: 700;
}

/* ==================== SIDEBAR BUTTONS ==================== */
QPushButton#sidebar_btn {
    background-color: transparent;
    color: #cbd5e1;
    text-align: right;
    padding: 11px 18px;
    border-radius: 0;
    font-weight: 500;
    font-size: 13px;
    border: none;
}
QPushButton#sidebar_btn:hover {
    background-color: #1e293b;
    color: #ffffff;
}
QPushButton#sidebar_btn:checked {
    background-color: #1e40af;
    color: #ffffff;
    font-weight: 700;
    border-right: 4px solid #3b82f6;
}

/* ==================== TABLES ==================== */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    gridline-color: #f1f5f9;
    font-size: 13px;
    outline: none;
}
QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f1f5f9;
}
QTableWidget::item:selected {
    background-color: #eff6ff;
    color: #1e40af;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    font-weight: 700;
    font-size: 12px;
}
QTableCornerButton::section {
    background-color: #f8fafc;
    border: none;
}

/* ==================== CHECKBOX ==================== */
QCheckBox {
    spacing: 8px;
    font-size: 13px;
    background: transparent;
    padding: 4px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #cbd5e1;
    background: #ffffff;
}
QCheckBox::indicator:hover {
    border-color: #3b82f6;
}
QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
    image: none;
}

/* ==================== SCROLLBAR ==================== */
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0; background: none; border: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0; background: none; border: none;
}

/* ==================== MESSAGE BOX ==================== */
QMessageBox {
    background-color: #ffffff;
}
QMessageBox QLabel {
    color: #1e293b;
    font-size: 13px;
}
"""