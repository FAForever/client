from OpenGL import GL
from OpenGL import GLU
from PyQt4 import QtCore, QtGui, QtOpenGL

import math
import random
import os
from util import CACHE_DIR

class GLWidget(QtOpenGL.QGLWidget):
    xRotationChanged = QtCore.pyqtSignal(int)
    yRotationChanged = QtCore.pyqtSignal(int)
    zRotationChanged = QtCore.pyqtSignal(int)
    
    UPDATE_ROTATION = 22


    def __init__(self, parent=None):
        super(GLWidget, self).__init__(QtOpenGL.QGLFormat(QtOpenGL.QGL.SampleBuffers), parent)

        self.parent = parent
        self.galaxy = self.parent.galaxy

        self.ctrl       = False
        self.shift      = False
        self.drawLink   = False

        self.zorig = None
        
        self.object = 0

        self.yRot = 0

        
        self.averageRadius = 5
        
        self.boundMove =self.galaxy.space_size
        self.backgroundDepth = -10000

        self._mode = GL.GL_MODELVIEW

        self.mouseMode = 0

        self.zones      = None
        self.planets    = None
        self.links      = None
        self.numPlanets = len(self.galaxy.star_field)

        
        self.curZone    = None
        self.dragPlanet = None
        
        self.lookAt = QtGui.QVector3D(0, 0, 0)
        self.zoomMin = 500
        self.zoomMax = 10
        self.cameraPos  = QtGui.QVector3D(0,0,self.zoomMin)
        self.vectorMove = QtGui.QVector3D(0,0,self.zoomMin)
        
        self.zooming = False
        
        self.galaxy.generate_star_field(self.zoomMin, self.backgroundDepth)

        
        
        self.cursor = QtGui.QVector3D(0,0,0)
        self.destination = QtGui.QVector3D(0,0,0)

        self.r = 0
        self.ir = 0

        self._numScheduledScalings = 0;

        
        self.lastPos = QtCore.QPoint()

        self.timerRotate = QtCore.QTimer(self)
        self.timerRotate.timeout.connect(self.rotateOneStep)
        
        
        self.animCam = QtCore.QTimeLine(300, self)

        self.animCam.setUpdateInterval(self.UPDATE_ROTATION/2)
        self.animCam.valueChanged.connect(self.scalingTime)
        self.animCam.finished.connect(self.animFinished)
        
        self.setMouseTracking(1)
        self.setAutoFillBackground(False)
        

    def rotateOneStep(self, update = True):
        
        if not update :
            self.yRot = self.yRot + math.radians(self.UPDATE_ROTATION*0.04)
        else :
            self.yRot = self.yRot + math.radians(self.UPDATE_ROTATION*0.04 * 2)
        if self.yRot >= math.radians(360) :
            self.yRot = 0
        
#        self.yRotationChanged.emit(self.yRot + 5)

        self.programPlanet.setAttributeValue(11, self.yRot)
        if update :
            self.update()


    def magnitude(self, v):
        return math.sqrt(sum(v[i]*v[i] for i in range(len(v))))
    

    def normalize(self, v):
        vmag = self.magnitude(v)
        return [ v[i]/vmag  for i in range(len(v)) ]

    def minimumSizeHint(self):
        return QtCore.QSize(50, 50)

    def sizeHint(self):
        return QtCore.QSize(400, 400)

    def initializeGL(self):
        self.textures = []

        self.galaxy.bindTextures(self)
        self.planetTexId        = self.bindTexture(QtGui.QPixmap(os.path.join(CACHE_DIR,'textures/planet_Tsu_Ni1200.png')), GL.GL_TEXTURE_2D)           
        self.backGroundTexId    = self.bindTexture(QtGui.QPixmap(os.path.join(CACHE_DIR,'textures/background.png')), GL.GL_TEXTURE_2D)
        self.starTexId          = self.bindTexture(QtGui.QPixmap(os.path.join(CACHE_DIR,'textures/star.png')), GL.GL_TEXTURE_2D)
        self.starTex2Id          = self.bindTexture(QtGui.QPixmap(os.path.join(CACHE_DIR,'textures/star.png')), GL.GL_TEXTURE_2D)


        
        
        self.programConstant = QtOpenGL.QGLShaderProgram(self)
        self.programConstant.addShaderFromSourceFile(QtOpenGL.QGLShader.Vertex, os.path.join(CACHE_DIR, "vertexTranspa.gl"))
        self.programConstant.addShaderFromSourceFile(QtOpenGL.QGLShader.Fragment, os.path.join(CACHE_DIR, "fragmentTranspa.gl"))  
        if not self.programConstant.link() :
            print "constant", self.programConstant.log()  

        self.programAtmosphere = QtOpenGL.QGLShaderProgram(self)
        self.programAtmosphere.addShaderFromSourceFile(QtOpenGL.QGLShader.Fragment, os.path.join(CACHE_DIR, "SkyFromSpaceFrag.glsl"))
        self.programAtmosphere.addShaderFromSourceFile(QtOpenGL.QGLShader.Vertex, os.path.join(CACHE_DIR, "SkyFromSpaceVert.glsl"))
        
        if not self.programAtmosphere.link() :
            print "atmo", self.programAtmosphere.log()          
    
        self.programAtmosphere.bindAttributeLocation('camPos', 10)
 

        self.programStars = QtOpenGL.QGLShaderProgram(self)
        self.programStars.addShaderFromSourceFile(QtOpenGL.QGLShader.Vertex, os.path.join(CACHE_DIR, "vertexBackground.gl"))
        self.programStars.addShaderFromSourceFile(QtOpenGL.QGLShader.Fragment, os.path.join(CACHE_DIR, "fragmentStars.gl"))
        if not self.programStars.link() :
            print "stars", self.programStars.log()  

        self.programBackground = QtOpenGL.QGLShaderProgram(self)
        self.programBackground.addShaderFromSourceFile(QtOpenGL.QGLShader.Vertex, os.path.join(CACHE_DIR, "vertexBackground.gl"))
        self.programBackground.addShaderFromSourceFile(QtOpenGL.QGLShader.Fragment, os.path.join(CACHE_DIR, "fragmentBackground.gl")) 
        if not self.programBackground.link() :
            print "background", self.programBackground.log()        
        
        
        self.programPlanet = QtOpenGL.QGLShaderProgram(self) 
        self.programPlanet.addShaderFromSourceFile(QtOpenGL.QGLShader.Vertex, os.path.join(CACHE_DIR, "vertex.gl"))
        self.programPlanet.addShaderFromSourceFile(QtOpenGL.QGLShader.Fragment, os.path.join(CACHE_DIR, "fragment.gl"))
        
        self.programPlanet.bindAttributeLocation('camPos', 10)
        self.programPlanet.bindAttributeLocation('rotation', 11) 
        
        
        if not self.programPlanet.link() :
            print "planet", self.programPlanet.log()  
#       
        
             
        self.planetsAtmosphere = None
        self.atmosphere = None
        self.object = None
        self.createAtmosphere(self.averageRadius+2)
        self.object     = self.createSphere(self.averageRadius,0)
        self.background = self.createBackground()
        self.zones      = self.createZones()
        self.planets    = self.createPlanets()
        self.galaxyBackground = self.drawGalaxy()
        self.galaxyStarsFront      = self.drawStars(0)
        self.galaxyStarsBack      = self.drawStars(1)
        
        ## TEMP

        self.drawLinks()
        self.createCamera(init=True)
        
        self.timerRotate.start(self.UPDATE_ROTATION)

    def drawGalaxy(self):
        ## BACKGROUND

        genList = GL.glGenLists(1)
        
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.backGroundTexId)
        self.programBackground.bind()
        

        self.programBackground.setUniformValue('texture', 0)

        GL.glPushMatrix()       
        
        sphere  = GLU.gluNewQuadric()
        GLU.gluQuadricTexture(sphere, GL.GL_TRUE)
        GLU.gluQuadricOrientation(sphere, GLU.GLU_INSIDE)
        
        GL.glRotatef(90,1,0,0)
        GL.glScalef(1,1,1)
        
        GLU.gluSphere(sphere, 10000, 10, 10)
        
              
        GL.glPopMatrix()
        GLU.gluDeleteQuadric(sphere)        
        self.programBackground.release()        
        
        GL.glEndList()
        return genList

    
    def drawStars(self, side):
        ## STARS
        
        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.starTexId)
        self.programStars.bind()
        self.programStars.setUniformValue('texture', 0)


        for star in self.galaxy.star_field :
            if side == 0 and star.z < 0 :
                continue
            if side == 1 and star.z > 0 :
                continue            
                
            #GL.glLoadIdentity()
            GL.glPushMatrix()       
            GL.glTranslatef(star.x(), star.y(), star.z())
            #GL.glRotatef(0,0,0,0)
            scale = random.randrange(1,10)/10.0
            GL.glScalef(scale,scale,1)  
            #GL.glActiveTexture(GL.GL_TEXTURE4)
            #GL.glBindTexture(GL.GL_TEXTURE_2D, self.textures[0])
                 
            GL.glCallList(self.background)       
            GL.glPopMatrix()        
        self.programStars.release()

        GL.glEndList()


        
        return genList 

    #
    def createPlanets(self):
        if self.planets :
            GL.glDeleteLists(self.planets, 1)

        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glMatrixMode(GL.GL_MODELVIEW)

 
        for uid in self.galaxy.control_points :
            point = self.galaxy.control_points[uid]            
            pos = point.pos3d
            scale = point.size

            
            self.programPlanet.bind()
            GL.glBindTexture(GL.GL_TEXTURE_2D, point.texture)
            self.programPlanet.setUniformValue('texture', 0)         
            self.programPlanet.setUniformValue('scaling', scale, scale, scale)
            self.programPlanet.setUniformValue('pos', pos.x(), pos.y(), 0.0)          
            GL.glCallList(self.object)
            self.programPlanet.release()
#            
            
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.starTex2Id)
            self.programAtmosphere.bind()
            self.programAtmosphere.setUniformValue('texture', 0)
            self.programAtmosphere.setUniformValue('scaling', scale, scale, scale)
            self.programAtmosphere.setUniformValue('pos', pos.x(), pos.y(), 0.0)
            GL.glCallList(self.atmosphere)         
            self.programAtmosphere.release()
            


        
            
        GL.glEndList()
        return genList 
    
    
    def paintEvent(self, event):
        

        if self.dragPlanet :
            pos3d = self.computeCursorPosition(self.lastMouseEventx, self.lastMouseEventy, True)
            self.galaxy.movePlanet(self.dragPlanet, pos3d.x(), pos3d.y())
            self.createPlanets()

        self.makeCurrent()
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)
        
        GL.glEnable( GL.GL_TEXTURE_2D )
        GL.glCullFace(GL.GL_BACK)
        GL.glFrontFace(GL.GL_CCW)
        GL.glEnable(GL.GL_CULL_FACE)
        
        GL.glEnable(GL.GL_FOG)

        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glBlendFunc (GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable (GL.GL_BLEND)
       

        GL.glLightModelfv(GL.GL_LIGHT_MODEL_AMBIENT, (0.0,0.0,0.0,1.0))


        #Lighting parameters:
        GL.glEnable(GL.GL_LIGHTING);
        GL.glEnable(GL.GL_LIGHT0);
        GL.glEnable(GL.GL_LIGHT1);

        self.light_pos = (-1.0, 0.7, 0.8, 0)
        self.light_pos2 = (0.5, -1.0, -1, 0)
        light_Ka  = (0.1, 0.1, 0.1, 0.0)
        light_Kd  = (1.1, 0.9, 0.8, 1.0)
        light_Ks  = (1.1, 1.0, 0.9, 1.0)


        #
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, self.light_pos)    
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, light_Ka);
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, light_Kd);
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, light_Ks);



        GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, self.light_pos2)    
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_AMBIENT, light_Ka);
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE, (.1, 0.1, .15, 1.0));
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPECULAR, light_Ks);


#        GL.glMatrixMode(GL.GL_MODELVIEW)
#        GL.glLoadIdentity()
        
        GL.glClearDepth(1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        if self.links :
            GL.glPushMatrix()
            GL.glCallList(self.links)
            GL.glPopMatrix()             

        
        if self.drawLink :
            GL.glPushMatrix()
            GL.glLineWidth(3)
            GL.glBegin(GL.GL_LINES)
            
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (1,1,1,1))

            GL.glVertex3f(self.drawLink[2], self.drawLink[3], 0)
            GL.glVertex3f(self.curZone[2], self.curZone[3], 0)
            
#            
            GL.glEnd()
            GL.glPopMatrix()


        GL.glPushMatrix()
        GL.glCallList(self.galaxyBackground)
        GL.glPopMatrix()

        GL.glPushMatrix()
        GL.glCallList(self.galaxyStarsBack)
        GL.glPopMatrix() 
       
        GL.glPushMatrix()
        GL.glCallList(self.zones)        
        GL.glPopMatrix()        


        
        GL.glPushMatrix()
        GL.glCallList(self.planets)
        GL.glPopMatrix()

        GL.glPushMatrix()
        GL.glCallList(self.galaxyStarsFront)
        GL.glPopMatrix() 
        
        

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        self.drawPlanetName(painter)
        #self.drawInstructions(painter)
        painter.end()
    

    def drawPlanetName(self, painter):
        
        if self.curZone :
            site = self.curZone[0]

            x = self.curZone[2]
            y = self.curZone[3]

            pos = self.computeWorldPosition(x, y)
            
            
        
            text = ("Planet number %i" % site)
            metrics = QtGui.QFontMetrics(self.font())
            border = max(4, metrics.leading())
    
            rect = metrics.boundingRect(0, 0, self.width() - 2*border,
                    int(self.height()*0.125),
                    QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, text)
            painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
#            painter.fillRect(QtCore.QRect(0, 0, self.width(), rect.height() + 2*border), QtGui.QColor(0, 0, 0, 127))
            painter.setPen(QtCore.Qt.white)
#            painter.fillRect(QtCore.QRect(0, 0, self.width(), rect.height() + 2*border), QtGui.QColor(0, 0, 0, 127))
            painter.drawText(pos[0], pos[1], rect.width(),
                    rect.height(), QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                    text)
            
    
    def createCamera(self, init = False):
#        if self.animCam.currentTime ()> 20 :
        #self.createPlanets()
        
        
        
        if init == True :
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GLU.gluPerspective(40, float(self.width()) / float(self.height()), 1, self.backgroundDepth)
            
            
        self.r = (self.cameraPos.z())/ (self.zoomMin - self.zoomMax)
        self.ir = 1-self.r

        self.moveBoundaries()
        
        
        orig = QtGui.QVector3D(self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z())
        orig.setZ(orig.z() - 1) 
        orig.setY(orig.y() + pow(self.ir, 5.0))  
        
        
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GLU.gluLookAt(
            self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z() ,
            self.cameraPos.x(), orig.y() ,orig.z() ,
            0.0, 1.0, 0.0)

        self.lookAt = QtGui.QVector3D(self.cameraPos.x(), orig.y() ,orig.z())
        
        
        self.programPlanet.setAttributeValue(10, self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z())
        self.programAtmosphere.setAttributeValue(10, self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z())

        self.repaint()
         


    def resizeGL(self, width, height):

        
        side = min(width, height)
        if side < 0:
            return


        GL.glViewport(0, 0, width, height)
        self.createCamera(True)



    def wheelEvent(self, event):
        ''' when we move the wheel '''

        self.timerRotate.stop()
        self.animCam.stop()
        numDegrees = int(event.delta() / 8)
        numSteps = int(numDegrees / 15) 
                
        self._numScheduledScalings += numSteps
        
        if self._numScheduledScalings * numSteps < 0 :
            self._numScheduledScalings = numSteps

        self.animCam.start()



    def scalingTime(self, val):
        self.rotateOneStep(False)
        factor = 1. - self._numScheduledScalings / 150.0
        self.cameraPos.setZ(self.cameraPos.z() * (factor))
        if not self.moveBoundaries() :
            if factor < 1.0 :
                if self.zooming == False :
                    self.zooming = True
                    
                    pos = self.mapFromGlobal(QtGui.QCursor.pos())
                    self.computeZoomPosition(pos.x(), pos.y())
            else :
                if self.zooming :
                    self.zooming = False
                    self.computeZoomPosition(origin = True)
                    self.zooming = False

            vectorMove = self.vectorMove
            maxSteps = self.zoomMin - self.zoomMax
            curStep = self.cameraPos.z() - self.zoomMax

            mult = (curStep / maxSteps)
           
            mult = 1-(mult * (1/self.currentStep))

            self.cameraPos.setX((self.camOriginPos.x() ) + (vectorMove.x() * mult ))
            self.cameraPos.setY((self.camOriginPos.y() ) + (vectorMove.y() * mult ))

        self.createCamera()

    def animFinished(self) :

        if self._numScheduledScalings > 0 :
            self._numScheduledScalings = self._numScheduledScalings - 1
        else :
            self._numScheduledScalings = self._numScheduledScalings + 1
        self.timerRotate.start(self.UPDATE_ROTATION)

    
    def moveBoundaries(self):
        if self.cameraPos.z() <= self.zoomMax :
            self.cameraPos.setZ(self.zoomMax)
            return True
        
        elif self.cameraPos.z() > self.zoomMin :
            self.cameraPos.setZ(self.zoomMin)        
            return False
        
        if self.cameraPos.x() > self.boundMove.x() : 
            self.cameraPos.setX(self.boundMove.x())
        elif self.cameraPos.x() < -self.boundMove.x() :
            self.cameraPos.setX(-self.boundMove.x())

        if self.cameraPos.y() > self.boundMove.y() : 
            self.cameraPos.setY(self.boundMove.y())
        elif self.cameraPos.y() < -self.boundMove.y() :
            self.cameraPos.setY(-self.boundMove.y())        
    
    def keyPressEvent(self, event):
        self.shift = False
        self.ctrl = False
        if (event.modifiers() & QtCore.Qt.ShiftModifier):
            self.shift = True
        if (event.modifiers() & QtCore.Qt.ControlModifier):
            self.ctrl = True     
            
        if event.key() == 68 :
            self.dumpToSql()
            
    
    def dumpToSql(self):
        
        for uid in self.galaxy.control_points :
            point = self.galaxy.control_points[uid]          
            pos = point.pos3d
            scale = point.size
            links = []
            if point.sitenum in self.galaxy.links :
                 
                links = self.galaxy.links[point.sitenum]
            
            
            pickle.dumps(links, 1)
            
            
            text = "INSERT INTO planets VALUES (%i, GeomFromText('POINT(%i %i)'), %f, '%i', '', %f, %f, %f, %f, '%s');" % (point.sitenum ,pos.x(), pos.y(), scale, point.sitenum, point.uef, point.cybran, point.aeon, point.sera, json.dumps(links))
            print text

            

    def keyReleaseEvent(self, event):
        if not (event.modifiers() & QtCore.Qt.ShiftModifier):
            self.shift = False
        if not (event.modifiers() & QtCore.Qt.ControlModifier):
            self.ctrl = False
            self.drawLink = None
            
        if self.dragPlanet :
            if self.ctrl == False or self.ctrl == False :
                self.stopDrag()
                
    
         

        

    def mousePressEvent(self, event):
        
        if  event.buttons() & QtCore.Qt.LeftButton :
            
            
            
            
            if self.dragPlanet :
                self.stopDrag()
            
            
            elif self.ctrl and self.shift :
                 
                self.dragPlanet = self.galaxy.control_points[self.curZone[0]]

                
            
            elif self.ctrl :
                if not self.drawLink :
                    self.drawLink = self.curZone
                else :
                    if not self.drawLink[0] == self.curZone[0] :
                        self.addLink()
                        
                        

            elif self.shift :
                x = event.x()
                y = event.y()
                pos = self.computeCursorPosition(x,y, True)
                self.galaxy.addPlanet(pos.x(), pos.y())          
                self.zones      = self.createZones()
                self.planets    = self.createPlanets()
        
        
        
        if  event.buttons() & QtCore.Qt.MiddleButton :
            x = event.x()
            y = event.y()
            
            self.lastMouseEventx = x
            self.lastMouseEventy = y
            self.mouseMode = 1

        
    def mouseReleaseEvent(self, event):
        self.mouseMode = 0

    def computeWorldPosition(self, x=0, y=0, invert = True):
        modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)    
        projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
        pos =GLU.gluProject(  x, 
                         y, 
                         0, 
                         modelview, 
                         projection, 
                         viewport)
        
        if invert :
            yresult = float(self.height()) - pos[1]
        else :
            yresult = pos[1]
        return (pos[0], yresult, 0)

    def computeCursorPosition(self, x=0, y=0, exact = False):
        modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        y = float(self.height()) - y
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
           
        projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        


        if exact :
            z = GL.glReadPixels( x, y, 1, 1, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT )[0][0]
        else :
            if not self.zorig :
                self.zorig = GL.glReadPixels( x, y, 1, 1, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT )[0][0]
            z = self.zorig
        mouseWorldSpace = GLU.gluUnProject( float(x), float(y), z, modelview, projection, viewport)

        return QtGui.QVector3D(mouseWorldSpace[0], mouseWorldSpace[1], 0)


    def computeZoomPosition(self, x=0, y=0, origin = False):
        if not origin and self.zooming == True:
            
            cursor = self.computeCursorPosition(x,y)
            self.cursor.setX(cursor.x())
            self.cursor.setY(cursor.y())            
    
            self.destination = self.cursor
            self.camOriginPos = QtGui.QVector3D(self.cameraPos.x(),self.cameraPos.y(), self.cameraPos.z()) 
    
            maxSteps = self.zoomMin - self.zoomMax
            curStep = self.cameraPos.z() - self.zoomMax
    
            mult = (curStep / maxSteps)
            if mult == 0 :
                mult = 0.001
    
            self.vectorMove = QtGui.QVector3D(self.destination.x() - self.cameraPos.x(), self.destination.y() - self.cameraPos.y(), (self.zoomMax -self.cameraPos.z()) )
            self.vectorMove = self.vectorMove * mult
    
            self.currentStep = mult        

        else :
            self.camOriginPos = QtGui.QVector3D(self.cameraPos.x(),self.cameraPos.y(), self.cameraPos.z())
            self.destination = QtGui.QVector3D(0,0,self.zoomMin)
            maxSteps = self.zoomMin - self.zoomMax
            curStep = self.cameraPos.z() - self.zoomMax
    
            mult = (curStep / maxSteps)
            if mult == 0 :
                mult = 0.001
    
            self.vectorMove = QtGui.QVector3D( self.cameraPos.x(),  self.cameraPos.y(), (self.zoomMax -self.cameraPos.z()) )
            self.vectorMove = self.vectorMove * mult
    
            self.currentStep = mult        
            


    def mouseMoveEvent(self, event):

        if self.mouseMode == 1 :
            deltaX = event.x() - float(self.lastMouseEventx)
            deltaY = event.y() - float(self.lastMouseEventy)
            
            self.cameraPos.setX(self.cameraPos.x() - deltaX)
            self.cameraPos.setY(self.cameraPos.y() + deltaY)
            
            self.createCamera() 
            
        x = event.x()
        y = event.y()
        
        self.lastMouseEventx = x
        self.lastMouseEventy = y

        self.computeZoomPosition(x, y)
        
        pos3d = self.computeCursorPosition(x,y, True)

        self.curZone = self.galaxy.closestSite(pos3d.x(), pos3d.y()) 
        

    def stopDrag(self):
        self.galaxy.computeVoronoi()
        self.createZones()
        self.drawLinks()
        self.dragPlanet = None
        

    def drawLinks(self):

        if self.links :
            GL.glDeleteLists(self.links, 1)
        
        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        self.programConstant.bind()
        GL.glLineWidth(2)
        for orig in self.galaxy.links :
            dests = self.galaxy.links[orig]
            for dest in dests :
                GL.glBegin(GL.GL_LINES)
                
                GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (1,1,1,1))
      
                GL.glVertex3f(self.galaxy.control_points[orig].x, self.galaxy.control_points[orig].y, 0)
                GL.glVertex3f(self.galaxy.control_points[dest].x, self.galaxy.control_points[dest].y, 0)
                
                GL.glEnd( ) 
        
        self.programConstant.release()
        GL.glEndList()
        self.links = genList        

    def addLink(self):
        
        self.galaxy.addLink(self.drawLink[0], self.curZone[0])
        self.drawLinks()
        


    def createZones(self):
        if self.zones :
            GL.glDeleteLists(self.zones, 1)
            
        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        
        bevel = 2.0
        opacity = 0.1
        extrude = -7
        origin  = -5
        polyBorders = {}
        #Computing borders polygons          
        for poly in self.galaxy.finalPolys :
            site  = self.galaxy.closest(float(poly.split()[0]), float(poly.split()[1]))
            borders = {}
            points = self.galaxy.finalPolys[poly]
            hull = self.galaxy.monotone_chain(points)


 
            i = 1
            border = 0
            for line in hull :
                if border in borders :
                    if len(borders[border]) != 4 :
                        borders[border].append((line[0], line[1], extrude))
                        borders[border].append((line[0], line[1], origin))

                        border = border + 1
                        borders[border] = [(line[0], line[1], origin)]                       
                        borders[border].append((line[0], line[1], extrude))  
                       

                        if i == len(hull) :
                            borders[border].append((hull[0][0], hull[0][1], extrude))
                            borders[border].append((hull[0][0], hull[0][1], origin))
                            border = border + 1
                        

                else :
                    borders[border] = [(line[0], line[1], origin), (line[0], line[1], extrude)]

                i = i + 1

            polyBorders[poly] = borders


        self.programConstant.bind()


        ## Back faces
        for poly in self.galaxy.finalPolys :
            site  = self.galaxy.closest(float(poly.split()[0]), float(poly.split()[1]))
            center = QtGui.QVector3D(float(poly.split()[0]), float(poly.split()[1]), 0)
            color  = self.galaxy.control_points[site[0]].color
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (color[0],color[1],color[2], opacity))            
            points = self.galaxy.finalPolys[poly]
            hull = self.galaxy.monotone_chain(points)
            GL.glBegin(GL.GL_POLYGON)
            for line in hull :
                vectorOffset = QtGui.QVector3D((line[0] - center.x())   , (line[1] - center.y()) , 0)
                vectorOffset.normalize()
                vectorOffset = vectorOffset * bevel 
                GL.glVertex3f(line[0] - vectorOffset.x(), line[1] - vectorOffset.y(), extrude)
            GL.glEnd( ) 

        ## borders
        for poly in  polyBorders :
            site  = self.galaxy.closest(float(poly.split()[0]), float(poly.split()[1]))
            color  = self.galaxy.control_points[site[0]].color
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (color[0],color[1],color[2], opacity * 1.5))
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (.2,.2,.2, 1))
            center = QtGui.QVector3D(float(poly.split()[0]), float(poly.split()[1]), 0)
            polyBorder = polyBorders[poly]
            for i in polyBorder :
                border = polyBorder[i]
                GL.glBegin(GL.GL_POLYGON)
                for point in border :
                    vectorOffset = QtGui.QVector3D((point[0] - center.x()) * bevel  , (point[1] - center.y()) * bevel, 0) 
                    vectorOffset.normalize()
                    vectorOffset = vectorOffset * bevel
                    GL.glVertex3f(point[0]  - vectorOffset.x(), point[1]  - vectorOffset.y(), point[2])
                GL.glEnd( )

            for i in polyBorder :
                border = polyBorder[i]
                border.reverse()
                GL.glBegin(GL.GL_POLYGON)
                for point in border :
                    vectorOffset = QtGui.QVector3D((point[0] - center.x()) * bevel  , (point[1] - center.y()) * bevel, 0) 
                    vectorOffset.normalize()
                    vectorOffset = vectorOffset * bevel
                    GL.glVertex3f(point[0]  - vectorOffset.x(), point[1]  - vectorOffset.y(), point[2])
                GL.glEnd( )        


        ## Front faces
        for poly in self.galaxy.finalPolys :
            
            site  = self.galaxy.closest(float(poly.split()[0]), float(poly.split()[1]))
            center = QtGui.QVector3D(float(poly.split()[0]), float(poly.split()[1]), 0)
            color  = self.galaxy.control_points[site[0]].color
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (color[0],color[1],color[2], opacity))
            points = self.galaxy.finalPolys[poly]
            hull = self.galaxy.monotone_chain(points)
            
            #hull.reverse()
            GL.glBegin(GL.GL_POLYGON)
            for line in hull :
                vectorOffset = QtGui.QVector3D((line[0] - center.x()) * bevel  , (line[1] - center.y()) * bevel, 0) 
                vectorOffset.normalize()
                vectorOffset = vectorOffset * bevel
                GL.glVertex3f(line[0] - vectorOffset.x(), line[1] - vectorOffset.y(), origin)
            GL.glEnd( )         

        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (.5,.5,.6, .5))
        GL.glBegin(GL.GL_POLYGON)
        GL.glVertex3f(self.galaxy.space_size.x()+50, -self.galaxy.space_size.y()-50, extrude)
        GL.glVertex3f(self.galaxy.space_size.x()+50, self.galaxy.space_size.y()+50, extrude)
        GL.glVertex3f(-self.galaxy.space_size.x()-50, self.galaxy.space_size.y()+50, extrude)
        GL.glVertex3f(-self.galaxy.space_size.x()-50, -self.galaxy.space_size.y()-50, extrude)
        GL.glEnd( )


        self.programConstant.release()
        

              
                
            
        
        GL.glEndList()
        return genList
    def createBackground(self):
        
        
        genList = GL.glGenLists(1)
        
        GL.glScalef (10, 10, 10)
        GL.glRotatef (90, 0, 0, 0);
        
        GL.glNewList(genList, GL.GL_COMPILE)
        
        GL.glBegin(GL.GL_QUAD_STRIP)

        GL.glNormal3f(0, 1, 0)       


        GL.glTexCoord2f(0, 1)
        GL.glVertex3f(-1.0, 1.0, 0.0)
        GL.glTexCoord2f(0, 0)
        GL.glVertex3f(-1.0, -1.0, 0.0)
        GL.glTexCoord2f(1, 1)
        GL.glVertex3f(1.0, 1.0, 0.0) 
        GL.glTexCoord2f(1, 0)
        GL.glVertex3f(1.0, -1.0, 0.0)

        

        GL.glEnd()
        
        GL.glEndList()

        return genList            
        
    
    def billBoardingBegin(self):
        GL.glPushMatrix()
        modelview = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)
        
        matrix = []
        
        for i in range(0,3) :
            #print i
            
            for j in range(3) :

                if i == j :
                    
                    modelview[i][j] = 1.0
                else :
                    modelview[i][j] = 0.0
                    
        print "----"
        for row in modelview :
            for col in row :
                matrix.append(col)
        
        modelMatrix = QtGui.QMatrix4x4(matrix)
        #print modelMatrix        
            
        GL.glLoadMatrixf(modelview)
        
    def billBoardingEnd(self):
        GL.glPopMatrix()
    
    def createAtmosphere(self, R):
        if self.atmosphere :
            GL.glDeleteLists(self.atmosphere,1)        
        
        R = R * 1.1
        genList = GL.glGenLists(1)
        

        GL.glNewList(genList, GL.GL_COMPILE)        
        #GL.glBindTexture(GL.GL_TEXTURE_2D, self.starTexId)
        
#        matrix1 = QtGui.QMatrix4x4()
#        matrix1.setToIdentity()
        #matrix1.rotate(90, 0, 1, 0)
        #GL.glMultMatrixf((matrix1).data())

        GL.glBegin(GL.GL_QUAD_STRIP)

        GL.glNormal3f(0, 1, 0)       
        GL.glTexCoord2f(0, 1)
        GL.glVertex3f(-R, R, 0.0)
        GL.glTexCoord2f(0, 0)
        GL.glVertex3f(-R, -R, 0.0)
        GL.glTexCoord2f(1, 1)
        GL.glVertex3f(R, R, 0.0) 
        GL.glTexCoord2f(1, 0)
        GL.glVertex3f(R, -R, 0.0)

        

        GL.glEnd()
        
        #GL.glActiveTexture(GL.GL_TEXTURE3)


        GL.glEndList()


        self.atmosphere = genList 

    def createSphere(self, R, rot = 0):
        
        
        
        if self.object :
            GL.glDeleteLists(self.object,1)

        genList = GL.glGenLists(1)
       
        sphere  = GLU.gluNewQuadric()
        
        
        
        GL.glNewList(genList, GL.GL_COMPILE)
        
        

        material_Ka = (0.5, 0.5, 0.5, 1.0)
        material_Kd = (0.8, 0.8, 0.8, 1.0)
        material_Ks = (0.3, 0.3, 0.3, 1.0)
        material_Ke = (0.1, 0.0, 0.0, 1.0)
        material_Se = 20.0        
        
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT, material_Ka)
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, material_Kd)
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, material_Ks)
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_EMISSION, material_Ke)
        GL.glMaterialf(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, material_Se)      
        GL.glPushMatrix()

        GLU.gluQuadricTexture(sphere, GL.GL_TRUE)
        GLU.gluQuadricOrientation(sphere, GLU.GLU_OUTSIDE)

        GLU.gluSphere(sphere,R, 40, 40)
       

        GLU.gluDeleteQuadric(sphere)
        
        GL.glPopMatrix()
        GL.glEndList()
        
        

        return genList        

    def normalizeAngle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle