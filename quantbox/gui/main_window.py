from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QLabel,
    QComboBox,
    QDateEdit,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QGroupBox,
    QProgressDialog,
    QApplication,
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence
from ..services.market_data_service import MarketDataService
from pymongo import MongoClient
import pandas as pd
from datetime import datetime


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuantBox Data Manager")
        self.setGeometry(100, 100, 1200, 800)

        # 添加强制退出快捷键 (Ctrl+Q)
        self.quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.quit_shortcut.activated.connect(self.force_quit)

        # 添加状态栏
        self.statusBar().showMessage("Ready (Press Ctrl+Q to force quit)")

        # Initialize components
        self.data_service = MarketDataService()
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["quantbox"]

        # Setup UI
        self.setup_ui()

    def force_quit(self):
        """Force quit the application"""
        try:
            # 清理资源
            if hasattr(self, "mongo_client"):
                self.mongo_client.close()
            # 如果 data_service 有 close 方法，则调用
            if hasattr(self, "data_service") and hasattr(self.data_service, "close"):
                self.data_service.close()
        except Exception:
            pass  # 忽略清理过程中的错误
        finally:
            QApplication.quit()

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            reply = QMessageBox.question(
                self,
                "Exit",
                "Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 正常清理资源
                if hasattr(self, "mongo_client"):
                    self.mongo_client.close()
                # 如果 data_service 有 close 方法，则调用
                if hasattr(self, "data_service") and hasattr(self.data_service, "close"):
                    self.data_service.close()
                event.accept()
            else:
                event.ignore()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Error while closing: {str(e)}")
            event.accept()

    def setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Add tabs
        tabs.addTab(self.create_data_fetch_tab(), "Data Fetch")
        tabs.addTab(self.create_data_view_tab(), "Data View")

        # Initialize database indexes
        self._init_db_indexes()

    def _init_db_indexes(self):
        """Initialize database indexes for better query performance."""
        try:
            # Common fields that we'll query frequently
            common_indexes = ["exchange", "symbol", "date", "trade_date"]

            # Create indexes for each collection
            for collection in self.db.list_collection_names():
                existing_indexes = self.db[collection].index_information()
                for field in common_indexes:
                    index_name = f"{field}_1"
                    if index_name not in existing_indexes:
                        self.db[collection].create_index(field)
        except Exception as e:
            print(f"Warning: Failed to create indexes: {e}")

    def create_data_fetch_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Data type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Data Type:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Holdings", "Contracts", "Trade Dates"])
        self.type_combo.currentTextChanged.connect(self.on_data_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # Exchange selection
        exchange_layout = QHBoxLayout()
        exchange_label = QLabel("Exchange:")
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["SHFE", "DCE", "CZCE", "INE", "CFFEX"])
        exchange_layout.addWidget(exchange_label)
        exchange_layout.addWidget(self.exchange_combo)
        layout.addLayout(exchange_layout)

        # Holdings query group
        self.holdings_group = QGroupBox("Holdings Query")
        holdings_layout = QVBoxLayout()

        # Query type selection
        query_type_layout = QHBoxLayout()
        query_type_label = QLabel("Query Type:")
        self.query_type_combo = QComboBox()
        self.query_type_combo.addItems(["Product", "Contract"])
        self.query_type_combo.currentTextChanged.connect(self.on_query_type_changed)
        query_type_layout.addWidget(query_type_label)
        query_type_layout.addWidget(self.query_type_combo)
        holdings_layout.addLayout(query_type_layout)

        # Product input
        product_layout = QHBoxLayout()
        product_label = QLabel("Product:")
        self.product_input = QLineEdit()
        self.product_input.setPlaceholderText("Enter product name (e.g., 豆粕)")
        product_layout.addWidget(product_label)
        product_layout.addWidget(self.product_input)
        holdings_layout.addLayout(product_layout)

        # Contract input
        contract_layout = QHBoxLayout()
        contract_label = QLabel("Contract:")
        self.contract_input = QLineEdit()
        self.contract_input.setPlaceholderText("Enter contract code (e.g., M2501)")
        contract_layout.addWidget(contract_label)
        contract_layout.addWidget(self.contract_input)
        holdings_layout.addLayout(contract_layout)

        self.holdings_group.setLayout(holdings_layout)
        layout.addWidget(self.holdings_group)
        self.holdings_group.setVisible(False)

        # Date selection
        date_layout = QHBoxLayout()
        start_label = QLabel("Start Date:")
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))

        end_label = QLabel("End Date:")
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date)
        layout.addLayout(date_layout)

        # Fetch button
        fetch_button = QPushButton("Fetch Data")
        fetch_button.clicked.connect(self.fetch_data)
        layout.addWidget(fetch_button)

        # Results table
        self.results_table = QTableWidget()
        layout.addWidget(self.results_table)

        return widget

    def create_data_view_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Collection selection
        coll_layout = QHBoxLayout()
        coll_layout.addWidget(QLabel("Collection:"))
        self.collection_combo = QComboBox()
        self.update_collections()
        self.collection_combo.currentTextChanged.connect(self.update_index_fields)
        coll_layout.addWidget(self.collection_combo)
        layout.addLayout(coll_layout)

        # Index-based query builder
        self.index_layouts = []  # Store layouts for dynamic updates
        self.index_widgets = []  # Store widgets for dynamic updates

        # Create a widget to hold all index query inputs
        self.index_query_widget = QWidget()
        self.index_query_layout = QVBoxLayout(self.index_query_widget)
        layout.addWidget(self.index_query_widget)

        # Advanced query input (for manual queries)
        advanced_group = QGroupBox("Advanced Query")
        advanced_layout = QVBoxLayout(advanced_group)

        query_layout = QHBoxLayout()
        query_layout.addWidget(QLabel("Manual Query:"))
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText('{"exchange": "SHFE"}')
        query_layout.addWidget(self.query_input)
        advanced_layout.addLayout(query_layout)

        layout.addWidget(advanced_group)

        # Limit input
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Limit:"))
        self.limit_input = QLineEdit()
        self.limit_input.setText("1000")
        self.limit_input.setPlaceholderText("Maximum number of results")
        limit_layout.addWidget(self.limit_input)
        layout.addLayout(limit_layout)

        # Query buttons
        buttons_layout = QHBoxLayout()

        index_query_btn = QPushButton("Query by Index")
        index_query_btn.clicked.connect(self.query_by_index)
        buttons_layout.addWidget(index_query_btn)

        advanced_query_btn = QPushButton("Advanced Query")
        advanced_query_btn.clicked.connect(self.query_data)
        buttons_layout.addWidget(advanced_query_btn)

        layout.addLayout(buttons_layout)

        # Results table
        self.query_results_table = QTableWidget()
        layout.addWidget(self.query_results_table)

        return widget

    def update_index_fields(self):
        """Update available index fields based on selected collection."""
        # Clear existing index inputs
        for layout in self.index_layouts:
            # Remove all widgets from layout
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self.index_layouts.clear()
        self.index_widgets.clear()

        # Clear the main index query layout
        while self.index_query_layout.count():
            item = self.index_query_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        collection = self.collection_combo.currentText()
        if not collection:
            return

        try:
            # Get index information for the selected collection
            indexes = self.db[collection].index_information()

            # Track unique fields to avoid duplicates
            unique_fields = set()

            # Create input fields for each indexed field
            for index_name, index_info in indexes.items():
                if index_name == "_id_":  # Skip the default _id index
                    continue

                # Get the field names from the index key
                for key, _ in index_info["key"]:
                    if key in unique_fields:  # Skip if we already have this field
                        continue
                    unique_fields.add(key)

                    # Create a horizontal layout for this field
                    field_layout = QHBoxLayout()
                    self.index_layouts.append(field_layout)

                    # Create label
                    label = QLabel(f"{key}:")
                    field_layout.addWidget(label)

                    # Create input field
                    input_field = QLineEdit()
                    input_field.setObjectName(f"index_{key}")
                    input_field.setPlaceholderText(f"Enter {key}")
                    field_layout.addWidget(input_field)
                    self.index_widgets.append(input_field)

                    self.index_query_layout.addLayout(field_layout)

            # Add a stretch to push everything to the top
            self.index_query_layout.addStretch()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get index information: {str(e)}")

    def query_by_index(self):
        """Execute query using index fields."""
        try:
            collection = self.collection_combo.currentText()
            if not collection:
                return

            # Build query from index inputs
            query = {}
            for widget in self.index_widgets:
                if widget.text().strip():  # Only add non-empty fields to query
                    field_name = widget.objectName().replace("index_", "")
                    value = widget.text().strip()

                    # Try to convert to appropriate type
                    try:
                        # Try to convert to number if possible
                        if "." in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        # If not a number, keep it as string
                        pass

                    query[field_name] = value

            limit = int(self.limit_input.text() or 1000)

            # Execute query
            cursor = (
                self.db[collection]
                .find(
                    query,
                    projection={
                        "_id": 0,
                        "date": 1,
                        "trade_date": 1,
                        "exchange": 1,
                        "symbol": 1,
                        "open": 1,
                        "high": 1,
                        "low": 1,
                        "close": 1,
                        "volume": 1,
                        "amount": 1,
                        "open_interest": 1,
                    },
                )
                .sort([("date", -1)])
                .limit(limit)
            )

            # Convert to DataFrame and display
            data = pd.DataFrame(list(cursor))

            if data.empty:
                QMessageBox.information(self, "Info", "No data found for the given query.")
                return

            self.display_query_results(data)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def update_collections(self):
        self.collection_combo.clear()
        collections = self.db.list_collection_names()
        self.collection_combo.addItems(collections)

    def on_data_type_changed(self, data_type):
        """Handle visibility of holdings query group based on data type"""
        is_holdings = data_type.lower() == "holdings"
        self.holdings_group.setVisible(is_holdings)

    def on_query_type_changed(self, query_type):
        """Handle visibility of product/contract inputs based on query type"""
        is_product = query_type.lower() == "product"
        self.product_input.setVisible(is_product)
        self.product_input.setEnabled(is_product)
        self.contract_input.setVisible(not is_product)
        self.contract_input.setEnabled(not is_product)

    def fetch_data(self):
        try:
            # Get parameters
            data_type = self.type_combo.currentText().lower()
            exchange = self.exchange_combo.currentText()
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            end_date = self.end_date.date().toString("yyyy-MM-dd")

            # Create progress dialog
            progress = QProgressDialog("Fetching data...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            def update_progress(step, total_steps=4):
                progress.setValue(int((step / total_steps) * 100))
                QApplication.processEvents()
                return not progress.wasCanceled()

            # Step 1: Initialize fetcher
            if not update_progress(1):
                return

            try:
                # Fetch data with timeout
                if data_type == "holdings":
                    data = self.data_service.get_future_holdings(
                        exchanges=[exchange],
                        start_date=start_date,
                        end_date=end_date,
                        use_local=False,  # 强制使用远程数据源
                    )

                    # Apply filters based on query type
                    if not data.empty:
                        query_type = self.query_type_combo.currentText().lower()
                        if query_type == "product":
                            product = self.product_input.text().strip()
                            if product:
                                # 使用商品名称进行模糊匹配
                                data = data[
                                    data["product_name"].str.contains(product, case=False, na=False)
                                ]
                        else:  # contract
                            contract = self.contract_input.text().strip().upper()  # 转换为大写
                            if contract:
                                # 使用合约代码进行精确匹配
                                data = data[data["symbol"].str.upper() == contract]

                elif data_type == "trade dates":
                    data = self.data_service.get_trade_calendar(
                        start_date=start_date,
                        end_date=end_date,
                        use_local=False,  # 强制使用远程数据源
                    )
                else:  # contracts
                    data = self.data_service.get_future_contracts(
                        exchanges=[exchange],
                        start_date=start_date,
                        end_date=end_date,
                        use_local=False,  # 强制使用远程数据源
                    )
            except Exception as e:
                progress.close()
                QMessageBox.critical(self, "Error", f"Failed to fetch data: {str(e)}")
                return

            if not update_progress(2):
                return

            # Step 3: Process and display data
            if data is not None and not data.empty:
                # 限制返回的数据量
                if len(data) > 10000:
                    data = data.head(10000)
                    QMessageBox.warning(
                        self, "Warning", "Results limited to 10,000 rows for performance reasons."
                    )

                self.display_data(data)
            else:
                progress.close()
                QMessageBox.information(self, "Info", "No data found for the given parameters.")
                return

            if not update_progress(3):
                return

            # Step 4: Save to MongoDB
            try:
                collection = f"{exchange.lower()}_{data_type}"
                # 使用 insert_many 的有序插入，忽略重复数据
                self.db[collection].insert_many(
                    data.to_dict("records"), ordered=False  # 设置为 False 以提高性能
                )
                self.update_collections()
            except Exception as e:
                if "duplicate key error" in str(e).lower():
                    # 忽略重复键错误，继续处理
                    pass
                else:
                    progress.close()
                    QMessageBox.warning(self, "Warning", f"Some data could not be saved: {str(e)}")

            progress.setValue(100)
            QMessageBox.information(self, "Success", "Data fetched and saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            if "progress" in locals():
                progress.close()

    def display_data(self, df):
        """Display data in the results table with optimized performance."""
        if df.empty:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
            return

        # Disable table updates during data loading
        self.results_table.setUpdatesEnabled(False)
        try:
            self.results_table.setRowCount(df.shape[0])
            self.results_table.setColumnCount(df.shape[1])
            self.results_table.setHorizontalHeaderLabels(df.columns)

            # 批量更新表格内容
            for i in range(df.shape[0]):
                for j in range(df.shape[1]):
                    value = df.iloc[i, j]
                    if pd.isna(value):
                        item = QTableWidgetItem("")
                    else:
                        # Format numbers for better display
                        if isinstance(value, (int, float)):
                            item = QTableWidgetItem(f"{value:,.2f}")
                        else:
                            item = QTableWidgetItem(str(value))
                    self.results_table.setItem(i, j, item)

                # 每处理 100 行就更新一次界面
                if i % 100 == 0:
                    QApplication.processEvents()

        finally:
            self.results_table.setUpdatesEnabled(True)

        # Auto-resize columns to content
        self.results_table.resizeColumnsToContents()

    def query_data(self):
        try:
            collection = self.collection_combo.currentText()
            query = eval(self.query_input.text() or "{}")
            limit = int(self.limit_input.text() or 1000)

            # Query data with limit and proper sorting
            projection = {"_id": 0}  # 只排除 _id 字段，显示所有其他字段
            if "holdings" in collection.lower():
                # 对于 holdings 集合，确保显示所有重要字段
                projection.update(
                    {
                        "date": 1,
                        "exchange": 1,
                        "symbol": 1,
                        "product_name": 1,
                        "product_id": 1,
                        "volume": 1,
                        "volume_chg": 1,
                        "long_volume": 1,
                        "long_volume_chg": 1,
                        "short_volume": 1,
                        "short_volume_chg": 1,
                        "long_amount": 1,
                        "long_amount_chg": 1,
                        "short_amount": 1,
                        "short_amount_chg": 1,
                        "net_volume": 1,
                        "net_amount": 1,
                        "member_name": 1,
                        "member_type": 1,
                    }
                )
            else:
                # 对于其他集合，使用默认字段
                projection.update(
                    {
                        "date": 1,
                        "trade_date": 1,
                        "exchange": 1,
                        "symbol": 1,
                        "open": 1,
                        "high": 1,
                        "low": 1,
                        "close": 1,
                        "volume": 1,
                        "amount": 1,
                        "open_interest": 1,
                    }
                )

            cursor = (
                self.db[collection]
                .find(query, projection=projection)
                .sort([("date", -1)])
                .limit(limit)
            )

            # Convert to DataFrame
            data = pd.DataFrame(list(cursor))

            if data.empty:
                QMessageBox.information(self, "Info", "No data found for the given query.")
                return

            # Display data
            self.display_query_results(data)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def display_query_results(self, df):
        """Display query results in the table with better formatting."""
        if df.empty:
            self.query_results_table.setRowCount(0)
            self.query_results_table.setColumnCount(0)
            return

        self.query_results_table.setRowCount(df.shape[0])
        self.query_results_table.setColumnCount(df.shape[1])
        self.query_results_table.setHorizontalHeaderLabels(df.columns)

        # Optimize table updates
        self.query_results_table.setUpdatesEnabled(False)
        try:
            for i in range(df.shape[0]):
                for j in range(df.shape[1]):
                    value = df.iloc[i, j]
                    if pd.isna(value):
                        item = QTableWidgetItem("")
                    else:
                        # Format numbers for better display
                        if isinstance(value, (int, float)):
                            item = QTableWidgetItem(f"{value:,.2f}")
                        else:
                            item = QTableWidgetItem(str(value))
                    self.query_results_table.setItem(i, j, item)
        finally:
            self.query_results_table.setUpdatesEnabled(True)

        # Auto-resize columns to content
        self.query_results_table.resizeColumnsToContents()
