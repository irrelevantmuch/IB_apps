from datetime import datetime
from pytz import utc    

def mergeAdjRanges(date_ranges):
    date_ranges.sort()  # Ensure the ranges are sorted (in-place)
    for index_right in reversed(range(len(date_ranges))):
        date_range_right = date_ranges[index_right]
        for index_left in range(index_right):
            date_range_left = date_ranges[index_left]
            if (date_range_right[0] >= date_range_left[0]) and (date_range_right[1] <= date_range_left[1]):
                del date_ranges[index_right]
                break
            elif (date_range_right[0] <= date_range_left[1]) and (date_range_right[1] > date_range_left[1]):
                date_ranges[index_left] = (date_range_left[0], date_range_right[1])
                del date_ranges[index_right]
                break
            elif (date_range_right[1] >= date_range_left[0]) and (date_range_right[0] < date_range_left[0]):
                date_ranges[index_left] = (date_range_right[0], date_range_left[1])
                del date_ranges[index_right]
                break

    return date_ranges


class RangeObject:

    def __init__(self, requested_ranges=None):
        if requested_ranges is not None:
            self._requested_ranges = self.constrainRanges(requested_ranges)
        else:
            self._requested_ranges = []


    def constrainRanges(self, ranges):
        for index, rng in enumerate(ranges):
            constrained_range = self.constrainRange(rng)
            if constrained_range != []:
                ranges[index] = constrained_range

        return ranges


    def constrainRange(self, rng):
        max_time = datetime.now(utc).replace(microsecond=0)
        if rng[0] > max_time:
            return []
        if rng[1] > max_time:
            rng = (rng[0], max_time)
        
        return rng


    def containsRange(self, inner_range):

        for req_range in self._requested_ranges:
            if (inner_range[0] >= req_range[0]) and (inner_range[1] <= req_range[1]):
                return True
        return False


    def withinRange(self, dt_object):

        for req_range in self._requested_ranges:
            if (dt_object >= req_range[0]) and (dt_object <= req_range[1]):
                return True
        return False


    def addRanges(self, req_range):
        req_range = self.constrainRange(req_range)
        self._requested_ranges.append(req_range)
        self._requested_ranges = mergeAdjRanges(self._requested_ranges)

        
    def getRanges(self):
        return self._requested_ranges
        

    def getRequestedRanges(self):
        return self._requested_ranges


