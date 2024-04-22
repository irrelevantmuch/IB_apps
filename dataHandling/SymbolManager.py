
# Copyright (c) 2024 Jelmer de Vries
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation in its latest version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


from PyQt5.QtCore import Qt, pyqtSlot, QObject
from ibapi.contract import Contract

from .DataStructures import DetailObject
from .Constants import Constants
from .IBConnectivity import IBConnectivity



class SymbolManager(IBConnectivity):

    _item_list = set()
    sec_type = Constants.STOCK


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    ############# CALLBACKS

    def contractDetails(self, req_id, contract_details):
        print(f"SymbolManager.contractDetails {req_id}")
        print(contract_details)
        contract = contract_details.contract
        
        if contract.primaryExchange == "":
            exchange = contract.exchange
        else:
            exchange = contract.primaryExchange

        detailObject = DetailObject(symbol=contract.symbol, exchange=exchange, long_name=contract_details.longName, numeric_id=contract.conId, currency=contract.currency)
        self._item_list.add(detailObject)
        self.api_updater.emit(Constants.CONTRACT_DETAILS_RETRIEVED, dict())
        

    def contractDetailsEnd(self, req_id: int):
        print(f"SymbolManager.contractDetailsEnd {req_id}")
        super().contractDetailsEnd(req_id)
        self.api_updater.emit(Constants.CONTRACT_DETAILS_FINISHED, dict())


    ############# REQUESTS

    def requestContractDetails(self, symbol_name):
        contract = Contract()
        contract.symbol = symbol_name
        contract.secType = self.sec_type
        contract.exchange = Constants.SMART
        self.makeRequest({'type': 'reqContractDetails', 'req_id': Constants.SYMBOL_SEARCH_REQID, 'contract': contract})


    ############# HELPERS

    def setSelectedSectype(self, to_type):
        self.sec_type = to_type


    def hasNewItem(self):
        return len(self._item_list) != 0


    def getLatestItem(self):
        if self.hasNewItem():
            return self._item_list.pop()
        else:
            return None


 
