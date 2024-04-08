
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

from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QObject, QReadWriteLock

from ibapi.contract import Contract

from dataHandling.Constants import Constants
import time
from ibapi.order import Order

import itertools
from dataHandling.DataManagement import DataManager

from functools import wraps

def lockForRead(func):
    @wraps(func)
    def wrapper(self, key, *args, **kwargs):
        # Acquire the lock for reading before accessing the shared resource
        self._locks[key].lockForRead()
        
        try:
            # Execute the function (access the shared resource)
            return func(self, key, *args, **kwargs) 
        finally:
            # Ensure the lock is always released
            self._locks[key].unlock()
    return wrapper


class OpenOrderBuffer(QObject):

    order_buffer_signal = pyqtSignal(str, int)
    _orders = dict()
    _editable = dict()
    _locks = dict()


    def setOrder(self, order_id, order, contract):

        new_order = order_id in self._orders
        self.order_buffer_signal.emit(Constants.DATA_WILL_CHANGE, order_id)

        if not (order_id in self._locks):
            self._locks[order_id] = QReadWriteLock()

        self._locks[order_id].lockForWrite()
        self._orders[order_id] = (order, contract)
        self._locks[order_id].unlock()

        if new_order:
            self.order_buffer_signal.emit(Constants.DATA_STRUCTURE_CHANGED, order_id)
        self.order_buffer_signal.emit(Constants.DATA_DID_CHANGE, order_id)


    def getPropTypeForColumn(self, colummn_name):
            if colummn_name == 'Count':
                return 'Count'
            elif colummn_name == 'Limit':
                return 'Limit'
            elif colummn_name == 'Stop level':
                return 'Trigger'
            return ''


    def getDataForColumn(self, index, colummn_name):
        order_id = list(self._orders.keys())[index]

        if colummn_name == 'Order ID':
            return order_id

        self._locks[order_id].lockForRead()
        try:
            order, contract = self._orders[order_id]

            if colummn_name == 'Symbol': 
                return contract.symbol
            elif colummn_name == 'Action':
                return order.action
            elif colummn_name == 'Action':
                return order.orderType
            elif colummn_name == 'Count':
                return order.totalQuantity
            elif colummn_name == 'Limit':
                return order.lmtPrice
            elif colummn_name == 'Stop level':
                if order.orderType == "STP LMT":
                    return order.auxPrice
                else:
                    return None
            elif colummn_name == 'Status':
                return 'Open'
        finally:
            self._locks[order_id].unlock()


    def getOrderId(self, index):
        return list(self._orders.keys())[index]


    def getOrderFor(self, order_id):
        self._locks[order_id].lockForRead()
        try:
            order, _ = self._orders[order_id]
            return order
        finally:
            self._locks[order_id].unlock()


    def getContractFor(self, order_id):
        self._locks[order_id].lockForRead()
        try:
            _, contract = self._orders[order_id]
            return contract
        finally:
            self._locks[order_id].unlock()
    

    def getOrderContract(self, order_id):
        self._locks[order_id].lockForRead()
        try:
            return self._orders[order_id]
        finally:
            self._locks[order_id].unlock()


    def getOrderCount(self):
        return len(self._orders)


    def isEditable(self, order_id):
        self._locks[order_id].lockForRead()
        try:
            return self.editable[order_id]
        finally:
            self._locks[order_id].unlock()


    def setEditable(self, order_id, editable):
        self._locks[order_id].lockForRead()
        self.editable[order_id] = editable
        self._locks[order_id].unlock()


    def isOpenOrder(self, order_id):
        return (order_id in self._orders)


    @pyqtSlot(int, dict)
    def orderUpdate(self, order_id, detail_object):
        # print(f"OpenOrderBuffer.orderUpdate {order_id}")
        # print(detail_object)
        if detail_object['status'] == 'Cancelled':
            self.removeOrder(order_id)
        elif detail_object['status'] == 'Filled' and ('remaining' in detail_object) and (detail_object['remaining'] == 0):
            self.removeOrder(order_id)
        elif 'order' in detail_object and 'contract' in detail_object:
            # print(f"What is the parentId {detail_object['order'].parentId}")
            self.setOrder(order_id, detail_object['order'], detail_object['contract'])


    def removeOrder(self, order_id):
        # print(f"OpenOrderBuffer.removeOrder {order_id}")
        if order_id in self._orders:
            self.order_buffer_signal.emit(Constants.DATA_WILL_CHANGE, order_id)

            self._locks[order_id].lockForWrite()
            del self._orders[order_id]
            self._locks[order_id].unlock()
            del self._locks[order_id]

            self.order_buffer_signal.emit(Constants.DATA_STRUCTURE_CHANGED, order_id)
            self.order_buffer_signal.emit(Constants.DATA_DID_CHANGE, order_id)



class OrderManager(DataManager):

    base_order_id = Constants.BASE_ORDER_REQID

    data_buffers = None
    
    open_order_request = pyqtSignal()
    

    def __init__(self, callback=None):
        super().__init__(callback, name="OrderManager")

        self.open_orders = OpenOrderBuffer()
        self.stair_tracker = StairManager()
        self.stair_tracker.update_order_signal.connect(self.orderEdit, Qt.QueuedConnection)


    def getOrderBuffer(self):
        return self.open_orders

    def getStairTracker(self):
        return self.stair_tracker


    def connectSignalsToSlots(self):
        super().connectSignalsToSlots()
        self.ib_interface.order_update_signal.connect(self.open_orders.orderUpdate, Qt.QueuedConnection)
        self.ib_interface.order_update_signal.connect(self.stair_tracker.orderUpdate, Qt.QueuedConnection)
        self.open_order_request.connect(self.ib_interface.trackAndBindOpenOrders, Qt.QueuedConnection)


    def setDataObject(self, data_buffers):
        self.data_buffers = data_buffers
        self.stair_tracker.setDataObject(data_buffers)

    
    # @pyqtSlot()
    # def run(self):
    #     super().run()
        # self.ib_request_signal.emit({'type': 'reqIds', 'num_ids': -1})

##########################################


    @pyqtSlot(list, Contract)
    def placeBracketOrder(self, bracket_order, contract):
        for order in bracket_order:
            request = dict()
            request['type'] = 'placeOrder'
            request['order_id'] = order.orderId
            request['contract'] = contract
            request['order'] = order
            self.ib_request_signal.emit(request)


    def createLimitOrder(self, order_id, action, quantity, limit_price, parent_id=None):
        limit_order = self.createBaseOrder(order_id, action, quantity, parent_id)
        limit_order.orderType = "LMT"
        limit_order.lmtPrice = limit_price
        return limit_order


    def createStopOrder(self, order_id, action, quantity, stop_price, stop_limit=None, parent_id=None):
        stop_loss = self.createBaseOrder(order_id, action, quantity, parent_id)
        
        stop_loss.auxPrice = stop_price
        if stop_limit is not None:
            stop_loss.orderType = "STP LMT"
            stop_loss.lmtPrice = stop_limit
        else:
            stop_loss.orderType = "STP"
        
        return stop_loss


    def getNextOrderIDs(self, count=1):
        next_order_id = self.ib_interface.next_order_ID
        # print("OrderManager.getNextOrderIDs")
        
        # print("OrderManager.getNextOrderIDs 1")
        if next_order_id < Constants.BASE_ORDER_REQID:
            next_order_id = Constants.BASE_ORDER_REQID
        order_id_list = [x + next_order_id for x in range(0, count)]
        # print("OrderManager.getNextOrderIDs 4")

        return order_id_list


    def makeOco(self, oco_order, oco_id):
        oco_order.ocaGroup = oco_id 
        oco_order.ocaType = 1         # 1 = Cancel all remaining orders with block
        oco_order.transmit = True
        return oco_order


    def getNewOcoId(self):
        return f"OCO{int(time.time())}"


    def createBaseOrder(self, order_id, action, quantity, parent_id=None):
        base_order = Order()
        if order_id is not None:
            base_order.orderId = order_id
        base_order.outsideRth = True
        base_order.action = action
        base_order.totalQuantity = int(quantity)
        base_order.eTradeOnly = ''
        base_order.firmQuoteOnly = ''
        if parent_id is not None:
            base_order.parentId = parent_id
        base_order.transmit = False #We leave which orders to transmit to the managing function
        return base_order


    ############## Active order cancellattion

    @pyqtSlot(int)
    def cancelOrderByRow(self, row_index):
        order_id = self.open_orders.getOrderId(row_index)
        self.ib_interface.cancelOrder(order_id, "")


    def cancelStairByRow(self, row_index):
        self.stair_tracker.cancelByRow(row_index)


    def cancelAllOrders(self):
        # print("OrderManager.cancelAllOrders")
        self.ib_request_signal({'type': 'reqGlobalCancel'})


##########################################


    @pyqtSlot(Contract, str, int, float, dict)
    def placeOrder(self, contract, action, count, limit_price, exit_dict):
        
        id_count = 1
        if 'profit_limit' in exit_dict: id_count += 1
        if 'stop_trigger' in exit_dict: id_count += 1
        order_ids = self.getNextOrderIDs(count=id_count)
        
        exit_action = Constants.SELL if action == Constants.BUY else Constants.BUY

        primary_id = order_ids.pop(0)
        new_order_ids = [primary_id]
        order_set = [self.createLimitOrder(primary_id, action, count, limit_price)]

        if 'profit_limit' in exit_dict:
            profit_id = order_ids.pop(0)
            profit_order = self.createLimitOrder(profit_id, exit_action, count, exit_dict['profit_limit'])
            profit_order.parentId = primary_id
            order_set += [profit_order]
            new_order_ids.append(profit_id)

        if 'stop_trigger' in exit_dict:
            stop_id = order_ids.pop(0)
            if 'stop_limit' in exit_dict:
                order_set += [self.createStopOrder(stop_id, exit_action, count, exit_dict['stop_trigger'], stop_limit=exit_dict['stop_limit'], parent_id=primary_id)]
            else:
                order_set += [self.createStopOrder(stop_id, exit_action, count, exit_dict['stop_trigger'], primary_id, stop_limit=None, parent_id=primary_id)]
            new_order_ids.append(stop_id)
        
        order_set[-1].transmit = True
        
        self.placeBracketOrder(order_set, contract)


    @pyqtSlot(Contract, str, int, float, float, float)
    def placeOcoOrder(self, contract, action, count, profit_limit, stop_trigger, stop_limit=None):       
        [profit_id, stop_id] = self.getNextOrderIDs(count=2)

        profit_order = self.createLimitOrder(profit_id, action, count, profit_limit)

        if stop_limit is not None:
            stop_order = self.createStopOrder(stop_id, action, count, stop_trigger, stop_limit=stop_limit)
        else:
            stop_order = self.createStopOrder(stop_id, action, count, stop_trigger, stop_limit=None)
        
        oco_id = self.getNewOcoId()
        profit_order = self.makeOco(profit_order, oco_id)
        stop_order = self.makeOco(stop_order, oco_id)
        
        self.placeBracketOrder([profit_order, stop_order], contract)



    @pyqtSlot(Contract, str, str)
    def openStairTrade(self, contract, entry_action, bar_type):
        uid = contract.conId
        stair_step = self.stair_tracker.createNewStairstep(uid, bar_type, entry_action, contract)

        if (stair_step is not None):
            order_ids = self.getNextOrderIDs(stair_step['order_count'])

            open_order_id = order_ids.pop(0)
            stop_open = self.createStopOrder(open_order_id, stair_step['entry_action'], stair_step['count'], stair_step['entry_trigger'], stop_limit=stair_step['entry_limit'])
            self.stair_tracker.updateStairprops((uid, bar_type), {'main_id': open_order_id})
            order_list = [stop_open]
            if 'stop_trigger' in stair_step:
                stop_loss_id = order_ids.pop(0)
                self.stair_tracker.updateStairprops((uid, bar_type), {'stop_id': stop_loss_id})
                stop_loss = self.createStopOrder(stop_loss_id, stair_step['exit_action'], stair_step['stop_count'], stair_step['stop_trigger'], stop_limit=stair_step['stop_limit'], parent_id=open_order_id)
                order_list.append(stop_loss)
            
            if 'profit_limit' in stair_step:
                profit_order_id = order_ids.pop(0)
                self.stair_tracker.updateStairprops((uid, bar_type), {'profit_id': profit_order_id})
                profit_limit_order = self.createLimitOrder(profit_order_id, stair_step['exit_action'], stair_step['profit_count'], limit_price=stair_step['profit_limit'], parent_id=open_order_id)
                order_list.append(profit_limit_order)
            
            order_list[-1].transmit = True
            self.placeBracketOrder(order_list, contract)
            self.data_buffers.buffer_updater.connect(self.stair_tracker.bufferUpdate, Qt.QueuedConnection)

        else:
            print("THIS IS NOT A VALID STAIRSTEP")



    @pyqtSlot()
    def killStairTrade(self):

        current_uid = self.stair_tracker.getCurrentKey()
        current_ids = self.stair_tracker.getOrderIdsFor(current_uid)
        # print(f"OrderManager.killStairTrade {current_ids}")
        if len(current_ids) > 0:
            for order_id in current_ids:
                self.ib_request_signal.emit({'type': 'cancelOrder', 'order_id': order_id})


    @pyqtSlot(int, dict)
    def orderEdit(self, order_id, properties):
        # print(f"OrderManager.orderEdit {order_id} {properties}")
        # print(properties)
        if self.open_orders.isOpenOrder(order_id):
            order, contract = self.open_orders.getOrderContract(order_id)

            for prop_type, prop_value in properties.items():
                if prop_type == 'Limit':
                    order.lmtPrice = prop_value
                elif prop_type == 'Trigger':
                    order.auxPrice = prop_value
                elif prop_type == 'Count':
                    order.totalQuantity = prop_value

            order.transmit = True

            request = dict()
            request['type'] = 'placeOrder'
            request['order_id'] = order_id
            request['contract'] = contract
            request['order'] = order
            self.ib_request_signal.emit(request)


class StairManager(QObject):

    _active_stairsteps = dict()
    _locks = dict()
    _current_property_object = dict()
    _current_key = None
    stair_buffer_signal = pyqtSignal(str)
    update_order_signal = pyqtSignal(int, dict)
    step_hist_count = 3

    tracking_updater = pyqtSignal(str, dict)


    def createNewStairstep(self, uid, bar_type, entry_action, contract):
        print("OrderManager.createNewStairstep")
        if self.data_buffers.bufferExists(uid, bar_type):
            
            latest_bars = self.data_buffers.getBarsFromIntIndex(uid, bar_type, -self.step_hist_count)
        
                #we don't want to place a stairstep when it's not actually stepping in the right direction
            if entry_action == Constants.BUY and (latest_bars.iloc[-2][Constants.HIGH] < latest_bars.iloc[-1][Constants.HIGH]):
                print("THATS VERY WEIRD")
                return None
            if entry_action == Constants.SELL and (latest_bars.iloc[-1][Constants.LOW] < latest_bars.iloc[-2][Constants.LOW]):
                print("THATS VERY WEIRD")
                return None        

            self.stair_buffer_signal.emit(Constants.DATA_WILL_CHANGE)
                
            key = (uid, bar_type)
            count = self._current_property_object['count']
            self._current_key = key
            
            self.initializeStairObject(key, {'status': 'Tracking', 'contract': contract, 'bar_type': bar_type, 'count': count, 'entry_action': entry_action})    
            self.updateStairLevels(key)
            entry_trigger, entry_limit = self.getStepEntryPrices(key)
            self.updateStepProperty(key, {'entry_trigger': entry_trigger, 'entry_limit': entry_limit}, False)

            order_count = 1
            
            exit_action = Constants.BUY if entry_action == Constants.SELL else Constants.SELL
            self._active_stairsteps[key]['exit_action'] = exit_action
            if self._current_property_object['stop_loss_on']:                
                stop_level = latest_bars[Constants.LOW].min() if entry_action == Constants.BUY else latest_bars[Constants.HIGH].max()
                stop_trigger, stop_limit = self.getStepStopPrices(key)
                self.updateStepProperty(key, {'stop_count': count, 'stop_trigger': stop_trigger, 'stop_limit': stop_limit}, False)
                order_count += 1
            
            if self._current_property_object['profit_take_on']:

                profit_limit = self.getProfitPrice(key)
                self.updateStepProperty(key, {'profit_count': count, 'profit_limit': profit_limit}, False)
                order_count += 1

            self.updateStepProperty(key, {'order_count': order_count}, False)

            self.stair_buffer_signal.emit(Constants.DATA_STRUCTURE_CHANGED)
            self.stair_buffer_signal.emit(Constants.DATA_DID_CHANGE)
            self._locks[key].unlock()

            self.tracking_updater.emit("Stair Opened", {'uid': uid, 'bar_type': bar_type})
            return self._active_stairsteps[key]
            
            
        print("DO WE END UP HERE?")
        return None
            

    def initializeStairObject(self, key, base_properties):
        self._locks[key] = QReadWriteLock()
        self._locks[key].lockForWrite()
        self._active_stairsteps[key] = base_properties
        self._active_stairsteps[key].update(self._current_property_object)
        self._locks[key].unlock()


    def setDataObject(self, data_object):
        self.data_buffers = data_object


    def cancelByRow(self, row_index):
        to_cancel = list(self._active_stairsteps.keys())[row_index]

        if self._active_stairsteps[key]['status'] == 'Tracking':
            print("We cancel everything")
        else:
            print("We stop tracking")


    def getCurrentKey(self):
        return self._current_key


    def getActiveKeys(self):
        return self._active_stairsteps.keys()


    def getKeyAndTypeForRow(self, row_index):
        stair_index = row_index // 3
        key = list(self._active_stairsteps)[stair_index]
        order_type = row_index % 3
        return key, order_type


    def updateStairprops(self, key, properties):
        self._locks[key].lockForWrite()
        self._active_stairsteps[key].update(properties)
        self._locks[key].unlock()


    def getRowCount(self):
        return len(self._active_stairsteps)*3


    def getNameForRow(self, row):
        
        key, order_type = self.getKeyAndTypeForRow(row)
        
        self._locks[key].lockForRead()
        try:
            if order_type == 0:
                contract = self._active_stairsteps[key]['contract']
                return contract.symbol
            elif order_type == 1:
                return "Stop Loss"
            elif order_type == 2:
                return "Profit Take"
        finally:
            self._locks[key].unlock()


    def getTriggerOffsetForRow(self, row):
        key, order_type = self.getKeyAndTypeForRow(row)

        self._locks[key].lockForRead()
        try:
            if order_type == 0:
                return self._active_stairsteps[key]['entry_trigger_offset']
            elif order_type == 1:
                return self._active_stairsteps[key]['stop_trigger_offset']
            elif order_type == 2:
                return ""
        finally:
            self._locks[key].unlock()


    def getOrderCount(self, row):
        key, order_type = self.getKeyAndTypeForRow(row)

        self._locks[key].lockForRead()
        try:
            if order_type == 0:
                return self._active_stairsteps[key]['count']
            elif order_type == 1:
                if 'stop_count' in self._active_stairsteps[key]:
                    return self._active_stairsteps[key]['stop_count']
                else:
                    return self._active_stairsteps[key]['count']
            elif order_type == 2:
                if 'profit_count' in self._active_stairsteps[key]:
                    return self._active_stairsteps[key]['profit_count']
                else:
                    return self._active_stairsteps[key]['count']
        finally:
            self._locks[key].unlock()


    def getOrderAction(self, row):
        key, order_type = self.getKeyAndTypeForRow(row)

        self._locks[key].lockForRead()
        try:
            if order_type == 0:
                return self._active_stairsteps[key]['entry_action']
            else:
                return self._active_stairsteps[key]['exit_action']
        finally:
            self._locks[key].unlock()


    def getLimitOffsetForRow(self, row):
        key, order_type = self.getKeyAndTypeForRow(row)

        self._locks[key].lockForRead()
        try:
            if order_type == 0:
                return self._active_stairsteps[key]['entry_limit_offset']
            elif order_type == 1:
                return self._active_stairsteps[key]['stop_limit_offset']
            elif order_type == 2:
                if 'profit_type' in self._active_stairsteps[key]:
                    if self._active_stairsteps[key]['profit_type'] == 'Factor':
                        return self._active_stairsteps[key]['profit_factor_level']
                    elif self._active_stairsteps[key]['profit_type'] == 'Offset':
                        return self._active_stairsteps[key]['profit_offset_level']
                    elif self._active_stairsteps[key]['profit_type'] == 'Price':
                        return self._active_stairsteps[key]['profit_price_level']


                self.step_profit_type = 'Factor'
            elif button == self.step_profit_offset_radio and value:
                self.step_profit_type = 'Offset'
            elif button == self.step_profit_price_radio and value:
                self.step_profit_type = 'Price'
        finally:
            self._locks[key].unlock()


    def getPropertyFor(self, colummn_name, row):
        order_type = row % 3

        if colummn_name == 'Count':
            if order_type == 0:
                return 'count'
            elif order_type == 1:
                return 'stop_count'
            elif order_type == 2:
                return 'profit_count'
        elif colummn_name == 'Trigger':
            if order_type == 0:
                return 'entry_trigger_offset'
            elif order_type == 1:
                return 'stop_trigger_offset'
            elif order_type == 2:
                return ""
        elif colummn_name == 'Limit':
            if order_type == 0:
                return 'entry_limit_offset'
            elif order_type == 1:
                return 'stop_limit_offset'
            elif order_type == 2:
                self._locks[key].lockForRead()
                try:
                    if 'profit_type' in self._active_stairsteps[key]:
                        if self._active_stairsteps[key]['profit_type'] == 'Factor':
                            return 'profit_factor_level'
                        elif self._active_stairsteps[key]['profit_type'] == 'Offset':
                            return 'profit_offset_level'
                        elif self._active_stairsteps[key]['profit_type'] == 'Price':
                            return 'profit_price_level'
                finally:
                    self._locks[key].unlock()


    def adjustStairTradeIfNeeded(self, key):
        # print("OrderManager.adjustStairTradeIfNeeded")
        if key in self._active_stairsteps:

            self._locks[key].lockForRead()
            stair_status = self._active_stairsteps[key]['status']
            self._locks[key].unlock()

            updated_orders = dict()

            if stair_status == 'Tracking':
                self.updateStairLevels(key)
                updated_orders.update(self.getUpdatedEntryIfNeeded(key))
            
            if (stair_status == 'Tracking') or (stair_status == 'Opened'):
                if 'stop_id' in self._active_stairsteps[key]:
                    updated_orders.update(self.getUpdateStopLossIfNeeded(key))
                if 'profit_id' in self._active_stairsteps[key]:
                    updated_orders.update(self.getUpdatedProfitOrderIfNeeded(key))

            for order_id, new_props in updated_orders.items():
                self.update_order_signal.emit(order_id, new_props)

            self._locks[key].unlock()


    def updateStairLevels(self, key):
        self._locks[key].lockForWrite()

        if self._active_stairsteps[key]['status'] == "Tracking":
            latest_bars = self.data_buffers.getBarsFromIntIndex(*key, -self.step_hist_count)

            if self._active_stairsteps[key]['entry_action'] == Constants.BUY:
                entry_level = latest_bars.iloc[-2][Constants.HIGH]
                stop_level = latest_bars[Constants.LOW].min()
            elif self._active_stairsteps[key]['entry_action'] == Constants.SELL:
                entry_level = latest_bars.iloc[-2][Constants.LOW]
                stop_level = latest_bars[Constants.HIGH].max()
                
            self._active_stairsteps[key]['entry_level'] = entry_level
            self._active_stairsteps[key]['stop_level'] = stop_level

        self._locks[key].unlock()


    # @lockForRead
    def getUpdatedEntryIfNeeded(self, key):
        entry_trigger, entry_limit = self.getStepEntryPrices(key)

        self._locks[key].lockForWrite()
        try:        
            new_props = dict()
            if (entry_trigger != self._active_stairsteps[key]['entry_trigger']):
                new_props['Trigger'] = entry_trigger
                self._active_stairsteps[key]['entry_trigger'] = entry_trigger

            if (entry_limit != self._active_stairsteps[key]['entry_limit']):
                new_props['Limit'] = entry_limit
                self._active_stairsteps[key]['entry_limit'] = entry_limit
                
            if len(new_props) > 0:
                return {self._active_stairsteps[key]['main_id']: new_props}
            else:
                return {}
        finally:
            self._locks[key].unlock()
    

    @lockForRead
    def getStepEntryPrices(self, key):
        entry_trigger = self._active_stairsteps[key]['entry_level'] + self._active_stairsteps[key]['entry_trigger_offset']
        entry_limit = entry_trigger + self._active_stairsteps[key]['entry_limit_offset']
        return entry_trigger, entry_limit


    # @lockForRead
    def getUpdateStopLossIfNeeded(self, key):
        stop_trigger, stop_limit = self.getStepStopPrices(key)
            
        self._locks[key].lockForWrite()
        try:
            new_props = dict()
            if (stop_trigger != self._active_stairsteps[key]['stop_trigger']):
                self._active_stairsteps[key]['stop_trigger'] = stop_trigger
                new_props['Trigger'] = self._active_stairsteps[key]['stop_trigger']

            if (stop_limit != self._active_stairsteps[key]['stop_limit']):
                self._active_stairsteps[key]['stop_limit'] = stop_limit
                new_props['Limit'] = self._active_stairsteps[key]['stop_limit']
            
            if len(new_props) > 0:
                return {self._active_stairsteps[key]['stop_id']: new_props}
            else:
                return {}
        finally:
            self._locks[key].unlock()

    
    @lockForRead
    def getStepStopPrices(self, key):
        stop_trigger = self._active_stairsteps[key]['stop_level'] + self._active_stairsteps[key]['stop_trigger_offset']
        stop_limit = stop_trigger + self._active_stairsteps[key]['stop_limit_offset']
        return stop_trigger, stop_limit


    def getUpdatedProfitOrderIfNeeded(self, key):
        profit_limit = self.getProfitPrice(key)
            
        self._locks[key].lockForWrite()
        try:
            if profit_limit != self._active_stairsteps[key]['profit_limit']:
                self._active_stairsteps[key]['profit_limit'] = profit_limit
                return {self._active_stairsteps[key]['profit_id'], {'Limit': self._active_stairsteps[key]['profit_limit']}}
            return {}
        finally:
            self._locks[key].unlock()


    @lockForRead
    def getProfitPrice(self, key):
        print("OrderManager.getProfitPrice")
        entry_action = self._active_stairsteps[key]['entry_action']
        level = self._active_stairsteps[key]['entry_level']
        stop_level = self._active_stairsteps[key]['stop_level']
        if self._active_stairsteps[key]['profit_type'] == "Factor":
            return level + (level - stop_level) * self._active_stairsteps[key]['profit_factor_level']
        elif self._active_stairsteps[key]['profit_type'] == "Price":
            return self._active_stairsteps[key]['profit_price_level']
        elif self._active_stairsteps[key]['profit_type'] == "Offset":
            if entry_action == Constants.BUY:
                return level + self._active_stairsteps[key]['profit_offset_level']
            elif entry_action == Constants.SELL:
                return level - self._active_stairsteps[key]['profit_offset_level']
    

    @lockForRead
    def getOrderIdsFor(self, key):
        current_stair = self._active_stairsteps[key]

        stair_ids = [current_stair['main_id']]
        if 'stop_id' in current_stair:
            stair_ids.append(current_stair['stop_id'])
        if 'profit_id' in current_stair:
            stair_ids.append(current_stair['profit_id'])

        return stair_ids

    
    @pyqtSlot(tuple, dict)
    def updateStepProperty(self, key, new_properties, trigger_adjustment=True):
        self._locks[key].lockForRead()
        self._active_stairsteps[key].update(new_properties)
        self._locks[key].unlock()
        if trigger_adjustment:
            self.adjustStairTradeIfNeeded(key)
    

    @pyqtSlot(dict)
    def updateCurrentStepProperty(self, new_property):
        # print(f"OrderManager.updateCurrentStepProperty {new_property}")
        self._current_property_object.update(new_property)
        if (self._current_key is not None) and (self._current_key in self._active_stairsteps):
            self.updateStepProperty(self._current_key, self._current_property_object)
        

    @pyqtSlot(str, dict)
    def bufferUpdate(self, signal, sub_signal):
        if signal == Constants.HAS_NEW_DATA:
            for key in itertools.product([sub_signal['uid']], sub_signal['bars']):
                if (key in self._active_stairsteps):
                    self.adjustStairTradeIfNeeded(key)


    def removeStairstepForKey(self, key):
        self.stair_buffer_signal.emit(Constants.DATA_WILL_CHANGE)
        self._locks[key].lockForWrite()
        del self._active_stairsteps[key]
        self._locks[key].unlock()
        del self._locks[key]
        self.stair_buffer_signal.emit(Constants.DATA_STRUCTURE_CHANGED)
        self.stair_buffer_signal.emit(Constants.DATA_DID_CHANGE)
        self.tracking_updater.emit("Stair Killed", {'uid': key[0], 'bar_type': key[1]})


    @pyqtSlot(int, dict)
    def orderUpdate(self, order_id, detail_object):
        # print(f"StairManager.orderUpdate {detail_object['status']} {detail_object.keys()}")
        # print(f"For {order_id} we get an update of")
        # print(detail_object)
        status = detail_object['status']

        stair_keys = list(self._active_stairsteps.keys())
        for key in stair_keys:
            self._locks[key].lockForRead()
            main_order_id = self._active_stairsteps[key]['main_id']
            self._locks[key].unlock()
            
            if (main_order_id == order_id):
                if (status == "Cancelled") or (status == "Filled"):
                    self.removeStairstepForKey(key)
                    



