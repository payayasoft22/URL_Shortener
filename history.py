# history.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QMessageBox, QScrollArea, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor
import firebase_admin
from firebase_admin import firestore
import sys
from datetime import datetime


class HistoryPage(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, user_id="test_user_123"):
        super().__init__()
        self.user_id = user_id
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 20, 40, 40)
        main_layout.setSpacing(20)

        # Header Section
        header_frame = QFrame()
        header_frame.setFixedHeight(60)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("My Links")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setStyleSheet("color: #111827;")

        subtitle_label = QLabel("Manage and track all your shortened links")
        subtitle_label.setFont(QFont("Arial", 14))
        subtitle_label.setStyleSheet("color: #6B7280;")

        title_container = QVBoxLayout()
        title_container.setSpacing(2)
        title_container.addWidget(title_label)
        title_container.addWidget(subtitle_label)

        header_layout.addLayout(title_container)
        header_layout.addStretch()

        main_layout.addWidget(header_frame)

        # Search Bar
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by URL or alias...")
        self.search_input.setFixedHeight(48)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 0 16px;
                font-family: Arial;
                font-size: 14px;
                color: #374151;
                background-color: white;
                width: 400px;
            }
            QLineEdit:focus {
                border: 2px solid #10C988;
                outline: none;
            }
        """)
        self.search_input.textChanged.connect(self.filter_cards)
        search_layout.addWidget(self.search_input)
        search_layout.addStretch()

        main_layout.addWidget(search_frame)

        # Scroll Area for Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                border: none;
                background-color: white;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #D1D5DB;
                border-radius: 4px;
                min-height: 30px;
            }
        """)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.cards_layout.setSpacing(16)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Status Label
        self.status_label = QLabel("Loading your links...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #6B7280;
            font-family: Arial;
            font-size: 14px;
            padding: 40px;
        """)
        self.status_label.setVisible(False)
        main_layout.addWidget(self.status_label)

    def load_data(self):
        """Load history data from Firebase"""
        try:
            if not firebase_admin._apps:
                self.status_label.setText("Firebase not initialized")
                self.status_label.setVisible(True)
                return

            db = firestore.client()

            # Try to fetch all data and filter locally
            all_docs = db.collection('url_history').stream()

            rows = []
            for doc in all_docs:
                data = doc.to_dict()

                # Filter by user_id locally
                if data.get('user_id') != self.user_id:
                    continue

                row = {
                    'id': doc.id,
                    'original_url': data.get('original_url', 'N/A'),
                    'short_url': data.get('short_url', 'N/A'),
                    'clicks': data.get('clicks', 0),
                    'created_at': data.get('created_at'),
                    'alias': data.get('alias_used', ''),
                    'expires_at': data.get('expires_at'),
                    'is_active': data.get('is_active', True)
                }
                rows.append(row)

            # Sort by created_at locally (newest first)
            def get_sort_key(row):
                created = row.get('created_at')
                if hasattr(created, 'to_datetime'):
                    return created.to_datetime()
                elif hasattr(created, 'timestamp'):
                    return created
                else:
                    return datetime.min

            rows.sort(key=get_sort_key, reverse=True)

            self.all_rows = rows

            if not rows:
                self.status_label.setText("No links yet. Create your first short link!")
                self.status_label.setVisible(True)
                self.clear_cards()
            else:
                self.status_label.setVisible(False)
                self.display_cards(rows)

        except Exception as e:
            error_msg = str(e)
            self.status_label.setText(f"Error loading data: {error_msg}")
            self.status_label.setVisible(True)
            self.clear_cards()

    def clear_cards(self):
        """Remove all cards from the layout"""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def display_cards(self, rows):
        """Display links as cards"""
        self.clear_cards()

        for row in rows:
            card = self.create_link_card(row)
            self.cards_layout.addWidget(card)

        # Add stretch at the end
        self.cards_layout.addStretch()

    def create_link_card(self, row):
        """Create a single link card"""
        card = QFrame()
        card.setObjectName("linkCard")
        card.setStyleSheet("""
            QFrame#linkCard {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 0px;
            }
        """)
        card.setMinimumHeight(120)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        # Top row: Original URL
        original_url_frame = QFrame()
        original_url_layout = QHBoxLayout(original_url_frame)
        original_url_layout.setContentsMargins(0, 0, 0, 0)

        original_label = QLabel("Original URL:")
        original_label.setFont(QFont("Arial", 12, QFont.Bold))
        original_label.setStyleSheet("color: #374151;")
        original_label.setFixedWidth(100)

        original_url = row['original_url']
        if len(original_url) > 60:
            display_url = original_url[:57] + "..."
        else:
            display_url = original_url

        original_url_text = QLabel(display_url)
        original_url_text.setFont(QFont("Arial", 12))
        original_url_text.setStyleSheet("color: #6B7280;")
        original_url_text.setWordWrap(True)
        original_url_text.setToolTip(original_url)

        original_url_layout.addWidget(original_label)
        original_url_layout.addWidget(original_url_text, 1)
        card_layout.addWidget(original_url_frame)

        # Middle row: Short URL and Clicks
        middle_frame = QFrame()
        middle_layout = QHBoxLayout(middle_frame)
        middle_layout.setContentsMargins(0, 0, 0, 0)

        # Short URL
        short_url_frame = QFrame()
        short_url_layout = QHBoxLayout(short_url_frame)
        short_url_layout.setContentsMargins(0, 0, 0, 0)

        short_label = QLabel("Short URL:")
        short_label.setFont(QFont("Arial", 12, QFont.Bold))
        short_label.setStyleSheet("color: #374151;")
        short_label.setFixedWidth(100)

        short_url_text = QLabel(row['short_url'])
        short_url_text.setFont(QFont("Arial", 12))
        short_url_text.setStyleSheet("color: #10C988; font-weight: bold;")
        short_url_text.setCursor(Qt.PointingHandCursor)

        short_url_layout.addWidget(short_label)
        short_url_layout.addWidget(short_url_text, 1)
        middle_layout.addWidget(short_url_frame, 3)

        # Clicks and Date
        stats_frame = QFrame()
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(20)

        # Created Date Only
        date_label = QLabel("Created:")
        date_label.setFont(QFont("Arial", 12))
        date_label.setStyleSheet("color: #6B7280;")

        date_value = QLabel(self.format_date(row['created_at']))
        date_value.setFont(QFont("Arial", 12, QFont.Bold))
        date_value.setStyleSheet("color: #374151;")

        stats_layout.addWidget(date_label)
        stats_layout.addWidget(date_value)
        stats_layout.addStretch()

        middle_layout.addWidget(stats_frame, 2)
        card_layout.addWidget(middle_frame)

        # Bottom row: Actions
        actions_frame = QFrame()
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(0, 0, 0, 0)

        actions_layout.addStretch()

        # Copy Button
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setFixedSize(120, 36)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8F8F4;
                color: #10C988;
                border: 1px solid #10C988;
                border-radius: 6px;
                font-family: Arial;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #10C988;
                color: white;
            }
        """)
        copy_btn.clicked.connect(lambda checked, url=row['short_url']: self.copy_url(url))

        # Delete Button
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setFixedSize(120, 36)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEF2F2;
                color: #EF4444;
                border: 1px solid #EF4444;
                border-radius: 6px;
                font-family: Arial;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: white;
            }
        """)
        delete_btn.clicked.connect(lambda checked, doc_id=row['id'], url=row['short_url']:
                                   self.delete_link(doc_id, url))

        actions_layout.addWidget(copy_btn)
        actions_layout.addSpacing(10)
        actions_layout.addWidget(delete_btn)

        card_layout.addWidget(actions_frame)

        # Add subtle shadow effect
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 10))
        card.setGraphicsEffect(shadow)

        return card

    def format_date(self, timestamp):
        """Format timestamp to readable date"""
        if not timestamp:
            return "N/A"

        try:
            if hasattr(timestamp, 'to_datetime'):
                dt = timestamp.to_datetime()
            elif hasattr(timestamp, 'strftime'):
                dt = timestamp
            else:
                return "N/A"

            # Format as M/D/YYYY (like in screenshot)
            return f"{dt.month}/{dt.day}/{dt.year}"
        except:
            return "N/A"

    def filter_cards(self):
        """Filter cards based on search text"""
        search_text = self.search_input.text().lower().strip()

        if not hasattr(self, 'all_rows'):
            return

        if not search_text:
            # Show all cards
            self.display_cards(self.all_rows)
            return

        # Filter rows
        filtered_rows = []
        for row in self.all_rows:
            if (search_text in row['original_url'].lower() or
                    search_text in row['short_url'].lower() or
                    search_text in str(row.get('alias', '')).lower()):
                filtered_rows.append(row)

        if filtered_rows:
            self.display_cards(filtered_rows)
            self.status_label.setVisible(False)
        else:
            self.clear_cards()
            self.status_label.setText(f"No links found for '{search_text}'")
            self.status_label.setVisible(True)

    def copy_url(self, url):
        """Copy URL to clipboard - SILENT OPERATION"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
            # No message shown - silent operation
        except:
            pass  # Silent fail

    def delete_link(self, doc_id, url):
        """Delete a link from Firebase - SILENT OPERATION"""
        try:
            db = firestore.client()
            db.collection('url_history').document(doc_id).delete()

            # Refresh data silently
            self.load_data()

            # Emit refresh signal silently
            self.refresh_requested.emit()

        except:
            pass  # Silent fail


# Test code
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Initialize Firebase for testing
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Firebase init error: {e}")

    window = HistoryPage()
    window.setWindowTitle("URL History")
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec_())