
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

import json
import pickle
import re

from os import walk

def fetchPositionNotes():

    try:
        with open('data/notes_data.json') as json_file:
            data = json.load(json_file)
            return data
    except: # (IOError, OSError) as e:
        return dict()


def readApiKeys():
    try:
        with open('data/api_keys.json') as json_file:
            data = json.load(json_file)
            return data
    except: # (IOError, OSError) as e:
        return dict()


def writePositionNotes(dict):

    try:
        with open('data/notes_data.json', 'w') as outfile:
            json.dump(dict, outfile)
    except: # (IOError, OSError) as e:
        print("We couldn't wite the JSON file.... :(")


def getStockListNames():
    print("UserDataManager.getStockListNames")
    files = []
    for (dirpath, dirnames, filenames) in walk('data/stock_lists/'):
        files.extend(filenames)
        break

    files = [fi for fi in files if fi.endswith(".pkl")]
    print(files)

    list_names = []
    for file in files:
        list_name = getListName(file)
        list_names.append(list_name)
    
    return list(zip(files, list_names))


def getListName(file_name):
    try:
        with open('data/stock_lists/' + file_name, 'rb') as pickle_file:
            list_dict = pickle.load(pickle_file)
            return list_dict["list_name"]
    except: # (IOError, OSError) as e:
        return ""


def readStockList(file_name, alphabetized=False):
    print(f"UserDataManager.readStockList {file_name}")
    try:
        with open('data/stock_lists/' + file_name, 'rb') as pickle_file:
            list_dict = pickle.load(pickle_file)
            if alphabetized:
                list_dict["stock_list"] = dict(sorted(list_dict["stock_list"].items()))
            return list_dict["stock_list"]
    except: # (IOError, OSError) as e:
        return dict()


def writeStockList(stock_dict, name, file_name=None):

    if file_name is None:
        file_name = convertToFileName(name)

    pickle_dict = {"list_name": name, "file_name": file_name, "stock_list": stock_dict}
    
    try:
        with open('data/stock_lists/' + file_name, 'wb') as outfile:
            pickle.dump(pickle_dict, outfile)
    except: # (IOError, OSError) as e:
        print("We couldn't wite the JSON file.... :(")


def convertToFileName(name):
    name = name.lower().replace(" ", "_")
    name = re.sub("[^a-z_]+", "", name)
    name = name + ".pkl"
    return name


def readPositionTypes():
    try:
        with open('data/position_types.json') as json_file:
            json_dict = json.load(json_file)
            return json_dict
    except: # (IOError, OSError) as e:
        return {"types": dict(), "split_counts": dict()}


def writePositionTypes(json_dict):

    try:
        with open('data/position_types.json', 'w') as outfile:
            json.dump(json_dict, outfile)
    except: # (IOError, OSError) as e:
        print("We couldn't wite the JSON file.... :(")


