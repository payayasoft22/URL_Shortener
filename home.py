# HomeWindow.py (Full Code)

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

# Import the corrected QWidget-based SettingsPage
# NOTE: Ensure settings.py is in the same directory
from settings import SettingsPage

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QHBoxLayout, QSizePolicy, QScrollArea, QLineEdit, QGraphicsDropShadowEffect,
    QApplication, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QPoint, QRect, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPainter, QPen

# NOTE: Assume HistoryPage is defined elsewhere.
try:
    from history import HistoryPage
except ImportError:
    class HistoryPage(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.setLayout(QVBoxLayout())
            self.layout().addWidget(
                QLabel("HistoryPage requires separate definition and is disabled.", alignment=Qt.AlignCenter))

# ==================== CONFIGURATION (is.gd / v.gd) ====================
ISGD_API_ENDPOINT = "https://v.gd/create.php"


# ======================================================================


# ==================== FIREBASE SETUP (Re-enabled for Saving History) ====================
def initialize_firebase():
    """Initializes Firebase if a service account key is available."""
    try:
        if not firebase_admin._apps:
            service_account_path = "serviceAccountKey.json"
            if os.path.exists(service_account_path):
                # Ensure you have serviceAccountKey.json file in your project directory
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                # print("✅ Firebase initialized successfully (using serviceAccountKey.json)")
                return firestore.client()
            else:
                # print("❌ Firebase skipped: 'serviceAccountKey.json' not found. History saving disabled.")
                return None
        return firestore.client()
    except Exception as e:
        # print(f"❌ Firebase initialization failed: {e}")
        return None


firebase_db = initialize_firebase()


# =========================================================================================

# ==================== IMPROVED NOTIFICATION BAR CLASS ====================
class NotificationBar(QFrame):
    def __init__(self, message_text, is_success, parent=None, position="top"):
        super().__init__(parent)
        self.position = position
        self.setAttribute(Qt.WA_StyledBackground)

        # Set size based on position
        if position == "top":
            self.setFixedWidth(450)
            self.setFixedHeight(60)
        else:  # bottom
            self.setFixedWidth(350)
            self.setFixedHeight(50)

        # Different styles for top vs bottom notifications
        if position == "top":
            if is_success:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #E8F8F4;
                        border: 2px solid #10C988;
                        border-radius: 12px;
                        padding: 10px;
                    }
                    QLabel {
                        color: #064E3B;
                        font-size: 16px;
                        font-weight: 600;
                    }
                """)
                icon = "✓"
            else:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #FEE2E2;
                        border: 2px solid #EF4444;
                        border-radius: 12px;
                        padding: 10px;
                    }
                    QLabel {
                        color: #7F1D1D;
                        font-size: 16px;
                        font-weight: 600;
                    }
                """)
                icon = "⚠️"
        else:  # bottom position
            if is_success:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #D1FAE5;
                        border: 1px solid #10C988;
                        border-radius: 8px;
                        padding: 8px;
                    }
                    QLabel {
                        color: #064E3B;
                        font-size: 14px;
                        font-weight: 500;
                    }
                """)
                icon = "✓"
            else:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #FEE2E2;
                        border: 1px solid #EF4444;
                        border-radius: 8px;
                        padding: 8px;
                    }
                    QLabel {
                        color: #7F1D1D;
                        font-size: 14px;
                        font-weight: 500;
                    }
                """)
                icon = "⚠️"

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

        # Setup animation
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        self.hide()

    def show_animated(self, parent_rect):
        """Show with slide-in animation"""
        if self.position == "top":
            start_rect = QRect(
                parent_rect.center().x() - self.width() // 2,
                -self.height(),
                self.width(),
                self.height()
            )
            end_rect = QRect(
                parent_rect.center().x() - self.width() // 2,
                80,  # Position below header
                self.width(),
                self.height()
            )
        else:  # bottom
            start_rect = QRect(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.bottom(),
                self.width(),
                self.height()
            )
            end_rect = QRect(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.bottom() - self.height() - 20,
                self.width(),
                self.height()
            )

        self.setGeometry(start_rect)
        self.show()
        self.raise_()

        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)
        self.animation.start()

    def hide_animated(self):
        """Hide with slide-out animation"""
        if self.position == "top":
            end_rect = QRect(
                self.x(),
                -self.height(),
                self.width(),
                self.height()
            )
        else:  # bottom
            end_rect = QRect(
                self.x(),
                self.parent().height(),
                self.width(),
                self.height()
            )

        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(end_rect)
        self.animation.finished.connect(self.hide_and_destroy)
        self.animation.start()

    def show_and_hide(self, duration=3000):
        """Shows the bar and sets a timer to hide and destroy it."""
        parent = self.parent()
        if parent:
            self.show_animated(parent.rect())
        else:
            # Fallback if no parent
            self.show()
        QTimer.singleShot(duration, self.hide_animated)

    def hide_and_destroy(self):
        """Hides the bar and marks it for garbage collection."""
        self.hide()
        self.deleteLater()


class CopyNotification(QFrame):
    """Special notification that appears above the copy button"""

    def __init__(self, message_text, parent_button):
        super().__init__(parent_button.parent())
        self.parent_button = parent_button
        self.setAttribute(Qt.WA_StyledBackground)
        self.setFixedWidth(200)
        self.setFixedHeight(40)

        self.setStyleSheet("""
            QFrame {
                background-color: #10C988;
                border: 1px solid #0DA875;
                border-radius: 6px;
                padding: 5px;
            }
            QLabel {
                color: white;
                font-size: 13px;
                font-weight: 500;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)

        message_label = QLabel(message_text)
        message_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(message_label)

        self.hide()

    def show_at_button(self):
        """Position above the copy button"""
        if not self.parent_button:
            return

        try:
            button_pos = self.parent_button.mapToGlobal(self.parent_button.rect().topLeft())
            parent_pos = self.parent().mapFromGlobal(button_pos)

            x = parent_pos.x() + (self.parent_button.width() - self.width()) // 2
            y = parent_pos.y() - self.height() - 5

            self.move(x, y)
            self.show()
            self.raise_()

            # Auto hide after 2 seconds
            QTimer.singleShot(2000, self.hide_and_destroy)
        except Exception as e:
            # print(f"Error showing copy notification: {e}")
            self.hide_and_destroy()

    def hide_and_destroy(self):
        self.hide()
        self.deleteLater()


# ======================================================================

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
    """
    Worker thread that 1) calls the v.gd API to shorten the link,
    and 2) saves the result to Firebase Firestore for user history.
    """
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url_data):
        super().__init__()
        self.url_data = url_data

    def run(self):
        # FIX: Import datetime module with an alias to avoid namespace conflict
        import datetime as dt

        long_url = self.url_data['original_url']
        alias = self.url_data.get('alias')

        # --- STEP 1: Call External API (v.gd) ---
        params = {
            "url": long_url,
            "format": "simple"
        }
        if alias:
            params["shorturl"] = alias

        try:
            response = requests.get(
                ISGD_API_ENDPOINT,
                params=params,
                timeout=15
            )
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
            # If Firebase fails, still report the short link but warn about history loss
            self.error.emit(f"Short link created: {short_url}, but Firebase is disconnected. History not saved.")
            return

        short_code = short_url.split('/')[-1]

        # Calculate expiration date (FIXED LOGIC)
        expires_at = None
        if self.url_data['expiration'] != "Never":
            days = 7 if "7" in self.url_data['expiration'] else 30
            # FIX: Use dt.datetime and dt.timedelta to avoid namespace error
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
            # Save to history collection using a unique document ID
            doc_id = str(uuid.uuid4())
            firebase_db.collection('url_history').document(doc_id).set(firestore_data)

            # 3. Return Success Result
            result = {
                'short_url': short_url,
                'original_url': long_url,
                'short_code': short_code,
                'alias': alias,
                'expiration': self.url_data['expiration'],
                'created_at': dt.datetime.now().isoformat()  # Use dt here too for consistency
            }
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(f"Short link created ({short_url}), but failed to save history to Firebase: {str(e)}")


class ShadowButton(QPushButton):
    """Custom QPushButton that calls parent methods to toggle shadow on mouse events."""

    def __init__(self, *args, parent_app, is_primary=True, is_danger=False, **kwargs): # Added is_danger
        super().__init__(*args, **kwargs)
        self.parent_app = parent_app
        self.is_primary = is_primary
        self.is_danger = is_danger # Store danger status
        self.parent_app.apply_button_shadow(self, self.is_primary, is_danger=self.is_danger) # Pass danger

    def enterEvent(self, event):
        if self.isEnabled():
            self.parent_app.apply_button_shadow(self, self.is_primary, is_danger=self.is_danger) # Pass danger
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.parent_app.remove_button_shadow(self)
        super().leaveEvent(event)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        if enabled:
            self.parent_app.apply_button_shadow(self, self.is_primary, is_danger=self.is_danger) # Pass danger
        else:
            self.parent_app.remove_button_shadow(self)


class HomeWindow(QMainWindow):
    # --- Shadow Helpers (Modified to include is_danger parameter) ---
    def apply_button_shadow(self, button, is_primary, is_danger=False):
        shadow = QGraphicsDropShadowEffect(button)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 3)
        if is_danger:
            # Red shadow for danger buttons (Used by SettingsPage)
            shadow.setColor(QColor(239, 68, 68, 120))
        elif is_primary:
            # Green shadow for primary buttons (Used by Dashboard)
            shadow.setColor(QColor(0, 180, 120, 120))
        else:
            # General/Secondary shadow
            shadow.setColor(QColor(0, 0, 0, 60))
        button.setGraphicsEffect(shadow)

    def remove_button_shadow(self, button):
        button.setGraphicsEffect(None)

    # ----------------------

    def __init__(self, auth_app_instance=None, user_id="test_user_123"):
        super().__init__()
        self.auth_app_instance = auth_app_instance
        self.user_id = user_id
        self.setWindowTitle("Shortly Desktop - Home")
        self.resize(1440, 1024)

        self.active_tab = "dashboard"
        self.current_expiration = "30 days"
        self.expiration_dialog = None
        self.current_short_url = ""
        self.worker = None
        self.notification_bar = None  # To track the active notification
        self.copy_notification = None  # Track copy button notification
        self.last_created_short_url = ""  # Store the last created URL
        self.current_copy_button = None  # Store reference to current copy button

        self.setStyleSheet("""
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

            /* Create Short Link Button Style */
            #createButton, #copyButton { 
                background-color: #10C988; 
                color: white; 
                border-radius: 14px; 
                border: none; 
                font-size: 16px; 
                font-weight: bold; 
                padding: 10px; 
                min-height: 25px; 
                cursor: pointer;
            } 
            #createButton:hover, #copyButton:hover { 
                background-color: #0DA875; /* Slightly darker */
            } 
            #createButton:pressed, #copyButton:pressed { 
                background-color: #0B8F67; /* Even darker */
            } 
            #createButton:disabled, #copyButton:disabled { 
                background-color: #9CA3AF; 
                cursor: not-allowed; 
            } 
            /* End Create/Copy Button Style */

            #shortUrlDisplay { background-color: #F8F8F8; border: 1px solid #DCDEE5; border-radius: 12px; padding: 10px 15px; } 
            #shortUrlText { font-size: 16px; font-weight: 500; color: #10C988; } 
            .actionButton { background-color: #E5E7EB; color: #374151; border-radius: 12px; border: 1px solid transparent; font-size: 16px; padding: 10px 20px; min-height: 48px; cursor: pointer; } 
            .actionButton:hover { background-color: #D1D5DB; } 
            .actionButton:pressed { background-color: #A0A4AD; } 
            .actionButton:disabled { background-color: #D1D5DB; color: #9CA3AF; cursor: not-allowed; } 
            #expirationButton::after { content: "▼"; float: right; font-size: 12px; color: #6B7280; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

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

        header_layout.addStretch(1)

        self.nav_frame = QFrame()
        self.nav_layout = QHBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(0)

        self.dash_btn = self._create_nav_button("Dashboard", "dashboard")
        self.hist_btn = self._create_nav_button("History", "history")
        self.sett_btn = self._create_nav_button("Settings", "settings")

        self.nav_layout.addWidget(self.dash_btn)
        self.nav_layout.addWidget(self.hist_btn)
        self.nav_layout.addWidget(self.sett_btn)

        header_layout.addWidget(self.nav_frame)
        header_layout.addStretch(1)

        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("logoutButton")
        logout_btn.setFixedSize(120, 38)
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(logout_btn)

        main_layout.addWidget(self.header_frame)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("scrollContent")
        self.scroll_area.setWidget(self.content_widget)

        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(40, 40, 40, 40)

        main_layout.addWidget(self.scroll_area, 1)

        self.switch_tab("dashboard")

    def show_notification(self, message, is_success, position="top", duration=3000):
        """Creates and displays a notification bar at specified position."""
        # Cleanup old notification if present
        if self.notification_bar:
            try:
                self.notification_bar.hide_and_destroy()
            except:
                pass
            self.notification_bar = None

        # Create new notification bar
        self.notification_bar = NotificationBar(message, is_success, parent=self, position=position)
        self.notification_bar.show_and_hide(duration)

    def show_copy_notification(self, message, button=None):
        """Shows a small notification above the copy button"""
        if self.copy_notification:
            try:
                self.copy_notification.hide_and_destroy()
            except:
                pass
            self.copy_notification = None

        target_button = button or self.current_copy_button
        if target_button:
            try:
                self.copy_notification = CopyNotification(message, target_button)
                self.copy_notification.show_at_button()
            except Exception as e:
                # print(f"Error showing copy notification: {e}")
                # Fallback to regular notification
                self.show_notification(message, is_success=True, position="bottom", duration=2000)

    def get_current_user_id(self):
        return self.user_id

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

    def create_short_link_display(self, short_url):
        """Create a display card for the shortened URL"""
        card = QFrame()
        card.setObjectName("successCard")
        card.setMinimumWidth(736)
        card.setMaximumWidth(736)
        card.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setOffset(0, 4)
        card_shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(card_shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 20, 30, 20)
        card_layout.setSpacing(15)

        success_frame = QFrame()
        success_layout = QHBoxLayout(success_frame)
        success_layout.setContentsMargins(0, 0, 0, 0)
        success_layout.setSpacing(10)

        check_icon = QLabel("✓")
        check_icon.setFont(QFont("Arial", 18, QFont.Bold))
        check_icon.setStyleSheet("color: #10C988;")

        title_label = QLabel("Short Link Created & Saved")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #064E3B;")

        success_layout.addWidget(check_icon)
        success_layout.addWidget(title_label)
        success_layout.addStretch(1)

        card_layout.addWidget(success_frame)

        message_label = QLabel("Your shortened link is ready!")
        message_label.setObjectName("successMessage")
        message_label.setFont(QFont("Arial", 14))
        card_layout.addWidget(message_label)

        display_frame = QFrame()
        display_frame.setObjectName("shortUrlDisplay")
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(2)

        short_label = QLabel("Your short link")
        short_label.setObjectName("inputLabel")

        short_link_text = QLabel(short_url)
        short_link_text.setObjectName("shortUrlText")
        short_link_text.setCursor(Qt.IBeamCursor)
        short_link_text.setTextInteractionFlags(Qt.TextSelectableByMouse)

        display_layout.addWidget(short_label)
        display_layout.addWidget(short_link_text)

        card_layout.addWidget(display_frame)

        action_frame = QFrame()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)

        # Create a regular QPushButton instead of ShadowButton to avoid parent_app issues
        copy_btn = QPushButton("Copy URL")
        copy_btn.setObjectName("copyButton")
        copy_btn.setCursor(Qt.PointingHandCursor)
        # Store the short_url in the button's property for access in the lambda
        copy_btn.setProperty("short_url", short_url)
        copy_btn.clicked.connect(lambda checked, btn=copy_btn: self.copy_to_clipboard(btn.property("short_url"), btn))
        self.apply_button_shadow(copy_btn, is_primary=True)  # Apply shadow manually

        action_layout.addStretch(1)
        action_layout.addWidget(copy_btn)

        card_layout.addWidget(action_frame)

        return card

    def create_url_shortener_card(self):
        card = QFrame()
        card.setObjectName("shortenerCard")
        card.setMinimumWidth(736)
        card.setMaximumWidth(736)
        card.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setOffset(0, 4)
        card_shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(card_shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(15)

        title_frame = QFrame()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_container = QFrame()
        title_vbox = QVBoxLayout(title_container)
        title_vbox.setContentsMargins(0, 0, 0, 0)
        title_vbox.setSpacing(5)

        card_title = QLabel("Shorten URL")
        card_title.setObjectName("cardTitle")
        card_subtitle = QLabel("Create a short link in seconds")
        card_subtitle.setObjectName("cardSubtitle")

        title_vbox.addWidget(card_title)
        title_vbox.addWidget(card_subtitle)

        title_layout.addWidget(title_container)
        title_layout.addStretch(1)

        card_layout.addWidget(title_frame)
        card_layout.addSpacing(10)

        url_label = QLabel("Long URL *")
        url_label.setObjectName("inputLabel")

        self.long_url_input = QLineEdit()
        self.long_url_input.setObjectName("urlInput")
        self.long_url_input.setPlaceholderText("https://example.com/very-long-url...")

        card_layout.addWidget(url_label)
        card_layout.addWidget(self.long_url_input)

        card_layout.addSpacing(5)

        side_by_side_frame = QFrame()
        side_by_side_layout = QHBoxLayout(side_by_side_frame)
        side_by_side_layout.setContentsMargins(0, 0, 0, 0)
        side_by_side_layout.setSpacing(15)

        alias_widget = QWidget()
        alias_vbox = QVBoxLayout(alias_widget)
        alias_vbox.setContentsMargins(0, 0, 0, 0)
        alias_vbox.setSpacing(5)
        alias_label = QLabel("Custom Alias (optional)")
        alias_label.setObjectName("inputLabel")
        self.alias_input = QLineEdit()
        self.alias_input.setObjectName("aliasInput")
        self.alias_input.setPlaceholderText("my-custom-link")
        alias_vbox.addWidget(alias_label)
        alias_vbox.addWidget(self.alias_input)

        exp_widget = QWidget()
        exp_vbox = QVBoxLayout(exp_widget)
        exp_vbox.setContentsMargins(0, 0, 0, 0)
        exp_vbox.setSpacing(5)
        exp_label = QLabel("Expiration")
        exp_label.setObjectName("inputLabel")

        self.exp_button = QPushButton(self.current_expiration)
        self.exp_button.setObjectName("expirationButton")
        self.exp_button.setCursor(Qt.PointingHandCursor)
        self.exp_button.clicked.connect(self.toggle_expiration_dialog)

        exp_vbox.addWidget(exp_label)
        exp_vbox.addWidget(self.exp_button)

        side_by_side_layout.addWidget(alias_widget, stretch=1)
        side_by_side_layout.addWidget(exp_widget, stretch=1)

        card_layout.addWidget(side_by_side_frame)
        card_layout.addSpacing(15)

        # Use ShadowButton here as it's intended to handle shadow logic
        self.create_btn = ShadowButton("Create Short Link", parent_app=self, is_primary=True, objectName="createButton")
        self.create_btn.clicked.connect(self.handle_create_link)

        card_layout.addWidget(self.create_btn)

        return card

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

        desktop = QApplication.desktop()
        screen_geometry = desktop.availableGeometry(desktop.primaryScreen())

        if dialog_y + self.expiration_dialog.height() > screen_geometry.bottom():
            dialog_y = button_pos.y() - self.expiration_dialog.height() - 5

        self.expiration_dialog.move(dialog_x, dialog_y)
        self.expiration_dialog.show()

    def on_expiration_selected(self, expiration):
        self.current_expiration = expiration
        self.exp_button.setText(expiration)

        if self.expiration_dialog:
            self.expiration_dialog.hide()
            self.expiration_dialog.deleteLater()
            self.expiration_dialog = None

    def handle_create_link(self):
        long_url = self.long_url_input.text().strip() if hasattr(self, 'long_url_input') else ""
        alias = self.alias_input.text().strip() if hasattr(self, 'alias_input') else ""

        normalized_url = self.validate_url(long_url)
        if not normalized_url:
            self.show_notification(
                "Please enter a valid URL (e.g., https://example.com)",
                is_success=False,
                position="bottom"
            )
            return

        if alias and not self.is_valid_custom_alias(alias):
            self.show_notification(
                "Alias can only contain letters, numbers, and hyphens (2-30 characters)",
                is_success=False,
                position="bottom"
            )
            return

        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating & Saving...")
        self.remove_button_shadow(self.create_btn)  # Remove shadow for disabled state

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
        self.current_short_url = short_url
        self.last_created_short_url = short_url

        # 1. Load the dashboard content to show the visual success card with the link
        self.load_dashboard_content(show_result=True, short_url=short_url)

        self.long_url_input.clear()
        self.alias_input.clear()

        # Show success notification at the top
        self.show_notification(
            "Short Link created and saved successfully!",
            is_success=True,
            position="top"
        )

        # Reset button state
        self.create_btn.setEnabled(True)
        self.create_btn.setText("Create Short Link")
        self.apply_button_shadow(self.create_btn, True)

    def on_link_error(self, error_message):
        self.show_notification(
            f"Operation Failed: {error_message.splitlines()[0]}",
            is_success=False,
            position="top",
            duration=5000
        )

        self.create_btn.setEnabled(True)
        self.create_btn.setText("Create Short Link")
        self.apply_button_shadow(self.create_btn, True)

    def copy_to_clipboard(self, text, button=None):
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

            # Store the button reference for the notification
            if button:
                self.current_copy_button = button

            # Show copy notification above the button
            self.show_copy_notification("Copied to clipboard!", button)

        except Exception as e:
            # Fallback to bottom notification if copy fails
            self.show_notification(
                f"Failed to copy: {str(e)}",
                is_success=False,
                position="bottom"
            )

    def _create_nav_button(self, text, name):
        btn = QPushButton(text)
        btn.setProperty("class", "navButton")
        btn.setObjectName(f"{name}Tab")
        btn.clicked.connect(lambda: self.switch_tab(name))
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def switch_tab(self, new_tab_name):
        buttons = {
            "dashboard": self.dash_btn,
            "history": self.hist_btn,
            "settings": self.sett_btn,
        }

        for name, btn in buttons.items():
            if name == new_tab_name:
                btn.setProperty("state", "active")
            else:
                btn.setProperty("state", "inactive")
            btn.style().polish(btn)

        self.active_tab = new_tab_name
        self.load_content_for_tab(new_tab_name)

    def load_content_for_tab(self, tab_name):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if tab_name == "dashboard":
            self.load_dashboard_content(show_result=bool(self.last_created_short_url))

        elif tab_name == "history":
            history_page = HistoryPage(self.get_current_user_id())
            self.content_layout.addWidget(history_page)

        elif tab_name == "settings":
            # SettingsPage is now a QWidget, correctly embedded
            # This is where the HomeWindow instance (self) is passed to settings.py
            settings_page = SettingsPage(parent_app=self, user_id=self.user_id)
            self.content_layout.addWidget(settings_page, alignment=Qt.AlignHCenter)

        self.content_layout.addStretch(1)

    def load_dashboard_content(self, show_result=False, short_url=None):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        shortener_card = self.create_url_shortener_card()
        self.content_layout.addWidget(shortener_card, alignment=Qt.AlignHCenter)

        if show_result:
            display_url = short_url or self.last_created_short_url
            if display_url:
                result_display = self.create_short_link_display(short_url=display_url)
                self.content_layout.addWidget(result_display, alignment=Qt.AlignHCenter)

        self.content_layout.addStretch(1)

    def logout(self):
        # Stop worker gracefully
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        # Handle authentication logic (if self.auth_app_instance exists)
        if self.auth_app_instance:
            self.hide()
            # Assuming auth_app_instance is the main application container/login window
            # and knows how to show itself.
            self.auth_app_instance.user_id = None
            # Assuming auth_app_instance has create_login_form method
            if hasattr(self.auth_app_instance, 'create_login_form'):
                 self.auth_app_instance.create_login_form("You have been successfully logged out.", is_success=True)
            self.auth_app_instance.show()
        else:
            # Fallback if no auth instance is passed (e.g., running HomeWindow standalone)
            QMessageBox.information(self, "Logout", "Logout successful! Closing application.")
            QApplication.quit()