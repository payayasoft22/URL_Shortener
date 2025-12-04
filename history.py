from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout, QPushButton, QFrame, QLineEdit,
    QComboBox, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor


class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # Page Header
        header_widget = self.create_header()
        main_layout.addWidget(header_widget)

        # Search Bar
        search_bar = self.create_search_bar()
        main_layout.addWidget(search_bar)

        # Links Table
        table_widget = self.create_links_table()
        main_layout.addWidget(table_widget, 1)  # 1 = stretch factor

        # Add some space at the bottom
        main_layout.addStretch(1)

    def create_header(self):
        frame = QFrame()
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Title
        title_label = QLabel("My Links")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setStyleSheet("color: #374151;")
        layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Manage and track all your shortened links")
        subtitle_label.setFont(QFont("Arial", 14))
        subtitle_label.setStyleSheet("color: #6B7280;")
        layout.addWidget(subtitle_label)

        return frame

    def create_search_bar(self):
        frame = QFrame()
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        frame.setFixedHeight(56)

        # Create shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 10))
        frame.setGraphicsEffect(shadow)

        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #D9D9D9;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 0, 20, 0)

        # Search icon
        search_icon = QLabel("🔍")
        search_icon.setFont(QFont("Arial", 14))
        layout.addWidget(search_icon)

        # Search input
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search by URL or alias...")
        search_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background-color: transparent;
                font-size: 14px;
                color: #374151;
                padding: 15px 10px;
            }
            QLineEdit:focus {
                border: none;
                outline: none;
            }
        """)
        layout.addWidget(search_input, 1)  # 1 = stretch factor

        # Filter dropdown
        filter_combo = QComboBox()
        filter_combo.addItems(["All links", "Active", "Expired", "Most clicked"])
        filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #DCDEE5;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                font-size: 14px;
                color: #374151;
                min-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6B7280;
                margin-right: 8px;
            }
        """)
        layout.addWidget(filter_combo)

        return frame

    def create_links_table(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #D9D9D9;
            }
        """)

        # Create shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 10))
        frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Original URL", "Short URL", "Clicks", "Created", "Actions"
        ])

        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #E5E7EB;
                selection-background-color: #E8F8F4;
            }
            QHeaderView::section {
                background-color: #F2F3F5;
                padding: 16px 20px;
                border: none;
                font-weight: 600;
                font-size: 14px;
                color: #374151;
                text-align: left;
            }
            QTableWidget::item {
                padding: 20px;
                border: none;
                border-bottom: 1px solid #E5E7EB;
                font-size: 14px;
                color: #666E7D;
            }
        """)

        # Configure table
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        # Set column resize policies
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Original URL
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Short URL
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Clicks
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Created
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Actions

        # Set column widths
        table.setColumnWidth(1, 150)  # Short URL
        table.setColumnWidth(2, 100)  # Clicks
        table.setColumnWidth(3, 120)  # Created
        table.setColumnWidth(4, 180)  # Actions

        # Add sample data (matching your image)
        self.populate_sample_data(table)

        layout.addWidget(table)
        return frame

    def create_action_buttons(self):
        """Creates the action buttons for each row"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Copy button
        copy_btn = QPushButton("📋")
        copy_btn.setToolTip("Copy")
        copy_btn.setFixedSize(32, 32)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #E5E7EB;
                border-radius: 8px;
                border: none;
                font-size: 14px;
                color: #374151;
            }
            QPushButton:hover {
                background-color: #D1D5DB;
            }
        """)

        # QR button
        qr_btn = QPushButton("QR")
        qr_btn.setToolTip("QR Code")
        qr_btn.setFixedSize(32, 32)
        qr_btn.setStyleSheet("""
            QPushButton {
                background-color: #E5E7EB;
                border-radius: 8px;
                border: none;
                font-size: 12px;
                color: #374151;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #D1D5DB;
            }
        """)

        # Analytics button
        analytics_btn = QPushButton("📈")
        analytics_btn.setToolTip("Analytics")
        analytics_btn.setFixedSize(32, 32)
        analytics_btn.setStyleSheet(copy_btn.styleSheet())

        # Delete button
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip("Delete")
        delete_btn.setFixedSize(32, 32)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEE2E2;
                border-radius: 8px;
                border: none;
                font-size: 14px;
                color: #DC2626;
            }
            QPushButton:hover {
                background-color: #FECACA;
            }
        """)

        layout.addWidget(copy_btn)
        layout.addWidget(qr_btn)
        layout.addWidget(analytics_btn)
        layout.addWidget(delete_btn)
        layout.addStretch()

        return container

    def populate_sample_data(self, table):
        # Sample data matching your image
        sample_data = [
            {
                "original_url": "https://example.com/very-long-article-about-techno...",
                "short_url": "https://short.ly/abc123",
                "clicks": "1,247",
                "created": "1/15/2024",
                "actions": self.create_action_buttons()
            },
            {
                "original_url": "https://github.com/username/repository-name",
                "short_url": "https://short.ly/gh-repo",
                "clicks": "856",
                "created": "1/10/2024",
                "actions": self.create_action_buttons()
            },
            {
                "original_url": "https://medium.com/article-title-goes-here",
                "short_url": "https://short.ly/med-art",
                "clicks": "432",
                "created": "1/5/2024",
                "actions": self.create_action_buttons()
            },
            {
                "original_url": "https://discord.com/channels/1141321686059323393/...",
                "short_url": "https://short.ly/discord",
                "clicks": "321",
                "created": "1/3/2024",
                "actions": self.create_action_buttons()
            },
            {
                "original_url": "https://stackoverflow.com/questions/123456/...",
                "short_url": "https://short.ly/stack",
                "clicks": "215",
                "created": "1/1/2024",
                "actions": self.create_action_buttons()
            }
        ]

        table.setRowCount(len(sample_data))

        for row, data in enumerate(sample_data):
            # Original URL (with truncation for long URLs)
            original_item = QTableWidgetItem(data["original_url"])
            original_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setItem(row, 0, original_item)

            # Short URL (clickable style)
            short_item = QTableWidgetItem(data["short_url"])
            short_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            short_item.setForeground(QColor("#10C988"))  # Green color for short URLs
            table.setItem(row, 1, short_item)

            # Clicks
            clicks_item = QTableWidgetItem(data["clicks"])
            clicks_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            table.setItem(row, 2, clicks_item)

            # Created date
            created_item = QTableWidgetItem(data["created"])
            created_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            table.setItem(row, 3, created_item)

            # Actions (set widget instead of item)
            table.setCellWidget(row, 4, data["actions"])

        # Adjust row heights
        for row in range(table.rowCount()):
            table.setRowHeight(row, 64)