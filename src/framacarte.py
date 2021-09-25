#!/usr/bin/python
# Author  : David DEVANT
# Desc    : Framacarte interface to build custom maps
# File    : framacarte.py
# Date    : Sept. 11th, 2021

import geojson        # To build GeoJSON files, can be imported on FramaCarte

# FramaCarte won't recognized the shapes used in Amaping so we need to convert them to icons
# Some icons are made available by FramaCarte
def convert_icon(shape):
	baseUrl = "/uploads/pictogram/"
	# Shapes db
	markerShapes = ["home", "star", "triangle", "sun", "circle", "rectangle", "cross"]
	markerIcons = [
		"convenience-24_W22NTg8.png",
		"alcohol-24_uiDmXKu.png",
		"camping-24_2qLEBqo.png",
		"luggage-24_jnGb8bD.png",
		"clothes-24_k5e76ia.png",
		"florist-24_V7jCu9j.png",
		"confectionery-24_WdoAJJD.png",
		"furniture-24_LyvkQP9.png",
		"viewpoint-24_KlNiPnM.png"
	]

	# Find into known shapes
	try:
		index = markerShapes.index(shape)
	except Exception as e:
		index = 0

	# Bound limits
	if (index < 0 and index >= len(markerIcons)):
		index = 0

	# Give the converted icon
	return baseUrl + markerIcons[index]

# Define a set of markers
# Each collection will generate a new file
class Collection:
	def __init__(self, name):
		self.featuresList = []
		self.name = name

	def get_name(self):
		return self.name

	def add_marker(self, name, pos, color, shape, description = ""):
		# Use Defaut icon for home point (Salle Brama for exemple)
		if shape == "home":
			iconClass = "Default"
		else:
			iconClass = "Drop"

		properties = {
			"name": name,
			"description": description,
			"_umap_options": {
				"color": color,
				"iconClass": iconClass,
				"iconUrl": convert_icon(shape)
			}
		}

		newFeature = geojson.Feature(
			geometry = geojson.Point(pos),
			properties = properties
		)

		self.featuresList.append(newFeature)

	def write_file(self):
		collection = geojson.FeatureCollection(self.featuresList)
		dump = geojson.dumps(collection)
		filename = "./output/FramaCarte_" + self.get_name() + ".geojson"

		outputFile = open(filename, "w")
		outputFile.write(dump)
		outputFile.close()





