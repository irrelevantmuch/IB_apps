
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


class DetailObject:

    def __init__(self, numeric_id, symbol, sec_type, exchange, time_zone, long_name, currency, **unused):
        self.symbol = symbol
        self.sec_type = sec_type
        self.exchange = exchange
        self.long_name = long_name
        self.numeric_id = numeric_id
        self.currency = currency
        self.time_zone = time_zone
