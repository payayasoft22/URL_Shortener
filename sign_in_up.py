import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

# --- Import the HomeWindow from home.py ---
from home import HomeWindow

# --- STYLESHEET ---
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

    # --- New Method for Login Success and Window Transition ---
    def login_success(self):
        """Hides the current AuthApp window and displays the HomeWindow."""

        if self.home_window is None:
            # Pass 'self' (the AuthApp instance) to the HomeWindow constructor
            self.home_window = HomeWindow(self)

        self.home_window.show()
        self.hide()

    def closeEvent(self, event):
        """Handle the close event for the main window, ensuring the HomeWindow is also closed."""
        if self.home_window:
            self.home_window.close()
        event.accept()

    # --- Helper Methods ---
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
        button.enterEvent = lambda e, b=button: self.apply_button_shadow(b)
        button.leaveEvent = lambda e, b=button: self.remove_button_shadow(b)
        return button

    def apply_button_shadow(self, button):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 180, 120, 120))
        button.setGraphicsEffect(shadow)

    def remove_button_shadow(self, button):
        button.setGraphicsEffect(None)

    def clear_card_layout(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # --- Login Form ---
    def create_login_form(self):
        self.main_title.setText("Welcome Back")
        self.main_subtitle.setText("Sign in to your account")
        self.clear_card_layout()

        self.card_layout.addWidget(QLabel("Email"))
        email_input = self.create_input_field("Email")
        self.card_layout.addWidget(email_input)

        self.card_layout.addSpacing(16)

        self.card_layout.addWidget(QLabel("Password"))
        pw_input = self.create_input_field("********", True)
        self.card_layout.addWidget(pw_input)

        self.card_layout.addSpacing(14)

        login_btn = self.create_primary_button("Login")
        # --- CONNECT THE LOGIN BUTTON TO TRANSITION METHOD ---
        login_btn.clicked.connect(self.login_success)

        self.card_layout.addWidget(login_btn)

        self.card_layout.addSpacing(15)

        switch_label = HoverLabel("Don't have an account?", "Create Account", self.create_signup_form, font_size=14)
        self.card_layout.addWidget(switch_label)
        self.auth_card.adjustSize()

    # --- Signup Form ---
    def create_signup_form(self):
        self.main_title.setText("Join Shortly Desktop")
        self.main_subtitle.setText("Create your account to get started")
        self.clear_card_layout()

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
        # NOTE: For signup, we don't connect it to a success screen,
        # but a real app would connect it to the registration logic.
        self.card_layout.addWidget(create_btn)

        self.card_layout.addSpacing(15)

        switch_label = HoverLabel("Already have an account?", "Back to Login", self.create_login_form, font_size=14)
        self.card_layout.addWidget(switch_label)
        self.auth_card.adjustSize()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuthApp()
    window.show()
    sys.exit(app.exec_())