from ibapi.order import Order
from ibapi.contract import Contract

from dataHandling.Constants import Constants

class StrategyTrader:



	# def evaluateNewData(self, strategy_processor):
	# 	for trade_index in range(len(strategy_processor.trades):
	# 		self.processTrade(strategy_processor.trades[trade_index])
	# 		del strategy_processor.trades[trade_index]
	
	def getContractForUID(self, selected_key):
		contract = Contract()
		contract.symbol = self.stock_list[selected_key][Constants.SYMBOL]
		contract.secType = Constants.STOCK
		contract.conId = selected_key
		contract.exchange = "SMART"
		return contract


	def placeOrder(self):
		print(3413)
    # action = self.action_type
    # contract = self.getCurrentContract()
    # id_count = 1
    # if self.stop_loss_on: id_count += 1
    # if self.profit_take_on: id_count += 1
    # order_ids = self.trade_manager.getNextOrderIDs(count=id_count)

    # quantity = self.count_field.value()
    # limit_price = self.limit_field.text()

    # primary_id = order_ids.pop(0)
    # order_set = [self.createBaseOrder(primary_id, action, quantity, limit_price)]

    # if self.profit_take_on:
    #     profit_take = self.profit_take_field.text()

    #     order_set += [self.createProfitTake(order_ids.pop(0), action, quantity, profit_take, primary_id)]


    # if self.stop_loss_on:
    #     stop_trigger = self.stop_trigger_field.text()
    #     stop_limit = self.stop_limit_field.text()

    #     if self.stop_limit_on:
    #         order_set += [self.createStopOrder(order_ids.pop(0), action, quantity, stop_trigger, primary_id, stop_limit=stop_limit)]
    #     else:
    #         order_set += [self.createStopOrder(order_ids.pop(0), action, quantity, stop_trigger, primary_id, stop_limit=None)]
    

    # for order in order_set: 
    #     print(f"{order.orderId}: {order.action}, {order.orderType}")
    # order_set[-1].transmit = True

    # last_order = order_set[-1]
    # print(f"{last_order.orderId}: {last_order.action}, {last_order.orderType}")
    
    # self.trade_manager.placeBracketOrder(order_set, contract)


	def triggerOrder(self):
		print(123)

	def createLimitBuyOrder(self, order_id, quantity, limit_price):
		return self.createLimitOrder(self, order_id, "BUY", quantity, limit_price)


	def createLimitSellOrder(self, order_id, quantity, limit_price):
		return self.createLimitOrder(self, order_id, "SELL", quantity, limit_price)


	def createLimitOrder(self, order_id, action, quantity, limit_price):
		limit_order = self.createBaseOrder(order_id, action, quantity)
		limit_order.orderType = "LMT"
		limit_order.lmtPrice = limit_price
		return limit_order


	def createStopOrder(self, order_id, action, stop_price, quantity, stop_limit=None):
		stop_order = self.createBaseOrder(order_id, action, quantity)
		stop_order.auxPrice = stop_price

		if stop_limit is not None:
			stop_order.orderType = "STP LMT"
			stop_order.lmtPrice = stop_limit
		else:
			stop_order.orderType = "STP"


		return stop_order


	def createStopBuyOrder(order_id, stop_price, quantity, stop_limit):
		self.createStopOrder(order_id, "BUY", stop_price, quantity, stop_limit)


	def createStopSellOrder(order_id, stop_price, quantity, stop_limit):
		self.createStopOrder(order_id, "SELL", stop_price, quantity, stop_limit)


	def createBaseOrder(self, order_id, action, quantity):
		print('This is what we are using right?')
		base_order = Order()
		base_order.orderId = order_id
		base_order.action = action
		base_order.totalQuantity = quantity
		base_order.eTradeOnly = ''
		base_order.firmQuoteOnly = ''
		base_order.tif = 'GTC'
		base_order.outsideRth = True

		base_order.transmit = False
		return base_order


	# def createParentOrder(self, order_id, action, quantity, limit_price):
	# 	#This will be our main or "parent" order
	# 	base_order = Order()
	# 	base_order.orderId = order_id
	# 	base_order.action = action
	# 	base_order.orderType = "LMT"
	# 	base_order.totalQuantity = quantity
	# 	base_order.lmtPrice = limit_price
	# 	base_order.eTradeOnly = ''
	# 	base_order.firmQuoteOnly = ''
	# 	#The parent and children orders will need this attribute set to False to prevent accidental executions.
	# 	#The LAST CHILD will have it set to True, 
	# 	base_order.transmit = False
	# 	return base_order


	#def createProfitTake(self, order_id, base_action, quantity, limit_price, parent_id):



	# def createStopOrder(self, order_id, base_action, quantity, stop_price):
	# 	stop_order = Order()
	# 	stop_order.orderId = order_id
	# 	stop_order.action = "SELL" if base_action == "BUY" else "BUY"
	# 	if stop_limit is not None:
	# 		stop_order.orderType = "STP LMT"
	# 		stop_order.lmtPrice = stop_limit
	# 	else:
	# 		stop_order.orderType = "STP"
	# 	stop_order.auxPrice = stop_price
	# 	stop_order.totalQuantity = quantity
	# 	stop_order.parentId = parent_id
	# 	#In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True 
	# 	#to activate all its predecessors
	# 	stop_order.eTradeOnly = ''
	# 	stop_order.firmQuoteOnly = ''

	# 	stop_order.transmit = False
	# 	return stop_order