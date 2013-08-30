
from galacticWar import logger
import logging
import warnings
from PyQt4 import QtCore, QtGui, QtOpenGL

logger = logging.getLogger("faf.galacticWar")
logger.setLevel(logging.DEBUG)
try:
    from OpenGL import GL
    from OpenGL import GLU
except:
    pass
warnings.simplefilter("error")
from fa import maps
import fa

from galacticWar import FACTIONS, RANKS

import math
import random
import os
import util
from util import GW_TEXTURE_DIR
import pickle

class GLWidget(QtOpenGL.QGLWidget):
    xRotationChanged = QtCore.pyqtSignal(int)
    yRotationChanged = QtCore.pyqtSignal(int)
    zRotationChanged = QtCore.pyqtSignal(int)
    
    UPDATE_ROTATION = 22

    def __init__(self, parent=None):
        if parent.AA:
            super(GLWidget, self).__init__(QtOpenGL.QGLFormat(QtOpenGL.QGL.SampleBuffers), parent)
        else:
            super(GLWidget, self).__init__(parent)
        
        self.parent = parent
        self.setMinimumWidth((self.parent.width()/100)*70)
        self.galaxy = self.parent.galaxy
            
        
        self.COLOR_FACTIONS = self.parent.COLOR_FACTIONS

        self.ctrl       = False
        self.shift      = False

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

        self.galaxyStarsFront      = None
        self.galaxyStarsBack      = None
        
        self.curZone        = None
        self.overlayPlanet  = False
        self.attackVector   = None
        self.animAttackVector = 0
        
        self.zoomMin = 1500
        self.zoomMax = 10
        self.cameraPos  = QtGui.QVector3D(0,0,self.zoomMin)
        self.vectorMove = QtGui.QVector3D(0,0,self.zoomMin)
        
        self.zooming = False
        
        self.starField()

        
        
        self.cursor = QtGui.QVector3D(0,0,0)
        self.destination = QtGui.QVector3D(0,0,0)

        self.r = 0
        self.ir = 0

        self._numScheduledScalings = 0
        self.currentStep = 0.001

        
        self.lastPos = QtCore.QPoint()

        self.timerRotate = QtCore.QTimer(self)
        self.timerRotate.timeout.connect(self.rotateOneStep)
        
        
        self.animCam = QtCore.QTimeLine(300, self)

        self.animCam.setUpdateInterval(self.UPDATE_ROTATION/2)
        self.animCam.valueChanged.connect(self.scalingTime)
        self.animCam.finished.connect(self.animFinished)
        
        self.parent.attacksUpdated.connect(self.planetsUnderAttack)
        self.parent.planetUpdated.connect(self.planetUpdate)
        
        self.setMouseTracking(1)
        self.setAutoFillBackground(False)
        
        self.setAcceptDrops(True)
    
    def starField(self):
        self.galaxy.generate_star_field(self.zoomMin, -self.zoomMin)
        

    def rotateOneStep(self, update = True): 
        if not update :
            self.yRot = self.yRot + math.radians(self.UPDATE_ROTATION*0.04)
        else :
            self.yRot = self.yRot + math.radians(self.UPDATE_ROTATION*0.04 * 2)
        if self.yRot >= math.radians(360) :
            self.yRot = 0.0
        
        self.programPlanet.setAttributeValue(11, self.yRot)
        
        self.programSwirl.setAttributeValue(self.programSwirl.attributeLocation("rotation_plane"), self.yRot * 10)
        
        
        
        if update :
            self.update()


    def minimumSizeHint(self):
        return QtCore.QSize(50, 50)

    def sizeHint(self):
        return QtCore.QSize(400, 400)

    def initializeGL(self):
        self.textures = []
            

        for uid in self.galaxy.control_points :
            site = self.galaxy.control_points[uid]
            site.texture = self.bindTexture(QtGui.QPixmap(os.path.join(GW_TEXTURE_DIR,'%s.png' % site.texname)), GL.GL_TEXTURE_2D)   

        
        self.backGroundTexId    = self.bindTexture(QtGui.QPixmap(os.path.join(GW_TEXTURE_DIR,'background.png')), GL.GL_TEXTURE_2D)
        self.starTexId          = self.bindTexture(QtGui.QPixmap(os.path.join(GW_TEXTURE_DIR,'star.png')), GL.GL_TEXTURE_2D)
        self.starTex2Id         = self.bindTexture(QtGui.QPixmap(os.path.join(GW_TEXTURE_DIR,'star.png')), GL.GL_TEXTURE_2D)        
        self.selectionId        = self.bindTexture(QtGui.QPixmap(os.path.join(GW_TEXTURE_DIR,'star.png')), GL.GL_TEXTURE_2D)
        self.attackId           = self.bindTexture(QtGui.QPixmap(os.path.join(GW_TEXTURE_DIR,'attack.png')), GL.GL_TEXTURE_2D)


        
        
        self.programConstant = QtOpenGL.QGLShaderProgram(self)
        if not self.programConstant.addShaderFromSourceCode(QtOpenGL.QGLShader.Vertex, self.parent.shaders["constant"]["vertex"]) :
            logger.error("Cannot compile constant vertex shader : %s " % self.programConstant.log())
        if not self.programConstant.addShaderFromSourceCode(QtOpenGL.QGLShader.Fragment, self.parent.shaders["constant"]["fragment"]) :
            logger.error("Cannot compile constant fragment shader : %s " % self.programConstant.log())  
        if not self.programConstant.link() :
            logger.error("Cannot link constant shader : %s " % self.programConstant.log())
        else :
            logger.info("constant shader linked.")
 

        self.programAtmosphere = QtOpenGL.QGLShaderProgram(self)        
        if not self.programAtmosphere.addShaderFromSourceCode(QtOpenGL.QGLShader.Vertex, self.parent.shaders["atmosphere"]["vertex"]) :
            logger.error("Cannot compile atmosphere vertex shader : %s " % self.programAtmosphere.log())
        if not self.programAtmosphere.addShaderFromSourceCode(QtOpenGL.QGLShader.Fragment, self.parent.shaders["atmosphere"]["fragment"]) :
            logger.error("Cannot compile atmosphere fragment shader : %s " % self.programAtmosphere.log())
        
        if not self.programAtmosphere.link() :
            logger.error("Cannot link atmosphere shader : %s " % self.programAtmosphere.log())
        else :
            logger.info("atmosphere shader linked.")
          
    
        self.programAtmosphere.bindAttributeLocation('camPos', 10)
        

        self.programStars = QtOpenGL.QGLShaderProgram(self)
        if not self.programStars.addShaderFromSourceCode(QtOpenGL.QGLShader.Vertex, self.parent.shaders["stars"]["vertex"]) :
            logger.error("Cannot compile star vertex shader : %s " % self.programStars.log())
        if not self.programStars.addShaderFromSourceCode(QtOpenGL.QGLShader.Fragment, self.parent.shaders["stars"]["fragment"]) :
            logger.error("Cannot compile star fragment shader : %s " % self.programStars.log())
        if not self.programStars.link() :
            logger.error("Cannot link star shader : %s " % self.programStars.log())
        else :
            logger.info("star shader linked.")

        self.programBackground = QtOpenGL.QGLShaderProgram(self)
        if not self.programBackground.addShaderFromSourceCode(QtOpenGL.QGLShader.Vertex, self.parent.shaders["background"]["vertex"]) :
            logger.error("Cannot compile background vertex shader : %s " % self.programBackground.log())
        if not self.programBackground.addShaderFromSourceCode(QtOpenGL.QGLShader.Fragment, self.parent.shaders["background"]["fragment"]) :
            logger.error("Cannot compile background fragment shader : %s " % self.programBackground.log()) 
        if not self.programBackground.link() :
            logger.error("Cannot link background shader : %s " % self.programBackground.log())
        else :
            logger.info("background shader linked.")       
        
        
        self.programPlanet = QtOpenGL.QGLShaderProgram(self) 
        if not self.programPlanet.addShaderFromSourceCode(QtOpenGL.QGLShader.Vertex, self.parent.shaders["planet"]["vertex"]) :
            logger.error("Cannot compile planet vertex shader : %s " % self.programPlanet.log())
        if not self.programPlanet.addShaderFromSourceCode(QtOpenGL.QGLShader.Fragment, self.parent.shaders["planet"]["fragment"]) :
            logger.error("Cannot compile planet fragment shader : %s " % self.programPlanet.log())
        self.programPlanet.bindAttributeLocation('camPos', 10)
        self.programPlanet.bindAttributeLocation('rotation', 11) 

        if not self.programPlanet.link() :
            logger.error("Cannot link planet shader : %s " % self.programPlanet.log())
        else :
            logger.info("planet shader linked.")   
        

        
        self.programSelection = QtOpenGL.QGLShaderProgram(self)        
        if not self.programSelection.addShaderFromSourceCode(QtOpenGL.QGLShader.Vertex, self.parent.shaders["selection"]["vertex"]) :
            logger.error("Cannot compile selection vertex shader : %s " % self.programSelection.log())
        if not self.programSelection.addShaderFromSourceCode(QtOpenGL.QGLShader.Fragment, self.parent.shaders["selection"]["fragment"]) :
            logger.error("Cannot compile selection fragment shader : %s " % self.programSelection.log())
            
        self.programSelection.bindAttributeLocation('camPos', 10)
        self.programSelection.bindAttributeLocation('pos', 12)        
        self.programSelection.bindAttributeLocation('scaling', 13)
        
        if not self.programSelection.link() :
            logger.error("Cannot link selection shader : %s " % self.programSelection.log())
        else :
            logger.info("selection shader linked.")            

        self.programSwirl = QtOpenGL.QGLShaderProgram(self)        
        if not self.programSwirl.addShaderFromSourceCode(QtOpenGL.QGLShader.Vertex, self.parent.shaders["swirl"]["vertex"]) :
            logger.error("Cannot compile swirl vertex shader : %s " % self.programSwirl.log())
        if not self.programSwirl.addShaderFromSourceCode(QtOpenGL.QGLShader.Fragment, self.parent.shaders["swirl"]["fragment"]) :
            logger.error("Cannot compile swirl fraglent shader : %s " % self.programSwirl.log())
        self.programSwirl.bindAttributeLocation('rotation_plane', 14)        

        
        if not self.programSwirl.link() :
            logger.error("Cannot link swirl shader : %s " % self.programSwirl.log())
        else :
            logger.info("swirl shader linked.")            


        self.planetsAtmosphere = None
        self.atmosphere = None
        self.object = None
        self.selection = None
        self.underAttack = None        
        self.attackVectorGl = None
        
        self.createAtmosphere(self.averageRadius+2)
        self.object     = self.createSphere(self.averageRadius,0)
        self.background = self.createBackground()
        self.plane      = self.createPlane()
        self.zones      = self.createZones()
        self.planets    = self.createPlanets()
        self.selection  = self.createPlanetOverlay()
        self.galaxyBackground = self.drawGalaxy()
        self.underAttack      = self.planetsUnderAttack()
        self.galaxyStarsFront      = self.drawStars(0)
        self.galaxyStarsBack      = self.drawStars(1)
        
        ## TEMP

        self.drawLinks()
        self.createCamera(init=True)
        if self.parent.rotation:
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
       
        if side == 0:
            if self.galaxyStarsFront :
                GL.glDeleteLists(self.galaxyStarsFront, 1)
        else:
            if self.galaxyStarsBack :
                GL.glDeleteLists(self.galaxyStarsBack, 1)
        
        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (1,1,1,1))
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.starTexId)
        self.programStars.bind()
        self.programStars.setUniformValue('texture', 0)


        for star in self.galaxy.star_field :
            
            if side == 0 and star.z() < 0 :
                continue
            if side == 1 and star.z() > 0 :
                continue            
                
            GL.glPushMatrix()
                   
            GL.glTranslatef(star.x(), star.y(), star.z())
            scale = random.randrange(1,10)/10.0
            GL.glScalef(scale,scale,1)  
                 
            GL.glCallList(self.background)       
            GL.glPopMatrix()        
        self.programStars.release()

        GL.glEndList()


        
        return genList 

    #
    def createPlanets(self):
        logger.info("Creating planets")
        
        if self.planets :
            GL.glDeleteLists(self.planets, 1)

        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        ordered = {}
        
 
        for uid in self.galaxy.control_points :
            point = self.galaxy.control_points[uid]            
            pos = point.pos3d


            if not pos.y() in ordered :
                ordered[pos.y()] = [self.galaxy.control_points[uid]]
            else :
                ordered[pos.y()].append(self.galaxy.control_points[uid])
            
        for key in sorted(ordered.iterkeys(), reverse=True):
            for point in ordered[key] : 
                pos = point.pos3d
                scale = point.size
                self.programPlanet.bind()
                GL.glBindTexture(GL.GL_TEXTURE_2D, point.texture)
                self.programPlanet.setUniformValue('texture', 0)         
                self.programPlanet.setUniformValue('scaling', scale, scale, scale)
                self.programPlanet.setUniformValue('pos', pos.x(), pos.y(), 5.0)          
                GL.glCallList(self.object)
                self.programPlanet.release()
          
                
                GL.glBindTexture(GL.GL_TEXTURE_2D, self.starTex2Id)
                self.programAtmosphere.bind()
                self.programAtmosphere.setUniformValue('texture', 0)
                self.programAtmosphere.setUniformValue('scaling', scale, scale, scale)
                self.programAtmosphere.setUniformValue('pos', pos.x(), pos.y(), 5.0)
                GL.glCallList(self.atmosphere)         
                self.programAtmosphere.release()
                
        GL.glEndList()
        return genList 
    
    def planetUpdate(self):
        self.zones = self.createZones()
    
    def planetsUnderAttack(self):
        if not hasattr(self, "underAttack"):
            return
       
        if self.underAttack :
            GL.glDeleteLists(self.underAttack, 1)

        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glMatrixMode(GL.GL_MODELVIEW)        
        

        for useruid in self.parent.attacks :
            for planetuid in self.parent.attacks[useruid] :
                uid = int(planetuid)
                
                if uid in self.galaxy.control_points :
                    
                    if self.parent.attacks[useruid][planetuid]["onHold"] == True :
                        color = QtGui.QColor(255,255,255)
                    else :
                        color = self.COLOR_FACTIONS[int(self.parent.attacks[useruid][planetuid]["faction"])]
                    self.programSwirl.bind()
                    
                    if self.parent.attacks[useruid][planetuid]["defended"] :
                        GL.glBindTexture(GL.GL_TEXTURE_2D, self.selectionId)
                        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (color.redF(),color.greenF(),color.blueF(), .6))
                    else :
                        GL.glBindTexture(GL.GL_TEXTURE_2D, self.attackId)
                        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (color.redF(),color.greenF(),color.blueF(), 1))
                        
                    self.programSwirl.setUniformValue('texture', 0)
                    
                    site = self.galaxy.control_points[uid]
                    pos = site.pos3d
                    scale = site.size * 10
                    self.programSwirl.setUniformValue('rotation', 1.0, 0, 0)
                    self.programSwirl.setUniformValue('scaling', scale, scale, scale)
                    self.programSwirl.setUniformValue('pos', pos.x(), pos.y(), scale)
                    
                    GL.glCallList(self.plane)

        
                    self.programSwirl.release()
        
        GL.glEndList()
        self.underAttack = genList 
        return genList 
    
    def createAttackVector(self):
        
        if self.attackVectorGl :
            GL.glDeleteLists(self.attackVectorGl, 1)        

        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glMatrixMode(GL.GL_MODELVIEW)        
        
        rot = 0
        if self.galaxy.control_points[self.attackVector[1]].pos3d.y() < self.galaxy.control_points[self.attackVector[0]].pos3d.y() :
            orig = self.galaxy.control_points[self.attackVector[1]].pos3d
            dest = self.galaxy.control_points[self.attackVector[0]].pos3d

            destScale = self.galaxy.control_points[self.attackVector[1]].size
            origScale = self.galaxy.control_points[self.attackVector[0]].size
            rot = 20
        else :
            orig = self.galaxy.control_points[self.attackVector[0]].pos3d
            dest = self.galaxy.control_points[self.attackVector[1]].pos3d

            destScale = self.galaxy.control_points[self.attackVector[0]].size
            origScale = self.galaxy.control_points[self.attackVector[1]].size
            rot = -20
            
            
        
        animVector = orig - dest
        
        steps = int(animVector.length() / 2)
        if steps == 0 :
            steps = 2
        
        for i in range(steps + 1) :
            pos = i / float(steps)
            
            self.programSwirl.bind()
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.attackId)
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (0.4,.6,.9, 1))
            self.programSwirl.setUniformValue('texture', 0)  
            
            scale = (origScale + pos * (destScale - origScale)) * 5

            self.programSwirl.setUniformValue('scaling', scale, scale, scale)
            self.programSwirl.setUniformValue('pos', dest.x() + animVector.x() * pos, dest.y() + animVector.y() * pos, 5+(scale) + (3*pos))
            self.programSwirl.setUniformValue('rotation', math.radians(i * rot),0,0)
            GL.glCallList(self.background)
            self.programSwirl.release()

        
        GL.glEndList()
        return genList         
    
    def drawAttackVector(self):
        
        
        
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.attackId)
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (0.4,.6,.9, 1))
        self.programStars.bind()
        self.programStars.setUniformValue('texture', 0)

        orig = self.galaxy.control_points[self.attackVector[0]].pos3d
        dest = self.galaxy.control_points[self.attackVector[1]].pos3d

        destScale = self.galaxy.control_points[self.attackVector[0]].size
        origScale = self.galaxy.control_points[self.attackVector[1]].size
        
        animVector = orig - dest
        
        steps = int(animVector.length() / 2) 
        
        for i in range(steps + 1) :
            pos = i / float(steps)
            GL.glPushMatrix()
            
            scale = (origScale + pos * (destScale - origScale)) * 5
            
            GL.glTranslatef( dest.x() + animVector.x() * pos, dest.y() + animVector.y() * pos, 5+(scale) + (3*pos))

            GL.glScalef(scale,scale,scale)
            GL.glRotatef(self.animAttackVector - i * 20, 0, 0, 1)     
            GL.glCallList(self.background)       
            GL.glPopMatrix()        

        
        
        self.animAttackVector = self.animAttackVector + 30 
        if self.animAttackVector > 360 :
            self.animAttackVector = 0
        
        
 
        self.programStars.release()
        
        
    
    def paintEvent(self, event):
        if fa.exe.running():
            return
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

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, self.light_pos)    
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, light_Ka);
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, light_Kd);
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, light_Ks);



        GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, self.light_pos2)    
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_AMBIENT, light_Ka);
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE, (.1, 0.1, .15, 1.0));
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPECULAR, light_Ks);

        
        GL.glClearDepth(1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        if self.links :
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (1,1,1,1))
            GL.glCallList(self.links)

        GL.glCallList(self.galaxyBackground)

        GL.glCallList(self.galaxyStarsBack)

        GL.glCallList(self.zones)

        GL.glCallList(self.planets)


        if self.curZone :                       
            GL.glCallList(self.selection)

        

        if self.underAttack :
            GL.glCallList(self.underAttack)
     
        if self.attackVectorGl :
            GL.glCallList(self.attackVectorGl)


        GL.glCallList(self.galaxyStarsFront)

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable( GL.GL_TEXTURE_2D )
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glDisable(GL.GL_LINE_SMOOTH)
        GL.glDisable (GL.GL_BLEND)            


        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier :
            self.drawAllPlanetName(painter)
        else :
            self.drawPlanetName(painter)

        
        
        painter.end()
    
    
    def createPlanetOverlay(self):
        if self.selection :
            GL.glDeleteLists(self.selection, 1)

        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        self.programSelection.bind()
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.selectionId)
        self.programSelection.setUniformValue('texture', 0)
        if self.curZone : 
            pos = self.galaxy.control_points[self.curZone[0]].pos3d
            scale  = self.galaxy.control_points[self.curZone[0]].size * 10
            self.programSelection.setAttributeValue(12, pos.x(), pos.y(), 5.1)
            self.programSelection.setAttributeValue(13, scale, scale, scale )
            
        GL.glCallList(self.background)         
        self.programSelection.release()        
        GL.glEndList()
        return genList               

    def drawAllPlanetName(self, painter):
        ''' paint all planet name in overlay '''

        painter.setOpacity(1)
        
        for site in self.galaxy.control_points :

            

            x = self.galaxy.control_points[site].x
            y = self.galaxy.control_points[site].y

            pos = self.computeWorldPosition(x, y)
        
            if pos[0] < 0 or pos[1] < 0 or pos[0] > self.width() or pos[1] > self.height() :
                continue

       
            painter.save()
            text = "<font color='silver'>%s</font>" % (self.galaxy.get_name(site))
            
            
            html = QtGui.QTextDocument()
            html.setHtml(text)
            width = html.size().width()
            height = html.size().height()


            painter.setPen(QtCore.Qt.white)
            
            painter.translate(pos[0] - width/2, pos[1] - height/2)
            painter.fillRect(QtCore.QRect(0, 0, width+5, height), QtGui.QColor(36, 61, 75, 150))
            clip = QtCore.QRectF(0, 0, width, height)
            html.drawContents(painter, clip)

            painter.restore()
    
    def drawPlanetName(self, painter):
        if self.curZone :
            width = 300
            painter.setOpacity(1)
            site = self.curZone[0]

            x = self.curZone[2]
            y = self.curZone[3]

            pos = self.computeWorldPosition(x, y)

            planet = self.galaxy.control_points[site]


            icon = maps.preview(planet.mapname)
            if not icon:
                self.parent.client.downloader.downloadMap(planet.mapname, None)

            text = "<font color='silver'><h2>%s</h2><table width='%i'><tr><td><p align='justify'><font color='silver' size='7pt'>%s</font</p></tr></td></table><font color='silver'><h4>Occupation:</h4></font><ul>" % (self.galaxy.get_name(site), width-5, self.galaxy.get_description(site))
            
            
            
            for i in range(4) :
                occupation = planet.occupation(i)
                if occupation != 0 :
                    occupation = occupation*100
                    if abs(occupation-round(occupation)) < 0.01 :
                        text += "<li><font color='%s'>%s</font><font color='silver'> : %i &#37;</font></li>" % (self.COLOR_FACTIONS[i].name(), FACTIONS[i], int(occupation))
                    else :
                        text += "<li><font color='%s'>%s</font><font color='silver'> : %.1f &#37;</font></li>" % (self.COLOR_FACTIONS[i].name(), FACTIONS[i], occupation)

                    
            text += "</ul>"

            for useruid in self.parent.attacks :
                for planetuid in self.parent.attacks[useruid] :
                    uid = int(planetuid)
                    if uid == site :
                        if self.parent.attacks[useruid][planetuid]["onHold"] == True :
                            text += "<font color='silver'><h2>Attack on hold.</font></h2>"
                        else :
                            faction = int(self.parent.attacks[useruid][planetuid]["faction"])
                            text += "<font color='red'><h2>Under %s Attack !</font></h2>" % (FACTIONS[faction])
                            
                            # Handling additional infos about attackers
                            if len(self.parent.attacks[useruid][planetuid]["attackers"]) > 0 :
                                text += "<font color='red'>Attackers :</font><br>"
                                names = []
                                for player in self.parent.attacks[useruid][planetuid]["attackers"] :
                                    rank = int(player[0])
                                    if player[1] != "Unknown" :
                                        name = "<font color='red'>%s(%i) %s</font>" % (RANKS[faction][rank], rank+1, player[1])
                                    else :
                                        name = "<font color='red'>%s(%i)</font>" % (RANKS[faction][rank], rank+1)
                                    names.append(name)
                                
                                
                                text += "<br>".join(names)
                            
                            
                            if self.parent.attacks[useruid][planetuid]["defended"] :
                                text += "<font color='green'><h2>Planet is currently defended!</font></h2>"
            
            painter.save()
            html = QtGui.QTextDocument()
            html.setHtml(text)
            html.setTextWidth(width)
            height = html.size().height() + 10
            width = html.size().width()
            #QtCore.Qrect(height, height+icon.)
            


            painter.setPen(QtCore.Qt.white)

            posx = pos[0]+20
            posy = pos[1]+20
            
            if (posy + height+100) > self.height() :
                posy = self.height() - (height + 100)

            if (posx + width) > self.width() :
                posx = self.width() - width - 20

            mapSize = 100
            painter.translate(posx, posy)
            painter.fillRect(QtCore.QRect(0, 0, width+5, height+mapSize), QtGui.QColor(36, 61, 75, 150))
            clip = QtCore.QRectF(0, 0, width, height)
            html.drawContents(painter, clip)
            if icon :
                painter.translate(0, height)
                icon.paint(painter, QtCore.QRect(0, 0, mapSize, mapSize), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)

             
            startItems = mapSize + 5
            painter.translate(startItems, 0)
            defenses = planet.getDefenses()
            itemsWidth = 0
            itemSize = 35
            for uid in defenses :
                item = defenses[uid]
                amount = item.amount
                if amount == 0:
                    continue
                structure = item.structure
                iconName = "%s_icon.png" % structure
                
                iconStructure = util.iconUnit(iconName)
                iconStructure.paint(painter, QtCore.QRect(0, 0, itemSize, itemSize), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
                painter.drawText(QtCore.QPoint(itemSize-5,itemSize-5), "%iX" % amount)
                itemsWidth = itemsWidth + itemSize
                
                if itemsWidth + itemSize + startItems > width:
                    painter.translate(-itemsWidth, itemSize)
                painter.translate(itemSize, 0)
                
            painter.restore()
            
    
    def createCamera(self, init = False):
        
        if init == True :
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GLU.gluPerspective(40, float(self.width()) / float(self.height()), 1, self.backgroundDepth)
        
                    
        self.r = (self.cameraPos.z())/ (self.zoomMin - self.zoomMax)
        self.ir = 1.0-self.r

        self.moveBoundaries()
        
        
        orig = QtGui.QVector3D(self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z())
        orig.setZ(orig.z() - 1.0) 
        orig.setY(orig.y() + pow(self.ir, 5.0))  
        
        
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GLU.gluLookAt(
            self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z() ,
            self.cameraPos.x(), orig.y() ,orig.z() ,
            0.0, 1.0, 0.0)      
        
        self.programPlanet.setAttributeValue(10, self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z())
        self.programAtmosphere.setAttributeValue(10, self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z())
        self.programSelection.setAttributeValue(10, self.cameraPos.x(), self.cameraPos.y(), self.cameraPos.z())
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
        if self.parent.rotation:
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
    
    
    def dropEvent(self, event):
        data = event.mimeData()
        bstream = data.retrieveData("application/x-building-reinforcement", QtCore.QVariant.ByteArray)
        selected = int(pickle.loads(bstream))
        
        if self.curZone :
            site = self.curZone[0]
            planet = self.galaxy.control_points[site]
        
            if selected in self.parent.planetaryItems.planetaryReinforcements:
                item = self.parent.planetaryItems.planetaryReinforcements[selected]
            
                question = QtGui.QMessageBox.question(self,"Defense system", "Build %s on %s ?" % (item.description, planet.name), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                if question == QtGui.QMessageBox.Yes :
                    self.parent.send(dict(command="buy_building", planetuid=site, uid=item.uid))        

        
        
        event.accept()
        
    def dragEnterEvent(self, event) :
        if event.mimeData().hasFormat("application/x-building-reinforcement"):
            event.accept()
        else:
            event.ignore()
        
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-building-reinforcement"):
            event.setDropAction(QtCore.Qt.MoveAction)

            x = event.pos().x()
            y = event.pos().y()
            if self.mouseMode == 0 :
                self.computeZoomPosition(x, y)
            
            pos3d = self.computeCursorPosition(x,y, True)
            if not self.overlayPlanet :
                self.curZone = self.galaxy.closestSite(pos3d.x(), pos3d.y())
                if self.curZone : 
                    self.selection = self.createPlanetOverlay()            
            
            event.accept()
        else:
            event.ignore()
 

                        

    
    def keyPressEvent(self, event):

        self.shift = False
        self.ctrl = False
        if (event.modifiers() & QtCore.Qt.ShiftModifier):
            self.shift = True
        if (event.modifiers() & QtCore.Qt.ControlModifier):
            self.ctrl = True 

            

    def keyReleaseEvent(self, event):
        if not (event.modifiers() & QtCore.Qt.ShiftModifier):
            self.shift = False
        if not (event.modifiers() & QtCore.Qt.ControlModifier):
            self.ctrl = False


    def mousePressEvent(self, event):
        
        if  event.buttons() & QtCore.Qt.LeftButton :
            self.overlayPlanet = not self.overlayPlanet
            if self.overlayPlanet :
                self.parent.planetClicked.emit(self.curZone[0])
                self.attackable()
            else :
                self.parent.hovering.emit()
                self.attackVector = None
                self.attackVectorGl = None

        elif  event.buttons() & QtCore.Qt.MiddleButton :
            self.animCam.stop()
            if self.parent.rotation:
                self.timerRotate.start(self.UPDATE_ROTATION)
            
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

        if self.mouseMode == 0 :
            self.computeZoomPosition(x, y)
        
        pos3d = self.computeCursorPosition(x,y, True)
        if not self.overlayPlanet :
            self.curZone = self.galaxy.closestSite(pos3d.x(), pos3d.y())
            if self.curZone : 
                self.selection = self.createPlanetOverlay()
        
        if not self.parent.rotation:
            self.update()
      
    def attackable(self):
        faction = self.parent.faction
        if faction == None :
            return
        
        
        if self.galaxy.control_points[self.curZone[0]].occupation(faction) > 0.9 :
            return
        
        for site in self.galaxy.getLinkedPlanets(self.curZone[0]) :
            if self.galaxy.control_points[site].occupation(faction) > 0.5 :
                
                self.attackVector = (self.curZone[0], site)
                self.attackVectorGl = self.createAttackVector()
                return
                
        

    def drawLinks(self):

        if self.links :
            GL.glDeleteLists(self.links, 1)
        
        genList = GL.glGenLists(1)
        
        GL.glNewList(genList, GL.GL_COMPILE)
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (0.7,.7,.7, 1))
        self.programConstant.bind()
        GL.glLineWidth(1)
        for orig in self.galaxy.links :
            dests = self.galaxy.links[orig]
            for dest in dests :
                GL.glBegin(GL.GL_LINES)
      
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
        
        bevel = 0.1
        opacity = float(self.parent.mapTransparency) / 100.0
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
            
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (color.redF(),color.greenF(),color.blueF(), opacity))            
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
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (color.redF(),color.greenF(),color.blueF(), opacity * 1.5))
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
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (color.redF(),color.greenF(),color.blueF(), opacity))
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

        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, (.0,.0,.0, 0.0))
        GL.glBegin(GL.GL_POLYGON)
        GL.glVertex3f(self.galaxy.space_size.x()+5000, -self.galaxy.space_size.y()-5000, extrude)
        GL.glVertex3f(self.galaxy.space_size.x()+5000, self.galaxy.space_size.y()+5000, extrude)
        GL.glVertex3f(-self.galaxy.space_size.x()-5000, self.galaxy.space_size.y()+5000, extrude)
        GL.glVertex3f(-self.galaxy.space_size.x()-5000, -self.galaxy.space_size.y()-5000, extrude)
        GL.glEnd( )


        self.programConstant.release()
        

              
                
            
        
        GL.glEndList()
        return genList

    def createPlane(self):
        
        
        genList = GL.glGenLists(1)
        
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
        
    

    def createAtmosphere(self, R):
        if self.atmosphere :
            GL.glDeleteLists(self.atmosphere,1)        
        
        R = R * 1.1
        genList = GL.glGenLists(1)

        GL.glNewList(genList, GL.GL_COMPILE)        
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
