from dataHandling.Constants import Constants
from uiComps.QHelper import SymbolCompleter, Validator

class SymbolFinderImplementation():

    def connectSearchField(self):
        self.forceUpperCase()
        self.search_field.textChanged.connect(lambda: self.fieldUpdate(Constants.SYMBOL_CHANGE))
        self.search_field.returnPressed.connect(lambda: self.fieldUpdate(Constants.SYMBOL_SUBMIT))
        
        self.symbol_completer = SymbolCompleter(self)
        self.search_field.setCompleter(self.symbol_completer)


    def contractUpdate(self, signal):
        if signal == Constants.CONTRACT_DETAILS_FINISHED:
            self.fetchItemsForList()
            self.symbol_completer.complete()
        elif signal == Constants.CONTRACT_DETAILS_RETRIEVED:
            self.fetchItemsForList()
        

    def fetchItemsForList(self):
        while self.symbol_manager.hasNewItem():
            item = self.symbol_manager.getLatestItem()
            self.symbol_completer.addToList(item)
            self.symbol_completer.complete()


    def fetchForSymbol(self, symbol_name):
        self.symbol_completer.refreshModel()
        self.symbol_manager.requestContractDetails(symbol_name)


    def fieldUpdate(self, action_type):
        if action_type == Constants.SYMBOL_CHANGE:
            self.fetchForSymbol(self.search_field.text())
        elif action_type == Constants.SYMBOL_SUBMIT:
            self.returnSelection()


    def forceUpperCase(self):
        self.search_field.setValidator(Validator(self))