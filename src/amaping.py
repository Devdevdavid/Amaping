#!/usr/bin/python
# Author  : David DEVANT
# Desc    : See APP_DESC :)
# File    : Amaping.py
# Date    : July 4th, 2021
# Version : 1.0.0

import time
import signal, os
import traceback                                # For debugging unhandled exceptions
import argparse                                 # To parse command line arguments
from geopy.geocoders import Nominatim           # Get GeoCode from text address
import pandas                                   # Read CSV file
import pickle                                   # Used to load/save context an speedup developpement

from Painter import Painter
from MapGenerator import MapGenerator
import Logger
import Framacarte                               # To generate geojson files
from AmapMember import AmapMember               # Define a member

# Constants
APP_NAME = "Amaping"
APP_DESC = "Build a map of AMAP members locations"

# Globale Variables
geoLocator = None

# Tell is value is considered as set or not
def _isset(value):
    if (pandas.isna(value)):
        return False
    elif (value == ""):
        return False
    else:
        return True

class Amaping:

    # =============
    # CONSTANTS
    # =============

    DEFAULT_CSV_FILENAME = './ressources/amap_data.csv'
    DEFAULT_ODS_FILENAME = './ressources/Cagette_Adh_Brama-2021-09.ods'
    DEFAULT_CSV_SEPARATOR = ';'
    DEFAULT_OUTPUT_MAP_NAME = './output/map.png'
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
        parser.add_argument('-j', '--geojson', default=False, dest="geojson", help='enable geojson file generation', action='store_true')
        parser.add_argument('-p', '--png', default=False, dest="png", help='enable PNG file generation', action='store_true')
        parser.add_argument('-c', '--csv', default=self.DEFAULT_CSV_FILENAME, dest="csvFilename", help='specify CSV data file', type=str)
        parser.add_argument('-d', '--ods', default=self.DEFAULT_ODS_FILENAME, dest="odsFilename", help='specify ODS data file', type=str)
        parser.add_argument('-s', '--separator', default=self.DEFAULT_CSV_SEPARATOR, dest="csvSeparator", help='specify CSV column speparator', type=str)
        parser.add_argument('-o', '--output', default=self.DEFAULT_OUTPUT_MAP_NAME, dest="mapFilename", help='specify a map filename', type=str)
        parser.add_argument('-m', '--mapSize', default=self.DEFAULT_MAP_SIZE, dest="mapSize", help='specify a size in pixel for map generation (Ex: 1920x1080)', type=str)
        parser.add_argument('-z', '--zoomLevel', default=self.DEFAULT_MAP_ZOOM_LEVEL, dest="zoomLevel", help='specify a zoom level for map generation', type=int)

        # Use vars() to get python dict from Namespace object
        self.args = vars(parser.parse_args())

        # Handle args
        if self.args["verbose"]:
            Logger.setLevelDebug()

        if not self.args["png"] and not self.args["geojson"]:
            raise RuntimeError("At least one type of file generation is needed, use -j or -p !")

        # See https://wiki.openstreetmap.org/wiki/Zoom_levels
        # 20 might not be available everywhere
        if (self.args["zoomLevel"] < 0) or (self.args["zoomLevel"] > 20):
            raise RuntimeError("Zoom level must be in range [0; 20]")

    def save_context(self):
        f = open('./output/amapMemberArray.obj', 'wb')
        pickle.dump(self.amapMemberArray, f)
        Logger.debug("Saving context to file")

    def load_context(self):
        try:
            f = open('./output/amapMemberArray.obj', 'rb')
        except Exception as e:
            Logger.info("There is no context to load")
            return -1

        self.amapMemberArray = pickle.load(f)
        return 0

    def open_ods_sheet(self, odsFile, sheetName):
        Logger.info("ODS - Reading sheet " +  sheetName)
        return pandas.read_excel(odsFile, engine='odf', sheet_name=sheetName)

    def find_member_by(self, name1, name2):
        # Find a match in our member list
        for member in self.amapMemberArray:
            displayName = member.get_display_name().lower()

            # Check name 1
            if (not name1.lower() in displayName):
                continue

            #  Check name 2
            if (name2 != ""):
                if (not name2.lower() in displayName):
                    continue

            # Return found member
            return member

        # Member not found
        Logger.warning("Couldn't find a match for {0}/{1}".format(name1, name2))
        return None

    def find_member_from_row(self, row, index):
        nom1 = nom2 = ""

        if (_isset(row['nom'])):
            nom1 = row['nom'].replace(" ", "")
        else:
            Logger.debug("Couldn't find a match for row {0}".format(index))
            return None

        if (_isset(row['nom conjoint'])):
            nom2 = row['nom conjoint'].replace(" ", "")

        # Find a match in our member list
        matchMember = self.find_member_by(nom1, nom2)

        return matchMember

    def run(self):
        # Load CSV file
        data = pandas.read_csv(self.args["csvFilename"], sep=self.args["csvSeparator"], header=0)

        # Get AMAP address
        salleBrama = AmapMember()
        salleBrama.add_people("Salle", "Brama")
        salleBrama.set_address(self.AMAP_ADDRESS)
        salleBrama.set_city(self.AMAP_CITY)
        salleBrama.set_postal_code(self.AMAP_POSTAL_CODE)
        if (salleBrama.req_map_position(geoLocator) == None):
            raise RuntimeError("Unable to find AMAP address: \"{0}\"".format(salleBrama.get_display_address()))

        # Clear output array
        self.amapMemberArray = []

        self.csvDataRowCount = len(data.index)
        Logger.debug("Found {0} rows in CSV file \"{1}\"".format(self.csvDataRowCount, self.args["csvFilename"]))

        if self.load_context() == -1:
            # Open a report file to log what needs to be modified in DB
            reportFile = open("./output/report.txt", "w")

            # For each line in the CSV...
            for index, rowdata in data.iterrows():
                member = AmapMember()

                # Manage ID
                if (_isset(rowdata['id'])):
                    member.set_id(rowdata['id'])

                # Manage names
                if (_isset(rowdata['Nom']) and _isset(rowdata['Prénom'])):
                    member.add_people(rowdata['Nom'], rowdata['Prénom'])

                if (_isset(rowdata['Nom partenaire']) and _isset(rowdata['Prénom partenaire'])):
                    member.add_people(rowdata['Nom partenaire'], rowdata['Prénom partenaire'])

                # Manage address
                if (_isset(rowdata['Adresse 1']) and _isset(rowdata['Adresse 2'])):
                    member.set_address(rowdata['Adresse 1'])

                    # Display warning
                    Logger.warning("2 addresses detected for member {0}, choosing {1}".format(
                        member.get_display_name(),
                        member.get_address()))
                elif (_isset(rowdata['Adresse 1'])):
                    member.set_address(rowdata['Adresse 1'])
                elif (_isset(rowdata['Adresse 2'])):
                    member.set_address(rowdata['Adresse 2'])
                else:
                    Logger.warning("No address detected for member {0}".format(member.get_display_name()))
                    reportFile.write("Pas d'adresse pour {0}\n".format(member.get_display_name()))
                    continue

                if (_isset(rowdata['Ville'])):
                    member.set_city(rowdata['Ville'])

                if (_isset(rowdata['Code postal'])):
                    member.set_postal_code(rowdata['Code postal'])

                # Get Geocode, ignore if it failed
                if (member.req_map_position(geoLocator) == None):
                    reportFile.write("Le membre {0} a une adresse non reconnue : \"{1}\"\n".format(
                        member.get_display_name(),
                        member.get_display_address()
                    ))
                    continue

                # Filter out member with far locations
                isCloseToHome = member.is_close_to(salleBrama.get_map_position())
                member.set_close_to_home(isCloseToHome)
                if (not isCloseToHome):
                    Logger.warning("Member {0} is too far away from {1}".format(
                        member.get_display_name(),
                        salleBrama.get_display_name())
                    )
                    reportFile.write("Le membre {0} est trop éloigné de {1} pour être affiché sur la map PNG\n".format(
                        member.get_display_name(),
                        salleBrama.get_display_name()
                    ))

                if (_isset(rowdata['Téléphone'])):
                    member.set_phone(rowdata['Téléphone'])

                if (_isset(rowdata['Email'])):
                    member.set_email(rowdata['Email'])

                # Add member to output array
                self.amapMemberArray.append(member)


            # Check remove members
            self.removeMemberCount = self.csvDataRowCount - len(self.amapMemberArray)
            if (self.removeMemberCount > 0):
                Logger.warning("{0} members will not be on the map because of above warnings/errors !".format(self.removeMemberCount))
                reportFile.write("{0} membre(s) nécessite de l'attention\n".format(self.removeMemberCount))

            # Close the report file, we don't need it anymore
            reportFile.close()

            # Save context to speed up latter execution
            self.save_context()
        else:
            Logger.info("Using cached context file")

        # ========================
        #        ODS FILE
        # ========================

        if (self.args["odsFilename"] != ""):
            Logger.info("ODS - Reading file " +  self.args["odsFilename"])

            # Analyse 1st sheet
            odsContent = self.open_ods_sheet(self.args["odsFilename"], "COORDONNEES")

            # Iterate over each lines of the file
            for index, row in odsContent.iterrows():
                matchMember = self.find_member_from_row(row, index)
                if (matchMember == None):
                    continue

                # Add info
                if (_isset(row['Rôles'])):
                    matchMember.set_role(row['Rôles'])
                else:
                    matchMember.set_role("Adhérent")

            # Analyse 1st sheet
            odsContent = self.open_ods_sheet(self.args["odsFilename"], "ENGAGEMENTS")

            # Iterate over each lines of the file
            for index, row in odsContent.iterrows():
                matchMember = self.find_member_from_row(row, index)
                if (matchMember == None):
                    continue

                # Add info
                if (row['Légumes'] in ("hebdo", "pair", "impair")):
                    matchMember.set_type_panier(row['Légumes'])

        # ========================
        #    COLORS AND SHAPES
        # ========================

        # Define color and shape for each members
        markerShapes = ["star", "triangle", "sun", "circle", "rectangle", "cross"]
        for member in self.amapMemberArray:
            color = "gray"
            shape = "cross"
            if (member.get_type_panier() != ""):
                if (member.get_type_panier() == "hebdo"):
                    color = "green"
                elif (member.get_type_panier() == "pair"):
                    color = "orange"
                elif (member.get_type_panier() == "impair"):
                    color = "blue"

            if (member.get_role() != "Adhérent"):
                shape = "rectangle"

            member.set_marker(color, shape)

        # Prepend Salle Brama to the member list in order to be drawn as all other members
        salleBrama.set_marker("red", "home")
        self.amapMemberArray.insert(0, salleBrama)

        # ========================
        #           GEOJSON
        # ========================

        if self.args["geojson"]:
            Logger.info("Generating GeoJSON file...")

            amapBrama = Framacarte.Collection("Brama")
            for member in self.amapMemberArray:
                # Set description
                description = member.get_display_address()

                # Add info if we got one
                if (member.get_type_panier() != ""):
                    description += "\nLégumes : " + member.get_type_panier().capitalize()
                if (member.get_phone() != ""):
                    description += "\nTel. : " + member.get_phone()
                if (member.get_email() != ""):
                    description += "\nEmail : " + member.get_email()
                if (member.get_role() != "Adhérent"):
                    description += "\nRôle : " + member.get_role()

                # Add the marker
                amapBrama.add_marker(
                    member.get_display_name(),
                    member.get_map_position(),
                    member.get_color(),
                    member.get_shape(),
                    description
                )
            amapBrama.write_file()

        # ========================
        #           PNG
        # ========================

        if self.args["png"]:
            Logger.info("Generating PNG file...")

            # Genarate map
            mapSize = tuple(map(int, self.args["mapSize"].split('x')))
            mapGen = MapGenerator(
                center=salleBrama.get_map_position(),
                zoomLevel=self.args["zoomLevel"],
                mapSize=mapSize
            )
            mapGen.render()

            # Reopend map with painter and sidebar
            painter = Painter(mapGen=mapGen)

            sideBarWidth = int(mapSize[0] / 3)
            painter.add_side_bar(sideBarWidth)

            # Add title
            painter.add_legend_title("{0} membres de l'AMAP Pétal :".format(len(self.amapMemberArray)))

            # Add markers
            Logger.info("Adding markers...")
            for member in self.amapMemberArray:
                # Ignore far members
                if (not member.is_close_to_home()):
                    continue

                painter.add_marker(
                    member.get_display_name(),
                    member.get_map_position(),
                    member.get_color(),
                    member.get_shape()
                )

            Logger.info("Openning output file...")
            painter.save(self.args["mapFilename"])
            painter.show()
            painter.close()

        # ========================
        #           DONE
        # ========================

        Logger.info("Work done !")

# ========================
#       ENTRY POINT
# ========================

if __name__ == '__main__':
    # Logging
    Logger.init(APP_NAME)

    # Init global variables
    geoLocator = Nominatim(user_agent="http")

    try:
        # Init app
        app = Amaping()

        # Configure signal handler
        signal.signal(signal.SIGINT, app.handler_sigint);

        app.run()
    except Exception as e:
        Logger.error("Exit with errors: " + str(e));
        Logger.debug(traceback.format_exc())









