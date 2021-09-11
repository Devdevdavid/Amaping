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

def error(msg):
	logger.info(msg)

def info(msg):
	logger.info(msg)

def debug(msg):
	logger.info(msg)

