#!/usr/bin/python
# Author  : David DEVANT
# Desc    : Describe an member
# File    : AmapMemebr.py
# Date    : Sept. 11th, 2021

import Logger
from geopy.distance import geodesic             # Mesure distances

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
    def req_map_position(self, geoLocator):
        # Init in case of error
        self.coords = None

        # Do nothing if address is not set
        if ((self.address == "") or (self.postalCode == "") or (self.city == "")):
            Logger.error("Bad address specified for member {0}".format(self.get_display_address()))
            return self.get_map_position()

        # Get complete address
        reqAddr = self.get_display_address()

        # Get location from address
        Logger.debug("Requesting geocode for \"{0}\"".format(reqAddr))
        try:
            location = geoLocator.geocode(reqAddr)
        except Exception as e:
            Logger.error("geoLocator failed: " + str(e));
            return self.get_map_position()

        # Check if request succeeded
        if (location == None):
            Logger.error("Unable to find GeoCode for \"{0}\" !".format(reqAddr))
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

        Logger.debug("{0} is {1:.2} km away from close point".format(self.id, distanceKm))

        # Return True if under threshold, False otherwise
        return distanceKm <= distanceThresholdKm
