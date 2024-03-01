from .StrategyTrader import StrategyTrader
from dataHandling.Constants import Constants
import sys
import pandas as pd
from datetime import datetime
import pytz
from dataclasses import dataclass
from generalFunctionality.GenFunctions import greatherThan, smallerThan


@dataclass
class StepObject:
	steps: int
	direction: str
	index: datetime
	level: float
	stop_level: float
	start: float


@dataclass
class ReversalObject:
	index: datetime
	direction: str
	level: float
	stop_level: float


class StairStrategy(StrategyTrader):

	stair_threshold = 5

	open_limit = False
	stop_limit = False

	up_step_objects = dict()
	down_step_objects = dict()
	top_reversals = dict()
	bottom_reversals = dict()

	active_stairsteps = dict()
	active_reversals = dict()


	def __init__(self, order_manager, live_buffer, stock_list):
		self.order_manager = order_manager
		self.live_buffer = live_buffer
		self.stock_list = stock_list


	def performPreprocessing(self, stock_buffers, sector_buffers, sector_list):
		daily_stock_rsis = self.getStockRSIs(stock_buffers)
		daily_sector_rsis = self.getStockRSIs(sector_buffers)
		stock_volatilities = self.getVolatilities(stock_buffers)
		sector_volatilities = self.getVolatilities(sector_buffers)

		key_for_spy = next(key for key, val in sector_list.items() if val.get('symbol') == 'SPY')
		spy_rsi = daily_sector_rsis[key_for_spy]
		key_for_qqq = next(key for key, val in sector_list.items() if val.get('symbol') == 'QQQ')
		qqq_rsi = daily_sector_rsis[key_for_qqq]
		key_for_iwm = next(key for key, val in sector_list.items() if val.get('symbol') == 'IWM')
		iwm_rsi = daily_sector_rsis[key_for_iwm]

		self.base_vars = dict()
		for uid in daily_stock_rsis.keys():
			daily_volatility = stock_volatilities[uid]
			daily_rsi = daily_stock_rsis[uid]

			self.base_vars[uid] = {"Prior Volatility": daily_volatility, "Daily RSI": daily_rsi, "SPY Daily RSI": spy_rsi, "QQQ Daily RSI": qqq_rsi, "IWM Daily RSI": iwm_rsi} #, "IWM/SPY Daily RSI": , "QQQ/SPY Daily RSI": , "IWM/QQQ Daily RSI":}

		print(self.base_vars)


	def getFeatureColumns(self, strategy):
		general_attributes = ['Stop Loss', 'Prior Volatility', 'Bar RSI', 'Daily RSI', 'Hourly RSI', 'QQQ Daily RSI', 'SPY Daily RSI', 'IWM/SPY Daily RSI', 'QQQ/SPY Daily RSI', 'IWM/QQQ Daily RSI', 'Day Move', 'Pre Move']
		if strategy == Constants.UP_STEPS or strategy == Constants.DOWN_STEPS:
			return general_attributes + ['Steps', 'Stair Run']
		elif strategy == Constants.BULL_BARS or strategy == Constants.BEAR_BARS:
			return general_attributes + ['Count']
		elif strategy == Constants.TOP_REVERSAL or strategy == Constants.BOTTOM_REVERSAL:
			return general_attributes + ['Peak Move']


	def getVolatilities(self, stock_buffers):
		volatility_buffer = dict()
		for (uid, bar_type), stock_buffer in stock_buffers.items():
			#if bar_type == '15 mins':
			volatility_buffer[uid] = self.getPreviousDayVolatility(stock_buffer)

		return volatility_buffer


	def getStockRSIs(self, stock_buffers):
		rsi_buffer = dict()
		for (uid, bar_type), stock_buffer in stock_buffers.items():
			if bar_type == '1 day':
				rsi_buffer[uid] = self.getPreviousDayRSI(stock_buffer)

		return rsi_buffer


	def getPreviousDayRSI(self, stock_buffer):
		ny_tz = pytz.timezone('America/New_York')
		yesterday = pd.Timestamp.now(tz=ny_tz).normalize() - pd.DateOffset(days=1)

		previous_rsi = stock_buffer['rsi'].asof(yesterday)

		return previous_rsi


	def getPreviousDayVolatility(self, buffer):
		return 0.50


	def performLiveProcessing(self, strategies, keys=None):
		#if 'up_steps' in strategies:
		self.countUpSteps(keys)
	#	if 'down_steps' in strategies:
		self.countDownSteps(keys)
#		if 'top_reversal' in strategies:
		self.getReversals(keys)
#		if 'bottom_reversal' in strategies:

		self.live_buffer.updateLiveStockFeatures(keys)
		# if '' in strategies:
		# 	self.getTopReversals(keys)
		# 	self.getBottomReversals(keys)


	def makeTrades(self):
		for uid in self.stock_list.keys():

			if self.up_step_objects[uid] is not None and self.checkUpStepTrade(uid):
				if not self.isOpenStairstep(uid):
					self.openStairstepTrade(uid, self.up_step_objects[uid])
				else:
					self.adjustOpenStairstepIfNeeded(uid, self.up_step_objects[uid])
			else:
				if self.isOpenStairstep(uid): self.cancelStairstepIfNeeded(uid)


			if self.down_step_objects[uid] is not None and self.checkDownStepTrade(uid):
				if not self.isOpenStairstep(uid):
					self.openStairstepTrade(uid, self.down_step_objects[uid])
				else:
					self.adjustOpenStairstepIfNeeded(uid, self.down_step_objects[uid])
			else:
				if self.isOpenStairstep(uid): self.cancelStairstepIfNeeded(uid)


			if self.top_reversals[uid] is not None and self.checkTopRevTrade(uid):
				if not self.isOpenReversalTrade(uid):
					self.openReversalTrade(uid, self.top_reversals[uid])
				else:
					self.adjustOpenReversalIfNeeded(uid, self.top_reversals[uid])
			else:
				if self.isOpenReversalTrade(uid): self.cancelReversalIfNeeded(uid)


			if self.bottom_reversals[uid] is not None and self.checkBottomRevTrade(uid):
				if not self.isOpenReversalTrade(uid):
					self.openReversalTrade(uid, self.bottom_reversals[uid])
				else:
					self.adjustOpenReversalIfNeeded(uid, self.bottom_reversals[uid])
			else:
				if self.isOpenReversalTrade(uid): self.cancelReversalIfNeeded(uid)


	def checkUpStepTrade(self, uid):
		current_attr = self.up_step_objects[uid]
		live_attrs = self.live_buffer.getLiveAttributes(uid)
		#comb_dict = 
		#print()
		return True

	
	def checkDownStepTrade(self, uid):
		self.down_step_objects[uid]
		live_attrs = self.live_buffer.getLiveAttributes(uid)
		return True


	def checkTopRevTrade(self, uid):
		self.top_reversals[uid]
		live_attrs = self.live_buffer.getLiveAttributes(uid)
		return True

	
	def checkBottomRevTrade(self, uid):
		self.bottom_reversals[uid]
		live_attrs = self.live_buffer.getLiveAttributes(uid)
		return True



	def cancelStairstepIfNeeded(self, uid):

		self.order_manager.placeBracketOrder([open_order, close_stop], contract)



	def adjustOpenStairstepIfNeeded(self, uid, level, stop_level):
		if level != self.active_stairsteps[uid]['level'] or stop_level != self.active_stairsteps[uid]['stop_level']:
			self.active_stairsteps[uid]['level'] = level
			self.active_stairsteps[uid]['stop_level'] = stop_level
			contract = self.getContractForUID(uid)
			
			open_order_id = self.active_stairsteps[uid]['main_id']
			open_order = self.createStopOrder(open_order_id, "SELL", level-0.01, 100, stop_limit=level-0.03)
			
			stop_order_id = self.active_stairsteps[uid]['stop_id']
			close_stop = self.createStopOrder(stop_order_id, "BUY", stop_level+0.01, 100, stop_limit=stop_level+0.03)
			close_stop.transmit = True
			
			self.order_manager.placeBracketOrder([open_order, close_stop], contract)


	def openTrade(self, uid, trade_object):

		contract = self.getContractForUID(uid)

		if trade_object.direction == "up" or trade_object.direction == "top":
			entry_action = "SELL"
			exit_action = "BUY"
		elif trade_object.direction == "down" or trade_object.direction == "bottom":
			entry_action = "BUY"
			exit_action = "SELL"

		[open_order_id, stop_order_id, profit_order_id] = self.order_manager.getNextOrderIDs(count=3)
		stop_open = self.createStopOrder(open_order_id, entry_action, level, 100)
		
		stop_loss = self.createStopOrder(stop_order_id, exit_action, stop_level, 100, stop_limit=stop_level)
		stop_loss.parentId = open_order_id

		profit_level = level - (stop_level - level) * 4
		limit_profit = self.createLimitOrder(profit_order_id, exit_action, 100, limit_price=profit_level)
		limit_profit.parentId = open_order_id
		limit_profit.transmit = True

		self.order_manager.placeBracketOrder([stop_open, stop_loss, limit_profit], contract)
		
		self.active_stairsteps[uid] = {'main_id': open_order_id, 'stop_id': stop_order_id, 'direction': trade_object.direction, 'profit_id': stop_order_id, 'level': level, 'stop_level': stop_level}


	def isOpenStairstep(self, uid):
		return uid in self.active_stairsteps


	def adjustOpenReversalIfNeeded(self, uid, level, stop_level):
		trade_id = self.active_reversals[uid]
		self.adjustTradeIfNeeded(trade_id, self.active_reversals[uid])

	def adjustTradeIfNeeded(self, uid, trade_object):
		if level != self.active_stairsteps[uid]['level'] or stop_level != self.active_stairsteps[uid]['stop_level']:
			self.active_stairsteps[uid]['level'] = level
			self.active_stairsteps[uid]['stop_level'] = stop_level
			contract = self.getContractForUID(uid)
			
			open_order_id = self.active_stairsteps[uid]['main_id']
			open_order = self.createStopOrder(open_order_id, "SELL", level-0.01, 100, stop_limit=level-0.03)
			
			stop_order_id = self.active_stairsteps[uid]['stop_id']
			close_stop = self.createStopOrder(stop_order_id, "BUY", stop_level+0.01, 100, stop_limit=stop_level+0.03)
			close_stop.transmit = True
			
			self.order_manager.placeBracketOrder([open_order, close_stop], contract)



	def isOpenReversalTade(self, uid):
		return uid in self.active_reversals


	def countUpSteps(self, keys):
		self.up_step_objects = self.countSteps(keys, Constants.LOW, Constants.HIGH, greatherThan)


	def countDownSteps(self, keys):
		self.down_step_objects = self.countSteps(keys, Constants.HIGH, Constants.LOW, smallerThan)


	def countSteps(self, keys, main_level, break_level, comparison):

		tail_count = 20
		step_objects = dict()

		if keys is None:
			keys = self.live_buffer.short_term_buffers.keys()

		for uid in keys:
			stock_df = self.live_buffer.short_term_buffers[uid]
			level_series = stock_df[main_level].tail(tail_count)
			level_selection = comparison(level_series.diff(), 0)
			
			step_count = level_selection.cumsum()
			groups = step_count.mask(~level_selection).ffill(downcast='int')
			
				# Get the last group and its size (number of consecutive True values)
			last_group = groups.iloc[-1]
			step_count = len(groups[groups == last_group]) + 1
		   
			stair_cap = stock_df[break_level].tail(step_count).max()
			stair_start = stock_df[main_level].tail(step_count).min()
			entry_level = level_series.iloc[-1]

			if step_count > 5:
				print(f"Are these correct? SC: {step_count}, P:{stair_cap}, S:{stair_start}, E:{entry_level}")
				step_objects[uid] = StepObject(direction='up', index=stock_df.index[-1], steps=step_count, level=entry_level, stop_level=stair_cap, start=stair_start)
			else:
				step_objects[uid] = None
		return step_objects


	def getReversals(self, keys):

		tail_count = 4

		if keys is None:
			keys = self.live_buffer.short_term_buffers.keys()

		for uid in keys:
			stock_df = self.live_buffer.short_term_buffers[uid]
			tail_values = stock_df.tail(25)
			rsi_values = tail_values['rsi']
			
			print(rsi_values)
			if (rsi_values[-2]) > 60 and ((rsi_values[-2] > rsi_values[-3]) and (rsi_values[-2] > rsi_values[-1])):
				self.top_reversals[uid] = ReversalObject(index=stock_df.index[-1], direction='Top', level=tail_values[Constants.CLOSE].iloc[-1], stop_level=tail_values[Constants.HIGH].iloc[-2])
				print(f'top_reversal')
			else:
				self.top_reversals[uid] = None

			if (rsi_values[-2]) < 40 and ((rsi_values[-2] < rsi_values[-3]) and (rsi_values[-2] < rsi_values[-1])):
				self.bottom_reversals[uid] = ReversalObject(index=stock_df.index[-1], direction='Bottom', level=tail_values[Constants.CLOSE].iloc[-1], stop_level=tail_values[Constants.LOW].iloc[-2])
				print(f'bottom_reversal')



			