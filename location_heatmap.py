import datetime
import json
import os.path

import pandas as pd
import numpy as np

import folium
from folium import plugins
from branca.element import MacroElement
from jinja2 import Template


from flask import Flask, Response


app = Flask(__name__)
app.config.from_object(__name__)


class FloatMacro(MacroElement):
    """Adds a floating image in HTML canvas on top of the map."""
    _template = Template("""
            {% macro header(this,kwargs) %}
                <style>
                    #{{this.get_name()}} {
                        position:absolute;
                        left:{{this.left}}%;
                        top:{{this.left}}%;
                        }
                </style>
            {% endmacro %}

            {% macro html(this,kwargs) %}
            <img id="{{this.get_name()}}" alt="float_image"
                 src="{{ this.image }}"
                 width="{{ this.width }}"
                 style="z-index: 999999">
            </img>
            {% endmacro %}
            """)

    def __init__(self, image, top=75, left=75, width=75):
        super(FloatMacro, self).__init__()
        self._name = 'FloatImage'
        self.image = image
        self.top = top
        self.left = left
        self.width = width


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


def load(path='data/Location History.short.json'):
    with open(path, 'r') as fh:
        raw = json.loads(fh.read())

    # use location_data as an abbreviation for location data
    location_data = pd.DataFrame(raw['locations'])
    del raw  # free up some memory
    print('data loaded')
    return location_data


def prepare(df):
    df['latitudeE7'] = df['latitudeE7'] / float(1e7)
    df['longitudeE7'] = df['longitudeE7'] / float(1e7)
    df['timestampMs'] = df['timestampMs'] \
        .map(lambda x: float(x) / 1000)  # to seconds
    df['datetime'] = df.timestampMs \
        .map(datetime.datetime.fromtimestamp)

    df.rename(columns={
        'latitudeE7': 'latitude',
        'longitudeE7': 'longitude',
        'timestampMs': 'timestamp'
    }, inplace=True)
    # Ignore locations with accuracy estimates over 1000m
    df.reset_index(drop=True, inplace=True)
    print('data prepared')
    return df


def generate_map(latitude, longitude, zoom):
    location_data = load()

    location_data = location_data[location_data.accuracy < 1000]
    location_data = prepare(location_data)

    m = folium.Map([latitude, longitude], zoom_start=zoom)
    geo_matrix = location_data[['latitude', 'longitude']].values

    m.add_child(plugins.HeatMap(geo_matrix, radius=15))
    m.add_child(folium.LatLngPopup())
    fn = 'index.html'
    m.save(fn)
    content = get_file(fn)
    return Response(content, mimetype="text/html")


def generate_animation(epochs=10):
    location_data = load()

    location_data = location_data[location_data.accuracy < 1000]
    location_data = prepare(location_data)

    m = folium.Map([location_data.latitude.median(),
                    location_data.longitude.median()],
                   zoom_start=9)
    heat_df = np.array_split(location_data, epochs)
    # List comprehension to make out list of lists
    heat_data = [
        [[row['latitude'], row['longitude']] for index, row in _df.iterrows()]
        for _df in heat_df]

    plugins.HeatMapWithTime(heat_data, auto_play=True, max_opacity=0.8).add_to(m)
    m.add_child(folium.LatLngPopup())
    fn = 'index.html'
    m.save(fn)
    content = get_file(fn)
    return Response(content, mimetype="text/html")

