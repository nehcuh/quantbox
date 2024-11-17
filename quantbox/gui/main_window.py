from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTabWidget, QLabel, QComboBox,
    QDateEdit, QLineEdit, QTableWidget, QTableWidgetItem,
    QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from ..fetchers import RemoteFetcher
from ..savers import DataSaver
from pymongo import MongoClient
import pandas as pd
from datetime import datetime

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuantBox Data Manager")
        self.setMinimumSize(1200, 800)
        
        # Initialize components
        self.fetcher = RemoteFetcher(engine='ts')
        self.mongo_client = MongoClient('mongodb://localhost:27017/')
        self.db = self.mongo_client['quantbox']
        
        # Setup UI
        self.setup_ui()
        
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
        
    def create_data_fetch_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Data source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Data Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(['TuShare', 'GoldMiner'])
        source_layout.addWidget(self.source_combo)
        layout.addLayout(source_layout)
        
        # Date range selection
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date Range:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("to"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        date_layout.addWidget(self.end_date)
        layout.addLayout(date_layout)
        
        # Data type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Data Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['Holdings', 'Trade Dates', 'Contracts'])
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Exchange selection
        exchange_layout = QHBoxLayout()
        exchange_layout.addWidget(QLabel("Exchange:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['SHFE', 'DCE', 'CZCE', 'INE', 'CFFEX'])
        exchange_layout.addWidget(self.exchange_combo)
        layout.addLayout(exchange_layout)
        
        # Fetch button
        fetch_btn = QPushButton("Fetch Data")
        fetch_btn.clicked.connect(self.fetch_data)
        layout.addWidget(fetch_btn)
        
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
        coll_layout.addWidget(self.collection_combo)
        layout.addLayout(coll_layout)
        
        # Query input
        query_layout = QHBoxLayout()
        query_layout.addWidget(QLabel("Query:"))
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText('{"exchange": "SHFE"}')
        query_layout.addWidget(self.query_input)
        layout.addLayout(query_layout)
        
        # Query button
        query_btn = QPushButton("Query")
        query_btn.clicked.connect(self.query_data)
        layout.addWidget(query_btn)
        
        # Results table
        self.query_results_table = QTableWidget()
        layout.addWidget(self.query_results_table)
        
        return widget
    
    def update_collections(self):
        self.collection_combo.clear()
        collections = self.db.list_collection_names()
        self.collection_combo.addItems(collections)
    
    def fetch_data(self):
        try:
            # Get parameters
            data_type = self.type_combo.currentText().lower()
            exchange = self.exchange_combo.currentText()
            start_date = self.start_date.date().toString('yyyy-MM-dd')
            end_date = self.end_date.date().toString('yyyy-MM-dd')
            
            # Fetch data
            if data_type == 'holdings':
                data = self.fetcher.fetch_get_holdings(
                    exchanges=[exchange],
                    start_date=start_date,
                    end_date=end_date
                )
            elif data_type == 'trade dates':
                data = self.fetcher.fetch_get_trade_dates(
                    start_date=start_date,
                    end_date=end_date
                )
            else:  # contracts
                data = self.fetcher.fetch_get_contracts(
                    exchanges=[exchange],
                    start_date=start_date,
                    end_date=end_date
                )
            
            # Display data
            self.display_data(data)
            
            # Save to MongoDB
            collection = f"{exchange.lower()}_{data_type}"
            self.db[collection].insert_many(data.to_dict('records'))
            self.update_collections()
            
            QMessageBox.information(self, "Success", "Data fetched and saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def query_data(self):
        try:
            collection = self.collection_combo.currentText()
            query = eval(self.query_input.text() or '{}')
            
            # Query data
            cursor = self.db[collection].find(query)
            data = pd.DataFrame(list(cursor))
            
            # Display data
            self.display_query_results(data)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def display_data(self, df):
        self.results_table.setRowCount(df.shape[0])
        self.results_table.setColumnCount(df.shape[1])
        self.results_table.setHorizontalHeaderLabels(df.columns)
        
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                item = QTableWidgetItem(str(df.iloc[i, j]))
                self.results_table.setItem(i, j, item)
    
    def display_query_results(self, df):
        if '_id' in df.columns:
            df = df.drop('_id', axis=1)
            
        self.query_results_table.setRowCount(df.shape[0])
        self.query_results_table.setColumnCount(df.shape[1])
        self.query_results_table.setHorizontalHeaderLabels(df.columns)
        
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                item = QTableWidgetItem(str(df.iloc[i, j]))
                self.query_results_table.setItem(i, j, item)
