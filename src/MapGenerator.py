#!/usr/bin/python
# Author  : David DEVANT
# Desc    : Generate a map with OSM
# File    : MapGenerator.py
# Date    : Sept. 11th, 2021

import Logger
from staticmap import *                         # Used to generate a map from OpenStreetMap database

class MapGenerator:

    # CONSTANTS
    MARKER_OUTLINE_COLOR = "white"

    # Prepare a new map
    def __init__(self, center, zoomLevel = 5, mapSize=(1920, 1080)):
        # Get map base image
        self.zoomLevel = zoomLevel
        self.center = center
        self.map = StaticMap(mapSize[0], mapSize[1], url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')

    # Render by donwloading map from OSM
    def render(self):
        Logger.info("Rendering map...")
        # Save image to file
        self.image = self.map.render(center=self.center, zoom=self.zoomLevel)

    # Get the image object of the rendered map
    def get_img_obj(self):
        return self.image

    # Save map to file
    def save(self, mapFileName):
        self.mapFileName = mapFileName
        Logger.debug("Saving map to file \"{0}\"".format(self.mapFileName))

        # Save image to file
        self.image.save(self.mapFileName)

    def lon_lat_to_px(self, markerPos):
        xTile = staticmap._lon_to_x(markerPos[0], self.zoomLevel)
        yTile = staticmap._lat_to_y(markerPos[1], self.zoomLevel)
        markerTilePos = (xTile, yTile)

        return (
            self.map._x_to_px(markerTilePos[0]),
            self.map._y_to_px(markerTilePos[1])
        )

    # Open last saved map
    def show(self):
        im = Image.open(self.mapFileName)
        im.show()