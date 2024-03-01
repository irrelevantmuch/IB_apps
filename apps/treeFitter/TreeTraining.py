from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
from xgboost import XGBRegressor, XGBClassifier
from sklearn.model_selection import GridSearchCV
import numpy as np
import pandas as pd
import seaborn as sns
import pickle
from dataHandling.Constants import Constants


class TreeTraining:

	
	regression_models = dict()	
	classification_models = dict()


	def prepareData(self, data_frame, strategy):

		print(strategy)
		data_frame_norm = self.normalizeData(data_frame, strategy)

		feature_columns = self.getFeatureColumns(strategy)
		target_column = 'Move Run'

		#data_frame_norm = self.standardizeDataframe(data_frame_norm, feature_columns)
		columns = feature_columns + [target_column]
		data = data_frame_norm[feature_columns]
		target_regr = data_frame_norm[target_column]

		target_class = pd.qcut(data_frame_norm[target_column], q=3, labels=False)

		regression_data = self.splitData(data, target_regr)
		classification_data = self.splitData(data, target_class)
		
		
		print(f"The dataset has {len(data)} datapoints")
		return regression_data, classification_data, data_frame_norm, columns


	def splitData(self, data, target):
		x_train, x_test, y_train, y_test = train_test_split(data, target, test_size=0.2)
		return {'data': data, 'target': target, 'x train': x_train, 'y train': y_train, 'x test': x_test, 'y test': y_test}
		

	def getFeatureColumns(self, strategy):
		print(strategy)
		#, 'Stop Loss'
		general_attributes = ['Stop Loss', 'Prior Volatility', 'Bar RSI', 'Daily RSI', 'Hourly RSI', 'QQQ Daily RSI', 'SPY Daily RSI', 'IWM/SPY Daily RSI', 'QQQ/SPY Daily RSI', 'IWM/QQQ Daily RSI', 'Day Move', 'Pre Move']
		if strategy == Constants.UP_STEPS or strategy == Constants.DOWN_STEPS:
			return general_attributes + ['Steps', 'Stair Run']
		elif strategy == Constants.BULL_BARS or strategy == Constants.BEAR_BARS:
			return general_attributes + ['Count']
		elif strategy == Constants.TOP_REVERSAL or strategy == Constants.BOTTOM_REVERSAL:
			return general_attributes + ['Peak Move']


	def plotCorrelations(self, data_frame, columns, strategy):
		
		# compute correlation matrix
		corr_matrix = data_frame[columns].corr()

		plt.figure(figsize=(8, 10))
		sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1)

		plt.title('Correlation of features with the target')
		plt.savefig(Constants.ANAYLIS_RESULTS_FOLDER + 'additionalFigures/corr_heat_' + strategy + '.png')

		# plt.figure(figsize=(8, 10))
		# sns.pairplot(relevant_frame, kind="reg", hue='Steps', palette='hls')
		# plt.savefig('correlation_pairs_fig_' + name + '.png')

		plt.close()


	def standardizeDataframe(self, data_frame, columns):
		for column in columns:
			data_frame[column] = self.standardize(data_frame[column])
		return data_frame


	def runTrainTestLoop(self, feature_frame, model_type):
		regression_data, classification_data, data_frame_norm, columns = self.prepareData(feature_frame, model_type)
			
		self.plotCorrelations(data_frame_norm, columns, model_type)

		# self.regression_models[model_type] = self.fitXGBRegressor(regression_data)
		# self.evaluateRegrModel(self.regression_models[model_type], model_type, regression_data)

		self.classification_models[model_type] = self.fitXGBClassifier(classification_data)
		self.evaluateClassModel(self.classification_models[model_type], model_type, classification_data)


	def fitXGBClassifier(self, data):
		X = data['data']
		y = data['target']

		# param_grid = {
		#     'max_depth': [3, 5],
		#     'learning_rate': [0.05, 0.1],
		#     'n_estimators': [100, 200, 300],
		#     'gamma': [0.001, 0.002]
		# }

		# # Perform grid search
		# grid_search = GridSearchCV(estimator=XGBClassifier(), param_grid=param_grid, cv=4, verbose=10, return_train_score=True, refit=True)
		# grid_search.fit(X, y)
		# Print the best hyperparameters and the corresponding mean cross-validated score
		# print("Best Hyperparameters: ", grid_search.best_params_)
		# print("Best Score: ", grid_search.best_score_)
		# best_p = grid_search.best_params_
		# xgbr_model = XGBClassifier(learning_rate=best_p['learning_rate'], max_depth=best_p['max_depth'], n_estimators=best_p['n_estimators'], gamma=best_p['gamma'])

		xgbr_model = XGBClassifier(learning_rate=0.05, max_depth=4, n_estimators=200)
		xgbr_model.fit(data['x train'], data['y train'])
		


		print(xgbr_model)
		return xgbr_model


	def fitXGBRegressor(self, data):
		X = data['data']
		y = data['target']

		# Define the parameter grid
		# param_grid = {
		#     'max_depth': [3,5],
		#     'learning_rate': [0.05, 0.1],
		#     'n_estimators': [100, 200, 400],
		#     'gamma': [0.001, 0.005]
		# }

		# # Perform grid search
		# grid_search = GridSearchCV(estimator=XGBRegressor(), param_grid=param_grid, cv=4, verbose=10, return_train_score=True, refit=True)
		# grid_search.fit(X, y)
		# # Print the best hyperparameters and the corresponding mean cross-validated score
		# print("Best Hyperparameters: ", grid_search.best_params_)
		# print("Best Score: ", grid_search.best_score_)
		# best_p = grid_search.best_params_
		# xgbr_model = XGBRegressor(learning_rate=best_p['learning_rate'], max_depth=best_p['max_depth'], n_estimators=best_p['n_estimators'], gamma=best_p['gamma'])

		# xgbr_model = XGBRegressor()
		xgbr_model = XGBRegressor(learning_rate=0.05, max_depth=3, n_estimators=200)
		xgbr_model.fit(data['x train'], data['y train'])
		
		print(xgbr_model)
		return xgbr_model

	def resultTransform(self, result):
		#how does this type get to be object?
		return np.log(result.astype('float'))*100

		#x = abs(result)-1
		# return np.log(x+1) / np.log(5)


	def resultInverse(self, y):
		return y
		#return 5**(y) - 1


	def normalizeData(self, data_frame, strategy):
		data_frame['Move Run'] = self.resultTransform(data_frame['Max Level']/data_frame['Entry Level'])
		data_frame['Stop Loss'] = self.resultTransform(data_frame['Stop Level']/data_frame['Entry Level'])
		data_frame['Day Move'] = self.resultTransform(data_frame['Previous Close']/data_frame['Entry Level'])
		data_frame['Pre Move'] = self.resultTransform(data_frame['Previous Close']/data_frame['Day Open'])
		
		if strategy == Constants.UP_STEPS or strategy == Constants.DOWN_STEPS:
			data_frame['Stair Run'] = self.resultTransform(data_frame['Stop Level']/data_frame['Start Level'])
		
		if strategy == Constants.TOP_REVERSAL or strategy == Constants.BOTTOM_REVERSAL:
			data_frame['Peak Move'] = self.resultTransform(data_frame['Stop Level']/data_frame['Start Level'])
				
		# normalize the RSIs
		for column in [column for column in data_frame.columns if column.endswith('RSI')]:
			data_frame[column] = data_frame[column]/100

		return data_frame


	def standardize(self, data_array):
		# std = data_array.std()
		# mean = data_array.mean()

		#return (data_array - mean)/std

		return (data_array-data_array.min())/(data_array.max() - data_array.min())


	def evaluateClassModel(self, model, model_type, data):
		y_train_p = model.predict(data['x train'])
		y_test_p = model.predict(data['x test'])

		print(f"{sum(y_train_p == data['y train'])} out of {len(y_train_p == data['y train'])}")
		print(f"{sum(y_test_p == data['y test'])} out of {len(y_test_p == data['y test'])}")
		print(type(data))
		print(type(data['y test']))
		#print(data['x test']['Stop Loss'])

		for target_class in data['y test'].unique():
			selection = data['y test'] == target_class
			unique_elements, proportions = np.unique(y_test_p[selection], return_counts=True)
			print(f"When the class is: {target_class} with {sum(selection)} elements we predict:")
			print(proportions/sum(selection))

		print("The important ones")
		for target_class in np.unique(y_test_p):
			selection = y_test_p == target_class
			proportions = data['y test'][selection].value_counts(normalize=True)
			print(f"When the prediction is: {target_class} with {sum(selection)} elements the actual classes are:")
			print(proportions)

		self.plotClassificationResults(y_test_p, data['y test'], 'by_actual', model_type) #, data['x test']['Stop Loss']
		self.plotClassificationResults(data['y test'], y_test_p, 'by_prediction', model_type) #, data['x test']['Stop Loss']


	def plotClassificationResults(self, y_class, y_target, plot_type, plot_name): #, trade_risk
		# Assume y_actual and y_pred are your arrays with actual and predicted classes
		df = pd.DataFrame({'Class': y_class, 'Target': y_target}) #, 'TradeRisk': trade_risk})

		# Create a cross-tabulation of actual and predicted classes
		cross_tab = pd.crosstab(df['Class'], df['Target'])

		# Convert counts to proportions
		cross_tab = cross_tab.div(cross_tab.sum(axis=1), axis=0)

		# Reset the index to allow 'Class' to be used as a hue in the barplot
		cross_tab = cross_tab.reset_index()

		# Convert dataframe from wide to long format
		df_long = pd.melt(cross_tab, id_vars='Class', var_name='Target', value_name='Proportion')

		# Calculate medians of TradeRisk
		#trade_risk_medians = df.groupby(['Class', 'Target'])['TradeRisk'].median().reset_index()

		# Create barplot
		plt.figure(figsize=(10, 6))
		sns.barplot(data=df_long, x='Class', y='Proportion', hue='Target')

		# Add points for median TradeRisk values
		#sns.pointplot(data=trade_risk_medians, x='Actual', y='TradeRisk', hue='Target', dodge=True, join=False, palette='dark')

		plt.title('Proportion of Predicted Classes for Each Actual Class and Median Trade Risk')
		plt.xlabel('Actual Class')
		plt.ylabel('Proportion / Median Trade Risk')

		plt.savefig(Constants.ANAYLIS_RESULTS_FOLDER + 'resultFigures/classification/' + plot_type + '/class_figure' + plot_name + '.png')


	def evaluateRegrModel(self, model, model_type, data):
		y_train_p = self.resultInverse(model.predict(data['x train']))
		y_test_p = self.resultInverse(model.predict(data['x test']))

		self.plotRegressionResults(y_train_p, self.resultInverse(data['y train']), y_test_p, self.resultInverse(data['y test']), model_type)


	def plotRegressionResults(self, y_train_p, y_train, y_test_p, y_test, plot_name):
		plt.figure(figsize=(20,20))
		plt.scatter(y_train, y_train_p, c='b')
		plt.scatter(y_test, y_test_p, c='r')
		if y_test.max() < 0:
			point_range = np.linspace(0,-0.06,10)
		else:
			point_range = np.linspace(0,0.06,10)

		plt.plot(point_range, point_range, '--', c='g', linewidth=5)
		# Set labels
		plt.xlabel('Actual Move (%)', fontsize=24)
		plt.ylabel('Predicted Move (%)', fontsize=24)

		# Set font of the ticks
		plt.xticks(fontsize=18)
		plt.yticks(fontsize=18)
		plt.savefig(Constants.ANAYLIS_RESULTS_FOLDER + 'resultFigures/combined_figure_' + plot_name + '.png')
		print('We saved no?')
		plt.close()
		#save figure


	def saveTreeModels(self):
		for key, model in self.regression_models.items():
			pickle.dump(model, open(Constants.ANAYLIS_RESULTS_FOLDER + 'models/xgbregressor_' + key + '.pkl', 'wb'))
		
		for key, model in self.classification_models.items():
			pickle.dump(model, open(Constants.ANAYLIS_RESULTS_FOLDER + 'models/xgbclassifier_' + key + '.pkl', 'wb'))

# # Load the saved model from file
# loaded_model = pickle.load(open(filename, 'rb'))

# # Use the loaded model for predictions
# predictions = loaded_model.predict(X_test)

