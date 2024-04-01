
from PyQt5.QtCore import Qt, pyqtSlot
from ibapi.contract import Contract

from .DataStructures import DetailObject
from .Constants import Constants
from .DataManagement import DataManager


class SymbolManager(DataManager):

    _item_list = set()
    sec_type = Constants.STOCK


    def __init__(self, callback=None, name=None):
        if name is None:
            super().__init__(callback, name="SymbolManager")
        else:
            super().__init__(callback, name=name)


    def connectSignalsToSlots(self):
        super().connectSignalsToSlots()
        self.ib_interface.contract_details_signal.connect(self.relayContractDetails, Qt.QueuedConnection)
        self.ib_interface.contract_details_finished_signal.connect(self.contractDetailFetchComplete, Qt.QueuedConnection)


    @pyqtSlot(DetailObject)
    def relayContractDetails(self, details):
        self._item_list.add(details)
        self.api_updater.emit(Constants.CONTRACT_DETAILS_RETRIEVED, dict())


    def contractDetailFetchComplete(self):
        self.api_updater.emit(Constants.CONTRACT_DETAILS_FINISHED, dict())


    def requestContractDetails(self, symbol_name):
        contract = Contract()
        contract.symbol = symbol_name
        contract.secType = self.sec_type
        contract.exchange = Constants.SMART
        self.ib_request_signal.emit({'type': 'reqContractDetails', 'req_id': Constants.SYMBOL_SEARCH_REQID, 'contract': contract})


    def setSelectedSectype(self, to_type):
        self.sec_type = to_type


    def hasNewItem(self):
        return len(self._item_list) != 0

    def getLatestItem(self):
        if self.hasNewItem():
            return self._item_list.pop()
        else:
            return None


 
