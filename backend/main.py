import sys
import requests
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QFrame, QTableWidget, \
    QTableWidgetItem, QHeaderView, QApplication  # Added QApplication for execution
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

# API URL must match the server
API_URL = "http://127.0.0.1:8000/api"

STYLESHEET = """
QMainWindow {
    background-color: #F8F8F8; 
}
#mainTitle {
    font-size: 30px; 
    font-weight: bold;
    color: #10C988;
}
QLabel {
    font-family: "Arial";
    font-size: 16px; 
    color: #374151;
}
#userIdLabel {
    font-size: 18px; 
    font-weight: bold;
    color: #374151;
    background-color: #E6F7F0;
    padding: 10px;
    border-radius: 8px;
}
#dashboardTitle {
    font-size: 24px;
    font-weight: 600;
    color: #374151;
}
QTableWidget {
    border: 1px solid #D9D9D9;
    border-radius: 10px;
    gridline-color: #E5E7EB;
    background-color: white;
    font-size: 14px;
    alternate-background-color: #F9FAFB;
}
QHeaderView::section {
    background-color: #F3F4F6;
    color: #4B5563;
    padding: 8px;
    border-bottom: 2px solid #D1D5DB;
    font-weight: bold;
}
"""


class HomeWindow(QMainWindow):
    """
    Main application window displayed after successful authentication.
    It fetches and displays user-specific data from the FastAPI server.
    """

    def __init__(self, parent=None, user_id="TEST_USER_ID"):  # Changed default for easy testing
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Shortly Desktop - Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(STYLESHEET)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(50, 50, 50, 50)

        # 1. Main Header
        title = QLabel("Welcome to Shortly, your URL Shortener.")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # 2. User ID Display
        user_id_label = QLabel(self.user_id if self.user_id else "N/A (Error)")
        user_id_label.setObjectName("userIdLabel")
        user_id_label.setAlignment(Qt.AlignCenter)

        user_box = QFrame()
        user_box_layout = QVBoxLayout(user_box)
        user_box_layout.addWidget(QLabel("Authenticated User ID:"))
        user_box_layout.addWidget(user_id_label)
        user_box_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(user_box)

        # 3. Info Label
        info_label = QLabel("You are securely connected. Below is your data fetched live from Firebase via FastAPI.")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(info_label)

        # 4. Dashboard Title
        dashboard_title = QLabel("Your Shortened URLs")
        dashboard_title.setObjectName("dashboardTitle")
        main_layout.addWidget(dashboard_title)

        # 5. URLs Table Area
        self.url_table = self._create_url_table()
        main_layout.addWidget(self.url_table)

        # 6. Status Label for data fetch
        self.data_status_label = QLabel("Fetching data...")
        self.data_status_label.setStyleSheet("color: #F59E0B; font-weight: 600;")
        main_layout.addWidget(self.data_status_label)

        main_layout.addStretch()

        # 7. Start data fetching after window creation
        QTimer.singleShot(100, self.fetch_user_urls)

    def _create_url_table(self):
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Short Code", "Original URL", "Clicks", "Created At"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(300)
        return table

    def fetch_user_urls(self):
        """Calls the FastAPI server to get the user's URLs."""
        if not self.user_id:
            self.data_status_label.setText("Error: No authenticated user ID.")
            self.data_status_label.setStyleSheet("color: #EF4444; font-weight: 600;")
            return

        # Uses the user_id passed from the AuthApp after successful login
        url = f"{API_URL}/urls/{self.user_id}"

        try:
            # Synchronous GET request
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                urls_data = response.json()
                self._populate_url_table(urls_data)
                self.data_status_label.setText(f"Successfully loaded {len(urls_data)} URL(s) from Firebase.")
                self.data_status_label.setStyleSheet("color: #10B981; font-weight: 600;")
            else:
                try:
                    error_detail = response.json().get("detail", f"Failed with status {response.status_code}")
                except requests.exceptions.JSONDecodeError:
                    error_detail = response.text or f"Failed with status {response.status_code}"

                self.data_status_label.setText(f"API Error fetching URLs: {error_detail}")
                self.data_status_label.setStyleSheet("color: #EF4444; font-weight: 600;")

        except requests.exceptions.ConnectionError:
            self.data_status_label.setText("Connection error: Cannot reach the FastAPI server. Is the backend running?")
            self.data_status_label.setStyleSheet("color: #EF4444; font-weight: 600;")
        except Exception as e:
            self.data_status_label.setText(f"An unexpected error occurred: {e}")
            self.data_status_label.setStyleSheet("color: #EF4444; font-weight: 600;")

    def _populate_url_table(self, urls_data):
        self.url_table.setRowCount(len(urls_data))
        for row, url_info in enumerate(urls_data):
            self.url_table.setItem(row, 0, QTableWidgetItem(url_info.get('short_code', 'N/A')))

            # Original URL with wrapping
            original_url_item = QTableWidgetItem(url_info.get('original_url', 'N/A'))
            original_url_item.setToolTip(url_info.get('original_url', 'N/A'))
            self.url_table.setItem(row, 1, original_url_item)

            self.url_table.setItem(row, 2, QTableWidgetItem(str(url_info.get('clicks', 0))))

            # Format date for display
            created_at_str = url_info.get('created_at', '')
            display_date = created_at_str.split('T')[0] if created_at_str else 'N/A'
            self.url_table.setItem(row, 3, QTableWidgetItem(display_date))


if __name__ == "__main__":
    # Example execution: Replace 'TEST_USER_ID' with a real UID after login
    # In a real app, the login screen would pass the UID here.
    app = QApplication(sys.argv)
    main_win = HomeWindow(user_id="YOUR_FIREBASE_USER_ID_HERE")
    main_win.show()
    sys.exit(app.exec_())