
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