import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pymc3 as pm
from dataHandling.Constants import Constants


def fitModel(data):
    
    # Extract the low, high, open and close values from the data
    low_values = data[Constants.LOW].values
    high_values = data[Constants.HIGH].values
    open_values = data[Constants.OPEN].values
    close_values = data[Constants.CLOSE].values

    # Combine the values into a single matrix
    observed_data = np.stack((low_values, high_values, open_values, close_values), axis=1)

    # Specify the number of previous samples to use as regressors
    lag_order = 5

    # Split the data into training and testing sets
    train_data = observed_data[:400]
    test_data = observed_data[400:]

    print("Maybe not more than 500?")
    print(train_data.shape)
    print(test_data.shape)

    # Define the PyMC3 model
    with pm.Model() as arima_model:
        # Priors for the ARIMA model parameters
        mu = pm.Normal('mu', mu=0, sigma=10)
        phi = pm.Normal('phi', mu=0, sigma=1, shape=(4, lag_order))
        sigma = pm.HalfNormal('sigma', sigma=10)

        # Likelihood function for the ARIMA model
        likelihood = pm.Normal('y', mu=mu, sigma=sigma, observed=train_data[lag_order:])

        # Use the NUTS sampler to obtain samples from the posterior distribution
        trace = pm.sample(1000, tune=100, target_accept=0.9)

    # Print the summary statistics of the posterior distribution for the parameter values
    pm.summary(trace)

    # Compute the mean and standard deviation of the posterior distribution for the parameter values
    posterior_mean = np.mean(trace['phi'], axis=0)
    posterior_std = np.std(trace['phi'], axis=0)

    print(f"Posterior Mean: {posterior_mean}")
    print(f"Posterior Standard Deviation: {posterior_std}")

    # Make predictions using the posterior distribution for the parameter values
    train_predictions = []
    for i in range(lag_order, len(train_data)):
        print(type(train_data[i-lag_order:i]))
        print(type(posterior_mean.T.reshape((4, lag_order))))
        print(train_data[i-lag_order:i].shape)
        print(posterior_mean.shape)
        print(train_data[i-lag_order:i])
        print(posterior_mean.T.reshape((4, lag_order)))
        #ar = np.dot(train_data[i-lag_order:i], posterior_mean.T)
        ar = np.dot(train_data[i-lag_order:i], posterior_mean.T.reshape((4, lag_order)))
        y_pred = np.random.normal(ar, posterior_std, size=4)
        train_predictions.append(y_pred)

    test_predictions = []
    for i in range(len(train_data), len(observed_data)):
        ar = np.dot(test_data[i-lag_order:i], posterior_mean.T)
        y_pred = np.random.normal(ar, posterior_std, size=4)
        test_predictions.append(y_pred)

    print('Can we do anything with this?')
    print(train_predictions)
    print(test_predictions)
    # # Plot the predictions for the training data
    # plt.figure(figsize=(12, 6))
    # plt.plot(train_data[lag_order:, 0], label='True Low')
    # plt.plot(train_predictions[:, 0], label='Predicted Low')
    # plt.plot(train_data[lag_order:, 1], label='True High')
    # plt.plot(train_predictions[:, 1], label='Predicted High')
    # plt.xlabel('Time')
    # plt.ylabel('Price')
    # plt.title('ARIMA Model - Training Data')
    # plt.legend()
    # plt.show()

    # # Plot the predictions for the testing data
    # plt.figure(figsize=(12, 6))
    # plt.plot(test_data[lag_order:, 0], label='True Low')
    # plt.plot(test_predictions[:, 0], label='Predicted Low')
    # plt.plot(test_data[lag_order:, 1], label='True High')
    # plt.plot(test_predictions[:, 1], label='Predicted High')
    # plt.xlabel('Time')
    # plt.ylabel('Price')
    # plt.title('ARIMA Model - Testing Data')
    # plt.legend