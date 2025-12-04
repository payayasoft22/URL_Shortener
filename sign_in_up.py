import sys
import requests
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

# --- Import the HomeWindow from home.py ---
try:
    from home import HomeWindow
except ImportError:
    # Fallback for testing if home.py is not yet available
    class HomeWindow(QMainWindow):
        def __init__(self, parent=None, user_id=None):
            super().__init__(parent)
            self.setWindowTitle(f"Home Window (User: {user_id or 'Unknown'})")
            self.setGeometry(100, 100, 800, 600)
            label = QLabel(f"Welcome Home! User ID: {user_id}", self)
            label.setAlignment(Qt.AlignCenter)
            self.setCentralWidget(label)

# --- STYLESHEET (Unchanged) ---
STYLESHEET = """
QMainWindow {
    background-color: #F8F8F8; 
}

#authCard {
    background-color: white;
    border-radius: 14px;
    border: 1px solid #D9D9D9;
}

QLabel {
    font-family: "Arial";
    font-size: 14px; 
    font-weight: 500; 
    color: #374151;
}

#statusMessage {
    /* Base style for any status message (color set dynamically in Python) */
    font-weight: 600;
    font-size: 14px;
    padding: 8px 0;
}

#mainTitle {
    font-size: 34px; 
    font-weight: bold;
    color: black;
}

#mainSubtitle, #subtitleLabel {
    font-size: 14px; 
    font-weight: normal; 
    color: #6B7280;
}

#authInput {
    border: 1px solid #DCDEE5;
    border-radius: 12px;
    padding: 10px 15px;
    background-color: #e8eaed;
    color: #374151;
    font-size: 16px; 
}

#authInput:focus {
    border: 2px solid #10C988;
    background-color: #e8eaed;
}

#primaryButton {
    background-color: #10C988;
    color: white;
    border-radius: 14px;
    border: none;
    font-size: 16px; 
    font-weight: bold;
    padding: 10px;
}

#primaryButton:hover {
    background-color: hsl(160, 84%, 39%, 0.9);
}

#primaryButton:pressed {
    background-color: #00A76A;
}
"""


class HoverLabel(QLabel):
    """Custom QLabel with hover effect for underline links."""

    def __init__(self, text_before, link_text, link_callback, font_size=14):
        super().__init__()
        self.text_before = text_before
        self.link_text = link_text
        self.link_callback = link_callback
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)
        self.setTextFormat(Qt.RichText)
        self.setOpenExternalLinks(False)
        self.update_text(underline=False)
        self.linkActivated.connect(self.link_callback)
        self.font_size = font_size

    def update_text(self, underline=False):
        deco = "underline" if underline else "none"
        self.setText(
            f"{self.text_before} <a href='#' style='text-decoration:{deco}; color:#10C988;'>{self.link_text}</a>"
        )

    def enterEvent(self, event):
        self.update_text(underline=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_text(underline=False)
        super().leaveEvent(event)


class AuthApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shortly Desktop")
        self.resize(1440, 1024)
        self.setStyleSheet(STYLESHEET)

        # 🟢 API Configuration (Must match the FastAPI server)
        self.api_url = "http://127.0.0.1:8000/api"
        self.user_id = None  # Stores the authenticated user ID from the server

        # Variable to hold the HomeWindow instance
        self.home_window = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setAlignment(Qt.AlignHCenter)
        self.main_layout.addStretch(1)

        # --- Main Title ---
        self.main_title = QLabel("Shortly Desktop")
        self.main_title.setObjectName("mainTitle")
        self.main_title.setAlignment(Qt.AlignCenter)
        self.main_title.setFont(QFont("Arial", 36, QFont.Bold))
        self.main_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_layout.addWidget(self.main_title)

        # --- Main Subtitle ---
        self.main_subtitle = QLabel("Sign in to your account")
        self.main_subtitle.setObjectName("mainSubtitle")
        self.main_subtitle.setAlignment(Qt.AlignCenter)
        self.main_subtitle.setFont(QFont("Arial", 16))
        self.main_layout.addWidget(self.main_subtitle)

        self.main_layout.addSpacing(30)

        # --- Status Label Placeholder (Used for Error and Success) ---
        self.status_label = None

        # --- Auth Card ---
        self.auth_card = QFrame()
        self.auth_card.setObjectName("authCard")
        self.auth_card.setFixedWidth(448)
        self.auth_card.setSizePolicy(self.auth_card.sizePolicy().horizontalPolicy(),
                                     self.auth_card.sizePolicy().Preferred)

        # Shadow
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setOffset(0, 4)
        card_shadow.setColor(QColor(0, 0, 0, 50))
        self.auth_card.setGraphicsEffect(card_shadow)

        self.card_layout = QVBoxLayout(self.auth_card)
        self.card_layout.setContentsMargins(40, 30, 40, 30)
        self.card_layout.setSpacing(15)

        self.main_layout.addWidget(self.auth_card, 0, Qt.AlignHCenter)
        self.main_layout.addStretch(2)

        # Start with login form
        self.create_login_form()

    # --- Status Message Helpers ---
    def set_status_message(self, message, is_success):
        """Sets the status message text and styling (color)."""
        if self.status_label:
            color = "#10C988" if is_success else "#EF4444"  # Green for success, Red for error
            self.status_label.setText(message)
            self.status_label.setStyleSheet(f"QLabel#statusMessage {{ color: {color}; }}")
            self.status_label.show()

    # --- Window Transition ---
    def login_success(self):
        """Triggers the window transition after a brief delay."""
        # This is where the successful login redirects the information (self.user_id)
        QTimer.singleShot(800, self._transition_to_home)

    def _transition_to_home(self):
        """Internal method to handle the window swap."""
        # Create HomeWindow only once, passing the authenticated user_id
        if self.home_window is None:
            # Passes the user_id retrieved from the successful API response
            self.home_window = HomeWindow(self, user_id=self.user_id)

        self.home_window.show()
        self.hide()

    def clear_card_layout(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # --- Helper Methods for UI (input and button creation) ---
    def create_input_field(self, placeholder, is_password=False):
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setFont(QFont("Arial", 14))
        field.setMinimumHeight(48)
        field.setObjectName("authInput")
        if is_password:
            field.setEchoMode(QLineEdit.Password)
        return field

    def create_primary_button(self, text):
        button = QPushButton(text)
        button.setMinimumHeight(48)
        button.setObjectName("primaryButton")
        return button

    # --- Login Form ---
    def create_login_form(self, initial_message=None, is_success=False):
        self.main_title.setText("Welcome Back")
        self.main_subtitle.setText("Sign in to your account")
        self.clear_card_layout()

        self.status_label = QLabel("Status Message Placeholder")
        self.status_label.setObjectName("statusMessage")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        self.card_layout.addWidget(self.status_label)

        if initial_message:
            self.set_status_message(initial_message, is_success)

        self.card_layout.addWidget(QLabel("Email"))
        email_input = self.create_input_field("Email")
        self.card_layout.addWidget(email_input)

        self.card_layout.addSpacing(16)

        self.card_layout.addWidget(QLabel("Password"))
        pw_input = self.create_input_field("********", True)
        self.card_layout.addWidget(pw_input)

        self.card_layout.addSpacing(14)

        login_btn = self.create_primary_button("Login")
        login_btn.clicked.connect(lambda: self.validate_login(email_input.text(), pw_input.text()))

        self.card_layout.addWidget(login_btn)

        self.card_layout.addSpacing(15)

        switch_label = HoverLabel("Don't have an account?", "Create Account", self.create_signup_form, font_size=14)
        self.card_layout.addWidget(switch_label)
        self.auth_card.adjustSize()

    # 🟢 API Call for Login
    def validate_login(self, email, password):
        """Attempts to log in via the FastAPI backend."""
        if not email or not password:
            self.set_status_message("Email and Password are required.", False)
            return

        self.set_status_message("Logging in...", True)

        url = f"{self.api_url}/login"
        payload = {"email": email, "password": password}

        try:
            response = requests.post(url, json=payload, timeout=5)

            if response.status_code == 200:
                # Login successful: Extract user_id from the server response
                user_data = response.json()
                self.user_id = user_data.get("user_id")  # <-- Capturing the user ID!

                self.set_status_message("Login successful! Redirecting...", True)
                self.login_success()
            else:
                # Handle API errors
                try:
                    error_detail = response.json().get("detail", "Login failed due to server error.")
                except json.JSONDecodeError:
                    error_detail = f"Login failed: Server responded with status {response.status_code}"
                self.set_status_message(error_detail, False)

        except requests.exceptions.ConnectionError:
            self.set_status_message("Connection error: Is the FastAPI server running on 127.0.0.1:8000?", False)
        except requests.exceptions.RequestException as e:
            self.set_status_message(f"An unexpected error occurred: {e}", False)

    # --- Signup Form ---
    def create_signup_form(self):
        self.main_title.setText("Join Shortly Desktop")
        self.main_subtitle.setText("Create your account to get started")
        self.clear_card_layout()

        self.status_label = QLabel("Status Message Placeholder")
        self.status_label.setObjectName("statusMessage")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        self.card_layout.addWidget(self.status_label)

        self.card_layout.addWidget(QLabel("Email"))
        email_input = self.create_input_field("Email")
        self.card_layout.addWidget(email_input)

        self.card_layout.addSpacing(16)

        self.card_layout.addWidget(QLabel("Password"))
        pw_input = self.create_input_field("********", True)
        self.card_layout.addWidget(pw_input)

        self.card_layout.addSpacing(16)

        self.card_layout.addWidget(QLabel("Confirm Password"))
        cpw_input = self.create_input_field("********", True)
        self.card_layout.addWidget(cpw_input)

        self.card_layout.addSpacing(14)

        create_btn = self.create_primary_button("Create Account")
        create_btn.clicked.connect(lambda: self.validate_signup(email_input.text(), pw_input.text(), cpw_input.text()))

        self.card_layout.addWidget(create_btn)

        self.card_layout.addSpacing(15)

        switch_label = HoverLabel("Already have an account?", "Back to Login", self.create_login_form, font_size=14)
        self.card_layout.addWidget(switch_label)
        self.auth_card.adjustSize()

    # 🟢 API Call for Signup
    def validate_signup(self, email, password, confirm_password):
        """Handles local validation and then attempts to sign up via the FastAPI backend."""

        # 1. Local validation checks
        if not email or not password or not confirm_password:
            self.set_status_message("All fields are required.", False)
            return
        elif password != confirm_password:
            self.set_status_message("Passwords do not match.", False)
            return

        self.set_status_message("Creating account...", True)

        url = f"{self.api_url}/signup"
        payload = {"email": email, "password": password}

        try:
            response = requests.post(url, json=payload, timeout=5)

            if response.status_code == 200:
                # Signup successful: Switch back to login form
                success_message = "Account successfully created! Please log in."
                self.create_login_form(initial_message=success_message, is_success=True)
            else:
                # Handle API errors
                try:
                    error_detail = response.json().get("detail", "Signup failed due to server error.")
                except json.JSONDecodeError:
                    error_detail = f"Signup failed: Server responded with status {response.status_code}"
                self.set_status_message(error_detail, False)

        except requests.exceptions.ConnectionError:
            self.set_status_message("Connection error: Is the FastAPI server running on 127.0.0.1:8000?", False)
        except requests.exceptions.RequestException as e:
            self.set_status_message(f"An unexpected error occurred: {e}", False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuthApp()
    window.show()
    sys.exit(app.exec_())