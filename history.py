# history.py (updated)
import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
    QProgressBar, QDialog, QLineEdit, QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


class HistoryPage(QWidget):
    def __init__(self, user_id, api_base_url="http://localhost:8000"):
        super().__init__()
        self.user_id = user_id
        self.api_base_url = api_base_url
        self.init_ui()
        self.load_urls()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel("URL History")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setStyleSheet("color: #10C988;")
        layout.addWidget(title)

        # Stats bar
        self.stats_label = QLabel("Loading...")
        layout.addWidget(self.stats_label)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_urls)
        refresh_btn.setMaximumWidth(100)
        layout.addWidget(refresh_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Short URL", "Original URL", "Clicks", "Created", "Expires", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_urls(self):
        """Load URLs from the backend database"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        try:
            self.progress_bar.setValue(30)
            response = requests.get(f"{self.api_base_url}/api/urls/{self.user_id}", timeout=10)
            self.progress_bar.setValue(70)

            if response.status_code == 200:
                urls = response.json()
                self.progress_bar.setValue(90)
                self.update_table(urls)
                self.update_stats(len(urls))

                # Show database status
                if len(urls) > 0:
                    self.stats_label.setText(f"✅ Connected to database. Found {len(urls)} URLs.")
                    self.stats_label.setStyleSheet("color: #10C988;")
                else:
                    self.stats_label.setText("✅ Connected to database. No URLs found yet.")
                    self.stats_label.setStyleSheet("color: #10C988;")

            else:
                self.stats_label.setText("❌ Failed to load URLs from database")
                self.stats_label.setStyleSheet("color: #EF4444;")
                QMessageBox.warning(self, "Error",
                                    f"Failed to load URLs. Status: {response.status_code}")

        except requests.exceptions.ConnectionError:
            self.stats_label.setText("❌ Cannot connect to backend server")
            self.stats_label.setStyleSheet("color: #EF4444;")
            QMessageBox.critical(self, "Connection Error",
                                 "Cannot connect to the server. Please check:\n"
                                 "1. Backend is running (python main.py)\n"
                                 f"2. Server URL: {self.api_base_url}")
        except Exception as e:
            self.stats_label.setText("❌ Error loading URLs")
            self.stats_label.setStyleSheet("color: #EF4444;")
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
        finally:
            self.progress_bar.setValue(100)
            QTimer.singleShot(500, lambda: self.progress_bar.setVisible(False))

    def update_stats(self, count):
        """Update statistics label"""
        self.stats_label.setText(f"Database Status: ✅ Connected | URLs in database: {count}")

    def update_table(self, urls):
        """Update the table with URL data"""
        self.table.setRowCount(len(urls))

        for row, url_data in enumerate(urls):
            # Short URL
            short_code = url_data.get('short_code', '')
            short_url = f"{self.api_base_url}/{short_code}"
            short_url_item = QTableWidgetItem(short_url)
            short_url_item.setFlags(short_url_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 0, short_url_item)

            # Original URL (truncated if too long)
            original_url = url_data.get('original_url', '')
            if len(original_url) > 40:
                original_url = original_url[:40] + "..."
            original_url_item = QTableWidgetItem(original_url)
            original_url_item.setToolTip(url_data.get('original_url', ''))
            original_url_item.setFlags(original_url_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 1, original_url_item)

            # Clicks
            clicks = url_data.get('clicks', 0)
            clicks_item = QTableWidgetItem(str(clicks))
            clicks_item.setFlags(clicks_item.flags() ^ Qt.ItemIsEditable)
            if clicks > 0:
                clicks_item.setForeground(QColor("#10C988"))
            self.table.setItem(row, 2, clicks_item)

            # Created date
            created = url_data.get('created_at', '')
            if created:
                created = created.split('T')[0]  # Get just the date part
            created_item = QTableWidgetItem(created)
            created_item.setFlags(created_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 3, created_item)

            # Expiration
            expires = url_data.get('expires_at', '')
            if expires:
                expires = expires.split('T')[0]
            else:
                expires = "Never"
            expires_item = QTableWidgetItem(expires)
            expires_item.setFlags(expires_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 4, expires_item)

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 5, 5, 5)
            action_layout.setSpacing(5)

            copy_btn = QPushButton("📋")
            copy_btn.setToolTip("Copy URL")
            copy_btn.setMaximumWidth(40)
            copy_btn.clicked.connect(lambda _, url=short_url: self.copy_url(url))

            qr_btn = QPushButton("QR")
            qr_btn.setToolTip("Generate QR Code")
            qr_btn.setMaximumWidth(40)
            qr_btn.clicked.connect(lambda _, url=short_url: self.generate_qr_code(url))

            delete_btn = QPushButton("🗑️")
            delete_btn.setToolTip("Delete URL")
            delete_btn.setMaximumWidth(40)
            delete_btn.setStyleSheet("background-color: #EF4444; color: white;")
            delete_btn.clicked.connect(lambda _, url_id=url_data.get('id', ''):
                                       self.delete_url(url_id, short_code))

            action_layout.addWidget(copy_btn)
            action_layout.addWidget(qr_btn)
            action_layout.addWidget(delete_btn)
            action_layout.addStretch()

            self.table.setCellWidget(row, 5, action_widget)

    def copy_url(self, url):
        """Copy URL to clipboard"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(url)
        QMessageBox.information(self, "Copied", f"URL copied to clipboard!\n\n{url}")

    def generate_qr_code(self, url):
        """Generate QR code for URL"""
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
            dialog.exec_()

        except ImportError:
            QMessageBox.warning(self, "QR Code Error",
                                "Please install qrcode[pil] package")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate QR code: {str(e)}")

    def delete_url(self, url_id, short_code):
        """Delete URL from database"""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete URL: {short_code}?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # This would be your delete endpoint
                # response = requests.delete(f"{self.api_base_url}/api/urls/{url_id}")
                # For now, show message
                QMessageBox.information(
                    self, "Delete Function",
                    f"Delete functionality for URL: {short_code}\n\n"
                    "In a real implementation, this would:\n"
                    "1. Send DELETE request to backend\n"
                    "2. Remove from database\n"
                    "3. Refresh the table"
                )
                # Refresh the table after deletion
                # self.load_urls()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete URL: {str(e)}")