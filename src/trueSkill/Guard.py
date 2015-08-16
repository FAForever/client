



class Guard(object):
    @staticmethod
    def argumentNotNull( value, parameterName) :
        if value == '' :
            raise Exception(parameterName, " can not be null")
    @staticmethod
    def argumentIsValidIndex( index, count, parameterName) :
        if index < 0 or index >= count :
            raise Exception(parameterName, " is an invalid index")
    
    @staticmethod
    def argumentInRangeInclusive( value, min, max, parameterName) :
        if value < min or value > max :
            raise Exception(parameterName, " is not in the valid range [" + min + ", " + max + "]")
    
