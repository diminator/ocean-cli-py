import datetime
import json
import os.path

import pandas as pd
import geopandas as gpd
import folium
from folium import plugins
from shapely.geometry import Point


from flask import Flask, Response


app = Flask(__name__)
app.config.from_object(__name__)


def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))


def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join(root_dir(), filename)
        # Figure out how flask returns static files
        # Tried:
        # - render_template
        # - send_file
        # This should not be so non-obvious
        return open(src).read()
    except IOError as exc:
        return str(exc)


def generate_map(latitude, longitude, zoom):
    with open('data/Location History.short.json', 'r') as fh:
        raw = json.loads(fh.read())

    # use location_data as an abbreviation for location data
    location_data = pd.DataFrame(raw['locations'])
    del raw  # free up some memory

    print('data loaded')
    location_data = location_data[location_data.accuracy < 1000]

    location_data['latitudeE7'] = location_data['latitudeE7']/float(1e7)
    location_data['longitudeE7'] = location_data['longitudeE7']/float(1e7)
    location_data['timestampMs'] = location_data['timestampMs']\
        .map(lambda x: float(x)/1000)  # to seconds
    location_data['datetime'] = location_data.timestampMs\
        .map(datetime.datetime.fromtimestamp)

    location_data.rename(columns={
        'latitudeE7': 'latitude',
        'longitudeE7': 'longitude',
        'timestampMs': 'timestamp'
    }, inplace=True)
    # Ignore locations with accuracy estimates over 1000m
    location_data.reset_index(drop=True, inplace=True)
    print('data parsed')
    geometry = [Point(xy) for xy in
                zip(location_data['longitude'], location_data['latitude'])]

    crs = {'init': 'epsg:4326'}
    geo_df = gpd.GeoDataFrame(location_data, crs=crs, geometry=geometry)

    m = folium.Map([latitude, longitude], zoom_start=zoom)

    geo_matrix = geo_df[['latitude', 'longitude']].as_matrix()

    m.add_child(plugins.HeatMap(geo_matrix, radius=15))
    m.add_child(folium.LatLngPopup())

    print('map generated')
    fn = 'index.html'
    m.save(fn)
    content = get_file(fn)
    return Response(content, mimetype="text/html")
    # return send_file('inddex', mimetype='image/png')
