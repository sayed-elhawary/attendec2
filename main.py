import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from database import init_db
from style import APP_STYLE
from ui_login import LoginPage
from ui_dashboard import Dashboard


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام الحضور والانصراف والمرتبات")
        self.resize(1400, 850)
        self.setLayoutDirection(Qt.RightToLeft)

        # ✅ توسيط النافذة على الشاشة
        self._center_on_screen()

        # ✅ أيقونة النافذة (اختياري — ضع ملف icon.ico في نفس المجلد)
        try:
            self.setWindowIcon(QIcon("icon.ico"))
        except Exception:
            pass

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage()
        self.login_page.logged_in.connect(self._on_login)
        self.stack.addWidget(self.login_page)

        # ✅ مرجع للـ Dashboard لإيقاف الـ threads عند الإغلاق
        self._dashboard = None

    # ----------------------------------------------------------
    #            توسيط النافذة على الشاشة
    # ----------------------------------------------------------
    def _center_on_screen(self):
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = (geo.width() - self.width()) // 2 + geo.x()
                y = (geo.height() - self.height()) // 2 + geo.y()
                self.move(x, y)
        except Exception:
            pass

    # ----------------------------------------------------------
    #            استقبال حدث تسجيل الدخول
    # ----------------------------------------------------------
    def _on_login(self, username):
        self._dashboard = Dashboard(username)
        self.stack.addWidget(self._dashboard)
        self.stack.setCurrentWidget(self._dashboard)

    # ----------------------------------------------------------
    #            إغلاق نظيف لكل الـ Threads
    # ----------------------------------------------------------
    def closeEvent(self, event):
        """
        عند إغلاق النافذة الرئيسية:
        - نوقف Thread الاستماع للبصمة (إن وجد) لتفادي تعليق البرنامج
        - نغلق كل الـ pages بشكل نظيف
        """
        try:
            if self._dashboard:
                # نستدعي closeEvent لكل صفحة في الـ stack
                stack = self._dashboard.findChild(QStackedWidget)
                if stack:
                    for i in range(stack.count()):
                        page = stack.widget(i)
                        try:
                            # استدعاء closeEvent إن وُجد
                            page.close()
                        except Exception:
                            pass
        except Exception:
            pass

        super().closeEvent(event)


# ============================================================
#                       نقطة البداية
# ============================================================
def main():
    # ✅ دعم High DPI (يجب قبل إنشاء QApplication)
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    # ✅ تهيئة قاعدة البيانات
    init_db()

    # ✅ إنشاء التطبيق
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(APP_STYLE)
    app.setApplicationName("نظام الحضور والانصراف")
    app.setOrganizationName("Attendance System")

    # ✅ أيقونة التطبيق (اختياري)
    try:
        app.setWindowIcon(QIcon("icon.ico"))
    except Exception:
        pass

    # ✅ فتح النافذة الرئيسية
    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()