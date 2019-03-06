#!/usr/bin/env python

from PIL import Image, ImageDraw, ImageFilter
from PIL.ImageQt import ImageQt

import json
import numpy
import sys, os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from control import Ui_ControlWindow
from display import Ui_DisplayDialog

def modAlpha(pixel):
    return int(0.70*pixel)

# Class representing the display window
class DispDialog(QDialog, Ui_DisplayDialog):

    def __init__(self, parent):
        super(DispDialog, self).__init__(parent)
        self.setupUi(self) 
        self.setWindowTitle('Mapster - Player View')
        self.setWindowFlags(QtCore.Qt.Window)
        self.scroll_display.viewport().installEventFilter(self)
        self.show()
        self.setStyleSheet("background-color: #000000;")
        
    def displayMap(self, scale_factor, pixmap):
        self.display_label = QLabel()
        self.display_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        scroll_w = self.scroll_display.width()
        scroll_h = self.scroll_display.height()
        pix_w = pixmap.width()
        pix_h = pixmap.height()

        # Fit image to window
        tmp_pixmap = pixmap.scaledToWidth(scroll_w)

        # Scale image to correct 5ft size
        new_pixmap = tmp_pixmap.scaledToWidth(scale_factor*tmp_pixmap.width())

        self.display_label.setPixmap(new_pixmap)  
        self.scroll_display.setWidget(self.display_label)
        self.scroll_display.show()

    def resizeEvent(self, event):
        if len(self.parent().map_names) > 0:
            self.parent().saveScrollValues()
            self.parent().displayMap()
        QDialog.resizeEvent(self, event)

    def eventFilter(self, source, event):
        if (event.type() == QtCore.QEvent.Wheel and
            source is self.scroll_display.viewport()):
            return True
        return super(DispDialog, self).eventFilter(source, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        event.accept()


# Class representing the control window
class ControlDialog(QMainWindow, Ui_ControlWindow):

    def __init__(self, parent=None):
        super(ControlDialog,self).__init__()
        self.setupUi(self)  
        self.initVariables()
        self.display_window = DispDialog(self)
        self.initControlUI()
                
    def initVariables(self):
        self.current_index = 0
        self.map_names = []
        self.dim_alpha = 220 # Alpha value for dim light
        self.blur_radius = 5 # Radius of Gaussian blur for fog
        self.tool_state = None  # Tool button being used
        self.display_mode = None # Current type of display (locked, elastic)
        self.grid_shown = False
        self.previous_scroll = [] # Previous scroll location prior to elastic view
        self.clicks_5ft = []    # Points clicked on for 5ft range setting
        self.clicks_polygon = []
        self.pixels_5ft = 90     # Number of pixels for correct 5ft scale
        self.control_label = QLabel()

    def initControlUI(self):
        self.setWindowTitle('Mapster - DM View')
        self.showMaximized()
        self.setStyleSheet("background-color: #eadcc0;")
        #self.setMouseTracking(True)
        self.initMapConfig()
        self.initWidgets()

    def initWidgets(self):
        self.but_set_5ft_range.toggled.connect(self.setTool5ft)
        self.but_erase.toggled.connect(self.setToolErase)
        self.but_dim.toggled.connect(self.setToolDim)
        self.but_refog.toggled.connect(self.setToolRefog)
        self.but_lock_view.toggled.connect(self.lockView)
        self.but_elastic_view.toggled.connect(self.elasticView)
        self.but_show_grid.toggled.connect(self.showGrid)
        self.but_reset_fog.clicked.connect(self.setResetFog)
        self.but_clear_fog.clicked.connect(self.setClearFog)
        self.map_list.selectionModel().currentChanged.connect(self.listChanged)
        self.scroll_control.viewport().installEventFilter(self)
        self.control_label.mousePressEvent = self.controlLabelClicked 
        self.control_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def initMapConfig(self):
        self.map_names = os.listdir('/home/benjamin/git_ws/mapster/maps')
        self.list_model = QStandardItemModel()

        for map_name in self.map_names:
            fname_no_ext = map_name.split(".")[0]
            filepath = 'config/' + fname_no_ext + ".json"
            self.list_model.appendRow(QStandardItem(fname_no_ext))

            # If this map doesn't already have a config file
            if not os.path.isfile(filepath):
                config_dict = {}
                config_dict["scale_factor"] = 1.0
                config_dict["grid_pcnt"] = 1.0
                config_dict["v_scroll_pcnt"] = 0.0
                config_dict["h_scroll_pcnt"] = 0.0

                with open(filepath, 'w') as file:
                    json.dump(config_dict, file)
                    file.close()
        
        self.displayMap()
        self.map_list.setModel(self.list_model)            
        self.map_list.show()

    def closeEvent(self, event):
        pass

    def getScaleFactor(self):
        return self.getJsonConfig()["scale_factor"]

    def saveScaleFactor(self, scale_factor):
        json_config = self.getJsonConfig()
        json_config["scale_factor"] = scale_factor
        self.saveJsonConfig(json_config)

    def saveGridPcnt(self, grid_pcnt):
        json_config = self.getJsonConfig()
        json_config["grid_pcnt"] = grid_pcnt
        self.saveJsonConfig(json_config)

    def displayMap(self):
        scale_factor = self.getScaleFactor()
        pixmap = self.getCompositeFog(transparent=True)
        
        # Update display window contents with composite image
        disp_pixmap = self.getCompositeFog()
        self.display_window.displayMap(scale_factor, disp_pixmap) 

        scroll_w = self.scroll_control.width()
        scroll_h = self.scroll_control.height()
        pix_w = pixmap.width()
        pix_h = pixmap.height()

        # Fit image to window
        tmp_pixmap = pixmap.scaledToWidth(scroll_w)

        # Scale image to correct 5ft size
        new_pixmap = tmp_pixmap.scaledToWidth(scale_factor*tmp_pixmap.width())

        if ((self.tool_state == "erase" or self.tool_state == "dim"
            or self.tool_state == "refog") and len(self.clicks_polygon) > 0):
            painter = QPainter()
            painter.begin(new_pixmap)
            pen = QPen(QtCore.Qt.red, 3)
            painter.setPen(pen)

            poly = self.clicks_polygon
            painter.drawPoint(poly[0][0], poly[0][1])
            for i in range(len(poly)-1):
                painter.drawLine(poly[i][0], poly[i][1],
                    poly[i+1][0], poly[i+1][1])
            
            painter.end()

        self.control_label.setPixmap(new_pixmap)  
        self.scroll_control.setWidget(self.control_label)
        self.scroll_control.show()

        self.loadScrollValues()
    
    def resizeEvent(self, event):
        if len(self.map_names) > 0:
            self.saveScrollValues()
            self.displayMap()
        QMainWindow.resizeEvent(self, event)
        
    def eventFilter(self, source, event):
        if (event.type() == QtCore.QEvent.Wheel and
            source is self.scroll_control.viewport()):
            if self.display_mode == "Locked":
                return True
            else:
                self.propogateScroll()
        '''elif (event.type() == QtCore.QEvent.MouseMove and
            event.buttons() == QtCore.Qt.LeftButton and
            source is self.scroll_control.viewport()):
                pos = event.pos()
                print('Mouse coords: ( %d : %d )' % (pos.x(), pos.y()))'''
        
        return super(ControlDialog, self).eventFilter(source, event)

    def getJsonConfig(self):
        fname_no_ext = self.getFilenameNoExt()
        filepath = 'config/' + fname_no_ext + ".json"
        with open(filepath, 'r') as file:
            json_config = json.loads(file.read().replace('\n', ''))
            file.close()
        return json_config

    def saveJsonConfig(self, json_config):
        fname_no_ext = self.getFilenameNoExt()
        filepath = 'config/' + fname_no_ext + ".json"
        with open(filepath, 'w') as file:
            json.dump(json_config, file)
            file.close()

    def getScrollPcnt(self):
        try:
            v_bar_ctrl = self.scroll_control.verticalScrollBar()
            h_bar_ctrl = self.scroll_control.horizontalScrollBar()
            v_pcnt = v_bar_ctrl.value() / v_bar_ctrl.maximum()
            h_pcnt = h_bar_ctrl.value() / h_bar_ctrl.maximum()
            return (v_pcnt, h_pcnt)
        except ZeroDivisionError:
            return (0, 0)

    def propogateScroll(self):
        v_pcnt, h_pcnt = self.getScrollPcnt()
        v_bar_disp = self.display_window.scroll_display.verticalScrollBar()
        h_bar_disp = self.display_window.scroll_display.horizontalScrollBar()
        v_new = v_pcnt*v_bar_disp.maximum()
        h_new = h_pcnt*h_bar_disp.maximum()

        v_bar_disp.setValue(v_new)
        h_bar_disp.setValue(h_new)

        # Gets to here fine

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.saveScrollValues()
            self.displayMap()
            if self.display_window.isFullScreen():
                self.display_window.showNormal()
            else:
                self.display_window.showFullScreen()
        elif event.key() == QtCore.Qt.Key_Space:
            self.but_lock_view.setChecked(not self.but_lock_view.isChecked())
        elif event.key() == QtCore.Qt.Key_V:
            self.but_elastic_view.setChecked(not self.but_elastic_view.isChecked())
        elif event.key() == QtCore.Qt.Key_G:
            self.but_show_grid.setChecked(not self.but_show_grid.isChecked())

        elif event.key() == QtCore.Qt.Key_E: 
            self.but_erase.setChecked(not self.but_erase.isChecked())
        elif event.key() == QtCore.Qt.Key_D:
            self.but_dim.setChecked(not self.but_dim.isChecked())
        elif event.key() == QtCore.Qt.Key_R:
            self.but_refog.setChecked(not self.but_refog.isChecked())
        event.accept()

    def listChanged(self, current, previous):
        self.saveScrollValues()
        self.current_index = current.row()
        self.displayMap()

    def controlLabelClicked(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.tool_state == "set_5ft_range":
                if len(self.clicks_5ft) < 2:
                    self.clicks_5ft.append(numpy.array([event.x(), event.y()]))
                if len(self.clicks_5ft) == 2:
                    dist = numpy.linalg.norm(self.clicks_5ft[0] - self.clicks_5ft[1])
                    self.set5ftRange(dist)
            elif (self.tool_state == "erase" or self.tool_state == "dim"
                    or self.tool_state == "refog"):
                self.clicks_polygon.append((event.x(), event.y()))
                self.saveScrollValues()
                self.displayMap()
        elif (event.button() == QtCore.Qt.RightButton
            and (self.tool_state == "erase" or self.tool_state == "dim"
            or self.tool_state == "refog") and len(self.clicks_polygon) > 2): 
            self.polygonEdit()
            self.uncheckTool()   
            self.saveScrollValues()
            self.displayMap()      

    def polygonEdit(self):
        if self.tool_state == "erase":
            alpha = 0
        elif self.tool_state == "dim":
            alpha = self.dim_alpha
        else: # self.tool_state == "refog"
            alpha = 255

        # Get fogmap
        filename = ("/home/benjamin/git_ws/mapster/config/fogmaps/" 
            + self.getFilenameNoExt() + ".png")
        im_fog = Image.open(filename)

        # Reprocess polygon coordinates
        map_w = self.control_label.pixmap().width()
        fog_w = im_fog.size[0]
        scale_w = fog_w/map_w
        for i in range(len(self.clicks_polygon)):
            point = self.clicks_polygon[i]
            new_point = (scale_w*point[0], scale_w*point[1])
            self.clicks_polygon[i] = new_point
        
        dr = ImageDraw.Draw(im_fog)
        dr.polygon(self.clicks_polygon, fill=(0, 0, 0, alpha))
        del dr
        im_fog.save(filename)

        self.saveScrollValues()
        self.displayMap()

    def uncheckTool(self):
        # If elastic view not active, activate it
        if not self.but_elastic_view.isChecked():
            self.but_elastic_view.setChecked(True)

        if self.tool_state == "erase":
            self.but_erase.setChecked(False)
        elif self.tool_state == "dim":
            self.but_dim.setChecked(False)
        elif self.tool_state == "refog":
            self.but_refog.setChecked(False)
        else:
            pass

    def setToolErase(self):
        if self.sender().isChecked():
            self.uncheckTool() 
            self.tool_state = "erase"            
        else:
            self.resetTool()     

    def setToolDim(self):
        if self.sender().isChecked():
            self.uncheckTool() 
            self.tool_state = "dim"
        else:
            self.resetTool()     

    def setToolRefog(self):
        if self.sender().isChecked():
            self.uncheckTool() 
            self.tool_state = "refog"
        else:
            self.resetTool()

    def resetTool(self):

        self.tool_state = None
        self.clicks_polygon = []   
        self.saveScrollValues()
        self.displayMap()

    def setTool5ft(self):
        if self.sender().isChecked():
            self.tool_state = "set_5ft_range"
            self.saveScaleFactor(1.0)
            self.displayMap()
        else:
            self.tool_state = None
            self.clicks_5ft = [] # Reset click tracker

    def set5ftRange(self, pix_length):
        scale_factor = self.pixels_5ft/pix_length
        grid_pcnt = pix_length/self.scroll_control.width()

        self.saveScrollValues()
        self.saveScaleFactor(scale_factor)
        self.displayMap()
        self.but_set_5ft_range.setChecked(False)
        self.saveGridPcnt(grid_pcnt)

    def saveScrollValues(self):
        json_config = self.getJsonConfig()
        (v_pcnt, h_pcnt) = self.getScrollPcnt()
        json_config["v_scroll_pcnt"] = v_pcnt
        json_config["h_scroll_pcnt"] = h_pcnt
        self.saveJsonConfig(json_config)
    
    def loadScrollValues(self):
        json_config = self.getJsonConfig()
        v_bar_ctrl = self.scroll_control.verticalScrollBar()
        h_bar_ctrl = self.scroll_control.horizontalScrollBar()
        v_bar_ctrl.setValue(json_config["v_scroll_pcnt"]*v_bar_ctrl.maximum())
        h_bar_ctrl.setValue(json_config["h_scroll_pcnt"]*h_bar_ctrl.maximum())
        self.propogateScroll()

    def showGrid(self):
        if self.sender().isChecked():
            self.grid_shown = True
        else:
            self.grid_shown = False
        self.saveScrollValues()
        self.displayMap()

    def lockView(self):
        if self.sender().isChecked():
            if self.display_mode == "Elastic":
                self.saveScrollValues()
                self.but_elastic_view.setChecked(False)
                self.loadScrollValues()
            self.display_mode = "Locked"
        else:
            self.display_mode = None

    def getFilenameNoExt(self):
        return self.map_names[self.current_index].split(".")[0]

    def getGridPcnt(self):
        json_config = self.getJsonConfig()
        return json_config["grid_pcnt"]

    def getGrid(self, size):
        im_grid = Image.new("RGBA", size)
        dr = ImageDraw.Draw(im_grid)
        
        gap_size = self.getGridPcnt()*size[0]
        alpha = 80
        width = int(numpy.ceil(gap_size/40))
        x = gap_size
        y = gap_size

        while y < size[1]:
            dr.line([(0, y), (size[0], y)], fill=(0, 0, 0, alpha), width=width)
            y += gap_size

        while x < size[0]:
            dr.line([(x, 0), (x, size[1])], fill=(0, 0, 0, alpha), width=width)
            x += gap_size
            
        del dr
        return im_grid

    def getCompositeFog(self, transparent=False):

        fname_no_ext = self.getFilenameNoExt()
        mapname = 'maps/' + self.map_names[self.current_index]
        fogname = 'config/fogmaps/' + fname_no_ext + ".png"
        im_orig = Image.open(mapname)
        im_fog = Image.open(fogname).filter(ImageFilter.GaussianBlur(self.blur_radius))

        if transparent:
            im_fog = Image.eval(im_fog, modAlpha)

        im_base = Image.new("RGBA", im_orig.size)
        im_base.paste(im_orig)
        im_comp = Image.alpha_composite(im_base, im_fog)

        if self.grid_shown:
            im_comp = Image.alpha_composite(im_comp, self.getGrid(im_orig.size))

        qim = ImageQt(im_comp)
        return QtGui.QPixmap.fromImage(qim)

    def setClearFog(self):
        self.resetFog(0)   

    def setResetFog(self):
        self.resetFog(255)        
    
    def elasticView(self):
        if self.sender().isChecked():
            h_scroll = self.scroll_control.horizontalScrollBar().value()
            v_scroll = self.scroll_control.verticalScrollBar().value()        
            self.previous_scroll = [h_scroll, v_scroll]
            self.but_lock_view.setChecked(False)
            self.display_mode = "Elastic"
        else:        
            h_bar_ctrl = self.scroll_control.horizontalScrollBar()
            v_bar_ctrl = self.scroll_control.verticalScrollBar()
            h_bar_ctrl.setValue(self.previous_scroll[0])
            v_bar_ctrl.setValue(self.previous_scroll[1])
            self.propogateScroll()
            self.display_mode = None  
            self.but_lock_view.setChecked(True)          

    def resetFog(self, alpha):
        pixmap = QPixmap('maps/' + self.map_names[self.current_index])
        im_w = pixmap.width()
        im_h = pixmap.height()

        im = Image.new("RGBA", (im_w, im_h))
        dr = ImageDraw.Draw(im)
        dr.rectangle([(0, 0), (im_w, im_h)], fill=(0, 0, 0, alpha))
        del dr
        im.save("/home/benjamin/git_ws/mapster/config/fogmaps/" 
            + self.getFilenameNoExt() + ".png")

        self.saveScrollValues()
        self.displayMap()

#--**--..--**--..--**--..--**--..--**--..--**--..--**--..--**--..--**--
# main():
#    Main function.
#--..--**--..--**--..--**--..--**--..--**--..--**--..--**--..--**--..-- 
def main():
    
    #sys.settrace(trace)
    app = QApplication(sys.argv)
  
    control_ui = ControlDialog()    
    control_ui.show()   
  
    app.exec_()

#--**--..--**--..--**--..--**--..--**--..--**--..--**--..--**--..--**--
# Initialiser.
#--..--**--..--**--..--**--..--**--..--**--..--**--..--**--..--**--..-- 
if __name__ == '__main__':
    main()