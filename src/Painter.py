#!/usr/bin/python
# Author  : David DEVANT
# Desc    : Modify a PNG file to add markers on it
# File    : Painter.py
# Date    : Sept. 11th, 2021

import Logger
from PIL import Image                           # Used to display a image file
from PIL import ImageDraw                       # Used to draw text and forms on images
from PIL import ImageFont                       # Used to access text fonts
import math                                     # For Pi constant

class Painter:

    MAX_SIDEBAR_ROW = 64

    def __init__(self, mapGen):
        self.open(mapGen.get_img_obj())

        self.sideBarRowCounter = 0
        self.sideBarWidth = 0
        self.sideBarFont = None
        self.mapGen = mapGen

    def open_file(self, imgPath):
        self.imgPath = imgPath
        self.img = Image.open(imgPath)

        self.open(self.img)

    def open(self, imgObj):
        self.img = imgObj
        self.artist = ImageDraw.Draw(self.img)

    def show(self):
        self.img.show()

    def save(self, path=None):
        if (path == None):
            path = self.imgPath

        self.img.save(path)

    def close(self):
        self.imgPath = ""
        self.img.close()

    def add_side_bar(self, sideBarWidth, backColor=0xFFFFFF):
        Logger.info("Adding side bar to image...")
        width, height = self.img.size

        # Create a new image wider, paste previous content and move to this new object
        result = Image.new(self.img.mode, (width + sideBarWidth, height), backColor)
        result.paste(self.img, (sideBarWidth - 1, 0))
        self.img.close()
        self.open(result)

        self.sideBarWidth = sideBarWidth
        self.sideBarHeight = height
        self.rowHeight = int(self.sideBarHeight / self.MAX_SIDEBAR_ROW)
        self.sideBarPadding = int(sideBarWidth * 0.01)
        self.yPadding = self.sideBarPadding
        # [Space][marker of heigh][Space][Text]
        self.xPadding = self.sideBarPadding + self.rowHeight + self.sideBarPadding
        self.markerSize = self.rowHeight * 0.95
        self.sideBarFont = ImageFont.truetype('Arial.ttf', self.rowHeight)

    def add_map_marker(self, markerPos, color, shape):
        x, y = self.mapGen.lon_lat_to_px(markerPos)

        # Don't forget the side bar on the left
        x = x + self.sideBarWidth
        self.add_icon_marker(x, y, color, shape)

    def add_icon_marker(self, x, y, color, shape):
        outlineColor = "black"
        r = self.markerSize / 2

        if (shape == "circle" or shape == "home"):
            r = r * 0.90
            self.artist.ellipse((x-r, y-r, x+r, y+r), fill=color, outline=outlineColor)
        elif (shape == "rectangle"):
            r = r * 0.80
            self.artist.rectangle((x-r, y-r, x+r, y+r), fill=color, outline=outlineColor)
        elif (shape == "triangle"):
            alpha = (2 * math.pi) / 3 / 2
            yUp = y - r * math.cos(alpha)
            xHalfUp = r * math.sin(alpha)
            xRight = x + xHalfUp
            xLeft = x - xHalfUp

            self.artist.polygon([(xLeft, yUp), (x, y + r), (xRight, yUp)], fill=color, outline=outlineColor)
        elif (shape == "cross"):
            thick = int(r * 0.50)
            r = r * 0.80
            line1Pos = (x-r, y-r, x+r, y+r)
            line2Pos = (x+r, y-r, x-r, y+r)
            self.artist.line(line1Pos, fill=color, width=thick)
            self.artist.line(line2Pos, fill=color, width=thick)
        elif (shape == "star") or (shape == "sun"):
            if (shape == "star"):
                picCount = 5
                radiusFactor = 0.4
            else:
                picCount = 10
                radiusFactor = 0.5
            polyPoints = []
            alpha = - math.pi / 2 # Begin at upper point
            alphaStep = (2 * math.pi) / picCount / 2

            # For each pic, add a sub pic at inferior radius
            for i in range(0, picCount):
                for picRadius in [r, r * radiusFactor]:
                    pX = x + picRadius * math.cos(alpha)
                    pY = y + picRadius * math.sin(alpha)
                    polyPoints.append((pX, pY))
                    alpha = alpha + alphaStep
            self.artist.polygon(polyPoints, fill=color, outline=outlineColor)
        else:
            Logger.error("Unknown shape for marker: \"{0}\"".format(shape))
            return

    def add_side_bar_marker(self, row, color, shape):
        x = self.xPadding / 2
        y = self.yPadding + row * self.rowHeight + self.rowHeight / 2

        self.add_icon_marker(x, y, color, shape)

    def add_legend_title(self, text):
        # Compute position
        x = self.sideBarPadding
        y = self.yPadding

        # Add Label
        self.artist.text((x, y), text, font=self.sideBarFont, fill=0x000000)

    def add_legend_name(self, row, name, color, shape):
        # Compute position
        x = self.xPadding
        y = self.yPadding + self.rowHeight * row

        # Add Label
        self.artist.text((x, y), name, font=self.sideBarFont, fill=0x000000)

        # Add the corresponding marker
        self.add_side_bar_marker(row, color, shape)

    def add_marker(self, name, markerPos, color, shape):
        # Ignore bad positions
        if (markerPos == None):
            return

        # Check space left
        if (self.sideBarRowCounter >= self.MAX_SIDEBAR_ROW):
            Logger.warning("No more space left in the side bar !")
            return
        else:
            self.sideBarRowCounter += 1

        # Add to sidebar
        self.add_legend_name(self.sideBarRowCounter, name, color, shape)
        self.add_map_marker(markerPos, color, shape)