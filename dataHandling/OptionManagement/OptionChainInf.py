import pickle
from generalFunctionality.GenFunctions import getDaysTillExpiration
from dataHandling.Constants import Constants
from datetime import datetime, timezone

class OptionChainInf:

    _expirations = []
    _contract_ids = dict()
    _strikes = []
    _option_chain_dict = dict()

    def __init__(self, uid):
        self._underlying_uid = uid
        self._option_chain_dict = self.readOptionChainInfo()

    @property
    def is_empty(self):
        return (len(self._option_chain_dict['chains'][Constants.CALL]) == 0) and (len(self._option_chain_dict['chains'][Constants.PUT]) == 0)

    @property
    def last_update(self):
        if 'timestamp' in self._option_chain_dict:
            return self._option_chain_dict['timestamp']
        return None

    def updateUnderlyingPrice(self, price):
        self._option_chain_dict['underlying_price'] = price
        self.writeOptionChain()

        
    def resetContractIDs(self):        
        self._contract_ids = dict()


    def setExpirationsFrom(self, expirations_ib_str):
        days_till_exp = [getDaysTillExpiration(exp) for exp in expirations_ib_str]
        date_to_days = dict(zip(expirations_ib_str, days_till_exp))
        self._expirations = sorted(expirations_ib_str, key=lambda x: date_to_days[x])
            

    def addContractID(self, opt_type, strike, expiration, contract_id):
        self._contract_ids[opt_type, strike, expiration] = contract_id
        if not expiration in self._option_chain_dict['chains'][opt_type]:
            self._option_chain_dict['chains'][opt_type][expiration] = dict()

        self._option_chain_dict['chains'][opt_type][expiration][strike] = {'con_id': self._contract_ids[opt_type, strike, expiration]}


    def removeEntireOptionChain(self):
        self.removeSavedOptionInfo()
        self._option_chain_dict = dict()


    def fetchPricesFromFrame(self, option_frame_2D):
        for opt_type in [Constants.CALL, Constants.PUT]:
            for expiration in self._option_chain_dict['chains'][opt_type].keys():
                for tick_type in [Constants.BID, Constants.ASK, Constants.CLOSE]:
                    if option_frame_2D.hasDataForExp(opt_type, expiration):
                        strikes, y_values = option_frame_2D.getValuesByExpiration(opt_type, expiration, tick_type)
                        for strike, price in zip(strikes, y_values):
                            self._option_chain_dict['chains'][opt_type][expiration][strike][tick_type] = price

        self.writeOptionChain()


    def loadPricesToFrame(self, option_frame_2D):
        if len(self._option_chain_dict) > 0:
            expirations_to_remove = []
            chain_dict = self._option_chain_dict['chains']

            for opt_type in chain_dict.keys():
                for expiration in chain_dict[opt_type].keys():
                    days_till_exp = getDaysTillExpiration(expiration)
                    if days_till_exp < 0:
                        expirations_to_remove.append((opt_type, expiration))
                    else:
                        for strike in chain_dict[opt_type][expiration].keys():
                            for tick_type in [Constants.BID, Constants.ASK, Constants.CLOSE]:
                                if tick_type in chain_dict[opt_type][expiration][strike]:
                                    option_price = float(chain_dict[opt_type][expiration][strike][tick_type])
                                    option_frame_2D.setValueFor(opt_type, (expiration, strike), tick_type, option_price)

            for (opt_type, expiration) in expirations_to_remove:
                del self._option_chain_dict['chains'][opt_type][expiration]

            if option_frame_2D.has_data:
                if 'underlying_price' in self._option_chain_dict:
                    option_frame_2D.setUnderlyingPrice(self._option_chain_dict['underlying_price'])

        return option_frame_2D


    def getContractIdsFromChain(self):
        self._contract_ids = dict()
        for opt_type in [Constants.CALL, Constants.PUT]:
            expiration_strings = list(self._option_chain_dict['chains'][opt_type].keys())
            self.setExpirationsFrom(expiration_strings)
            
            strikes = set()
            for exp_str in expiration_strings:
                float_strikes = set(map(float, self._option_chain_dict['chains'][opt_type][exp_str].keys()))
                strikes.update(float_strikes)
                for strike in self._option_chain_dict['chains'][opt_type][exp_str].keys():
                    self._contract_ids[opt_type, strike, exp_str] = self._option_chain_dict['chains'][opt_type][exp_str][strike]['con_id']

            self._strikes = list(strikes)

        return expiration_strings, self._strikes


    def readOptionChainInfo(self):
        try:
            with open(f"{Constants.OPTION_CHAIN_FOLDER}{self._underlying_uid}_chain.pkl", 'rb') as pickle_file:
                option_inf = pickle.load(pickle_file)
                return option_inf
        except (IOError, OSError) as e:
            inner_dict = dict()
            inner_dict['chains'] = dict()
            inner_dict['chains'][Constants.PUT] = dict()
            inner_dict['chains'][Constants.CALL] = dict()
            return inner_dict


    def writeOptionChain(self, price_data=None):
        if price_data is not None:
            self.fetchPricesFromFrame(price_data)
        try:
            with open(f"{Constants.OPTION_CHAIN_FOLDER}{self._underlying_uid}_chain.pkl", 'wb') as outfile:
                pickle.dump(self._option_chain_dict, outfile)
        except (IOError, OSError) as e:
            print("We couldn't wite the JSON file.... :(")
            print(e)
    


    def removeSavedOptionInfo(self):
        os.remove(f"{Constants.OPTION_CHAIN_FOLDER}{self._underlying_uid}_chain.pkl")


    def removeSavedPriceInf(self):
        if len(self._option_chain_dict) > 0:

            chain_dict = self._option_chain_dict['chains']

            for opt_type in chain_dict.keys():
                for expiration in chain_dict[opt_type].keys():
                    for strike in chain_dict[opt_type][expiration].keys():
                        for tick_type in [Constants.BID, Constants.ASK, Constants.CLOSE]:
                            if tick_type in chain_dict[opt_type][expiration][strike]:
                                del self._option_chain_dict['chains'][opt_type][expiration][strike][tick_type]

        self.writeOptionChain()


    def finalizeChainGathering(self):
        self._option_chain_dict['timestamp'] = datetime.now(timezone.utc).timestamp()
            
        self.writeOptionChain()

        return self.getAllExpirations(), self.getAllStrikes()


    def getAllExpirations(self):
        return list({key[2] for key in self._contract_ids.keys()})
            

    def getAllStrikes(self):
        return list({key[1] for key in self._contract_ids.keys()})


    def getExpirationsFor(self, strike):
        return [key[2] for key in self._contract_ids.keys() if key[1] == strike]

    def getStrikesFor(self, expiration):
        return [key[1] for key in self._contract_ids.keys() if key[2] == expiration]

    def getExpirations(self):
        return self._expirations


    def expirationsLoaded(self):
        return len(self._expirations) !=0

        
    def getContractItems(self):
        return self._contract_ids.items()
