import requests
import json
from urllib.parse import urlparse
import re
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import datetime
import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QHBoxLayout, QSizePolicy, QScrollArea, QLineEdit, QGraphicsDropShadowEffect,
    QApplication, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QRect, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QClipboard

# --- Import SettingsPage and HistoryPage ---
# NOTE: You must have settings.py in the same directory.
try:
    from settings import SettingsPage
except ImportError:
    # Fallback class if settings.py is missing
    class SettingsPage(QWidget):
        def __init__(self, parent_app, user_id, *args, **kwargs):
            super().__init__()
            self.setLayout(QVBoxLayout())
            self.layout().addWidget(
                QLabel("SettingsPage failed to import. (Check settings.py)", alignment=Qt.AlignCenter))

# NOTE: Assume HistoryPage is defined elsewhere.
try:
    from history import HistoryPage
except ImportError:
    # Fallback class if history.py is missing
    class HistoryPage(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.setLayout(QVBoxLayout())
            self.layout().addWidget(
                QLabel("HistoryPage requires separate definition and is disabled.", alignment=Qt.AlignCenter))

# ==================== CONFIGURATION & FIREBASE SETUP ====================
ISGD_API_ENDPOINT = "https://v.gd/create.php"


def initialize_firebase():
    """Initializes Firebase if a service account key is available."""
    try:
        if not firebase_admin._apps:
            service_account_path = "serviceAccountKey.json"
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                # print("✅ Firebase initialized successfully (using serviceAccountKey.json)")
                return firestore.client()
            else:
                # print("❌ Firebase skipped: 'serviceAccountKey.json' not found. History saving disabled.")
                return None
        return firestore.client()
    except Exception:
        # print(f"❌ Firebase initialization failed: {e}")
        return None


firebase_db = initialize_firebase()


# ==================== NOTIFICATION CLASSES ====================

class NotificationBar(QFrame):
    """Animated notification bar sliding from the top/bottom."""

    def __init__(self, message_text, is_success, parent=None, position="top"):
        super().__init__(parent)
        self.position = position
        self.setAttribute(Qt.WA_StyledBackground)

        if position == "top":
            self.setFixedWidth(450)
            self.setFixedHeight(60)
        else:
            self.setFixedWidth(350)
            self.setFixedHeight(50)

        # Apply specific styling based on position and success state
        style_template = """
            QFrame {{ background-color: {bg_color}; border: 2px solid {border_color}; border-radius: 12px; padding: 10px; }}
            QLabel {{ color: {text_color}; font-size: {font_size}px; font-weight: 600; }}
        """

        if is_success:
            bg, border, text, icon = ("#E8F8F4", "#10C988", "#064E3B", "✓")
        else:
            bg, border, text, icon = ("#FEE2E2", "#EF4444", "#7F1D1D", "⚠️")

        font_size = 16 if position == "top" else 14

        self.setStyleSheet(style_template.format(
            bg_color=bg, border_color=border, text_color=text, font_size=font_size
        ))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 14 if position == "top" else 12, QFont.Bold))

        message_label = QLabel(message_text)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        layout.addWidget(message_label, stretch=1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20 if position == "top" else 15)
        shadow.setOffset(0, 4 if position == "top" else 3)
        shadow.setColor(QColor(0, 0, 0, 100 if position == "top" else 60))
        self.setGraphicsEffect(shadow)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.hide()

    def show_animated(self, parent_rect):
        if self.position == "top":
            # Slide down from above the header (80px below the top of the window)
            start_rect = QRect(parent_rect.center().x() - self.width() // 2, -self.height(), self.width(),
                               self.height())
            end_rect = QRect(parent_rect.center().x() - self.width() // 2, 80, self.width(), self.height())
        else:
            # Slide up from below the bottom
            start_rect = QRect(parent_rect.center().x() - self.width() // 2, parent_rect.bottom(), self.width(),
                               self.height())
            end_rect = QRect(parent_rect.center().x() - self.width() // 2, parent_rect.bottom() - self.height() - 20,
                             self.width(), self.height())

        self.setGeometry(start_rect)
        self.show()
        self.raise_()

        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)
        self.animation.start()

    def hide_animated(self):
        if self.position == "top":
            end_rect = QRect(self.x(), -self.height(), self.width(), self.height())
        else:
            end_rect = QRect(self.x(), self.parent().height(), self.width(), self.height())

        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(end_rect)
        self.animation.finished.connect(self.hide_and_destroy)
        self.animation.start()

    def show_and_hide(self, duration=3000):
        parent = self.parent()
        if parent:
            self.show_animated(parent.rect())
        else:
            self.show()
        QTimer.singleShot(duration, self.hide_animated)

    def hide_and_destroy(self):
        self.hide()
        self.deleteLater()


class CopyNotification(QFrame):
    """Small tooltip notification that appears above a button."""

    def __init__(self, message_text, parent_button):
        super().__init__(parent_button.parent())
        self.parent_button = parent_button
        self.setAttribute(Qt.WA_StyledBackground)
        self.setFixedWidth(180)
        self.setFixedHeight(35)

        self.setStyleSheet("""
            QFrame { background-color: #10C988; border-radius: 6px; padding: 5px; }
            QLabel { color: white; font-size: 13px; font-weight: 500; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        message_label = QLabel(message_text)
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)
        self.hide()

    def show_at_button(self):
        if not self.parent_button: return

        try:
            # Map button's position in global coordinates
            button_pos = self.parent_button.mapToGlobal(self.parent_button.rect().topLeft())
            # Map that global position back to this widget's parent (HomeWindow)
            parent_pos = self.parent().mapFromGlobal(button_pos)

            # Center horizontally above the button
            x = parent_pos.x() + (self.parent_button.width() - self.width()) // 2
            # Position 5px above the button
            y = parent_pos.y() - self.height() - 5

            self.move(x, y)
            self.show()
            self.raise_()
            QTimer.singleShot(2000, self.hide_and_destroy)
        except Exception:
            self.hide_and_destroy()

    def hide_and_destroy(self):
        self.hide()
        self.deleteLater()


# ==================== DIALOGS AND WORKERS ====================

class ExpirationDialog(QFrame):
    expiration_selected = pyqtSignal(str)

    def __init__(self, parent=None, current_expiration="30 days"):
        super().__init__(parent)
        self.current_expiration = current_expiration
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setStyleSheet("""
            QFrame { background-color: transparent; border-radius: 12px; border: none; }
            QPushButton { background-color: white; border: none; padding: 12px 16px; text-align: left; font-family: "Arial"; font-size: 14px; color: #374151; border-radius: 8px; }
            QPushButton:hover { background-color: #E8F8F4; }
            QPushButton[selected="true"] { color: #10C988; font-weight: bold; padding-left: 36px; }
        """)

        self.inner_frame = QFrame(self)
        self.inner_frame.setStyleSheet("""
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #D9D9D9; }
        """)

        inner_layout = QVBoxLayout(self.inner_frame)
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(4)

        self.options = ["7 days", "30 days", "Never"]
        self.buttons = []
        self.selected_button = None

        for option in self.options:
            btn = QPushButton(option)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("option", option)
            is_selected = (option == current_expiration)
            btn.setProperty("selected", is_selected)

            if is_selected:
                self.selected_button = btn

            btn.clicked.connect(self.on_option_clicked)
            self.buttons.append(btn)
            inner_layout.addWidget(btn)

        inner_layout.addStretch()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.inner_frame)

        for btn in self.buttons:
            btn.style().polish(btn)

    def resizeEvent(self, event):
        self.inner_frame.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def on_option_clicked(self):
        btn = self.sender()
        option = btn.property("option")

        if self.selected_button:
            self.selected_button.setProperty("selected", False)
            self.selected_button.style().polish(self.selected_button)

        btn.setProperty("selected", True)
        self.selected_button = btn
        btn.style().polish(btn)

        self.current_expiration = option
        self.expiration_selected.emit(option)
        self.hide()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.selected_button:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            rect = self.selected_button.geometry()
            x = 10
            y = rect.center().y()

            painter.setPen(QPen(QColor("#10C988"), 2))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(x, y + 5, "✓")


class CreateLinkWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url_data):
        super().__init__()
        self.url_data = url_data

    def run(self):
        import datetime as dt

        long_url = self.url_data['original_url']
        alias = self.url_data.get('alias')

        # --- STEP 1: Call External API (v.gd) ---
        params = {"url": long_url, "format": "simple"}
        if alias: params["shorturl"] = alias

        try:
            response = requests.get(ISGD_API_ENDPOINT, params=params, timeout=15)
            response.raise_for_status()
            short_url = response.text.strip()
            if short_url.lower().startswith("error:"):
                self.error.emit(f"API Error during shortening: {short_url}")
                return
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Network failure while calling v.gd: {str(e)}")
            return

        # --- STEP 2: Save Result to Firebase Firestore ---
        if not firebase_db:
            # Report the short link, but issue a warning about history not being saved
            self.error.emit(f"Short link created: {short_url}, but Firebase is disconnected. History not saved.")

            # Still proceed to the finished state so the user sees the created link
            result = {
                'short_url': short_url,
                'original_url': long_url,
                'short_code': short_url.split('/')[-1],
                'alias': alias,
                'expiration': self.url_data['expiration'],
                'created_at': dt.datetime.now().isoformat()
            }
            self.finished.emit(result)
            return

        short_code = short_url.split('/')[-1]
        expires_at = None
        if self.url_data['expiration'] != "Never":
            days = 7 if "7" in self.url_data['expiration'] else 30
            expires_at = dt.datetime.now() + dt.timedelta(days=days)

        firestore_data = {
            'original_url': long_url,
            'short_url': short_url,
            'short_code': short_code,
            'alias_used': alias,
            'service': 'v.gd',
            'expiration': self.url_data['expiration'],
            'user_id': self.url_data['user_id'],
            'created_at': firestore.SERVER_TIMESTAMP,
            'clicks': 0,
            'is_active': True,
            'expires_at': expires_at
        }

        try:
            doc_id = str(uuid.uuid4())
            firebase_db.collection('url_history').document(doc_id).set(firestore_data)

            # 3. Return Success Result
            result = {
                'short_url': short_url,
                'original_url': long_url,
                'short_code': short_code,
                'alias': alias,
                'expiration': self.url_data['expiration'],
                'created_at': dt.datetime.now().isoformat()
            }
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(f"Short link created ({short_url}), but failed to save history to Firebase: {str(e)}")


class ShadowButton(QPushButton):
    """
    Custom QPushButton with shadow effects.
    It communicates with parent_app (HomeWindow) to apply/remove shadows.
    """

    def __init__(self, *args, parent_app, is_primary=True, is_danger=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_app = parent_app
        self.is_primary = is_primary
        self.is_danger = is_danger
        if self.isEnabled():
            self.parent_app.apply_button_shadow(self, self.is_primary, is_danger=self.is_danger)

    def enterEvent(self, event):
        if self.isEnabled():
            self.parent_app.apply_button_shadow(self, self.is_primary, is_danger=self.is_danger)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.parent_app.remove_button_shadow(self)
        super().leaveEvent(event)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        if enabled:
            self.parent_app.apply_button_shadow(self, self.is_primary, is_danger=self.is_danger)
        else:
            self.parent_app.remove_button_shadow(self)


# ==================== HOME WINDOW ====================

class HomeWindow(QMainWindow):

    # --- Shadow Helpers ---
    def apply_button_shadow(self, button, is_primary, is_danger=False):
        shadow = QGraphicsDropShadowEffect(button)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 3)
        if is_danger:
            shadow.setColor(QColor(239, 68, 68, 120))
        elif is_primary:
            shadow.setColor(QColor(0, 180, 120, 120))
        else:
            shadow.setColor(QColor(0, 0, 0, 60))
        button.setGraphicsEffect(shadow)

    def remove_button_shadow(self, button):
        button.setGraphicsEffect(None)

    # --- Communication Methods (Used by SettingsPage) ---
    def show_notification(self, message, is_success=True, position="top", duration=3000):
        if self.notification_bar:
            try:
                self.notification_bar.hide_and_destroy()
            except:
                pass
            self.notification_bar = None

        self.notification_bar = NotificationBar(message, is_success, parent=self, position=position)
        self.notification_bar.show_and_hide(duration)

    def show_copy_notification(self, message, button):
        if self.copy_notification:
            try:
                self.copy_notification.hide_and_destroy()
            except:
                pass
            self.copy_notification = None

        self.copy_notification = CopyNotification(message, button)
        self.copy_notification.show_at_button()

    def logout(self, message="Logged out.", is_success=True):
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        if self.auth_app_instance:
            self.hide()
            self.auth_app_instance.user_id = None
            # Assuming auth_app_instance has show_login_form or similar
            # self.auth_app_instance.show_login_form(message, is_success)
            self.auth_app_instance.show()
        self.close()

    def get_current_user_id(self):
        return self.user_id

    # --- Initialization ---
    def __init__(self, auth_app_instance=None, user_id="test_user_123"):
        super().__init__()
        self.auth_app_instance = auth_app_instance
        self.user_id = user_id
        self.setWindowTitle("Shortly Desktop - Home")
        self.resize(1440, 1024)

        self.active_tab = "dashboard"
        self.current_expiration = "30 days"
        self.expiration_dialog = None
        self.worker = None
        self.notification_bar = None
        self.copy_notification = None

        self.setStyleSheet(self._get_main_stylesheet())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. HEADER SETUP
        self._setup_header()
        self.main_layout.addWidget(self.header_frame)

        # 2. CONTENT CONTAINER SETUP (Scrollable Wrapper)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_container = QWidget()
        self.content_container.setObjectName("scrollContent")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        self.scroll_area.setWidget(self.content_container)
        self.main_layout.addWidget(self.scroll_area, 1)

        # 3. INSTANTIATE PAGE WIDGETS
        self.dashboard_page = self.create_dashboard_content_widget()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(parent_app=self, user_id=self.user_id)

        self.content_layout.addWidget(self.dashboard_page)
        self.content_layout.addWidget(self.history_page)
        self.content_layout.addWidget(self.settings_page)
        self.content_layout.addStretch(1)

        self.switch_tab("dashboard")

    def _get_main_stylesheet(self):
        # Combined stylesheet to keep the code clean
        return """
            QMainWindow { background-color: #F8F8F8; } 
            #headerFrame { background-color: white; border-top: 1px solid #D9D9D9; border-bottom: 1px solid #D9D9D9; } 
            #headerTitle { font-family: "Arial"; font-size: 24px; font-weight: bold; color: #10C988; padding-right: 20px; } 
            #logoutButton { background-color: #EF4444; color: white; border-radius: 10px; border: none; font-size: 16px; padding: 5px 15px; } 
            #logoutButton:hover { background-color: #DC2626; } 
            QScrollArea { border: none; background-color: #F8F8F8; } 
            #scrollContent { background-color: #F8F8F8; } 
            .navButton { font-family: "Arial"; font-size: 14px; font-weight: 500; border: none; border-radius: 10px; padding: 10px 15px; margin-right: 8px; cursor: pointer; } 
            .navButton[state="inactive"] { background-color: transparent; color: #6B7280; } 
            .navButton[state="inactive"]:hover { background-color: #E5E7EB; color: #374151; } 
            .navButton[state="active"] { background-color: #E8F8F4; color: #10C988; } 
            .navButton[state="active"]:hover { background-color: #10C988; color: white; } 
            #shortenerCard, #successCard { background-color: white; border-radius: 14px; border: 1px solid #D9D9D9; } 
            #inputLabel { font-family: "Arial"; font-size: 14px; font-weight: 500; color: #374151; } 
            #cardTitle { font-size: 20px; font-weight: bold; color: black; } 
            #cardSubtitle, #successMessage { font-size: 14px; font-weight: normal; color: #6B7280; } 
            #urlInput, #aliasInput, #expirationButton { border: 1px solid #DCDEE5; border-radius: 12px; padding: 10px 15px; background-color: #F3F4F6; color: #374151; font-size: 16px; } 
            #urlInput:focus, #aliasInput:focus, #expirationButton:focus { border: 2px solid #10C988; background-color: #e8eaed; } 
            #expirationButton { text-align: left; background-color: #F3F4F6; cursor: pointer; } 
            #expirationButton:hover { background-color: #E5E7EB; } 
            #createButton, #copyButton { 
                background-color: #10C988; 
                color: white; 
                border-radius: 14px; 
                border: none; 
                font-size: 16px; 
                font-weight: bold; 
                padding: 10px; 
                min-height: 54px; 
                cursor: pointer;
            } 
            #createButton:hover, #copyButton:hover { background-color: #0DA875; }
            #createButton:disabled, #copyButton:disabled { background-color: #9CA3AF; cursor: not-allowed; } 
            #shortUrlDisplay { background-color: #F8F8F8; border: 1px solid #DCDEE5; border-radius: 12px; padding: 10px 15px; } 
            #shortUrlText { font-size: 16px; font-weight: 500; color: #10C988; } 
            .actionButton { background-color: #E5E7EB; color: #374151; border-radius: 12px; border: 1px solid transparent; font-size: 16px; padding: 10px 20px; min-height: 54px; cursor: pointer; } 
            .actionButton:hover { background-color: #D1D5DB; } 
            .actionButton:pressed { background-color: #A0A4AD; }
            #expirationButton::after { content: "▼"; float: right; font-size: 12px; color: #6B7280; }
        """

    def _setup_header(self):
        self.header_frame = QFrame()
        self.header_frame.setObjectName("headerFrame")
        self.header_frame.setFixedHeight(65)
        self.header_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.header_frame.setGraphicsEffect(shadow)

        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(40, 0, 40, 0)
        header_layout.setSpacing(10)

        header_title = QLabel("Shortly Desktop")
        header_title.setObjectName("headerTitle")
        header_layout.addWidget(header_title)

        header_layout.addSpacing(40)  # Spacing after title

        # Navigation Buttons Container
        self.nav_frame = QFrame()
        self.nav_layout = QHBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(5)

        self.dash_btn = self._create_nav_button("Dashboard", "dashboard")
        self.hist_btn = self._create_nav_button("History", "history")
        self.sett_btn = self._create_nav_button("Settings", "settings")

        self.nav_layout.addWidget(self.dash_btn)
        self.nav_layout.addWidget(self.hist_btn)
        self.nav_layout.addWidget(self.sett_btn)

        header_layout.addWidget(self.nav_frame)
        header_layout.addStretch(1)  # Pushes everything right of the nav buttons to the far right

        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("logoutButton")
        logout_btn.setFixedSize(120, 38)
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(logout_btn)

    # --- Dashboard and Link Handling ---

    def create_dashboard_content_widget(self):
        content_widget = QWidget()
        self.dash_content_layout = QVBoxLayout(content_widget)
        self.dash_content_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.dash_content_layout.setSpacing(20)
        self.dash_content_layout.setContentsMargins(0, 0, 0, 0)

        # The main input card widget
        self.link_input_card = self.create_url_shortener_card()
        self.dash_content_layout.addWidget(self.link_input_card)

        # Result display widget (initially empty/hidden)
        self.result_card = QFrame()  # Placeholder
        self.dash_content_layout.addWidget(self.result_card)

        return content_widget

    def load_dashboard_content(self, show_result=False, short_url=None):
        """Swaps between the input card and the result card."""

        # Clean up old result card if it exists
        if self.result_card.parent():
            self.result_card.setParent(None)
            self.result_card.deleteLater()
            self.result_card = QFrame()

        if show_result and short_url:
            self.link_input_card.hide()
            self.result_card = self.create_short_link_display(short_url=short_url)
            # Find the position of the link_input_card and insert the result card above it
            index = self.dash_content_layout.indexOf(self.link_input_card)
            self.dash_content_layout.insertWidget(index, self.result_card, alignment=Qt.AlignHCenter)
            self.result_card.show()
        else:
            self.link_input_card.show()
            self.result_card.hide()

        self.content_container.adjustSize()

    def create_url_shortener_card(self):
        card = QFrame()
        card.setObjectName("shortenerCard")
        card.setMinimumWidth(736)
        card.setMaximumWidth(736)

        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setOffset(0, 4)
        card_shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(card_shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(15)

        card_layout.addWidget(QLabel("Shorten URL", objectName="cardTitle"))
        card_layout.addWidget(QLabel("Create a short link in seconds", objectName="cardSubtitle"))
        card_layout.addSpacing(10)

        # Long URL Input
        card_layout.addWidget(QLabel("Long URL *", objectName="inputLabel"))
        self.long_url_input = QLineEdit(objectName="urlInput", placeholderText="https://example.com/very-long-url...")
        card_layout.addWidget(self.long_url_input)

        card_layout.addSpacing(5)

        side_by_side_frame = QFrame()
        side_by_side_layout = QHBoxLayout(side_by_side_frame)
        side_by_side_layout.setContentsMargins(0, 0, 0, 0)
        side_by_side_layout.setSpacing(15)

        # Alias Input
        alias_widget = QWidget()
        alias_vbox = QVBoxLayout(alias_widget)
        alias_vbox.setContentsMargins(0, 0, 0, 0)
        alias_vbox.setSpacing(5)
        alias_vbox.addWidget(QLabel("Custom Alias (optional)", objectName="inputLabel"))
        self.alias_input = QLineEdit(objectName="aliasInput", placeholderText="my-custom-link")
        alias_vbox.addWidget(self.alias_input)

        # Expiration Dropdown
        exp_widget = QWidget()
        exp_vbox = QVBoxLayout(exp_widget)
        exp_vbox.setContentsMargins(0, 0, 0, 0)
        exp_vbox.setSpacing(5)
        exp_vbox.addWidget(QLabel("Expiration", objectName="inputLabel"))

        self.exp_button = QPushButton(self.current_expiration, objectName="expirationButton")
        self.exp_button.setCursor(Qt.PointingHandCursor)
        self.exp_button.clicked.connect(self.toggle_expiration_dialog)

        exp_vbox.addWidget(self.exp_button)

        side_by_side_layout.addWidget(alias_widget, stretch=1)
        side_by_side_layout.addWidget(exp_widget, stretch=1)

        card_layout.addWidget(side_by_side_frame)
        card_layout.addSpacing(15)

        # Create Button
        self.create_btn = ShadowButton("Create Short Link", parent_app=self, is_primary=True, objectName="createButton")
        self.create_btn.clicked.connect(self.handle_create_link)

        card_layout.addWidget(self.create_btn)

        return card

    def create_short_link_display(self, short_url):
        card = QFrame()
        card.setObjectName("successCard")
        card.setMinimumWidth(736)
        card.setMaximumWidth(736)

        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setOffset(0, 4)
        card_shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(card_shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 20, 30, 20)
        card_layout.setSpacing(15)

        card_layout.addWidget(
            QLabel("✓ Short Link Created & Saved", styleSheet="color: #10C988; font-size: 18px; font-weight: bold;"))
        card_layout.addWidget(QLabel("Your shortened link is ready!", objectName="successMessage"))

        display_frame = QFrame(objectName="shortUrlDisplay")
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(2)

        display_layout.addWidget(QLabel("Your short link", objectName="inputLabel"))

        short_link_text = QLabel(short_url, objectName="shortUrlText")
        short_link_text.setCursor(Qt.IBeamCursor)
        short_link_text.setTextInteractionFlags(Qt.TextSelectableByMouse)

        display_layout.addWidget(short_link_text)
        card_layout.addWidget(display_frame)

        action_frame = QFrame()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)

        back_btn = QPushButton("← Create Another")
        back_btn.setObjectName("actionButton")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(lambda: self.load_dashboard_content(show_result=False))

        # Use ShadowButton for consistency
        copy_btn = ShadowButton("📋 Copy Link", parent_app=self, is_primary=True, objectName="copyButton")
        copy_btn.setCursor(Qt.PointingHandCursor)

        # Store a reference to the copy button and short URL
        self.current_copy_button = copy_btn
        self.last_created_short_url = short_url
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(short_url, copy_btn))

        action_layout.addWidget(back_btn, 1)
        action_layout.addWidget(copy_btn, 1)

        card_layout.addWidget(action_frame)

        return card

    def copy_to_clipboard(self, text, button):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.show_copy_notification("🔗 Copied to Clipboard!", button)

    def handle_create_link(self):
        long_url = self.long_url_input.text().strip()
        alias = self.alias_input.text().strip()

        normalized_url = self.validate_url(long_url)
        if not normalized_url:
            self.show_notification("❌ Please enter a valid URL (e.g., https://example.com)", is_success=False)
            return

        if alias and not self.is_valid_custom_alias(alias):
            self.show_notification("❌ Alias can only contain letters, numbers, and hyphens (2-30 characters)",
                                   is_success=False)
            return

        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating & Saving...")
        self.remove_button_shadow(self.create_btn)  # Remove shadow to indicate loading

        url_data = {
            "original_url": normalized_url,
            "alias": alias if alias else None,
            "expiration": self.current_expiration,
            "user_id": self.get_current_user_id()
        }

        self.worker = CreateLinkWorker(url_data)
        self.worker.finished.connect(self.on_link_created)
        self.worker.error.connect(self.on_link_error)
        self.worker.start()

    def on_link_created(self, result):
        short_url = result.get('short_url', '')

        self.load_dashboard_content(show_result=True, short_url=short_url)

        self.long_url_input.clear()
        self.alias_input.clear()

        self.create_btn.setEnabled(True)
        self.create_btn.setText("Create Short Link")
        self.create_btn.style().polish(self.create_btn)
        self.apply_button_shadow(self.create_btn, is_primary=True)  # Re-apply shadow

        # Inform the user
        if "warning" not in short_url.lower():  # Simple check if the error was a warning from Firebase
            self.show_notification("✅ Link created and saved successfully!", is_success=True)

    def on_link_error(self, error_message):

        # If the error is the Firebase warning, treat it as a success but show a warning
        if "Firebase is disconnected" in error_message:
            # Extract the actual short link from the message for the user
            short_url = error_message.split(":")[1].split(",")[0].strip()
            self.load_dashboard_content(show_result=True, short_url=short_url)
            self.long_url_input.clear()
            self.alias_input.clear()
            self.show_notification(f"⚠️ Link created: {short_url}, but history save failed (Firebase error).",
                                   is_success=False)
        else:
            # A true failure (e.g., v.gd API error)
            QMessageBox.critical(self, "Operation Failed", f"Failed to create or save link:\n\n{error_message}")

        self.create_btn.setEnabled(True)
        self.create_btn.setText("Create Short Link")
        self.create_btn.style().polish(self.create_btn)
        self.apply_button_shadow(self.create_btn, is_primary=True)  # Re-apply shadow

    def validate_url(self, url: str) -> str:
        if not url: return ""
        if not url.startswith(('http://', 'https://')): url = 'https://' + url
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]): return url
        except:
            pass
        return ""

    def is_valid_custom_alias(self, alias: str) -> bool:
        if not alias: return True
        pattern = r'^[a-zA-Z0-9-]{2,30}$'
        return bool(re.match(pattern, alias))

    def toggle_expiration_dialog(self):
        if self.expiration_dialog and self.expiration_dialog.isVisible():
            self.expiration_dialog.hide()
            self.expiration_dialog.deleteLater()
            self.expiration_dialog = None
        else:
            self.show_expiration_dialog()

    def show_expiration_dialog(self):
        if self.expiration_dialog:
            self.expiration_dialog.deleteLater()
            self.expiration_dialog = None

        self.expiration_dialog = ExpirationDialog(self, self.current_expiration)
        self.expiration_dialog.expiration_selected.connect(self.on_expiration_selected)

        button_width = self.exp_button.width()
        self.expiration_dialog.setFixedWidth(button_width)

        button_pos = self.exp_button.mapToGlobal(self.exp_button.rect().bottomLeft())
        dialog_x = button_pos.x()
        dialog_y = button_pos.y() + 5
        self.expiration_dialog.move(dialog_x, dialog_y)
        self.expiration_dialog.show()

    def on_expiration_selected(self, expiration):
        self.current_expiration = expiration
        self.exp_button.setText(expiration)

        if self.expiration_dialog:
            self.expiration_dialog.hide()
            self.expiration_dialog.deleteLater()
            self.expiration_dialog = None

    # --- Navigation Logic ---
    def _create_nav_button(self, text, name):
        btn = QPushButton(text)
        btn.setObjectName("navButton")
        btn.clicked.connect(lambda: self.switch_tab(name))
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _update_nav_state(self, new_tab):
        buttons = {
            "dashboard": self.dash_btn,
            "history": self.hist_btn,
            "settings": self.sett_btn
        }

        for name, btn in buttons.items():
            if name == new_tab:
                btn.setProperty("state", "active")
            else:
                btn.setProperty("state", "inactive")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def switch_tab(self, new_tab):
        if self.active_tab == new_tab:
            return

        self.active_tab = new_tab
        self._update_nav_state(new_tab)

        # Hide all page widgets
        self.dashboard_page.hide()
        self.history_page.hide()
        self.settings_page.hide()

        # Show the selected page widget
        if new_tab == "dashboard":
            self.dashboard_page.show()
            self.load_dashboard_content(show_result=False)  # Always reset to input form on tab change
        elif new_tab == "history":
            self.history_page.show()
        elif new_tab == "settings":
            self.settings_page.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # NOTE: Set auth_app_instance=None for standalone testing
    home_window = HomeWindow(user_id="standalone_user_42")
    home_window.show()
    sys.exit(app.exec_())