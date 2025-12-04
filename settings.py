# settings.py (FINAL, COMPLETE, AND INTEGRATED VERSION)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QHBoxLayout, QLineEdit, QGraphicsDropShadowEffect,
    QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont


# ------------------------ SHADOW BUTTON (Duplicated for module independence) ------------------------
class ShadowButton(QPushButton):
    """Custom QPushButton with shadow effects. Assumes parent_app has shadow methods."""

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


# ------------------------ SETTINGS PAGE ------------------------
class SettingsPage(QWidget):

    def __init__(self, parent_app, user_id="test_user_123"):
        super().__init__()
        self.user_id = user_id
        self.parent_app = parent_app  # Reference to HomeWindow

        # Input Styles
        self.NORMAL_INPUT_STYLE = "border: 1px solid #DCDEE5; border-radius: 12px; padding: 10px 15px; background-color: #F3F4F6; color: #374151; font-size: 16px;"
        self.ERROR_INPUT_STYLE = "border: 2px solid #EF4444; border-radius: 12px; padding: 10px 15px; background-color: #F3F4F6; color: #374151; font-size: 16px;"

        self.setStyleSheet(self._get_widget_stylesheet())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Centering is handled by HomeWindow wrapper
        main_layout.setSpacing(20)

        # Header Title
        header_label = QLabel("Settings")
        header_label.setFont(QFont("Arial", 32, QFont.Bold))
        header_label.setStyleSheet("color: black;")
        main_layout.addWidget(header_label)

        self.load_settings_content(main_layout)

    def _get_widget_stylesheet(self):
        return """
            #settingsCard { background-color: white; border-radius: 14px; border: 1px solid #D9D9D9; } 
            #inputLabel { font-family: "Arial"; font-size: 14px; font-weight: 500; color: #374151; } 
            #cardTitle { font-size: 20px; font-weight: bold; color: black; } 
            #cardSubtitle { font-size: 14px; font-weight: normal; color: #6B7280; } 
            #newPasswordInput, #confirmPasswordInput { 
                border: 1px solid #DCDEE5; 
                border-radius: 12px; 
                padding: 10px 15px; 
                background-color: #F3F4F6; 
                color: #374151; 
                font-size: 16px; 
            } 
            #newPasswordInput:focus, #confirmPasswordInput:focus { 
                border: 2px solid #10C988; 
                background-color: #e8eaed; 
            } 
            #updateButton { background-color: #10C988; color: white; border-radius: 14px; border: none; font-size: 16px; font-weight: bold; padding: 10px; min-height: 54px; cursor: pointer; } 
            #updateButton:hover { background-color: #0DA875; } 
            #updateButton:disabled { background-color: #9CA3AF; cursor: not-allowed; } 
            .errorLabel { color: #EF4444; font-size: 12px; margin-top: 4px; font-weight: 500;} 
            #deleteAccountButton { 
                background-color: #EF4444; 
                color: white; 
                border-radius: 14px; 
                border: none; 
                font-size: 16px; 
                font-weight: bold; 
                padding: 10px; 
                min-height: 54px; 
                cursor: pointer; 
            }
            #deleteAccountButton:hover { background-color: #DC2626; }
        """

    def load_settings_content(self, layout):
        layout.addWidget(self.create_password_update_card())
        layout.addWidget(self.create_delete_account_card())
        layout.addStretch(1)  # Ensures cards stay at the top of the centered page

    # ------------------------ PASSWORD UPDATE CARD ------------------------
    def create_password_update_card(self):
        card = QFrame(objectName="settingsCard")
        card.setMinimumWidth(736)
        card.setMaximumWidth(736)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(15)

        card_layout.addWidget(QLabel("Password", objectName="cardTitle"))
        card_layout.addWidget(QLabel("Update your account password", objectName="cardSubtitle"))

        card_layout.addSpacing(10)

        card_layout.addWidget(QLabel("New Password *", objectName="inputLabel"))
        self.new_password_input = QLineEdit(objectName="newPasswordInput", placeholderText="Enter your new password")
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setStyleSheet(self.NORMAL_INPUT_STYLE)
        card_layout.addWidget(self.new_password_input)

        self.new_pass_error_label = QLabel(objectName="errorLabel")
        self.new_pass_error_label.hide()
        card_layout.addWidget(self.new_pass_error_label)

        card_layout.addSpacing(5)
        card_layout.addWidget(QLabel("Confirm Password *", objectName="inputLabel"))
        self.confirm_password_input = QLineEdit(objectName="confirmPasswordInput",
                                                placeholderText="Confirm your new password")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setStyleSheet(self.NORMAL_INPUT_STYLE)
        card_layout.addWidget(self.confirm_password_input)

        self.confirm_pass_error_label = QLabel(objectName="errorLabel")
        self.confirm_pass_error_label.hide()
        card_layout.addWidget(self.confirm_pass_error_label)

        card_layout.addSpacing(15)

        self.update_btn = ShadowButton("🔒 Update Password", parent_app=self.parent_app, is_primary=True,
                                       objectName="updateButton")
        self.update_btn.clicked.connect(self.handle_update_password)
        card_layout.addWidget(self.update_btn)

        return card

    def _set_input_style(self, line_edit, is_valid, error_label=None, msg=""):
        if is_valid:
            line_edit.setStyleSheet(self.NORMAL_INPUT_STYLE)
            if error_label: error_label.hide()
        else:
            line_edit.setStyleSheet(self.ERROR_INPUT_STYLE)
            if error_label:
                error_label.setText(msg)
                error_label.show()

    def handle_update_password(self):
        new_pass = self.new_password_input.text().strip()
        confirm_pass = self.confirm_password_input.text().strip()

        valid = True
        self._set_input_style(self.new_password_input, True, self.new_pass_error_label)
        self._set_input_style(self.confirm_password_input, True, self.confirm_pass_error_label)

        if not new_pass or len(new_pass) < 8:
            msg = "⚠️ Password must be at least 8 characters long."
            self._set_input_style(self.new_password_input, False, self.new_pass_error_label, msg)
            valid = False

        if not confirm_pass:
            self._set_input_style(self.confirm_password_input, False, self.confirm_pass_error_label,
                                  "⚠️ Please confirm your password.")
            valid = False

        if new_pass != confirm_pass and valid:
            msg = "⚠️ Passwords do not match."
            self._set_input_style(self.confirm_password_input, False, self.confirm_pass_error_label, msg)
            valid = False

        if not valid: return

        # Simulation
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Updating...")
        self.parent_app.remove_button_shadow(self.update_btn)

        self.parent_app.show_notification("Password change simulated successfully!", is_success=True)

        QTimer.singleShot(1500, lambda: self._reset_password_fields())

    def _reset_password_fields(self):
        self.update_btn.setEnabled(True)
        self.update_btn.setText("🔒 Update Password")
        self.new_password_input.clear()
        self.confirm_password_input.clear()
        self.parent_app.apply_button_shadow(self.update_btn, True)

    # ------------------------ DELETE ACCOUNT CARD ------------------------
    def create_delete_account_card(self):
        card = QFrame(objectName="settingsCard")
        card.setMinimumWidth(736)
        card.setMaximumWidth(736)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(15)

        card_layout.addWidget(QLabel("Account Deletion", objectName="cardTitle"))
        card_layout.addWidget(
            QLabel("Permanently delete your account and all associated data.", objectName="cardSubtitle"))

        delete_btn = ShadowButton("Delete Your Account", parent_app=self.parent_app, is_primary=False, is_danger=True,
                                  objectName="deleteAccountButton")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(self.handle_delete_account)
        card_layout.addWidget(delete_btn)

        return card

    def handle_delete_account(self):
        reply = QMessageBox.critical(
            self,
            "Confirm Account Deletion",
            "Are you absolutely sure you want to delete your account? This action is permanent and cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Simulation of deletion logic
            self.parent_app.show_notification(
                f"Account for User ID: {self.user_id} has been permanently deleted (simulated).",
                is_success=True
            )
            # Call the HomeWindow's logout function which handles the transition
            QTimer.singleShot(100,
                              lambda: self.parent_app.logout(message="Account permanently deleted.", is_success=True))