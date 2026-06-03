from PyQt6.QtWidgets import QComboBox, QLineEdit
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtGui import QStandardItemModel, QStandardItem

class SearchableComboBox(QComboBox):
    def __init__(self, parent=None, fallback_text=""):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        self.fallback_text = fallback_text
        
        # Setup model and proxy for filtering
        self.source_model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        self.setModel(self.proxy_model)
        
        # Connect line edit text changed to filter
        self.lineEdit().textEdited.connect(self.filter_items)
        self.lineEdit().returnPressed.connect(self.on_return_pressed)
        
        self.all_items = []

    def addItems(self, texts):
        self.all_items.extend(texts)
        for text in texts:
            item = QStandardItem(text)
            self.source_model.appendRow(item)

    def filter_items(self, text):
        self.proxy_model.setFilterFixedString(text)
        
        # If no items match, show fallback
        if self.proxy_model.rowCount() == 0:
            self.proxy_model.setFilterFixedString("") # Clear filter to show something, or handle differently
            # We will temporarily clear the model and add the fallback
            self.source_model.clear()
            self.source_model.appendRow(QStandardItem(self.fallback_text))
        else:
            # Restore original items if we had fallback
            if self.source_model.rowCount() == 1 and self.source_model.item(0).text() == self.fallback_text:
                self.source_model.clear()
                for item_text in self.all_items:
                    self.source_model.appendRow(QStandardItem(item_text))
            self.proxy_model.setFilterFixedString(text)
            
        self.showPopup()

    def on_return_pressed(self):
        if self.proxy_model.rowCount() > 0:
            self.setCurrentIndex(0)
            self.lineEdit().setText(self.currentText())
        self.hidePopup()
