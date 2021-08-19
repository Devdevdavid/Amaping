#!/usr/bin/python
# Author  : David DEVANT
# Desc    : See APP_DESC :)
# File    : amaping.py
# Date    : July 4th, 2021
# Version : 0.1.0

import time
import signal, os
import logging                                  # Use for log message in console
import traceback                                # For debugging unhandled exceptions
import argparse                                 # To parse command line arguments
from geopy.geocoders import Nominatim           # Get GeoCode from text address
from geopy.distance import geodesic             # Mesure distances
import pandas as pd                             # Read CSV file
from staticmap import *                         # Used to generate a map from OpenStreetMap database
from PIL import Image                           # Used to display a image file
from PIL import ImageDraw                       # Used to draw text and forms on images
from PIL import ImageFont                       # Used to access text fonts
import pickle                                   # Used to load/save context an speedup developpement

# Constants
APP_NAME = "Amaping"
APP_DESC = "Build a map of AMAP members locations"

# Globale Variables
logger = None
geoLocator = None

# Tell is value is considered as set or not
def _isset(value):
    if (pd.isna(value)):
        return False
    elif (value == ""):
        return False
    else:
        return True

class Painter:

    MAX_SIDEBAR_ROW = 64

    def __init__(self, imgPath=None, mapGen=None):
        if (imgPath == None):
            self.imgPath = ""
            self.img = None
        else:
            self.open(imgPath)

        self.sideBarRow = 0
        self.sideBarWidth = 0
        self.sideBarFont = None
        self.mapGen = mapGen

    def open(self, imgPath):
        self.imgPath = imgPath
        self.img = Image.open(imgPath)
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

    def add_side_bar(self, sideBarWidth, backColor=0xFFFFFFFF):
        newImgPath = self.imgPath + ".jpeg"
        width, height = self.img.size

        result = Image.new(self.img.mode, (width + sideBarWidth, height), backColor)
        result.paste(self.img, (sideBarWidth - 1, 0))
        result.save(newImgPath)
        result.close()

        self.sideBarWidth = sideBarWidth
        self.sideBarHeight = height
        self.rowHeight = int(self.sideBarHeight / self.MAX_SIDEBAR_ROW)
        self.yPadding = int(sideBarWidth * 0.05)
        # [Space][marker of heigh][Space][Text]
        self.xPadding = int(sideBarWidth * 0.01) + self.rowHeight + int(sideBarWidth * 0.01)
        self.markerSize = self.rowHeight * 0.95
        self.sideBarFont = ImageFont.truetype('Arial.ttf', self.rowHeight)

        # Reopen file
        self.close()
        self.open(newImgPath)

    def add_map_marker(self, markerPos, color="blue", shape="circle"):
        print(markerPos)
        print(self.mapGen.lon_lat_to_px(markerPos))
        pass

    def add_icon_marker(self, x, y, color="blue", shape="circle"):
        if (shape == "circle"):
            r = self.markerSize / 2
            self.artist.ellipse((x-r, y-r, x+r, y+r), fill=color)
        elif (shape == "rectangle"):
            r = self.markerSize / 2
            self.artist.rectangle((x-r, y-r, x+r, y+r), fill=color)
        elif (shape == "triangle"):
            pass
        else:
            logger.error("Unknown shape for marker: \"{0}\"".format(shape))
            return

    def add_side_bar_marker(self, row, color="blue", shape="circle"):
        x = self.xPadding / 2
        y = self.yPadding + row * self.rowHeight + self.rowHeight / 2

        self.add_icon_marker(x, y, color, shape)

    def add_legend_name(self, row, name, color="blue", shape="circle"):
        # Compute position
        x = self.xPadding
        y = self.yPadding + self.rowHeight * row

        # Add Label
        self.artist.text((x, y), name, font=self.sideBarFont, fill=0x000000)

        # Add the corresponding marker
        self.add_side_bar_marker(row, color, shape)

    def add_marker(self, name, markerPos, color="blue", shape="circle"):
        # Ignore bad positions
        if (markerPos == None):
            return

        # Check space left
        if (self.sideBarRow >= self.MAX_SIDEBAR_ROW):
            logger.warning("No more space left in the side bar !")
            return

        # Add to sidebar
        self.add_legend_name(self.sideBarRow, name, color, shape)
        self.add_map_marker(markerPos, color, shape)
        self.sideBarRow += 1

class AmapMember:
    # =============
    # Variables
    # =============

    def __init__(self):
        self.people = []
        self.address = ""
        self.coords = None
        self.color = "blue"
        self.shape = "circle"

    def set_id(self, id):
        self.id = id

    def add_people(self, name, firstname):
        self.people.append((name, firstname))

    # Build a nice string with all declared people
    # in a coma separated list with the id at the end
    def get_display_name(self):
        # Check people count
        if (len(self.people) == 0):
            return "<No name>"

        # Build independant strings
        displayNames = []
        for name, firstname in self.people:
            name = name.upper()

            displayNames.append("{0} {1}".format(name, firstname))

        displayString =  ", ".join(str(x) for x in displayNames)
        # displayString += " (id: {0})".format(self.id)

        return displayString

    def set_address(self, address):
        self.address = address

    def set_city(self, city):
        self.city = city

    # Pandas gives a float, cast it to int
    def set_postal_code(self, postalCode):
        self.postalCode = int(postalCode)

    # Build a nicec string with address related informations
    def get_display_address(self):
        return "{0}, {1}, {2}".format(self.address, self.city, self.postalCode)

    def set_marker(self, color, shape):
        self.color = color
        self.shape = shape

    def get_color(self):
        return self.color

    def get_shape(self):
        return self.shape

    # Return the (lat, lon) pin point location corresponding to the address
    def req_map_position(self):
        # Init in case of error
        self.coords = None

        # Do nothing if address is not set
        if ((self.address == "") or (self.postalCode == "") or (self.city == "")):
            return self.get_map_position()

        # Get complete address
        reqAddr = self.get_display_address()

        # Get location from address
        logger.debug("Requesting geocode for \"{0}\"".format(reqAddr))
        try:
            location = geoLocator.geocode(reqAddr)
        except Exception as e:
            logger.error("geoLocator failed: " + str(e));
            return self.get_map_position()

        # Check if request succeeded
        if (location == None):
            logger.error("Unable to find GeoCode for \"{0}\" !".format(reqAddr))
            return self.get_map_position()

        # Return coords
        self.coords = (location.longitude, location.latitude)

        # Return result
        return self.get_map_position()

    def get_map_position(self):
        return self.coords

    # Tell if member is located near the closePoint
    def is_close_to(self, closePoint, distanceThresholdKm = 5):
        # Check if we have valid coords
        if (self.get_map_position() == None):
            return False

        # Compute the distance between the closePoint and the member location
        distanceKm = geodesic(self.get_map_position(), closePoint).km

        logger.debug("{0} is {1:.2} km away from close point".format(self.id, distanceKm))

        # Return True if under threshold, False otherwise
        return distanceKm <= distanceThresholdKm

class MapGenerator:

    # CONSTANTS
    MARKER_OUTLINE_COLOR = "white"

    # Prepare a new map
    def __init__(self, zoomLevel = 5, mapSize=(1920, 1080)):
        # Get map base image
        self.zoomLevel = zoomLevel
        self.map = StaticMap(mapSize[0], mapSize[1], url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')

    # Save map to file
    def save(self, mapFileName):
        self.mapFileName = mapFileName
        logger.debug("Saving map to file \"{0}\"".format(self.mapFileName))

        # Save image to file
        image = self.map.render(zoom=self.zoomLevel)
        image.save(self.mapFileName)

    def lon_lat_to_px(self, markerPos):
        return (
            self.map._x_to_px(staticmap._lon_to_x(markerPos[0], self.zoomLevel)) * 2,
            self.map._y_to_px(staticmap._lat_to_y(markerPos[1], self.zoomLevel)) * 2
        )


    def add_marker(self, markerPos, color="blue", shape="circle"):
        # Ignore bad positions
        if (markerPos == None):
            return

        if (shape == "circle"):
            markerOutline = CircleMarker(markerPos, self.MARKER_OUTLINE_COLOR, 18)
            marker = CircleMarker(markerPos, color, 12)

            self.map.add_marker(markerOutline)
            self.map.add_marker(marker)
        elif (shape == "rectangle") or (shape == "triangle"):
            # Those shapes are handled with polygons

            # There is the outline and the inside to draw
            for isInside in range(0, 2):

                # The ratio between latitude and longitude is not 1
                latFactor = 0.0001 * (4 - isInside * 1)
                if (shape == "rectangle"):
                    longFactor = 0.0001 * (3 - isInside * 1)
                else:
                    longFactor = 0.0001 * (5 - isInside * 1)

                # Compute polygon points
                longWest = markerPos[0] - longFactor
                longEast = markerPos[0] + longFactor
                latNorth = markerPos[1] + latFactor
                latSouth = markerPos[1] - latFactor

                if (shape == "rectangle"):
                    polyCoords = [
                        [longWest, latNorth],
                        [longWest, latSouth],
                        [longEast, latSouth],
                        [longEast, latNorth]
                    ]
                elif (shape == "triangle"):
                    polyCoords = [
                        [markerPos[0], latNorth],
                        [longWest, latSouth],
                        [longEast, latSouth]
                    ]

                # Choose color
                if (isInside):
                    polyColor = color
                else:
                    polyColor = self.MARKER_OUTLINE_COLOR

                # Add the new marker
                marker = Polygon(polyCoords, polyColor, "white")
                self.map.add_polygon(marker)
        else:
            logger.error("Unknown shape for marker: \"{0}\"".format(shape))
            return

    # Open last saved map
    def show(self):
        im = Image.open(self.mapFileName)
        im.show()

class Amaping:
    """
    """

    # =============
    # CONSTANTS
    # =============

    DEFAULT_CSV_FILENAME = 'amap_data.csv'
    DEFAULT_CSV_SEPARATOR = ';'
    DEFAULT_OUTPUT_MAP_NAME = 'map.png'
    DEFAULT_MAP_ZOOM_LEVEL = 16
    DEFAULT_MAP_SIZE = "4080x4080"
    AMAP_ADDRESS = "Salle Brama, Avenue Sainte-Marie"
    AMAP_CITY = "Talence"
    AMAP_POSTAL_CODE = "33400"

    # =============
    # Variables
    # =============

    config = None             # Store the configuration
    amapMemberArray = []      # Store data of all members

    # =============
    # Members
    # =============

    def handler_sigint(self, signum, frame):
        self.isAppQuitting = True
        raise RuntimeError("Stopped by user")

    def __init__(self):
        # Init
        self.isAppQuitting = False

        # Check arguments
        parser = argparse.ArgumentParser(description=APP_DESC)
        parser.add_argument('-v', '--verbose', help='enable verbose logs', default=False, action='store_true')
        parser.add_argument('-c', '--csv', default=self.DEFAULT_CSV_FILENAME, dest="csvFilename", help='specify CSV data file', type=str)
        parser.add_argument('-s', '--separator', default=self.DEFAULT_CSV_SEPARATOR, dest="csvSeparator", help='specify CSV column speparator', type=str)
        parser.add_argument('-o', '--output', default=self.DEFAULT_OUTPUT_MAP_NAME, dest="mapFilename", help='specify a map filename', type=str)
        parser.add_argument('-m', '--mapSize', default=self.DEFAULT_MAP_SIZE, dest="mapSize", help='specify a size in pixel for map generation (Ex: 1920x1080)', type=str)
        parser.add_argument('-z', '--zoomLevel', default=self.DEFAULT_MAP_ZOOM_LEVEL, dest="zoomLevel", help='specify a zoom level for map generation', type=int)

        # Use vars() to get python dict from Namespace object
        self.args = vars(parser.parse_args())

        # Handle args
        if self.args["verbose"]:
            logger.setLevel(logging.DEBUG)

        # See https://wiki.openstreetmap.org/wiki/Zoom_levels
        # 20 might not be available everywhere
        if (self.args["zoomLevel"] < 0) or (self.args["zoomLevel"] > 20):
            raise RuntimeError("Zoom level must be in range [0; 20]")

    def save_context(self):
        f = open('amapMemberArray.obj', 'wb')
        pickle.dump(self.amapMemberArray, f)
        logger.debug("Saving context to file")

    def load_context(self):
        try:
            f = open('amapMemberArray.obj', 'rb')
        except Exception as e:
            logger.info("There is no context to load")
            return -1

        self.amapMemberArray = pickle.load(f)
        return 0

    def run(self):
        # Load CSV file
        data = pd.read_csv(self.args["csvFilename"], sep=self.args["csvSeparator"], header=0)

        # Get AMAP address
        salleBrama = AmapMember()
        salleBrama.set_address(self.AMAP_ADDRESS)
        salleBrama.set_city(self.AMAP_CITY)
        salleBrama.set_postal_code(self.AMAP_POSTAL_CODE)
        if (salleBrama.req_map_position() == None):
            raise RuntimeError("Unable to find AMAP address: \"{0}\"".format(amap.get_display_address()))

        # Clear output array
        self.amapMemberArray = []

        self.csvDataRowCount = len(data.index)
        logger.debug("Found {0} rows in CSV file \"{1}\"".format(self.csvDataRowCount, self.args["csvFilename"]))

        if self.load_context() == -1:
            # For each line in the CSV...
            for index, rowdata in data.iterrows():
                member = AmapMember()

                time.sleep(1)

                # Manage ID
                if (_isset(rowdata['id'])):
                    member.set_id(rowdata['id'])

                # Manage names
                if (_isset(rowdata['Nom']) and _isset(rowdata['Prénom'])):
                    member.add_people(rowdata['Nom'], rowdata['Prénom'])

                if (_isset(rowdata['Nom du·de la conjoint·e']) and _isset(rowdata['Prénom du·de la conjoint·e'])):
                    member.add_people(rowdata['Nom du·de la conjoint·e'], rowdata['Prénom du·de la conjoint·e'])

                # Manage address
                if (_isset(rowdata['Adresse 1']) and _isset(rowdata['Adresse 2'])):
                    member.set_address(rowdata['Adresse 1'])

                    # Display warning
                    logger.warning("2 addresses detected for member {0}, choosing {1}".format(
                        member.get_display_name(),
                        member.get_address()))
                elif (_isset(rowdata['Adresse 1'])):
                    member.set_address(rowdata['Adresse 1'])
                elif (_isset(rowdata['Adresse 2'])):
                    member.set_address(rowdata['Adresse 2'])
                else:
                    logger.warning("No address detected for member {0}".format(member.get_display_name()))
                    continue

                if (_isset(rowdata['Ville'])):
                    member.set_city(rowdata['Ville'])

                if (_isset(rowdata['Code postal'])):
                    member.set_postal_code(rowdata['Code postal'])

                # Get Geocode, ignore if it failed
                if (member.req_map_position() == None):
                    continue

                # Filter out member with far locations
                if (not member.is_close_to(amap.get_map_position())):
                    continue

                # Add member to output array
                self.amapMemberArray.append(member)

            # DEBUG - Keep only a few members for tests
            # self.amapMemberArray = self.amapMemberArray[0:2]

            # Check remove members
            self.removeMemberCount = self.csvDataRowCount - len(self.amapMemberArray)
            if (self.removeMemberCount > 0):
                logger.warning("{0} members will not be on the map because of above warnings/errors !".format(self.removeMemberCount))

            # Save context to speed up latter execution
            self.save_context()
        else:
            logger.info("Using cached context file")

        # Add Salle Brama to the member list in order to be drawn as all other members
        self.amapMemberArray.append(salleBrama)

        # Generate colors

        # Define color and shape for each members
        colorIndex = 0
        shapeIndex = 0
        markerColors = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta"]
        markerShapes = ["circle", "rectangle", "triangle"]
        for member in self.amapMemberArray:
            member.set_marker(markerColors[colorIndex], markerShapes[shapeIndex])

            # Move on
            # Use next color
            if (colorIndex < len(markerColors) - 1):
                colorIndex += 1
            else:
                colorIndex = 0
                # Use next shape when all color have been used
                if (shapeIndex < len(markerShapes) - 1):
                    shapeIndex += 1
                else:
                    shapeIndex = 0
                    logger.warning("All Color/Shape combo have been used !")

        # Genarate map
        mapSize = tuple(map(int, self.args["mapSize"].split('x')))
        mapGen = MapGenerator(zoomLevel=self.args["zoomLevel"], mapSize=mapSize)

        # Add sidebar
        painter = Painter(self.args["mapFilename"], mapGen=mapGen)

        sideBarWidth = int(mapSize[0] / 3)
        painter.add_side_bar(sideBarWidth)

        # Add markers
        self.amapMemberArray = self.amapMemberArray[0:10]

        for member in self.amapMemberArray:
            mapGen.add_marker(member.get_map_position(), member.get_color(), member.get_shape())
        # mapGen.save(self.args["mapFilename"])

        for member in self.amapMemberArray:
            painter.add_marker(member.get_display_name(), member.get_map_position(), member.get_color(), member.get_shape())
        painter.save(self.args["mapFilename"] + ".jpg")

        painter.show()
        painter.close()


if __name__ == '__main__':
    # Logging
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)
    logger = logging.getLogger(APP_NAME)

    # Init global variables
    geoLocator = Nominatim(user_agent="http")

    try:
        # Init app
        app = Amaping()

        # Configure signal handler
        signal.signal(signal.SIGINT, app.handler_sigint);

        app.run()
    except Exception as e:
        logger.error("Exit with errors: " + str(e));
        logger.debug(traceback.format_exc())









