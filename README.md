# AMAPING

Build a map of AMAP members locations

# Installation

```
pip install -r requirements.txt
```

# Usage

```
usage: amaping.py [-h] [-v] [-c CSVFILENAME] [-s CSVSEPARATOR] [-o MAPFILENAME] [-m MAPSIZE] [-z ZOOMLEVEL]

Build a map of AMAP members locations

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         enable verbose logs
  -c CSVFILENAME, --csv CSVFILENAME
                        specify CSV data file
  -s CSVSEPARATOR, --separator CSVSEPARATOR
                        specify CSV column speparator
  -o MAPFILENAME, --output MAPFILENAME
                        specify a map filename
  -m MAPSIZE, --mapSize MAPSIZE
                        specify a size in pixel for map generation (Ex: 1920x1080)
  -z ZOOMLEVEL, --zoomLevel ZOOMLEVEL
                        specify a zoom level for map generation
```

Exemple
```
python amaping.py -o map.png -z 15 -m 2560x1440 -c exemple_data.csv
```