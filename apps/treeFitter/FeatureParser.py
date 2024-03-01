import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys
from datetime import datetime, timedelta
from dataHandling.Constants import Constants
import pytz
import timeit
import time
from generalFunctionality.GenFunctions import calculateRSI, addRSIsEMAs, greatherThan, smallerThan
		

class FeatureParser:

	min_steps = 5
	inside_bar_threshold = 1
	rev_counter = 0
	rsi_counter = 0

	low_rsi_threshold = 40
	high_rsi_threshold = 60

	feature_frames = dict()


	def __init__(self):
		self.feature_frames[Constants.UP_STEPS] = dict()
		self.feature_frames[Constants.DOWN_STEPS] = dict()

		self.feature_frames[Constants.BULL_BARS] = dict()
		self.feature_frames[Constants.BEAR_BARS] = dict()

		self.feature_frames[Constants.TOP_REVERSAL] = dict()
		self.feature_frames[Constants.BOTTOM_REVERSAL] = dict()


	def calculateMaxUpMove(self, day_frame_1m, index, pattern_level, break_level):
		trigger_hit = False
		high = None
		for sub_index, sub_row in day_frame_1m.loc[day_frame_1m.index >= index].iterrows():
			if not trigger_hit:
				if sub_row[Constants.HIGH] > pattern_level:
					high = sub_row[Constants.HIGH]
					trigger_hit = True
			if trigger_hit:
				if sub_row[Constants.LOW] < break_level:
					break
				if sub_row[Constants.HIGH] > high:
					high = sub_row[Constants.HIGH]

		return high


	def getStepFrames(self):
		return self.returnFrames([Constants.UP_STEPS, Constants.DOWN_STEPS])


	def returnFrames(self, strategy_types):
		frames = []
		for index, strategy in enumerate(strategy_types):
			feature_frame_comb = pd.concat(self.feature_frames[strategy].values(), ignore_index=True)
			feature_frame_comb = feature_frame_comb.dropna()
			frames.append(feature_frame_comb)
		
		return frames


	def getInsideFrames(self):
		return self.returnFrames([Constants.BULL_BARS, Constants.BEAR_BARS])


	def getReversalFrames(self):
		return self.returnFrames([Constants.TOP_REVERSAL, Constants.BOTTOM_REVERSAL])


	def setTargetBartype(self, bar_type):
		self.target_bar_type = bar_type


	def generateStairSteps(self, uid, buffers):
		
		for bar_type in buffers.keys():
			if self.target_bar_type == bar_type:
				current_frame = buffers[self.target_bar_type]
				one_min_frame = buffers["1 min"]
				
				self.feature_frames[Constants.UP_STEPS][uid] = self.getUpstepFrame(current_frame, one_min_frame)
				self.feature_frames[Constants.DOWN_STEPS][uid] = self.getDownstepFrame(current_frame, one_min_frame)

				# print('We have some up steps')
				# print(self.feature_frames[Constants.UP_STEPS][uid].tail(30))
				# print('and some down steps')
				# print(self.feature_frames[Constants.DOWN_STEPS][uid].tail(30))
			

	def generateInsideBars(self, uid, buffers, clear_old_data=False):
		
		#is this even being used?
		if clear_old_data:
			self.insideBarBulls = dict()
			self.insidebar_bears = dict()

		for bar_type in buffers.keys():
			if self.target_bar_type == bar_type:
				current_frame = buffers[self.target_bar_type]
				one_min_frame = buffers["1 min"]
				
				self.feature_frames[Constants.BULL_BARS][uid], self.feature_frames[Constants.BEAR_BARS][uid] = self.getInsideBars(current_frame, one_min_frame)


	def generateRsiReversals(self, uid, buffers):
		
		for bar_type in buffers.keys():
			if self.target_bar_type == bar_type:
				current_frame = buffers[self.target_bar_type]
				one_min_frame = buffers["1 min"]

				one_min_by_date = self.splitFrameByDate(one_min_frame)
				self.feature_frames[Constants.TOP_REVERSAL][uid] = self.getTopReversals(current_frame, one_min_by_date)
				self.feature_frames[Constants.BOTTOM_REVERSAL][uid] = self.getBottomReversals(current_frame, one_min_by_date)

				# print('Top reversal')
				# print(self.feature_frames[Constants.TOP_REVERSAL][uid].dropna().tail(30))
				# print('Bottom reversal')
				# print(self.feature_frames[Constants.BOTTOM_REVERSAL][uid].dropna().tail(30))



	def getBottomReversals(self, current_frame, one_min_by_date):
		regular_hours = current_frame.between_time('9:30', '15:59')
		reversal = (regular_hours['rsi'].shift(1) < self.low_rsi_threshold) & ((regular_hours['rsi'].shift(2) > regular_hours['rsi'].shift(1)) & (regular_hours['rsi'] > regular_hours['rsi'].shift(1)))
		break_attr = Constants.LOW
		move_attr = Constants.HIGH
		cap_function = np.min
		move_calc = lambda row: self.calcReversalMove(row, one_min_by_date, break_attr, move_attr=move_attr, break_check=smaller_than, move_extreme=np.max)
		return self.getRsiReversals(regular_hours, move_calc, reversal, cap_attr=Constants.LOW, cap_function=cap_function)


	def getTopReversals(self, current_frame, one_min_by_date):
		regular_hours = current_frame.between_time('9:30', '15:59')
		reversal = (regular_hours['rsi'].shift(1) > self.high_rsi_threshold) & ((regular_hours['rsi'].shift(2) < regular_hours['rsi'].shift(1)) & (regular_hours['rsi'] < regular_hours['rsi'].shift(1)))
		break_attr = Constants.HIGH
		move_attr = Constants.LOW
		cap_function = np.max
		move_calc = lambda row: self.calcReversalMove(row, one_min_by_date, break_attr, move_attr=move_attr, break_check=greather_than, move_extreme=np.min)
		return self.getRsiReversals(regular_hours, move_calc, reversal, cap_attr=Constants.HIGH, cap_function=cap_function)


	def getRsiReversals(self, regular_hours, move_calc, reversal_sel, cap_attr, cap_function):
	
		reversal_indices = np.where(reversal_sel)[0]
		
		# Compute the indices for each group of three rows
		grouped_indices = np.column_stack((reversal_indices-2, reversal_indices-1, reversal_indices))
		
		caps = cap_function(regular_hours[cap_attr].values[grouped_indices], axis=1)
		opens = regular_hours[Constants.OPEN].values[grouped_indices[:, 0]]
		closes = regular_hours[Constants.CLOSE].values[grouped_indices[:, -1]]
		timestamps = regular_hours.index[reversal_sel]

		result = pd.DataFrame({'Time Index': timestamps, 'Stop Level': caps, 'Start Level': opens, 'Entry Level': closes})

		result['Max Level'] = result.apply(move_calc, axis=1)

		return result


	def calcReversalMove(self, row, one_min_by_date, break_attr, move_attr, break_check, move_extreme):
		timing_info = ""

		date = row['Time Index'].date()
		self.rev_counter += 1

		if date in one_min_by_date:
			trade_frame = one_min_by_date[date]
			trade_frame = trade_frame.between_time(row['Time Index'].replace(second=1).strftime('%H:%M:%S'), '16:30:00')

			if len(trade_frame) > 0:
				break_level_exceeded = break_check(trade_frame[break_attr], row['Stop Level'])
				if break_level_exceeded.any():
					break_level_hit_id = break_level_exceeded.idxmax()
					between_frame = trade_frame.loc[trade_frame.index <= break_level_hit_id]
					return move_extreme(between_frame[move_attr])
				else:
					return move_extreme(trade_frame[move_attr])


		return None

	def getFrames(self):
		return self.feature_frames

				
	def addFeatures(self, uid,  buffers, sector_buffers, sector_list, feature_selection):

		stock_rsi_on, sector_rsi_on, volatility_rsi_on, stock_move_on = feature_selection

		for strategy, frames in [(key, fs) for key, fs in self.feature_frames.items() if len(fs) > 0]:
			frame = frames[uid]
			print(f"For {strategy}:")
			print(f"We gots for {uid}:")
			if stock_rsi_on:
				frame = self.addRSIFeatures(frame, buffers)
			if sector_rsi_on:
				frame = self.addSectorFeatures(frame, sector_buffers, sector_list)
			if volatility_rsi_on:
				frame = self.addVolatilityFeatures(frame, buffers)
			if stock_move_on:
				frame = self.addMoveData(frame, buffers)
			
			self.feature_frames[strategy][uid] = frame

			pd.set_option('display.max_columns', None)
			pd.set_option('display.width', 1_000)
			
			print(frame.tail(30))
			

	def addRSIFeatures(self, feature_frame, buffers):
		
		current_frame = buffers[self.target_bar_type]
		feature_frame['Bar RSI'] = feature_frame['Time Index'].map(current_frame['rsi'])
		
		day_frame = buffers['1 day']
		normalized_days = feature_frame['Time Index'].dt.normalize()
		feature_frame['Daily RSI'] = normalized_days.map(day_frame['rsi'].shift(1))

		hourly_frame = buffers['1 hour']
		hourly_by_date = self.splitFrameByDate(hourly_frame)
		one_min_frame = buffers["1 min"]
		one_min_by_date = self.splitFrameByDate(one_min_frame)
				
		feature_frame['Hourly RSI'] = feature_frame.apply(self.getPartialHourlyRSI, hourly_by_date=hourly_by_date, one_min_by_date=one_min_by_date, axis=1)
		
		return feature_frame


	def addMoveData(self, feature_frame, buffers):
		
		day_frame = buffers['1 day']
		normalized_days = feature_frame['Time Index'].dt.normalize()
		feature_frame['Previous Close'] = normalized_days.map(day_frame[Constants.CLOSE].shift(1))
		feature_frame['Day Open'] = normalized_days.map(day_frame[Constants.OPEN])
		
		return feature_frame


	def addSectorFeatures(self, feature_frame, sector_buffers, sector_list):
		# print(sector_list)
		key_for_qqq = next(key for key, val in sector_list.items() if val.get('symbol') == 'QQQ')
		key_for_spy = next(key for key, val in sector_list.items() if val.get('symbol') == 'SPY')
		key_for_iwm = next(key for key, val in sector_list.items() if val.get('symbol') == 'IWM')

		normalized_dates = feature_frame['Time Index'].dt.normalize()
		shifted_rsi_qqq = sector_buffers[key_for_qqq, '1 day']['rsi'].shift(1)
		feature_frame['QQQ Daily RSI'] = normalized_dates.map(shifted_rsi_qqq)

		shifted_rsi_spy = sector_buffers[key_for_spy, '1 day']['rsi'].shift(1)
		feature_frame['SPY Daily RSI'] = normalized_dates.map(shifted_rsi_spy)

		shifted_rsi_iwm = sector_buffers[key_for_iwm, '1 day']['rsi'].shift(1)
		feature_frame['IWM Daily RSI'] = normalized_dates.map(shifted_rsi_iwm)

		qqq_spy_closes = sector_buffers[key_for_qqq, '1 day'][Constants.CLOSE]/sector_buffers[key_for_spy, '1 day'][Constants.CLOSE]
		qqq_spy_volume = sector_buffers[key_for_qqq, '1 day'][Constants.VOLUME]*sector_buffers[key_for_spy, '1 day'][Constants.VOLUME]
		qqq_spy_frame = pd.DataFrame({Constants.CLOSE: qqq_spy_closes, Constants.VOLUME: qqq_spy_volume})
		qqq_spy_frame = addRSIsEMAs(qqq_spy_frame)
		shifted_rsi_qqq_spy = qqq_spy_frame['rsi'].shift(1)
		feature_frame['QQQ/SPY Daily RSI'] = normalized_dates.map(shifted_rsi_qqq_spy)

		iwm_qqq_closes = sector_buffers[key_for_iwm, '1 day'][Constants.CLOSE]/sector_buffers[key_for_qqq, '1 day'][Constants.CLOSE]
		iwm_qqq_volume = sector_buffers[key_for_iwm, '1 day'][Constants.VOLUME]*sector_buffers[key_for_qqq, '1 day'][Constants.VOLUME]
		iwm_qqq_frame = pd.DataFrame({Constants.CLOSE: iwm_qqq_closes, Constants.VOLUME: iwm_qqq_volume})
		iwm_qqq_frame = addRSIsEMAs(iwm_qqq_frame)
		shifted_rsi_iwm_qqq = iwm_qqq_frame['rsi'].shift(1)
		feature_frame['IWM/QQQ Daily RSI'] = normalized_dates.map(shifted_rsi_iwm_qqq)

		iwm_spy_closes = sector_buffers[key_for_iwm, '1 day'][Constants.CLOSE]/sector_buffers[key_for_spy, '1 day'][Constants.CLOSE]
		iwm_spy_volume = sector_buffers[key_for_iwm, '1 day'][Constants.VOLUME]*sector_buffers[key_for_spy, '1 day'][Constants.VOLUME]
		iwm_spy_frame = pd.DataFrame({Constants.CLOSE: iwm_spy_closes, Constants.VOLUME: iwm_spy_volume})
		iwm_spy_frame = addRSIsEMAs(iwm_spy_frame)
		shifted_rsi_spy_qqq = iwm_spy_frame['rsi'].shift(1)
		feature_frame['IWM/SPY Daily RSI'] = normalized_dates.map(shifted_rsi_spy_qqq)

		# for frame_by_date
		# self.splitFrameByDate(sector_buffers)
		# feature_frame['sector positive corr'] = normalized_day_befores.apply(
		# feature_frame['sector negative corr'] = normalized_day_befores.apply(
		# feature_frame['sector corr balance'] = normalized_day_befores.apply(

		return feature_frame


		# Assuming sector_data is your dictionary of dataframes
	def getSectorCorrelations(self, sector_buffers):
		# First, we create a new dataframe that will contain the 'Close' prices of each sector

		close_prices = pd.DataFrame()

		# Fill the 'close_prices' dataframe with the close prices of each sector
		for (key, bar_type), buffer in sector_data.items():
			close_prices[sector] = buffer[Constants.CLOSE]

		# Use the pandas .corr() method to compute pairwise correlation of columns, excluding NA/null values.
		correlation_matrix = close_prices.corr()

		# Filter positive and negative correlations
		positive_correlations = correlation_matrix[correlation_matrix > 0]
		negative_correlations = correlation_matrix[correlation_matrix < 0]

		# Calculate average positive and negative correlations
		max_correlation = positive_correlations.mean().max()
		average_negative_correlation = negative_correlations.mean().min()

		# Count of positive and negative correlations
		positive_correlation_count = positive_correlations.count().sum()
		negative_correlation_count = negative_correlations.count().sum()
		difference = np.sum(np.abs(positive_correlation_count - negative_correlation_count))
		return max_correlation, min_correlation, difference


	def getPartialHourlyRSI(self, row, hourly_by_date, one_min_by_date):
		start_time = time.time()
		self.rsi_counter += 1
		date = row['Time Index'].date()

		date_time = time.time() - start_time
		start_time = time.time()

		if date in one_min_by_date and date in hourly_by_date:
			day_minute_frame = one_min_by_date[date]
			day_hour_frame = hourly_by_date[date]

			day_min_time = time.time() - start_time
			start_time = time.time()

			hourly_cutoff_frame = day_hour_frame[day_hour_frame.index <= row['Time Index']]
			if len(hourly_cutoff_frame) > 0:

				hourly_cutoff_time = time.time() - start_time
				start_time = time.time()

				last_hourly_idx = row['Time Index'].floor('H')

				last_hourly_time = time.time() - start_time
				start_time = time.time()

				#pd.set_option('display.max_rows', None)
				# pd.set_option('display.width', 1_000)
			
				#TODO, which really is the last bar? Have to take into account bar length like 11:00 5 minute is 11:04 on the 1 minute frame
				minute_bars = day_minute_frame[(day_minute_frame.index >= last_hourly_idx) & (day_minute_frame.index <= row['Time Index'])]

				minute_bars_time = time.time() - start_time
				start_time = time.time()

				
				if len(minute_bars) > 0:
					bar_data = {Constants.LOW: minute_bars[Constants.LOW].min(), Constants.HIGH: minute_bars[Constants.HIGH].max(), Constants.OPEN: minute_bars[Constants.OPEN].iloc[0], Constants.CLOSE: minute_bars[Constants.CLOSE].iloc[-1]}
					
					bar_data_time = time.time() - start_time
					start_time = time.time()

					hourly_cutoff_frame.loc[row['Time Index']] = bar_data

					loc_time = time.time() - start_time
					start_time = time.time()

					rsi = calculateRSI(hourly_cutoff_frame)

					calc_rsi_time = time.time() - start_time

				# if self.rsi_counter < 20:
				# 	print(f"Time Index to date time: {date_time}")
				# 	print(f"Day minute frame time: {day_min_time}")
				# 	print(f"Hourly cutoff frame time: {hourly_cutoff_time}")
				# 	print(f"Last hourly index time: {last_hourly_time}")
				# 	print(f"Minute bars time: {minute_bars_time}")
				# 	print(f"Bar data time: {bar_data_time}")
				# 	print(f"Loc operation time: {loc_time}")
				# 	print(f"Calculate RSI time: {calc_rsi_time}")

					return rsi
		return None


	def addVolatilityFeatures(self, feature_frame, buffers):
		current_frame = buffers[self.target_bar_type]
		# vol_grouped_by_day = current_frame.groupby(current_frame.index.date).apply(self.calculateGKvolatility)
		# realized_volatility = vol_grouped_by_day.apply(lambda x: np.sqrt(np.sum(np.square(x))))

		std_volatility = current_frame.groupby(current_frame.index.date).apply(self.calculateSDvolatility)
		ewma_volatility = std_volatility.ewm(span=3).mean()
		ewma_volatility_shifted = ewma_volatility.shift(1)
		normalized_dates = feature_frame['Time Index'].apply(lambda x: x.date)
		feature_frame['Prior Volatility'] = normalized_dates.map(ewma_volatility_shifted)
		return feature_frame


	def calculateSDvolatility(self, current_frame):
		# Calculate the log returns for high/low and close/open

		#TODO this astype can be removed if we make sure the dtype is set correctly at a prior level
		returns = np.array(current_frame[Constants.CLOSE].astype('float')) / np.array(current_frame[Constants.OPEN].astype('float')) - 1

		# Calculate the volatility using the Garman-Klass estimator
		return returns.std()


	def calculateGKvolatility(self, current_frame):
		# Calculate the log returns for high/low and close/open

		#TODO this astype can be removed if we make sure the dtype is set correctly at a prior level
		hl_log_returns = np.log(np.array(current_frame[Constants.HIGH].astype('float')) / np.array(current_frame[Constants.LOW].astype('float')))
		co_log_returns = np.log(np.array(current_frame[Constants.CLOSE].astype('float')) / np.array(current_frame[Constants.OPEN].astype('float')))

		# Calculate the volatility using the Garman-Klass estimator
		volatility = np.sqrt(0.5 * np.square(hl_log_returns) - (2 * np.log(2) - 1) * np.square(co_log_returns))

		return volatility


	def getInsideBars(self, current_frame, one_min_frame):

		regular_hours = current_frame.between_time('9:30', '15:59')
		#print(regular_hours[[Constants.LOW, Constants.HIGH]].head(30))
		cons_inside_bar = (regular_hours[Constants.LOW].diff() > 0) & (regular_hours[Constants.HIGH].diff() < 0)
		#print(cons_inside_bar.head(30))
			#mark all the transitions from subsequent higher lows and give each group a subsequent number by upping when there is a transition
		transitions = cons_inside_bar.ne(cons_inside_bar.shift())
		inside_bar_bools = (transitions.cumsum())
		inside_bar_groups = inside_bar_bools[cons_inside_bar]
		
		#print(inside_bar_bools.head(30))

			#get stairs as groups
		inside_bars_seq = regular_hours[cons_inside_bar].groupby(inside_bar_groups)

			# get the last and count from each group
		result = inside_bars_seq.agg({Constants.LOW: ['last'], Constants.HIGH: ['last', 'count']}).reset_index(drop=True)
		#print(result.tail(10))
		result.columns = ['Bar Low', 'Bar High', 'Count']
			# Add the index of the last higher close in each group to the result dataframe
		result['Time Index'] = regular_hours[cons_inside_bar].groupby(inside_bar_groups).tail(1).index
		
		#print('does this cut it down a lot?')
		#print(len(result))
		result = result[result['Count'] > self.inside_bar_threshold]
		#print(len(result))

		one_min_by_date = self.splitFrameByDate(one_min_frame)
		result['Max Level'] = result.apply(self.addInsideMove, axis=1, one_min_by_date=one_min_by_date)

		bull_frame = result[result['Max Level'] > result['Bar Low']]
		bull_frame = bull_frame.rename(columns={'Bar High': 'Entry Level', 'Bar Low': 'Stop Level'})

		bear_frame = result[result['Max Level'] < result['Bar High']]
		
		bear_frame = bear_frame.rename(columns={'Bar Low': 'Entry Level', 'Bar High': 'Stop Level'})

		return bull_frame, bear_frame


	def addInsideMove(self, row, one_min_by_date):

		date = row['Time Index'].date()

		if date in one_min_by_date:
			day_frame = one_min_by_date[date]
			day_frame = day_frame.between_time(row['Time Index'].strftime('%H:%M'), '15:59')

			low_exceeded = (day_frame[Constants.LOW] < row['Bar Low'])
			high_exceeded = (day_frame[Constants.HIGH] > row['Bar High'])

			if low_exceeded.any():
				first_low_id = low_exceeded.idxmax()
			else:
				first_low_id = day_frame.index.max()

			if high_exceeded.any():
				first_high_id = high_exceeded.idxmax()
				# print(type(first_high_id))
				# print(type(day_frame.index.max()))
			else:
				first_high_id = day_frame.index.max()
			
			if first_low_id < first_high_id:
				running_frame = day_frame.loc[(day_frame.index >= first_low_id) & (day_frame.index <= first_high_id)]
				return running_frame[Constants.LOW].min()
			else:
				running_frame = day_frame.loc[(day_frame.index >= first_high_id) & (day_frame.index <= first_low_id)]
				return running_frame[Constants.HIGH].max()


	def getUpstepFrame(self, current_frame, one_min_frame):

		pattern_attr = Constants.LOW
		break_attr = Constants.HIGH

		one_min_by_date = self.splitFrameByDate(one_min_frame)	#for efficiency
		get_move = lambda row: self.calcStairBreakMove(row, one_min_by_date, pattern_attr, break_attr, trigger_check=smaller_than, break_check=greather_than, move_extreme=np.min)
		
		def confirms_pattern(low): return low >= 0
		return self.generalizedStairstep(current_frame, 'max', get_move, pattern_attr, break_attr, confirms_pattern)


	def getDownstepFrame(self, current_frame, one_min_frame):
		
		pattern_attr = Constants.HIGH
		break_attr = Constants.LOW

		one_min_by_date = self.splitFrameByDate(one_min_frame)	#for efficiency
		get_move = lambda row: self.calcStairBreakMove(row, one_min_by_date, pattern_attr, break_attr, trigger_check=greather_than, break_check=smaller_than, move_extreme=np.max)
		
		def confirms_pattern(high): return high <= 0
		return self.generalizedStairstep(current_frame, 'min', get_move, pattern_attr, break_attr, confirms_pattern)


	def generalizedStairstep(self, current_frame, extreme, get_move, pattern_attr, break_attr, pattern_check):

		regular_hours = current_frame.between_time('9:30', '16:00')
		cons_step_sel = pattern_check(regular_hours[pattern_attr].diff())

			#mark all the transitions from subsequent higher lows and give each group a subsequent number by upping when there is a transition
		stair_numbering = cons_step_sel.ne(cons_step_sel.shift()).cumsum()
		
			# add the first "step" to the consecutive increments/decrements
		staircase_starts_selection = cons_step_sel.shift(-1) & ~cons_step_sel
		staircase_starts_selection_shifted = staircase_starts_selection.shift(1, fill_value=False)
		stair_numbering.loc[staircase_starts_selection] = stair_numbering.loc[staircase_starts_selection_shifted].values		
		full_stair_selection = cons_step_sel | staircase_starts_selection

		stair_selection = stair_numbering[full_stair_selection]
			#get stairs as groups
		stairs = regular_hours[full_stair_selection].groupby(stair_selection)
					# Get the first and last indices from each group
			# get the last and count from each group
		result = stairs.agg({pattern_attr: ['last', 'count', 'first'], break_attr: [extreme]})
		result.columns = ['Entry Level', 'Steps', 'Start Level', 'Stop Level']


			# Add the index of the last higher close in each group to the result dataframe
		result['Time Index'] = regular_hours[cons_step_sel].groupby(stair_selection).tail(1).index

		result = result[result['Steps'] >= self.min_steps]

		result['Max Level'] = result.apply(get_move, axis=1)
		return result


	def calcStairBreakMove(self, row, one_min_by_date, trigger_attr, break_attr, trigger_check, break_check, move_extreme):
		date = row['Time Index'].date()

		if date in one_min_by_date:
			trade_frame = one_min_by_date[date]
			trade_frame = trade_frame.between_time(row['Time Index'].strftime('%H:%M'), '15:59')

			trigger_exceeded = trigger_check(trade_frame[trigger_attr], row['Entry Level'])	
			trigget_hit_id = trigger_exceeded.idxmax()
			after_trigger_frame = trade_frame.loc[trade_frame.index >= trigget_hit_id]

			break_exceeded = break_check(after_trigger_frame[break_attr], row['Stop Level'])
			if break_exceeded.any():
				break_level_hit_id = break_exceeded.idxmax()
				between_frame = after_trigger_frame.loc[after_trigger_frame.index < break_level_hit_id]
				return move_extreme(between_frame[trigger_attr])
			else:
				return move_extreme(after_trigger_frame[trigger_attr])
		else:
			return None


	def splitFrameByDate(self, data_frame):
		# Normalize index to date
		data_frame['date'] = data_frame.index.normalize().date
		
		# Group by date and convert each group to a separate dataframe
		date_dict = {k: v for k, v in data_frame.groupby('date')}
		
		# Remove the extra 'date' column
		for df in date_dict.values():
			df.drop(columns='date', inplace=True)
		
		return date_dict


	def saveData(self):
		print("FeatureParser.saveData")

		for strategy, frames in self.feature_frames.items():
			for uid in frames.keys():
				frames[uid].to_pickle(Constants.ANAYLIS_RESULTS_FOLDER + 'parsedFrames/' + uid + '_' + self.target_bar_type + '_' + strategy + '.pkl')
						

	def loadData(self, stock_list, strategy_types):
		for strategy in strategy_types:
			for uid in stock_list.keys():
				try:
					self.feature_frames[strategy][uid] = pd.read_pickle(Constants.ANAYLIS_RESULTS_FOLDER + 'parsedFrames/' + uid + '_' + self.target_bar_type + '_' + strategy + '.pkl')
				except:
					print(f"There is no {strategy} frame for {stock_list[uid][Constants.SYMBOL]} ({uid})")
	

