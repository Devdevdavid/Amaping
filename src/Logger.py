#!/usr/bin/python
# Author  : David DEVANT
# Desc    : Logging messages
# File    : Logger.py
# Date    : Sept. 11th, 2021

import logging                                  # Use for log message in console

# Globale Variables
logger = None

def init(name):
	global logger

	# Logging
	logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)
	logger = logging.getLogger(name)

def setLevelDebug():
	logger.setLevel(logging.DEBUG)

def error(msg):
	logger.error(msg)

def warning(msg):
	logger.warning(msg)

def info(msg):
	logger.info(msg)

def debug(msg):
	logger.debug(msg)

