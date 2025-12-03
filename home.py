from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QHBoxLayout, QSizePolicy, QScrollArea, QLineEdit, QGraphicsDropShadowEffect,
    QApplication, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPen


class ExpirationDialog(QFrame):
    expiration_selected = pyqtSignal(str)

    def __init__(self, parent=None, current_expiration="30 days"):
        super().__init__(parent)
        self.current_expiration = current_expiration
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)  # IMPORTANT: Make background translucent

        # Set style for the dialog - remove background from QFrame
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;  /* Changed from white to transparent */
                border-radius: 12px;
                border: none;  /* Remove border */
            }
            QPushButton {
                background-color: white;
                border: none;
                padding: 12px 16px;
                text-align: left;
                font-family: "Arial";
                font-size: 14px;
                color: #374151;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #E8F8F4;
            }

            /* Specific style for the currently selected item */
            QPushButton[selected="true"] {
                color: #10C988;
                font-weight: bold;
                /* Increased padding to make room for the checkmark */
                padding-left: 36px; 
            }
        """)

        # Create an inner container with white background and rounded corners
        self.inner_frame = QFrame(self)
        self.inner_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #D9D9D9;
            }
        """)

        # Layout for the inner frame
        inner_layout = QVBoxLayout(self.inner_frame)
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(4)

        # Options (Reordered to match the image: 7 days, 30 days, Never)
        self.options = ["7 days", "30 days", "Never"]
        self.buttons = []

        # Track the button that is currently selected
        self.selected_button = None

        for option in self.options:
            btn = QPushButton(option)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("option", option)

            # Check if this button should be selected initially
            is_selected = (option == current_expiration)
            btn.setProperty("selected", is_selected)

            if is_selected:
                self.selected_button = btn

            btn.clicked.connect(self.on_option_clicked)
            self.buttons.append(btn)
            inner_layout.addWidget(btn)

        inner_layout.addStretch()

        # Apply shadow to the main frame (not the inner frame)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        # Set layout for the main dialog (transparent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.inner_frame)

        # Manually apply the initial style to load the [selected="true"] padding
        for btn in self.buttons:
            btn.style().polish(btn)

    def resizeEvent(self, event):
        """Ensure inner frame matches the size of the dialog."""
        self.inner_frame.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def on_option_clicked(self):
        btn = self.sender()
        option = btn.property("option")

        # 1. Deselect previous
        if self.selected_button:
            self.selected_button.setProperty("selected", False)
            self.selected_button.style().polish(self.selected_button)

        # 2. Select new
        btn.setProperty("selected", True)
        self.selected_button = btn
        btn.style().polish(btn)  # Re-polish to apply the [selected="true"] style

        self.current_expiration = option
        self.expiration_selected.emit(option)
        self.hide()

    def paintEvent(self, event):
        """Draws the checkmark for the selected item."""
        super().paintEvent(event)

        if self.selected_button:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Position the checkmark relative to the selected button
            rect = self.selected_button.geometry()

            # X position: 10px from the left edge of the frame
            x = 10
            # Y position: Center of the button
            y = rect.center().y()

            # Draw green checkmark symbol (✓)
            painter.setPen(QPen(QColor("#10C988"), 2))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(x, y + 5, "✓")  # y+5 to center it vertically


class HomeWindow(QMainWindow):
    def __init__(self, auth_app_instance=None):
        super().__init__()
        self.auth_app_instance = auth_app_instance
        self.setWindowTitle("Shortly Desktop - Home")
        self.resize(1440, 1024)

        # --- Internal State ---
        self.active_tab = "dashboard"
        self.current_expiration = "30 days"  # Default expiration
        self.expiration_dialog = None  # Store dialog reference

        # --- STYLESHEET (Combined and Adjusted) ---
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F8F8;
            }
            /* HEADER STYLES */
            #headerFrame {
                background-color: white; 
                border-top: 1px solid #D9D9D9; 
                border-bottom: 1px solid #D9D9D9; 
            }
            #headerTitle {
                font-family: "Arial";
                font-size: 24px;
                font-weight: bold;
                color: #10C988;
                padding-right: 20px;
            }

            /* LOGOUT BUTTON STYLES */
            #logoutButton {
                background-color: #EF4444; 
                color: white;
                border-radius: 10px;
                border: none;
                font-size: 16px;
                padding: 5px 15px;
            }
            #logoutButton:hover {
                background-color: #DC2626; 
            }

            /* SCROLL & CONTENT STYLES */
            QScrollArea {
                border: none;
                background-color: #F8F8F8;
            }
            #scrollContent {
                background-color: #F8F8F8;
            }

            /* NAVIGATION BUTTON STYLES */
            .navButton {
                font-family: "Arial";
                font-size: 14px;
                font-weight: 500;
                border: none;
                border-radius: 10px;
                padding: 10px 15px;
                margin-right: 8px;
                cursor: pointer;
            }
            .navButton[state="inactive"] {
                background-color: transparent;
                color: #6B7280; 
            }
            .navButton[state="inactive"]:hover {
                background-color: #E5E7EB;
                color: #374151;
            }
            .navButton[state="active"] {
                background-color: #E8F8F4;
                color: #10C988;
            }
            .navButton[state="active"]:hover {
                background-color: #10C988;
                color: white;
            }

            /* URL CARD STYLES */
            #shortenerCard, #successCard {
                background-color: white;
                border-radius: 14px;
                border: 1px solid #D9D9D9;
            }

            /* Card Typography */
            #inputLabel {
                font-family: "Arial";
                font-size: 14px; 
                font-weight: 500; 
                color: #374151;
            }
            #cardTitle {
                font-size: 20px; 
                font-weight: bold;
                color: black;
            }
            #cardSubtitle, #successMessage {
                font-size: 14px; 
                font-weight: normal; 
                color: #6B7280;
            }

            /* Input fields */
            #urlInput, #aliasInput, #expirationButton {
                 border: 1px solid #DCDEE5;
                 border-radius: 12px;
                 padding: 10px 15px;
                 background-color: #F3F4F6;
                 color: #374151;
                 font-size: 16px;
            }
            #urlInput:focus, #aliasInput:focus, #expirationButton:focus {
                border: 2px solid #10C988;
                background-color: #e8eaed;
            }

            /* Expiration Button */
            #expirationButton {
                text-align: left;
                background-color: #F3F4F6;
                cursor: pointer;
            }
            #expirationButton:hover {
                background-color: #E5E7EB;
            }

            /* Expiration dropdown arrow */
            #expirationButton::after {
                content: "▼";
                float: right;
                font-size: 12px;
                color: #6B7280;
            }

            /* Create Button */
            #createButton {
                background-color: #10C988;
                color: white;
                border-radius: 14px;
                border: none;
                font-size: 16px; 
                font-weight: bold;
                padding: 10px;
                min-height: 48px;
                cursor: pointer;
            }
            #createButton:hover {
                background-color: hsl(160, 84%, 39%, 0.9);
            }
            #createButton:pressed {
                background-color: #00A76A;
            }

            /* Short Link Display Field (Success Card content) */
            #shortUrlDisplay {
                background-color: #F8F8F8;
                border: 1px solid #DCDEE5;
                border-radius: 12px;
                padding: 10px 15px;
            }
            #shortUrlText {
                font-size: 16px;
                font-weight: 500;
                color: #10C988;
            }

            /* Action Buttons (Copy, QR) */
            .actionButton {
                background-color: #E5E7EB; 
                color: #374151;
                border-radius: 12px;
                border: 1px solid transparent;
                font-size: 16px; 
                padding: 10px 20px;
                min-height: 48px;
                cursor: pointer;
            }
            .actionButton:hover {
                background-color: #D1D5DB;
            }
        """)
        # --- END STYLESHEET ---

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 2. Create the Header Frame (65px Height) ---
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

        # Header Title (Left side)
        header_title = QLabel("Shortly Desktop")
        header_title.setObjectName("headerTitle")
        header_layout.addWidget(header_title)

        # --- Centering Logic ---
        header_layout.addStretch(1)

        # Navigation Tabs Container
        self.nav_frame = QFrame()
        self.nav_layout = QHBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(0)

        # Create Navigation Buttons
        self.dash_btn = self._create_nav_button("Dashboard", "dashboard")
        self.hist_btn = self._create_nav_button("History", "history")
        self.sett_btn = self._create_nav_button("Settings", "settings")

        self.nav_layout.addWidget(self.dash_btn)
        self.nav_layout.addWidget(self.hist_btn)
        self.nav_layout.addWidget(self.sett_btn)

        header_layout.addWidget(self.nav_frame)

        header_layout.addStretch(1)

        # Logout Button (Right side)
        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("logoutButton")
        logout_btn.setFixedSize(120, 38)
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(logout_btn)

        # --- Add Header to Main Layout ---
        main_layout.addWidget(self.header_frame)

        # --- Content Area (Scrollable) ---
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

        # Add the Scroll Area to the Main Layout
        main_layout.addWidget(self.scroll_area, 1)

        # Initialize the state and load content
        self.switch_tab("dashboard")

    # --- SUCCESS LINK DISPLAY CARD ---
    def create_short_link_display(self, short_url="https://short.ly/gerg"):
        """Creates and returns the short link display field and actions (the bottom card)."""

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

        # 1. Success Message
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

        # 2. Short URL Display Field
        display_frame = QFrame()
        display_frame.setObjectName("shortUrlDisplay")
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(2)

        short_label = QLabel("Short URL")
        short_label.setObjectName("inputLabel")

        short_link_text = QLabel(short_url)
        short_link_text.setObjectName("shortUrlText")
        short_link_text.setCursor(Qt.IBeamCursor)
        short_link_text.setTextInteractionFlags(Qt.TextSelectableByMouse)

        display_layout.addWidget(short_label)
        display_layout.addWidget(short_link_text)

        card_layout.addWidget(display_frame)

        # 3. Action Buttons (Copy, QR)
        action_frame = QFrame()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)

        copy_btn = QPushButton("📋 Copy")
        copy_btn.setObjectName("copyButton")
        copy_btn.setProperty("class", "actionButton")
        copy_btn.setCursor(Qt.PointingHandCursor)

        qr_btn = QPushButton("QR")
        qr_btn.setObjectName("qrButton")
        qr_btn.setProperty("class", "actionButton")
        qr_btn.setCursor(Qt.PointingHandCursor)

        action_layout.addStretch(1)
        action_layout.addWidget(copy_btn)
        action_layout.addWidget(qr_btn)

        card_layout.addWidget(action_frame)

        return card

    # --- SHORTENER FORM CARD CREATION ---
    def create_url_shortener_card(self):
        """Creates and returns the styled URL Shortener form card (the top card)."""

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

        # 1. Title and Subtitle Area
        title_frame = QFrame()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)

        star_icon = QLabel("⚡")
        star_icon.setFont(QFont("Arial", 20))

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

        title_layout.addWidget(star_icon)
        title_layout.addWidget(title_container)
        title_layout.addStretch(1)

        card_layout.addWidget(title_frame)
        card_layout.addSpacing(10)

        # 2. Long URL Input
        url_label = QLabel("Long URL *")
        url_label.setObjectName("inputLabel")

        self.long_url_input = QLineEdit()
        self.long_url_input.setObjectName("urlInput")
        self.long_url_input.setPlaceholderText("https://discord.com/channels/1141321686059323393/...")

        card_layout.addWidget(url_label)
        card_layout.addWidget(self.long_url_input)

        card_layout.addSpacing(5)

        # 3. Alias and Expiration (Side by Side)
        side_by_side_frame = QFrame()
        side_by_side_layout = QHBoxLayout(side_by_side_frame)
        side_by_side_layout.setContentsMargins(0, 0, 0, 0)
        side_by_side_layout.setSpacing(15)

        # Custom Alias Input
        alias_widget = QWidget()
        alias_vbox = QVBoxLayout(alias_widget)
        alias_vbox.setContentsMargins(0, 0, 0, 0)
        alias_vbox.setSpacing(5)
        alias_label = QLabel("Custom Alias (optional)")
        alias_label.setObjectName("inputLabel")
        self.alias_input = QLineEdit()
        self.alias_input.setObjectName("aliasInput")
        self.alias_input.setPlaceholderText("haha")
        alias_vbox.addWidget(alias_label)
        alias_vbox.addWidget(self.alias_input)

        # Expiration Button (replaces QComboBox)
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

        # Set equal stretch factors for 50/50 split
        side_by_side_layout.addWidget(alias_widget, stretch=1)
        side_by_side_layout.addWidget(exp_widget, stretch=1)

        card_layout.addWidget(side_by_side_frame)
        card_layout.addSpacing(15)

        # 4. Create Short Link Button
        create_btn = QPushButton("🔗 Create Short Link")
        create_btn.setObjectName("createButton")
        create_btn.clicked.connect(self.handle_create_link)

        card_layout.addWidget(create_btn)

        return card

    def toggle_expiration_dialog(self):
        """Shows or hides the expiration dropdown dialog."""
        if self.expiration_dialog and self.expiration_dialog.isVisible():
            self.expiration_dialog.hide()
            self.expiration_dialog.deleteLater()  # Clean up dialog
            self.expiration_dialog = None
        else:
            self.show_expiration_dialog()

    def show_expiration_dialog(self):
        """Shows the modal expiration selection dialog."""
        # Clean up existing dialog if open
        if self.expiration_dialog:
            self.expiration_dialog.deleteLater()
            self.expiration_dialog = None

        # Create new dialog
        self.expiration_dialog = ExpirationDialog(self, self.current_expiration)
        self.expiration_dialog.expiration_selected.connect(self.on_expiration_selected)

        # DYNAMIC WIDTH ADJUSTMENT
        button_width = self.exp_button.width()
        self.expiration_dialog.setFixedWidth(button_width)

        # Position the dialog below the expiration button
        button_pos = self.exp_button.mapToGlobal(self.exp_button.rect().bottomLeft())
        dialog_x = button_pos.x()
        dialog_y = button_pos.y() + 5

        # Get screen geometry from the primary screen
        desktop = QApplication.desktop()
        screen_geometry = desktop.availableGeometry(desktop.primaryScreen())

        # Ensure dialog stays within screen bounds (e.g., if near the bottom)
        if dialog_y + self.expiration_dialog.height() > screen_geometry.bottom():
            # If it would go off the bottom, position it above the button instead
            dialog_y = button_pos.y() - self.expiration_dialog.height() - 5

        self.expiration_dialog.move(dialog_x, dialog_y)
        self.expiration_dialog.show()

    def on_expiration_selected(self, expiration):
        """Handles when an expiration is selected from the dialog."""
        self.current_expiration = expiration
        self.exp_button.setText(expiration)

        # Hide and clean up the dialog after selection
        if self.expiration_dialog:
            self.expiration_dialog.hide()
            self.expiration_dialog.deleteLater()
            self.expiration_dialog = None

    def handle_create_link(self):
        """
        When Create Link is clicked, it clears the current content and
        reloads the dashboard with both the form and the result card.
        """
        long_url = self.long_url_input.text() if hasattr(self, 'long_url_input') else "https://default.long.url"
        alias = self.alias_input.text() if hasattr(self, 'alias_input') else "gerg"

        # Simple validation
        if not long_url.strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a Long URL.")
            return

        short_url_result = f"https://short.ly/{alias.strip() or 'newlink'}"

        self.load_dashboard_content(show_result=True, short_url=short_url_result)

    # --- Helper Methods ---
    def _create_nav_button(self, text, name):
        """Helper to create a stylized navigation button (Text Only)."""
        btn = QPushButton(text)
        btn.setProperty("class", "navButton")
        btn.setObjectName(f"{name}Tab")
        btn.clicked.connect(lambda: self.switch_tab(name))
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def switch_tab(self, new_tab_name):
        """Switches the active tab, updates styles, and changes content."""

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
        """Clears existing content and loads new content based on tab_name."""

        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if tab_name == "dashboard":
            self.load_dashboard_content(show_result=False)

        elif tab_name == "history":
            title = QLabel("Page: History")
            title.setFont(QFont("Arial", 48, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(title)

            content_label = QLabel("Viewing your recent activity history...")
            content_label.setFont(QFont("Arial", 24))
            self.content_layout.addWidget(content_label)
            self.content_layout.addStretch(1)

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
        """Loads the Dashboard content, optionally showing the result card."""

        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 1. Always add the Shortener Form
        shortener_card = self.create_url_shortener_card()
        self.content_layout.addWidget(shortener_card, alignment=Qt.AlignHCenter)

        # 2. Conditionally add the Result Display
        if show_result:
            display_url = short_url if short_url else "https://short.ly/default"

            result_display = self.create_short_link_display(short_url=display_url)
            self.content_layout.addWidget(result_display, alignment=Qt.AlignHCenter)

        # Add stretch at the bottom
        self.content_layout.addStretch(1)

    def logout(self):
        """Hides the HomeWindow and quits the application."""
        QApplication.quit()

