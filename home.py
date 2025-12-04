# home.prtgry (Complete Code using v.gd API + Firebase Firestore)
import requests
import json
from urllib.parse import urlparse
import re
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import datetime  # Keep this top-level import
import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QHBoxLayout, QSizePolicy, QScrollArea, QLineEdit, QGraphicsDropShadowEffect,
    QApplication, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
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
                print("✅ Firebase initialized successfully (using serviceAccountKey.json)")
                return firestore.client()
            else:
                print("❌ Firebase skipped: 'serviceAccountKey.json' not found. History saving disabled.")
                return None
        return firestore.client()
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return None


firebase_db = initialize_firebase()


# =========================================================================================


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

    def __init__(self, *args, parent_app, is_primary=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_app = parent_app
        self.is_primary = is_primary
        self.parent_app.apply_button_shadow(self, self.is_primary)

    def enterEvent(self, event):
        if self.isEnabled():
            self.parent_app.apply_button_shadow(self, self.is_primary)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.parent_app.remove_button_shadow(self)
        super().leaveEvent(event)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        if enabled:
            self.parent_app.apply_button_shadow(self, self.is_primary)
        else:
            self.parent_app.remove_button_shadow(self)


class HomeWindow(QMainWindow):
    # --- Shadow Helpers ---
    def apply_button_shadow(self, button, is_primary):
        shadow = QGraphicsDropShadowEffect(button)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 3)
        if is_primary:
            shadow.setColor(QColor(0, 180, 120, 120))
        else:
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

        self.setStyleSheet("""
            QMainWindow { background-color: #F8F8F8; } #headerFrame { background-color: white; border-top: 1px solid #D9D9D9; border-bottom: 1px solid #D9D9D9; } #headerTitle { font-family: "Arial"; font-size: 24px; font-weight: bold; color: #10C988; padding-right: 20px; } #logoutButton { background-color: #EF4444; color: white; border-radius: 10px; border: none; font-size: 16px; padding: 5px 15px; } #logoutButton:hover { background-color: #DC2626; } QScrollArea { border: none; background-color: #F8F8F8; } #scrollContent { background-color: #F8F8F8; } .navButton { font-family: "Arial"; font-size: 14px; font-weight: 500; border: none; border-radius: 10px; padding: 10px 15px; margin-right: 8px; cursor: pointer; } .navButton[state="inactive"] { background-color: transparent; color: #6B7280; } .navButton[state="inactive"]:hover { background-color: #E5E7EB; color: #374151; } .navButton[state="active"] { background-color: #E8F8F4; color: #10C988; } .navButton[state="active"]:hover { background-color: #10C988; color: white; } #shortenerCard, #successCard { background-color: white; border-radius: 14px; border: 1px solid #D9D9D9; } #inputLabel { font-family: "Arial"; font-size: 14px; font-weight: 500; color: #374151; } #cardTitle { font-size: 20px; font-weight: bold; color: black; } #cardSubtitle, #successMessage { font-size: 14px; font-weight: normal; color: #6B7280; } #urlInput, #aliasInput, #expirationButton { border: 1px solid #DCDEE5; border-radius: 12px; padding: 10px 15px; background-color: #F3F4F6; color: #374151; font-size: 16px; } #urlInput:focus, #aliasInput:focus, #expirationButton:focus { border: 2px solid #10C988; background-color: #e8eaed; } #expirationButton { text-align: left; background-color: #F3F4F6; cursor: pointer; } #expirationButton:hover { background-color: #E5E7EB; } #createButton { background-color: #10C988; color: white; border-radius: 14px; border: none; font-size: 16px; font-weight: bold; padding: 10px; min-height: 25px; cursor: pointer; } #createButton:hover { background-color: #10C988; } #createButton:pressed { background-color: #10C988; } #createButton:disabled { background-color: #9CA3AF; cursor: not-allowed; } #shortUrlDisplay { background-color: #F8F8F8; border: 1px solid #DCDEE5; border-radius: 12px; padding: 10px 15px; } #shortUrlText { font-size: 16px; font-weight: 500; color: #10C988; } .actionButton { background-color: #E5E7EB; color: #374151; border-radius: 12px; border: 1px solid transparent; font-size: 16px; padding: 10px 20px; min-height: 48px; cursor: pointer; } .actionButton:hover { background-color: #E5E7EB; } .actionButton:pressed { background-color: #E5E7EB; } .actionButton:disabled { background-color: #D1D5DB; color: #9CA3AF; cursor: not-allowed; } #expirationButton::after { content: "▼"; float: right; font-size: 12px; color: #6B7280; }
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

        check_icon = QLabel("✅")
        check_icon.setFont(QFont("Arial", 18))

        message_label = QLabel("Your shortened link is ready!")
        message_label.setObjectName("successMessage")

        success_layout.addWidget(check_icon)
        success_layout.addWidget(message_label)
        success_layout.addStretch(1)

        card_layout.addWidget(success_frame)

        display_frame = QFrame()
        display_frame.setObjectName("shortUrlDisplay")
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(2)

        short_label = QLabel("Short URL")
        short_label.setObjectName("inputLabel")

        self.short_link_text = QLabel(short_url)
        self.short_link_text.setObjectName("shortUrlText")
        self.short_link_text.setCursor(Qt.IBeamCursor)
        self.short_link_text.setTextInteractionFlags(Qt.TextSelectableByMouse)

        display_layout.addWidget(short_label)
        display_layout.addWidget(self.short_link_text)

        card_layout.addWidget(display_frame)

        # Action Buttons (Copy, QR) - Use ShadowButton, is_primary=False
        action_frame = QFrame()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)

        self.copy_btn = ShadowButton("📋 Copy", parent_app=self, is_primary=False)
        self.copy_btn.setObjectName("copyButton")
        self.copy_btn.setProperty("class", "actionButton")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(lambda: self.copy_to_clipboard(short_url))

        self.qr_btn = ShadowButton("QR", parent_app=self, is_primary=False)
        self.qr_btn.setObjectName("qrButton")
        self.qr_btn.setProperty("class", "actionButton")
        self.qr_btn.setCursor(Qt.PointingHandCursor)
        self.qr_btn.clicked.connect(lambda: self.generate_qr_code(short_url))

        action_layout.addStretch(1)
        action_layout.addWidget(self.copy_btn)
        action_layout.addWidget(self.qr_btn)

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

        self.create_btn = ShadowButton("🔗 Create Short Link", parent_app=self, is_primary=True)
        self.create_btn.setObjectName("createButton")
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
            QMessageBox.warning(self, "Validation Error",
                                "Please enter a valid URL (e.g., https://example.com)")
            return

        if alias and not self.is_valid_custom_alias(alias):
            QMessageBox.warning(self, "Validation Error",
                                "Alias can only contain letters, numbers, and hyphens (2-30 characters)")
            return

        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating & Saving...")

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

        self.load_dashboard_content(show_result=True, short_url=short_url)

        self.long_url_input.clear()
        self.alias_input.clear()

        success_msg = f"""✅ Short URL created via v.gd and History SAVED!

📊 Details:
• Original URL: {result.get('original_url', '')[:60]}...
• **Accessible Short URL:** {short_url}
• Short Code: {result.get('short_code', '')}

🔗 The link is public, and the details are stored in your Firebase History.
"""
        QMessageBox.information(self, "Success - Link Created & Saved", success_msg)

        self.create_btn.setEnabled(True)
        self.create_btn.setText("🔗 Create Short Link")
        self.create_btn.style().polish(self.create_btn)

    def on_link_error(self, error_message):
        QMessageBox.critical(self, "Operation Failed",
                             f"Failed to create or save link:\n\n{error_message}")

        self.create_btn.setEnabled(True)
        self.create_btn.setText("🔗 Create Short Link")
        self.create_btn.style().polish(self.create_btn)

    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        msg = QMessageBox(self)
        msg.setWindowTitle("Copied")
        msg.setText("✅ URL copied to clipboard!")
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def generate_qr_code(self, url):
        try:
            import qrcode
            from PIL import ImageQt
            from PyQt5.QtGui import QPixmap

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            qim = ImageQt.ImageQt(img)
            pixmap = QPixmap.fromImage(qim)

            dialog = QMessageBox(self)
            dialog.setWindowTitle("QR Code")
            dialog.setText(f"QR Code for:\n{url}")

            qr_label = QLabel()
            qr_label.setPixmap(pixmap)
            qr_label.setAlignment(Qt.AlignCenter)

            dialog.layout().addWidget(qr_label, 1, 0, 1, dialog.layout().columnCount())

            copy_btn = QPushButton("Copy URL")
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(url))
            dialog.addButton(copy_btn, QMessageBox.ActionRole)

            dialog.exec_()

        except ImportError:
            QMessageBox.warning(self, "QR Code Error",
                                "Please install qrcode and PIL packages:\n"
                                "pip install qrcode[pil]")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate QR code: {str(e)}")

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
            self.load_dashboard_content(show_result=False)

        elif tab_name == "history":
            history_page = HistoryPage(self.get_current_user_id())
            self.content_layout.addWidget(history_page)

        elif tab_name == "settings":
            title = QLabel("Page: Settings")
            title.setFont(QFont("Arial", 48, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(title)

            content_label = QLabel("Adjusting application preferences...")
            content_label.setFont(QFont("Arial", 24))
            self.content_layout.addWidget(content_label)
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
            display_url = short_url if short_url else "https://v.gd/example"
            result_display = self.create_short_link_display(short_url=display_url)
            self.content_layout.addWidget(result_display, alignment=Qt.AlignHCenter)

        self.content_layout.addStretch(1)

    def logout(self):
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        if self.auth_app_instance:
            self.hide()
            self.auth_app_instance.user_id = None
            self.auth_app_instance.show()
            self.auth_app_instance.create_login_form(initial_message="Logged out successfully.", is_success=True)
        else:
            QApplication.quit()
