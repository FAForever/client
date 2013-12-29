#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------


import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)


import logging
import string
import sys
from urllib2 import HTTPError
import fa

logger= logging.getLogger("faf.fa.maps")
logger.setLevel(logging.INFO)



from PyQt4 import QtCore, QtGui
import cStringIO
import util
import os, stat
import struct
import FreeImagePy as FIPY
import warnings
import shutil
import urllib2
import zipfile
import tempfile
import re


VAULT_PREVIEW_ROOT = "http://www.faforever.com/faf/vault/map_previews/small/" 
VAULT_DOWNLOAD_ROOT = "http://www.faforever.com/faf/vault/"
VAULT_COUNTER_ROOT = "http://www.faforever.com/faf/vault/map_vault/inc_downloads.php"

 
maps = { # A Lookup table for info (names, sizes, players) of the official Forged Alliance Maps
                 "scmp_001" : ["Burial Mounds", "1024x1024", 8],
                 "scmp_002" : ["Concord Lake", "1024x1024", 8],
                 "scmp_003" : ["Drake's Ravine", "1024x1024", 4],
                 "scmp_004" : ["Emerald Crater", "1024x1024", 4],
                 "scmp_005" : ["Gentleman's Reef", "2048x2048", 7],
                 "scmp_006" : ["Ian's Cross", "1024x1024", 4],
                 "scmp_007" : ["Open Palms", "512x512", 6],
                 "scmp_008" : ["Seraphim Glaciers", "1024x1024", 8],
                 "scmp_009" : ["Seton's Clutch", "1024x1024", 8],
                 "scmp_010" : ["Sung Island", "1024x1024", 5],
                 "scmp_011" : ["The Great Void", "2048x2048", 8],
                 "scmp_012" : ["Theta Passage", "256x256", 2],
                 "scmp_013" : ["Winter Duel", "256x256", 2],
                 "scmp_014" : ["The Bermuda Locket", "1024x1024", 8],
                 "scmp_015" : ["Fields Of Isis", "512x512", 4],
                 "scmp_016" : ["Canis River", "256x256", 2],
                 "scmp_017" : ["Syrtis Major", "512x512", 4],
                 "scmp_018" : ["Sentry Point", "256x256", 3],
                 "scmp_019" : ["Finn's Revenge", "512x512", 2],
                 "scmp_020" : ["Roanoke Abyss", "1024x1024", 6],
                 "scmp_021" : ["Alpha 7 Quarantine", "2048x2048", 8],
                 "scmp_022" : ["Artic Refuge", "512x512", 4],
                 "scmp_023" : ["Varga Pass", "512x512", 2],
                 "scmp_024" : ["Crossfire Canal", "1024x1024", 6],
                 "scmp_025" : ["Saltrock Colony", "512x512", 6],
                 "scmp_026" : ["Vya-3 Protectorate", "512x512", 4],
                 "scmp_027" : ["The Scar", "1024x1024", 6],
                 "scmp_028" : ["Hanna oasis", "2048x2048", 8],
                 "scmp_029" : ["Betrayal Ocean", "4096x4096", 8],
                 "scmp_030" : ["Frostmill Ruins", "4096x4096", 8],
                 "scmp_031" : ["Four-Leaf Clover", "512x512", 4],
                 "scmp_032" : ["The Wilderness", "512x512", 4],
                 "scmp_033" : ["White Fire", "512x512", 6],
                 "scmp_034" : ["High Noon", "512x512", 4],
                 "scmp_035" : ["Paradise", "512x512", 4],
                 "scmp_036" : ["Blasted Rock", "256x256", 4],
                 "scmp_037" : ["Sludge", "256x256", 3],
                 "scmp_038" : ["Ambush Pass", "256x256", 4],
                 "scmp_039" : ["Four-Corners", "256x256", 4],
                 "scmp_040" : ["The Ditch", "1024x1024", 6],
                 "x1mp_001" : ["Crag Dunes", "256x256", 2],
                 "x1mp_002" : ["Williamson's Bridge", "256x256", 2],
                 "x1mp_003" : ["Snoey Triangle", "512x512", 3],
                 "x1mp_004" : ["Haven Reef", "512x512", 4],
                 "x1mp_005" : ["The Dark Heart", "512x512", 6],
                 "x1mp_006" : ["Daroza's Sanctuary", "512x512", 4],
                 "x1mp_007" : ["Strip Mine", "1024x1024", 4],
                 "x1mp_008" : ["Thawing Glacier", "1024x1024", 6],
                 "x1mp_009" : ["Liberiam Battles", "1024x1024", 8],
                 "x1mp_010" : ["Shards", "2048x2048", 8],
                 "x1mp_011" : ["Shuriken Island", "2048x2048", 8],
                 "x1mp_012" : ["Debris", "4096x4096", 8],
                 "x1mp_014" : ["Flooded Strip Mine", "1024x1024", 4],
                 "x1mp_017" : ["Eye Of The Storm", "512x512", 4],
                 }

__exist_maps = None

def gwmap(mapname):
    folder = folderForMap(mapname)
    if folder:       
        scenario = getScenarioFile(folder)        
        if scenario:
            
            if not os.path.isdir(os.path.join(getUserMapsFolder(), "gwScenario")):
                os.makedirs(os.path.join(getUserMapsFolder(), "gwScenario"))                        
            save = os.path.join(getUserMapsFolder(), "gwScenario", "gw_scenario.lua")

            fopen = open(os.path.join(folder, scenario), 'r')
            temp = []
            for line in fopen:
                temp.append(line.rstrip())                
            text = " ".join(temp)
            
            pattern = re.compile("customprops.*?=.*?({.*?}),")
            match = re.search(pattern, text)
            if match:
                pattern2 = re.compile("'*ExtraArmies'*.*?[\"'](.*)[\"']")
                match2 = re.search(pattern2, match.group(1))
                if match2 :
                    text = text.replace(match2.group(1), "SUPPORT_1 SUPPORT_2 " + match2.group(1))
                else:
                    text = text.replace(match.group(1), "{ ExtraArmies=\" SUPPORT_1 SUPPORT_2\" }")
            
            fopen.close()
            f  = open(save, 'w')
            f.write(text)
            f.close() 
            return True
            
    return False
            
        

def isBase(mapname):
    '''
    Returns true if mapname is the name of an official map
    '''
    if mapname in maps :
        return True
    return False

def getUserMaps():
    maps = []
    if os.path.isdir(getUserMapsFolder()) :
            maps = os.listdir(getUserMapsFolder())
    return maps

def getDisplayName(mapname):
    '''
    Tries to return a pretty name for the map (for official maps, it looks up the name)
    For nonofficial maps, it tries to clean up the filename
    '''      
    if str(mapname) in maps :
        return maps[mapname][0]
    else :
        #cut off ugly version numbers, replace "_" with space.
        pretty = mapname.rsplit(".v0",1)[0]
        pretty = pretty.replace("_", " ")
        pretty = string.capwords(pretty)  
        return pretty

def name2link(name):
    '''
    Returns a quoted link for use with the VAULT_xxxx Urls
    TODO: This could be cleaned up a little later.
    '''
    return urllib2.quote("maps/" + name + ".zip")

def link2name(link):
    '''
    Takes a link and tries to turn it into a local mapname
    '''
    name = link.rsplit("/")[1].rsplit(".zip")[0]
    logger.info("Converted link '" + link + "' to name '" + name + "'")
    return name

def getScenarioFile(folder):
    ''' 
    Return the scenario.lua file
    '''
    for infile in os.listdir(folder) :
        if infile.lower().endswith("_scenario.lua") :
            return infile 
    return None

def getSaveFile(folder):
    ''' 
    Return the save.lua file
    '''
    for infile in os.listdir(folder) :
        if infile.lower().endswith("_save.lua") :
            return infile 
    return None

def isMapFolderValid(folder):
    '''
    Check if the folder got all the files needed to be a map folder.
    '''
    baseName = os.path.basename(folder).split('.')[0]

    checklist1 = False
    checklist2 = False
    checklist3 = False
    checklist4 = False

    for infile in os.listdir(folder) :
        if infile.lower() == (baseName.lower() + ".scmap") :
            checklist1 = True
        if infile.lower() == (baseName.lower() + "_save.lua") :
            checklist2 = True
        if infile.lower() == (baseName.lower() + "_scenario.lua") :
            checklist3 = True
        if infile.lower() == (baseName.lower() + "_script.lua") :
            checklist4 = True 

    if checklist1 and checklist2 and checklist3 and checklist4 :
        return True
    else :
        return False


def existMaps(force = False):
    global __exist_maps
    if force or __exist_maps == None:
        
        __exist_maps = getUserMaps()

        if os.path.isdir(getBaseMapsFolder()) :
            if __exist_maps == None :
                __exist_maps = os.listdir(getBaseMapsFolder())
            else : 
                __exist_maps.extend(os.listdir(getBaseMapsFolder()))
    return __exist_maps        
    


def isMapAvailable(mapname):
    '''
    Returns true if the map with the given name is available on the client
    '''
    if isBase(mapname):
        return True
    
    if os.path.isdir(getUserMapsFolder()):
        for infile in os.listdir(getUserMapsFolder()) :
            if infile.lower() == mapname.lower(): 
                return True

    return False    

def mapExists(mapname):
    '''
    improved isMapAvailable
    '''
    for map in existMaps():
        if mapname == map.lower():
            return True
    return False
    

def folderForMap(mapname):
    '''
    Returns the folder where the application could find the map
    '''
    if isBase(mapname):
        return os.path.join(getBaseMapsFolder(), mapname)
    
    if os.path.isdir(getUserMapsFolder()):
        for infile in os.listdir(getUserMapsFolder()) :
            if infile.lower() == mapname.lower(): 
                return os.path.join(getUserMapsFolder(), mapname)

    return None

def getBaseMapsFolder():
    '''
    Returns the folder containing all the base maps for this client.
    '''
    if fa.gamepath:
        return os.path.join(fa.gamepath, "maps")
    else:
        return "maps" #This most likely isn't the valid maps folder, but it's the best guess.
 
 
def getUserMapsFolder():
    '''
    Returns to folder where the downloaded maps of the user are stored.
    '''
    return os.path.join(util.PERSONAL_DIR, "My Games", "Gas Powered Games", "Supreme Commander Forged Alliance", "Maps") 


def genPrevFromDDS(sourcename, destname,small=False):
    '''
    this opens supcom's dds file (format: bgra8888) and saves to png
    '''
    try:
        img = bytearray()
        buf = bytearray(16)
        file = open(sourcename,"rb")
        file.seek(128) # skip header
        while file.readinto(buf):
            img += buf[:3] + buf[4:7] + buf[8:11] + buf[12:15]
        file.close()

        size = int((len(img)/3) ** (1.0/2))
        if small:
            imageFile = QtGui.QImage(img,size,size,QtGui.QImage.Format_RGB888).rgbSwapped().scaled(100,100,transformMode = QtCore.Qt.SmoothTransformation)
        else:
            imageFile = QtGui.QImage(img,size,size,QtGui.QImage.Format_RGB888).rgbSwapped()
        imageFile.save(destname)
    except IOError:
        pass # cant open the

def __exportPreviewFromMap(mapname, positions=None):
    '''
    This method auto-upgrades the maps to have small and large preview images
    '''
    if mapname == "" or mapname == None:
        return
    smallExists = False
    largeExists = False
    ddsExists = False
    previews = {"cache":None, "tozip":list()}
    
    if os.path.isdir(mapname):
        mapdir = mapname
    elif os.path.isdir(os.path.join(getUserMapsFolder(), mapname)):
        mapdir = os.path.join(getUserMapsFolder(), mapname)
    elif os.path.isdir(os.path.join(getBaseMapsFolder(), mapname)):
        mapdir = os.path.join(getBaseMapsFolder(), mapname)
    else:
        logger.debug("Can't find mapname in file system: " + mapname)
        return previews
        
    mapname = os.path.basename(mapdir).lower()
    mapfilename = os.path.join(mapdir, mapname.split(".")[0]+".scmap")
    
    mode = os.stat(mapdir)[0]
    if not (mode and stat.S_IWRITE):
        logger.debug("Map directory is not writable: " + mapdir)
        logger.debug("Writing into cache instead.")
        mapdir = os.path.join(util.CACHE_DIR, mapname)
        if not os.path.isdir(mapdir):
            os.mkdir(mapdir)
    
    previewsmallname = os.path.join(mapdir, mapname + ".small.png")
    previewlargename = os.path.join(mapdir, mapname + ".large.png")
    previewddsname = os.path.join(mapdir, mapname + ".dds")
    cachepngname = os.path.join(util.CACHE_DIR, mapname + ".png")
        
    logger.debug("Generating preview from user maps for: " + mapname)
    logger.debug("Using directory: " + mapdir)
    
    #Unknown / Unavailable mapname? 
    if not os.path.isfile(mapfilename):
        logger.warning("Unable to find the .scmap for: " + mapname + ", was looking here: " + mapfilename)
        return previews

    #Small preview already exists?
    if os.path.isfile(previewsmallname):
        logger.debug(mapname + " already has small preview")
        previews["tozip"].append(previewsmallname)
        smallExists = True
        #save it in cache folder
        shutil.copyfile(previewsmallname, cachepngname)
        #checking if file was copied correctly, just in case
        if os.path.isfile(cachepngname):
            previews["cache"] = cachepngname
        else:
            logger.debug("Couldn't copy preview into cache folder")
            return previews
        
    #Large preview already exists?
    if os.path.isfile(previewlargename):
        logger.debug(mapname + " already has large preview")
        previews["tozip"].append(previewlargename)
        largeExists = True

    #Preview DDS already exists?
    if os.path.isfile(previewddsname):
        logger.debug(mapname + " already has DDS extracted")
        previews["tozip"].append(previewddsname)
        ddsExists = True
    
    if not ddsExists:
        logger.debug("Extracting preview DDS from .scmap for: " + mapname)
        mapfile = open(mapfilename, "rb")
        """
        magic = struct.unpack('i', mapfile.read(4))[0]       
        version_major = struct.unpack('i', mapfile.read(4))[0]       
        unk_edfe = struct.unpack('i', mapfile.read(4))[0]
        unk_efbe = struct.unpack('i', mapfile.read(4))[0]
        width = struct.unpack('f', mapfile.read(4))[0]
        height = struct.unpack('f', mapfile.read(4))[0]
        unk_32 = struct.unpack('i', mapfile.read(4))[0]
        unk_16 = struct.unpack('h', mapfile.read(2))[0]
        """
        mapfile.seek(30)    #Shortcut. Maybe want to clean out some of the magic numbers some day
        size = struct.unpack('i', mapfile.read(4))[0]
        data = mapfile.read(size)
        #version_minor = struct.unpack('i', mapfile.read(4))[0]   
        mapfile.close()
        #logger.debug("SCMAP version %i.%i" % (version_major, version_minor))

        try:
            with open(previewddsname, "wb") as previewfile:
                previewfile.write(data)

                #checking if file was created correctly, just in case
                if os.path.isfile(previewddsname):
                    previews["tozip"].append(previewddsname)
                else:
                    logger.debug("Failed to make DDS for: " + mapname)
                    return previews
        except IOError:
            pass
    
    if not smallExists:
        logger.debug("Making small preview from DDS for: " + mapname)
        genPrevFromDDS(previewddsname,previewsmallname,small=True)
        if os.path.isfile(previewsmallname):
            previews["tozip"].append(previewsmallname)
        else:
            logger.debug("Failed to make small preview for: " + mapname)
            return previews
        
        shutil.copyfile(previewsmallname, cachepngname)
        #checking if file was copied correctly, just in case
        if os.path.isfile(cachepngname):
            previews["cache"] = cachepngname
        else:
            logger.debug("Failed to write in cache folder")
            return previews
    
    if not largeExists:
        logger.debug("Making large preview from DDS for: " + mapname)
        if not isinstance(positions, dict):
            logger.debug("Icon positions were not passed or they were wrong for: " + mapname)
            return previews
        genPrevFromDDS(previewddsname,previewlargename,small=False)
        mapimage = QtGui.QPixmap(previewlargename)
        armyicon = QtGui.QPixmap(os.path.join(os.getcwd(), ur"_res\vault\map_icons\army.png")).scaled(8, 9, 1, 1)
        massicon = QtGui.QPixmap(os.path.join(os.getcwd(), ur"_res\vault\map_icons\mass.png")).scaled(8, 8, 1, 1)
        hydroicon = QtGui.QPixmap(os.path.join(os.getcwd(), ur"_res\vault\map_icons\hydro.png")).scaled(10, 10, 1, 1)
        
        
        painter = QtGui.QPainter()
        
        painter.begin(mapimage)
        #icons should be drawn in certain order: first layer is hydros, second - mass, and army on top. made so that previews not look messed up.
        if positions.has_key("hydro"):
            for pos in positions["hydro"]:
                target = QtCore.QRectF(positions["hydro"][pos][0]-5, positions["hydro"][pos][1]-5, 10, 10)
                source = QtCore.QRectF(0.0, 0.0, 10.0, 10.0)
                painter.drawPixmap(target, hydroicon, source)
        if positions.has_key("mass"):
            for pos in positions["mass"]:
                target = QtCore.QRectF(positions["mass"][pos][0]-4, positions["mass"][pos][1]-4, 8, 8)
                source = QtCore.QRectF(0.0, 0.0, 8.0, 8.0)
                painter.drawPixmap(target, massicon, source)
        if positions.has_key("army"):
            for pos in positions["army"]:
                target = QtCore.QRectF(positions["army"][pos][0]-4, positions["army"][pos][1]-4, 8, 9)
                source = QtCore.QRectF(0.0, 0.0, 8.0, 9.0)
                painter.drawPixmap(target, armyicon, source)
        painter.end()
        
        mapimage.save(previewlargename)
        #checking if file was created correctly, just in case
        if os.path.isfile(previewlargename):
            previews["tozip"].append(previewlargename)
        else:
            logger.debug("Failed to make large preview for: " + mapname)

    return previews

iconExtensions = ["png"] #, "jpg" removed to have less of those costly 404 misses.


def __downloadPreviewFromWeb(name):
    '''
    Downloads a preview image from the web for the given map name
    '''
    #This is done so generated previews always have a lower case name. This doesn't solve the underlying problem (case folding Windows vs. Unix vs. FAF)
    name = name.lower()

    logger.debug("Searching web preview for: " + name)
        
    for extension in iconExtensions:
        try:
            header = urllib2.Request(VAULT_PREVIEW_ROOT + urllib2.quote(name) + "." + extension, headers={'User-Agent' : "FAF Client"})   
            req = urllib2.urlopen(header)
            img = os.path.join(util.CACHE_DIR, name + "." + extension)
            with open(img, 'wb') as fp:
                shutil.copyfileobj(req, fp)
                fp.flush()
                os.fsync(fp.fileno())       #probably works fine without the flush and fsync
                fp.close()
                
                #Create alpha-mapped preview image
                im = QtGui.QImage(img) #.scaled(100,100)
                im.save(img)
                logger.debug("Web Preview " + extension + " used for: " + name)
                return img
        except:
            logger.debug("Web preview download failed for " + name)
            pass    #don't bother if anything goes wrong
        
    logger.debug("Web Preview not found for: " + name)
    return None
     
def preview(mapname, pixmap = False, force=False):
    try:
        # Try to load directly from cache
        for extension in iconExtensions:
            img = os.path.join(util.CACHE_DIR, mapname + "." + extension)
            if os.path.isfile(img):
                logger.debug("Using cached preview image for: " + mapname)
                return util.icon(img, False, pixmap)
        if force :
        # Try to download from web
            img = __downloadPreviewFromWeb(mapname)
            if img and os.path.isfile(img):
                logger.debug("Using web preview image for: " + mapname)
                return util.icon(img, False, pixmap)
    
        # Try to find in local map folder    
        img = __exportPreviewFromMap(mapname)["cache"]
        if img and os.path.isfile(img):
            logger.debug("Using fresh preview image for: " + mapname)
            return util.icon(img, False, pixmap)
        
        return None
    except:
        logger.error("Error raised in maps.preview(...) for " + mapname)
        logger.error("Map Preview Exception", exc_info=sys.exc_info())




def downloadMap(name, silent=False):
    ''' 
    Download a map from the vault with the given name
    LATER: This type of method is so common, it could be put into a nice util method.
    '''
    link = name2link(name)
    url = VAULT_DOWNLOAD_ROOT + link
    logger.debug("Getting map from: " + url)

    progress = QtGui.QProgressDialog()
    if not silent:
        progress.setCancelButtonText("Cancel")
    else:
        progress.setCancelButton(None)
        
    progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
    progress.setAutoClose(False)
    progress.setAutoReset(False)
       
    
    try:
        req = urllib2.Request(url, headers={'User-Agent' : "FAF Client"})         
        zipwebfile  = urllib2.urlopen(req)
        meta = zipwebfile.info()
        file_size = int(meta.getheaders("Content-Length")[0])

        
        progress.setMinimum(0)
        progress.setMaximum(file_size)
        progress.setModal(1)
        progress.setWindowTitle("Downloading Map")
        progress.setLabelText(name)
        progress.show()
    
        #Download the file as a series of 8 KiB chunks, then uncompress it.
        output = cStringIO.StringIO()
        file_size_dl = 0
        block_sz = 8192       

        while progress.isVisible():
            read_buffer = zipwebfile.read(block_sz)
            if not read_buffer:
                break
            file_size_dl += len(read_buffer)
            output.write(read_buffer)
            progress.setValue(file_size_dl)
    
        progress.close()
        if file_size_dl == file_size:
            zfile = zipfile.ZipFile(output)
            zfile.extractall(getUserMapsFolder())

            #check for eventual sound files
            if folderForMap(name):
                if "sounds" in os.listdir(folderForMap(name)) :
                    root_src_dir = os.path.join(folderForMap(name), "sounds")
                    for src_dir, _, files in os.walk(root_src_dir):
                        dst_dir = src_dir.replace(root_src_dir, util.SOUND_DIR)
                        for file_ in files:
                            src_file = os.path.join(src_dir, file_)
                            dst_file = os.path.join(dst_dir, file_)
                            if os.path.exists(dst_file):
                                os.remove(dst_file)
                            shutil.move(src_file, dst_dir)

                
            logger.debug("Successfully downloaded and extracted map from: " + url)
        else:    
            logger.warn("Map download cancelled for: " + url)        
            return False



    except:
        logger.warn("Map download or extraction failed for: " + url)        
        if sys.exc_type is HTTPError:
            logger.warning("Vault download failed with HTTPError, map probably not in vault (or broken).")
            QtGui.QMessageBox.information(None, "Map not downloadable", "<b>This map was not found in the vault (or is broken).</b><br/>You need to get it from somewhere else in order to use it." )
        else:                
            logger.error("Download Exception", exc_info=sys.exc_info())
            QtGui.QMessageBox.information(None, "Map installation failed", "<b>This map could not be installed (please report this map or bug).</b>" )
        return False

    #Count the map downloads
    try:
        url = VAULT_COUNTER_ROOT + "?map=" + urllib2.quote(link)
        req = urllib2.Request(url, headers={'User-Agent' : "FAF Client"})
        urllib2.urlopen(req)
        logger.debug("Successfully sent download counter request for: " + url)        
        
    except:
        logger.warn("Request to map download counter failed for: " + url)
        logger.error("Download Count Exception", exc_info=sys.exc_info())

    return True





def createBigMapPreview():
    pass



def processMapFolderForUpload(mapDir, positions):
    """ 
    Zipping the file and creating thumbnails
    """
    # creating thumbnail
    files = __exportPreviewFromMap(mapDir, positions)["tozip"]
    #abort zipping if there is insufficient previews
    if len(files) != 3:
        logger.debug("Insufficient previews for making an archive.")
        return None
    
    #mapName = os.path.basename(mapDir).split(".v")[0]

    #making sure we pack only necessary files and not random garbage
    for filename in os.listdir(mapDir):
        if filename.endswith(".lua") or filename.endswith("preview.jpg") or filename.endswith(".scmap") or filename.endswith(".dds"):
            files.append(os.path.join(mapDir, filename))
    
    temp = tempfile.NamedTemporaryFile(mode='w+b', suffix=".zip", delete=False)
    
    #creating the zip
    zipped = zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED)

    for filename in files:
        zipped.write(filename, os.path.join(os.path.basename(mapDir),os.path.basename(filename)))
    
    temp.flush()
    
    return temp