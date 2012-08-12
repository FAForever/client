from Factor import Factor

class Schedule(object):
    def __init__(self, name):
        self._name = name

    def visit(self, depth = -1, maxDepth = 0) :
        pass
#
    def __str__(self) :
        return self._name


class ScheduleStep(Schedule) :
    def __init__(self, name, factor, index):

        super(ScheduleStep, self).__init__(name)
       
        self._factor = factor
        self._index = index

    def visit(self, depth = -1, maxDepth = 0) :

#        print "Schedule Step  : " + self._name

        currentFactor = self._factor

        delta = currentFactor.updateMessageIndex(self._index)
        return delta


class ScheduleSequence(Schedule) :
    def __init__(self, name, schedules) :

        super(ScheduleSequence, self).__init__(name)
        self._schedules = schedules
        
  

    def visit(self, depth = -1, maxDepth = 0) :
        maxDelta = 0
        
        schedules = self._schedules
        
       
        for currentSchedule in schedules :
            currentVisit = currentSchedule.visit(depth + 1, maxDepth)
            maxDelta = max(currentVisit, maxDelta)

        return maxDelta
    
class ScheduleLoop(Schedule) :
    def __init__(self, name, scheduleToLoop, maxDelta) :
        super(ScheduleLoop, self).__init__(name)
        self._scheduleToLoop = scheduleToLoop
        self._maxDelta = maxDelta

    def visit(self, depth = -1, maxDepth = 0) :


        totalIterations = 1
        delta = self._scheduleToLoop.visit(depth + 1, maxDepth)
        

        while delta > self._maxDelta :
            if totalIterations > 1000 : break
            delta = self._scheduleToLoop.visit(depth + 1, maxDepth)
            totalIterations = totalIterations + 1
 

        return delta

