
import shutil
import urllib.request as request
from contextlib import closing

def downloadShortData(folder):
    print("We attempt to download US short data")
    with closing(request.urlopen('ftp://shortstock: @ftp3.interactivebrokers.com/usa.txt')) as r:
        with open(folder + 'usa.txt', 'wb') as f:
            shutil.copyfileobj(r, f)
            print("We succeeded")



def getShortDataFor(uid):
    with open("data/usa.txt", "r") as filestream:
        for index, line in enumerate(filestream):
            current_line = line.split("|")
            if len(current_line) >= 4 and current_line[3] == uid:
                return current_line

    return list()