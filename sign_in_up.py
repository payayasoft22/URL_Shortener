import sys
import requests
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

# --- Import the HomeWindow from home.py ---
try:
    # Assuming home.py is fixed and available
    from home import HomeWindow
except ImportError:
    # Fallback if home.py is not yet available in the environment
    class HomeWindow(QMainWindow):
        def __init__(self, auth_app_instance=None, user_id=None):  # Critical for redirection
            super().__init__(auth_app_instance)
            self.auth_app_instance = auth_app_instance
            self.user_id = user_id
            self.setWindowTitle(f"Home Window (User: {user_id or 'Unknown'})")
            self.setGeometry(100, 100, 800, 600)
            label = QLabel(f"Welcome Home! User ID: {user_id}", self)
            label.setAlignment(Qt.AlignCenter)
            self.setCentralWidget(label)

            # Placeholder for required methods to prevent errors
            def load_dashboard_content(self, show_result=False, short_url=None):
                pass

            def logout(self, message="Logged out.", is_success=True):
                if self.auth_app_instance:
                    self.auth_app_instance.show_login_form(message, is_success)
                self.close()

# --- STYLESHEET (No changes needed) ---
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


# --- HoverLabel and ShadowButton Classes (No changes needed) ---
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


class ShadowButton(QPushButton):
    """Custom QPushButton that toggles shadow on mouse events."""

    def __init__(self, *args, parent_app, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_app = parent_app
        # Apply shadow on initial creation
        self.parent_app.apply_button_shadow(self)

    def enterEvent(self, event):
        if self.isEnabled():
            self.parent_app.apply_button_shadow(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.parent_app.remove_button_shadow(self)
        super().leaveEvent(event)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        if enabled:
            self.parent_app.apply_button_shadow(self)
        else:
            self.parent_app.remove_button_shadow(self)


class AuthApp(QMainWindow):

    # --- Shadow Helpers ---
    def apply_button_shadow(self, button):
        # Greenish shadow for primary buttons in AuthApp
        shadow = QGraphicsDropShadowEffect(button)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 180, 120, 120))
        button.setGraphicsEffect(shadow)

    def remove_button_shadow(self, button):
        button.setGraphicsEffect(None)

    # ----------------------

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shortly Desktop")
        self.resize(1440, 1024)
        self.setStyleSheet(STYLESHEET)

        self.api_url = "http://127.0.0.1:8000/api"
        self.user_id = None

        # 🔑 CRITICAL CHANGE 1: Initialize HomeWindow early
        # This instance is created once and reused, passed 'self' (the AuthApp)
        self.home_window = HomeWindow(auth_app_instance=self, user_id=None)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setAlignment(Qt.AlignHCenter)
        self.main_layout.addStretch(1)

        self.main_title = QLabel("Shortly Desktop")
        self.main_title.setObjectName("mainTitle")
        self.main_title.setAlignment(Qt.AlignCenter)
        self.main_title.setFont(QFont("Arial", 36, QFont.Bold))
        self.main_layout.addWidget(self.main_title)

        self.main_subtitle = QLabel("Sign in to your account")
        self.main_subtitle.setObjectName("mainSubtitle")
        self.main_subtitle.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.main_subtitle)

        self.main_layout.addSpacing(30)

        self.status_label = None

        self.auth_card = QFrame()
        self.auth_card.setObjectName("authCard")
        self.auth_card.setFixedWidth(448)

        # Original crash-prone shadow restored on card
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

        self.create_login_form()

    # 🔑 CRITICAL CHANGE 2: New Method for Redirection from HomeWindow
    def show_login_form(self, message=None, is_success=False):
        """
        Method called by HomeWindow's logout after deletion/logout.
        Hides the home window, shows the login window, and sets the status message.
        """
        # Hide the HomeWindow (or the active window if it were visible)
        self.home_window.hide()

        # Reset the AuthApp UI to the login form, displaying a message
        self.create_login_form(initial_message=message, is_success=is_success)

        self.show()

    def set_status_message(self, message, is_success):
        """Sets the status message text and styling (color)."""
        if self.status_label:
            color = "#10C988" if is_success else "#EF4444"
            self.status_label.setText(message)
            self.status_label.setStyleSheet(f"QLabel#statusMessage {{ color: {color}; }}")
            self.status_label.show()

    def login_success(self):
        """Triggers the window transition after a brief delay."""
        QTimer.singleShot(800, self._transition_to_home)

    def _transition_to_home(self):
        """Internal method to handle the window swap."""
        # 1. Update the HomeWindow with the logged-in user's ID
        self.home_window.user_id = self.user_id

        # 2. Re-load the dashboard content for the new user
        # Note: HomeWindow must have this method, which you confirmed previously.
        self.home_window.load_dashboard_content()

        # 3. Perform the window swap
        self.home_window.show()
        self.hide()

    def clear_card_layout(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def create_input_field(self, placeholder, is_password=False):
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setFont(QFont("Arial", 14))
        field.setMinimumHeight(48)
        field.setObjectName("authInput")
        if is_password:
            field.setEchoMode(QLineEdit.Password)
        return field

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

        # Use ShadowButton
        login_btn = ShadowButton("Login", parent_app=self)
        login_btn.setMinimumHeight(48)
        login_btn.setObjectName("primaryButton")
        login_btn.clicked.connect(lambda: self.validate_login(email_input.text(), pw_input.text()))

        self.card_layout.addWidget(login_btn)

        self.card_layout.addSpacing(15)

        switch_label = HoverLabel("Don't have an account?", "Create Account", self.create_signup_form, font_size=14)
        self.card_layout.addWidget(switch_label)
        self.auth_card.adjustSize()

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
                user_data = response.json()
                self.user_id = user_data.get("user_id", "test_user_123")

                self.set_status_message("Login successful! Redirecting...", True)
                self.login_success()
            else:
                try:
                    error_detail = response.json().get("detail", "Login failed due to server error.")
                except json.JSONDecodeError:
                    error_detail = f"Login failed: Server responded with status {response.status_code}"
                self.set_status_message(error_detail, False)

        except requests.exceptions.ConnectionError:
            self.set_status_message("Connection error: Is the FastAPI server running on 127.0.0.1:8000?", False)
        except requests.exceptions.RequestException as e:
            self.set_status_message(f"An unexpected error occurred: {e}", False)

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

        # Use ShadowButton
        create_btn = ShadowButton("Create Account", parent_app=self)
        create_btn.setMinimumHeight(48)
        create_btn.setObjectName("primaryButton")
        create_btn.clicked.connect(lambda: self.validate_signup(email_input.text(), pw_input.text(), cpw_input.text()))

        self.card_layout.addWidget(create_btn)

        self.card_layout.addSpacing(15)

        switch_label = HoverLabel("Already have an account?", "Back to Login", self.create_login_form, font_size=14)
        self.card_layout.addWidget(switch_label)
        self.auth_card.adjustSize()

    def validate_signup(self, email, password, confirm_password):
        """Handles local validation and then attempts to sign up via the FastAPI backend."""
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
                success_message = "Account successfully created! Please log in."
                self.create_login_form(initial_message=success_message, is_success=True)
            else:
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