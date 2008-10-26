#
# PhotoFilmStrip - Creates movies out of your pictures.
#
# Copyright (C) 2008 Jens Goepfert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import os

from ConfigParser import ConfigParser
from lib.common.Singleton import Singleton


class Settings(Singleton):
    
    APP_NAME = u"PhotoFilmStrip"
    APP_VERSION = "0.73"
    
    def Init(self):
        self.filename = os.path.join(os.path.expanduser("~"), '.%s' % Settings.APP_NAME)
        self.__isFirstStart = False
        self.cp = None
        if not os.path.isfile(self.filename):
            self.Create()
            self.__isFirstStart = True
        self.Load()
        
    def Create(self):
        self.cp = ConfigParser()
        self.cp.add_section("General")
        self.cp.add_section("History")
        self.cp.add_section("Profiles")
        self.Save()
        
    def Load(self):
        self.cp = ConfigParser()
        self.cp.read(self.filename)
        
    def Save(self):
        fd = open(self.filename, 'w')
        self.cp.write(fd)
        fd.close()

    def IsFirstStart(self):
        return self.__isFirstStart
    
    def SetFileHistory(self, fileList):
        self.Load()
        for idx, filename in enumerate(fileList):
            if os.path.exists(filename):
                self.cp.set("History", "%d" % idx, filename)
        self.Save()
        
    def GetFileHistory(self):
        self.Load()
        fileList = []
        for idx in range(9, -1, -1):
            if self.cp.has_option("History", str(idx)):
                filename = self.cp.get("History", str(idx))
                if os.path.exists(filename):
                    fileList.append(filename)

        return fileList
    
    def SetProjectPath(self, path):
        self.Load()
        self.cp.set("General", "ProjectPath", path)
        self.Save()

    def GetProjectPath(self):
        self.Load()
        if self.cp.has_option("General", "ProjectPath"):
            return self.cp.get("General", "ProjectPath")
        return ""

    def SetImagePath(self, path):
        self.Load()
        self.cp.set("General", "ImagePath", path)
        self.Save()

    def GetImagePath(self):
        self.Load()
        if self.cp.has_option("General", "ImagePath"):
            return self.cp.get("General", "ImagePath")
        return ""

    def SetVideoSize(self, size):
        self.Load()
        self.cp.set("General", "VideoSize", size)
        self.Save()

    def GetVideoSize(self):
        self.Load()
        if self.cp.has_option("General", "VideoSize"):
            return self.cp.getint("General", "VideoSize")
        return 3

    def SetVideoType(self, typ):
        self.Load()
        self.cp.set("General", "VideoType", typ)
        self.Save()

    def GetVideoType(self):
        self.Load()
        if self.cp.has_option("General", "VideoType"):
            return self.cp.getint("General", "VideoType")
        return 0

    def SetUsedRenderer(self, renderer):
        self.Load()
        self.cp.set("General", "Renderer", renderer)
        self.Save()

    def GetUsedRenderer(self):
        self.Load()
        if self.cp.has_option("General", "Renderer"):
            return self.cp.getint("General", "Renderer")
        return 1
    
    def SetLastOutputPath(self, path):
        self.Load()
        self.cp.set("General", "LastOutputPath", path)
        self.Save()

    def GetLastOutputPath(self):
        self.Load()
        if self.cp.has_option("General", "LastOutputPath"):
            return self.cp.get("General", "LastOutputPath")
        return os.getcwd()
    
    def SetRenderProperties(self, renderer, props):
        self.Load()
        if self.cp.has_section(renderer):
            self.cp.remove_section(renderer)
        self.cp.add_section(renderer)
        for prop, value in props.items():
            self.cp.set(renderer, prop, value)
        self.Save()
    
    def GetRenderProperties(self, renderer):
        self.Load()
        result = {}
        if not self.cp.has_section(renderer):
            return result
        for prop, value in self.cp.items(renderer):
            result[prop] = eval(value)
        
        return result
    
    def GetOutputProfiles(self):
        vcd = OutputProfile()
        vcd.PName = "VCD"
        vcd.PResPal = (352, 288)
        vcd.PResNtsc = (352, 240)
        vcd.PBitrate = 1150
        
        svcd = OutputProfile()
        svcd.PName = "SVCD"
        svcd.PResPal = (576, 480)
        svcd.PResNtsc = (480, 480)
        svcd.PBitrate = 2500

        dvd = OutputProfile()
        dvd.PName = "DVD"
        dvd.PResPal = (720, 576)
        dvd.PResNtsc = (720, 480)
        dvd.PBitrate = 8000

        medium = OutputProfile()
        medium.PName = "Medium 640x360"
        medium.PResPal = (640, 360)
        medium.PResNtsc = (640, 360) 
        medium.PBitrate = 8000

        hd = OutputProfile()
        hd.PName = "HD 1280x720"
        hd.PResPal = (1280, 720)
        hd.PResNtsc = (1280, 720) 
        hd.PBitrate = 10000

        fullhd = OutputProfile()
        fullhd.PName = "FULL-HD 1920x1080"
        fullhd.PResPal = (1920, 1080)
        fullhd.PResNtsc = (1920, 1080) 
        fullhd.PBitrate = 12000
        
        return [vcd, svcd, dvd, medium, hd, fullhd]


class OutputProfile(object):
    
    def __init__(self):
        self.PName = ""
        self.PResPal = 0
        self.PResNtsc = 0
        self.PBitrate = 0
