class FactorList(object) :
    
    def __init__(self) :
    
        self._list = []

    def getLogNormalization(self) :

        list = self._list
        for currentFactor in list :

            currentFactor.resetMarginals()

        sumLogZ = 0.0

        listCount = len(self._list)

        for i in range (listCount) :

            f = self._list[i]

            numberOfMessages = f.getNumberOfMessages()

            for j in range (numberOfMessages) :

                sumLogZ = sumLogZ + f.sendMessageIndex(j)


        sumLogS = 0.0

        for currentFactor in list :

            sumLogS = sumLogS + currentFactor.getLogNormalization()
 
        return sumLogZ + sumLogS


    def count(self) :
        return len(self._list)


    def addFactor(self, factor) :

        self._list.append(factor)
        return factor
    