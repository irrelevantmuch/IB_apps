import json
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

    files = []
    for (dirpath, dirnames, filenames) in walk('data/stock_lists/'):
        files.extend(filenames)
        break

    files = [ fi for fi in files if fi.endswith(".json") ]

    list_names = []
    for file in files:
        list_name = getListName(file)
        list_names.append(list_name)
    
    return list(zip(files, list_names))


def getListName(file_name):
    try:
        with open('data/stock_lists/' + file_name) as json_file:
            json_dict = json.load(json_file)
            return json_dict["list_name"]
    except: # (IOError, OSError) as e:
        return ""


def readStockList(file_name, alphabetized=False):
    print(file_name)
    try:
        with open('data/stock_lists/' + file_name) as json_file:
            json_dict = json.load(json_file)
            if alphabetized:
                json_dict["stock_list"] = dict(sorted(json_dict["stock_list"].items()))
            return json_dict["stock_list"]
    except: # (IOError, OSError) as e:
        return dict()


def writeStockList(stock_dict, name, file_name=None):

    if file_name is None:
        file_name = convertToFileName(name)

    json_dict = {"list_name": name, "file_name": file_name, "stock_list": stock_dict}
    
    try:
        with open('data/stock_lists/' + file_name, 'w') as outfile:
            json.dump(json_dict, outfile)
    except: # (IOError, OSError) as e:
        print("We couldn't wite the JSON file.... :(")


def convertToFileName(name):
    name = name.lower().replace(" ", "_")
    name = re.sub("[^a-z_]+", "", name)
    name = name + ".json"
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


