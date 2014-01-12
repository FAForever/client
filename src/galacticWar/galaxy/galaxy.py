
from PyQt4 import QtCore, QtGui
import random
from  voronoi import Site, computeVoronoiDiagram
import math
import copy

class Galaxy(object):
    def __init__(self, parent):
        self.parent = parent

        sizex = 2000
        sizey = 2000
        
        self.space_size = QtGui.QVector3D(sizex, sizey, 0)

        self.COLOR_FACTIONS = self.parent.COLOR_FACTIONS
        

        self.star_field = []
        self.control_points = {}
        self.links = {}

        self.sectors = {}


        p1 = QtCore.QPointF(-self.space_size.x()-50, -self.space_size.y()-50)
        p2 = QtCore.QPointF(-self.space_size.x()-50, self.space_size.y()+50) 
        p3 = QtCore.QPointF(self.space_size.x()+50, self.space_size.y()+50) 
        p4 = QtCore.QPointF(self.space_size.x()+50, -self.space_size.y()-50)  
        
        line1 = QtCore.QLineF(p1,p2)
        line2 = QtCore.QLineF(p2,p3)
        line3 = QtCore.QLineF(p3,p4)
        line4 = QtCore.QLineF(p4,p1)
        
        self.boundLines=[line1, line2, line3, line4]

        self.finalPolys={}
#        self.computeVoronoi()
#        self.createNetwork()
    
    def updateAllSites(self):
        for uid in self.control_points :
            self.control_points[uid].computeColor()
    
    def update(self, message):
        uid = message["uid"]
        if uid in self.control_points :
            self.control_points[uid].setOccupation(0, message['uef'])
            self.control_points[uid].setOccupation(1, message['aeon'])
            self.control_points[uid].setOccupation(2, message['cybran'])
            self.control_points[uid].setOccupation(3, message['seraphim'])
            
            self.control_points[uid].computeColor()
    
    def get_maxplayer(self,uid):
        if uid in self.control_points :
            return self.control_points[uid].get_maxplayer()
        else :
            return 0
        
    def get_name(self, uid):
        if uid in self.control_points :
            return self.control_points[uid].get_name()
        else :
            return "unknown"

    def get_description(self, uid):
        if uid in self.control_points :
            return self.control_points[uid].get_description()
        else :
            return "unknown"        
    
    def monotone_chain(self, points):
        '''Returns a convex hull for an unordered group of 2D points.
        Uses Andrew's Monotone Chain Convex Hull algorithm.'''
    

        def _isLeft(q, r, p):
            return (r[0]-q[0])*(p[1]-q[1]) - (p[0]-q[0])*(r[1]-q[1])
    
        # Remove duplicates (this part of code is useless for Panda's
        # Point2 or Point3! In their case set() doesn't remove duplicates;
        # this is why internally this class has all points as (x,y) tuples).
        points = list(set(points))
    
        # Sort points first by X and then by Y component.
        points.sort()
        # Now, points[0] is the lowest leftmost point, and point[-1] is
        # the highest rightmost point. The line through points[0] and points[-1]
        # will become dividing line between the upper and the lower groups
        # of points.
       
        p0x, p0y = points[0]
        p1x, p1y = points[-1]
    
        
        # Initialize upper and lower stacks as empty lists.
        U = []
        L = []
    
        # For each point:
        for p in points:
       
            # First, we check if the point in # i.e. points is left or right or
            # colinear to the dividing line through points[0] and points[-1]:
            cross = (p1x-p0x)*(p[1]-p0y) - (p[0]-p0x)*(p1y-p0y)
           
            # If the point is lower or colinear, test it for inclusion
            # into the lower stack.
            if cross <= 0:
                # While L contains at least two points and the sequence
                # of the last two points in L and p does not make
                # a counter-clockwise turn:
                while len(L) >= 2 and _isLeft(L[-2], L[-1], p) <= 0:
                    L.pop()
                L.append(p)
               
            # If the point is higher or colinear, test it for inclusion
            # into the upper stack.
            if cross >= 0:           
                # While U contains at least two points and the sequence
                # of the last two points in U and p does not make
                # a clockwise turn:
                while len(U) >= 2 and _isLeft(U[-2], U[-1], p) >= 0:
                    U.pop()
                U.append(p)
    
        L.pop()
        U.reverse()
        U.pop()
    
        return L+U
    
    def generate_star_field(self, minDepth, maxDepth):
        self.star_field = []
        numStars = int(max(1, 15000 * (float(self.parent.stars) / 100.0)))
        for _ in range(numStars) :
            star = QtGui.QVector3D(random.randrange(-self.space_size.x(),self.space_size.x()), random.randrange(-self.space_size.y(),self.space_size.y()), random.randrange(float(-200*2), float(minDepth)))            
            self.star_field.append(star)
    
   
        return True

    def addLink (self, orig, dest):
        planetFrom  = orig
        planetTo    = dest

        if orig > dest :
            planetFrom  = dest
            planetTo    = orig
        
        
        line = QtCore.QLineF(self.control_points[planetFrom].x, self.control_points[planetFrom].y, self.control_points[planetTo].x, self.control_points[planetTo].y)
        for link in self.links :
            for dest in self.links[link] :
                otherLine = QtCore.QLineF(self.control_points[link].x, self.control_points[link].y, self.control_points[dest].x, self.control_points[dest].y)
                intersection = QtCore.QPointF()
 
                if otherLine.intersect(line, intersection) == 1 :
                    if line.p1() != intersection and  line.p2() != intersection :
                        return
  
      
        if planetFrom in self.links :
            if not planetTo in self.links[planetFrom] :
                self.links[planetFrom].append(planetTo)
        else :
            self.links[planetFrom] = [planetTo]
    
    def numLinks(self, site):
        numLinks = 0
        
        if site in self.links :
            numLinks = numLinks + len(self.links[site])
            
        
        for link in self.links :
            if link != site :
                if site in self.links[link] :
                    
                    numLinks = numLinks + 1

        return numLinks

    def getLinkedPlanets(self, site):
        planets = []
        
        if site in self.links :
            
            planets = copy.deepcopy(self.links[site])
            
        for link in self.links :
            if link != site :
                if site in self.links[link] :
                    planets.append(link)
        
        return planets            
        
    
    def computeVoronoi(self):
        self.coords, self.equation, self.edges, self.bounds = computeVoronoiDiagram(self.control_points)
        self.voronoi = computeVoronoiDiagram(self.control_points)
        self.computePolys()         
    
    def movePlanet(self, site, x, y):    
        x = round(x)
        y = round(y)
        
        if x > self.space_size.x() or x < -self.space_size.x() or y > self.space_size.y() or y < -self.space_size.y() :
            return
        
        site.x = x
        site.y = y
        
        site.pos3d.setX(site.x)
        site.pos3d.setY(site.y)
        
    def updateDefenses(self, uid, message):
        if uid in self.control_points :
            self.control_points[uid].updateDefenses(message)
        
    def removeDefenses(self, uid):
        if uid in self.control_points :
            self.control_points[uid].removeDefenses()
    
    
    def addPlanet(self, uid, sector, name, desc, x, y, size, texture=1, mapname="", init=False, display = False, maxplayer=0):
        
        x = round(x)
        y = round(y)
        
        uef = 0.0
        cybran  = 0.0
        aeon = 0.0
        sera = 0.0
        
        if display:
            if not sector in self.sectors:
                self.sectors[sector] = [uid]
            else:
                self.sectors[sector].append(uid)            
       
        if x > self.space_size.x() or x < -self.space_size.x() or y > self.space_size.y() or y < -self.space_size.y() :
            return

        self.control_points[uid]=(Site(parent=self, sector=sector, x=x, y=y, size = size, sitenum = uid, name=name, desc=desc, aeon = aeon, uef = uef, cybran = cybran, sera = sera, texture = texture, mapname=mapname, display=display, maxplayer=maxplayer))
        if not init :
            self.computeVoronoi()
     

    def closestSite(self, x, y, notPoint = None):

        points = []
        closest = None
        distance = None
        xout = None
        yout = None
        
        for uid in self.control_points:
            pt = self.control_points[uid]
            px = pt.x
            py = pt.y
            d = math.hypot(px - x, py - y)
            if d == 0:
                return _, 0, x, y
            
            if d < distance or not distance :
                
                closest = uid
                distance = d
                xout = px
                yout = py

        for uid in self.control_points:
            pt = self.control_points[uid]
            px = pt.x
            py = pt.y
            d = math.hypot(px - x, py - y)
            if d == 0:

                return uid, 0
            if d <= distance + 0.001 :        
                return uid, distance, px, py              
                

 
    def closest(self, x, y, notPoint = None):

        points = []
        closest = None
        distance = None
        xout = None
        yout = None
        
        for uid in self.control_points:
            pt = self.control_points[uid]
            px = pt.x
            py = pt.y
            d = math.hypot(px - x, py - y)
            if d == 0:
                return uid, 0
            
            if d < distance or not distance :
                
                closest = uid
                distance = d
                xout = px
                yout = py
                
                #return closest, distance, xout, yout

        for uid in self.control_points:
            pt = self.control_points[uid]
            px = pt.x
            py = pt.y
            d = math.hypot(px - x, py - y)
            if d == 0:

                return uid, 0
            if d <= distance + 0.001 :
                points.append((distance, px, py, uid))
         
        return points


    def getConnected(self, siteIdx):
        ''' This return all the sites that are linked to the one provided'''
        connections = []
        if siteIdx in self.links :
            for idx in self.links[siteIdx] :
                if idx != siteIdx :
                    connections.append(idx)            
        for otherSite in self.links :
            if siteIdx != otherSite :
                if siteIdx in self.links[otherSite] :
                    connections.append(otherSite)
        return connections

    def computeDistance(self, siteIdx, otherSiteIdx, numConn = 0, previous=[]):
        '''compute the number of links between two planets'''
        numConn = numConn+1 
        previous.append(siteIdx)
        for idx in self.getConnected(siteIdx) :
            if otherSiteIdx == idx:
                return numConn 
            else:
                if not idx in previous:
                    return self.computeDistance(idx, otherSiteIdx, numConn, previous)
              
                
    def isLooping(self, siteIdx):
        ''' This compute if the current site is forming a triangle'''
        
        for first in self.getConnected(siteIdx) :
            for second in self.getConnected(first) :
                for third in self.getConnected(second) :
                    if third == siteIdx :
                        return True
        return False

    def willLoop(self, siteIdx, otherSiteIdx):
        ''' This compute if the current site is forming a triangle'''
        
        first = self.getConnected(siteIdx)
        for idx in self.getConnected(otherSiteIdx) :
            if idx in first :
                return True

        return False        
        

    def createNetwork(self):
        for i, point in enumerate(self.control_points) :
            around = self.getSitesAroundSite(point,100)
            for _, siteIdx in around :
                
                if self.willLoop(siteIdx, i) :
                    continue
                
                if self.numLinks(i) <= 3 :
                    if self.numLinks(siteIdx) > 3 :
                        continue
                    if self.numLinks(siteIdx) <= 4 :
                        self.addLink(i, siteIdx)
                        
        ## check for planet that are alone...
        for i, point in enumerate(self.control_points) :
            if self.numLinks(i) < 2 :
                around = self.getSitesAroundSite(point,200)
                for _, siteIdx in around :

                    
                    if self.numLinks(i) <= 3 :
                        if self.numLinks(siteIdx) > 3 :
                            continue
                        if self.numLinks(siteIdx) <= 4 :
                            self.addLink(i, siteIdx)                
        


    def numSitesAround(self, x, y, distance):
        num = 0
        for _, point in enumerate(self.control_points) :
            px = point.x
            py = point.y 
            d = math.hypot(px - x, py - y)   
            if d < distance and d != 0.01 :
                num = num + 1
                
        return num
                
                
                
    def getSitesAroundSite(self, site, distance):
        x = site.x
        y = site.y
        
        aroundThisPoint = []
        
        for i, point in enumerate(self.control_points) :
            px = point.x
            py = point.y 
            d = math.hypot(px - x, py - y)   
            if d < distance and d != 0.01 :
                aroundThisPoint.append((d,i))
        
        return sorted(aroundThisPoint, key=lambda point: point[0])        
        
#        for point in aroundThisPoint :
#            return 

    def computePolys(self):

        self.finalPolys = {}
        coords = self.coords
        edges = self.edges


        for i in range(len(edges)) :

            _, xpos, ypos = edges[i]

            if xpos == -1 :
                continue
            else :
                point1 = coords[xpos] 
            
            if ypos == -1 :
                continue
            else :
                point2 = coords[ypos]
            
            xcoord = (point1[0] + point2[0]) / 2.0
            ycoord = (point1[1] + point2[1]) / 2.0


            points = self.closest(xcoord, ycoord, self.control_points)
            
            for _, x, y, name in points :
                
                points = [] 
                pointOrigin = (QtCore.QPointF(x, y))
                

                rect = QtCore.QRectF(QtCore.QPointF(-self.space_size.x()-50,-self.space_size.y()-50), QtCore.QPointF(self.space_size.x()+50,self.space_size.y()+50))


                out1 = QtCore.QPointF(point1[0], point1[1])
                out2 = QtCore.QPointF(point2[0], point2[1])
                
                if rect.contains(out1) :
                    points.append((point1[0], point1[1]))
                else :

                    #point is outside the zone, we check the intersection
                    line1 = QtCore.QLineF(pointOrigin, out1)
                    intersection = False
                    for line in self.boundLines :
#                       
                        intersect = QtCore.QPointF()
                        if  line1.intersect(line, intersect) == 1 :

                            points.append((intersect.x(),intersect.y()))
                            intersection = True
                            break
                
                if rect.contains(out2) :
                    
                    points.append((point2[0], point2[1]))
                else :
                    intersect = True
                    line1 = QtCore.QLineF(pointOrigin, out2)
                    for line in self.boundLines :

                        intersect = QtCore.QPointF()
                        if  line1.intersect(line, intersect) == 1 :
                            points.append((intersect.x(),intersect.y()))
                            #break


                line1 = QtCore.QLineF(out1, out2)
                for line in self.boundLines :
#
                    intersect = QtCore.QPointF()
                    if  line1.intersect(line, intersect) == 1 :
                        points.append((intersect.x(),intersect.y()))
                        #break

                if name in self.finalPolys :
                    for point in points :
                        self.finalPolys[name].append(point)
                else :
                    self.finalPolys[name] = points
                    
                if pointOrigin.x() == self.space_size.x() :
                    if pointOrigin.y() == self.space_size.y() :
                        self.finalPolys[name].append((self.space_size.x()+50, self.space_size.y()+50))
                    elif pointOrigin.y() == -self.space_size.y() :
                        self.finalPolys[name].append((self.space_size.x()+50, -self.space_size.y()-50))
                elif pointOrigin.x() == -self.space_size.x() :
                    if pointOrigin.y() == self.space_size.y() :
                        self.finalPolys[name].append((-self.space_size.x()-50, self.space_size.y()+50))
                    elif pointOrigin.y() == -self.space_size.y() :
                        self.finalPolys[name].append((-self.space_size.x()-50, -self.space_size.y()-50))                    

