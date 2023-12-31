import json
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import requests
#import folium
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from urllib.request import urlopen
#from googletrans import Translator, constants
from pprint import pprint
import streamlit_analytics
import sys

################################################### input variables #####################################################################
#coorindates [x,y] indicates the targeted destination
st.title("Parking options in Zurich")

st.write("This page shows the public parking spots in the city of zurich, including both on-street parking and parking houses. With input of the final desination and the acceptable walking distance to the destination, the parking options are displayed in an interactive map.")
st.write("Try it with your favorite bar or shop!!! Steps:")
"""
* 1 Provide your destination address
* 2 Provide acceptable walking radius
* 3 Click "clicke me" to update the input
* 4 Interactive map provides information below:
    * Hover over single parking spots to see, e.g, zone type, parking duration allowed. 
    * Hover over map layer to see, e.g, tarif level, area, open hours. 
    * Zoom in and out to see the neighborhood and parking houses nearby.    
"""



st.header("Input needed")

def get_geocode_from_address(address):
    endpoint = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    response = requests.get(endpoint, params=params)
    if response.status_code == 200 and response.json():
        location = response.json()[0]
        return float(location['lat']), float(location['lon'])
    return None


new_address = st.text_input("Where are you going? Enter your destination:",value="St. Peterhofstatt 1, 8001 Zürich")
#address = "Heinrichstrasse 200, 8005 Zurich"  # Example address
coordinates = get_geocode_from_address("St. Peterhofstatt 1, 8001 Zürich")

radius = st.number_input("How far are you willing to park (in meters)?",value=300)

# page view counts ##
# https://pypi.org/project/streamlit-analytics/


with streamlit_analytics.track():
    if st.button("CLICK ME to update input !!!!!!",key=1):
        coordinates = get_geocode_from_address(new_address)

# get coordinates from the given address ## 
if coordinates:
    #st.write(f"Latitude: {coordinates[0]}, Longitude: {coordinates[1]}")
    user_input_lat =coordinates[0]
    user_input_lon =coordinates[1]
else:
    st.write("Try another address! Format: 'Heinrichstrasse 200, 8005 Zurich'")
    sys.exit()

###################################################obtain geo of on-street parking - Antonio + Tim code#####################################################################

############################## SCORING: Tim traffic score ############################
geo_url = 'https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Oeffentlich_zugaengliche_Strassenparkplaetze_OGD?service=WFS&version=1.1.0&request=GetFeature&outputFormat=GeoJSON&typename=view_pp_ogd'

with urlopen(geo_url) as response:
    df_park = json.load(response)
to_trans = {'Blaue Zone': 'Blue Zone',
            'Weiss markiert': 'White Zone',
            'Nur mit Geh-Behindertenausweis': 'Disabled',
            'Nur für Taxi': 'Only Taxi',
            'Für Reisecars': 'Only Coaches',
            'Für Elektrofahrzeuge': 'Only Electric vehicles',
            'Zeitweise Taxi, zeitweise Güterumschlag': 'Temporary'}

df_park = pd.json_normalize(df_park['features'])

rename_dict = { 'properties.id1' : 'property_id', 
                'properties.parkdauer' : 'parking_duration', 
                'properties.art' : 'parking_kind',
                'properties.gebuehrenpflichtig': 'payed', 
                'properties.objectid' : 'object_id',
                'geometry.coordinates': 'coord'}

df_park = df_park.rename(columns=rename_dict)

df_park[['lon', 'lat']] = pd.DataFrame(df_park.coord.to_list())
df_park = df_park.drop(['type', 'geometry.type', 'coord', 'id', 'object_id'], axis=1)
df_park.loc[df_park['payed'] == 'nicht gebührenpflichtig', 'payed'] = 0
df_park.loc[df_park['payed'] == 'gebührenpflichtig', 'payed'] = 1
for key in to_trans:
    df_park.loc[df_park['parking_kind'] == key, 'parking_kind'] = to_trans[key]

# to_trans = {'Blaue Zone': 'Blue Zone',
#             'Weiss markiert': 'White Zone',
#             'Nur mit Geh-Behindertenausweis': 'Disabled',
#             'Nur für Taxi': 'Only Taxi',
#             'Für Reisecars': 'Only Coaches',
#             'Für Elektrofahrzeuge': 'Only Electric vehicles',
#             'Zeitweise Taxi, zeitweise Güterumschlag': 'Temporary'}

# rename_dict = { 'properties.id1' : 'property_id', 
#                 'properties.parkdauer' : 'parking_duration', 
#                 'properties.art' : 'parking_kind',
#                 'properties.gebuehrenpflichtig': 'payed', 
#                 'properties.objectid' : 'object_id',
#                 'geometry.coordinates': 'coord'}

# df_park = df_park.rename(columns=rename_dict)

# df_park = df_park.drop(['type', 'geometry.type', 'coord', 'id', 'object_id'], axis=1)
# df_park.loc[df_park['payed'] == 'nicht gebührenpflichtig', 'payed'] = 0
# df_park.loc[df_park['payed'] == 'gebührenpflichtig', 'payed'] = 1
# for key in to_trans:
#     df_park.loc[df_park['parking_kind'] == key, 'parking_kind'] = to_trans[key]

############################## NEW  ############################
# ############################## Filter parking spots inside Radius ############################
############################## Filter parking spots inside Radius ############################
# ############################## Filter parking spots inside Radius ############################
# ############################## Filter parking spots inside Radius ############################

lat_dis_zh=77.8 #one degree of lat is about 78 km at Zurich
lon_dis_zh=39.305 
def cal_d(row):
    return (np.sqrt(((row['lat']-user_input_lat)*lat_dis_zh)**2+((row['lon']-user_input_lon)*lon_dis_zh)**2))*1000

df_park['dis_to_des']=df_park.apply(cal_d,axis=1)

def label_in_radius(row):
    if row['dis_to_des']<radius:
        return 1
    else:
        return 0

df_park['in_radius']=df_park.apply(label_in_radius,axis=1)

#############################################obtain geo of parking houses - Timothycode##############################################################
geo_url2 = "https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Oeffentlich_zugaengliche_Parkhaeuser?service=WFS&version=1.1.0&request=GetFeature&outputFormat=GeoJSON&typename=poi_parkhaus_view"

with urlopen(geo_url2) as response:
    geo_data_house = json.load(response)

df = pd.json_normalize(geo_data_house, "features")

df["lon"] = df["geometry.coordinates"].apply(lambda row: row[0])
df["lat"] = df["geometry.coordinates"].apply(lambda row: row[1])

parkinghouse_trace=go.Scattermapbox(
    lat = df["lat"],
    lon = df["lon"],
    mode = "markers",
    marker=dict(size=20),
    name='Park houses'
    )

#######################################obtain tarifzones Jin code####################################################################################
url = "https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Gebietseinteilung_Parkierungsgebuehren?service=WFS&version=1.1.0&request=GetFeature&outputFormat=GeoJSON&typename=tarifzonen"
response=requests.get(url)
tarif=response.json()

data = pd.DataFrame({
    'region_id': ['1', '2', '3','4'],
    'region':['Zürich-West','Innenstadt und Oerlikon','Innenstadt und Oerlikon','suburban district'],
    'value': ['high tarif', 'high tarif', 'high tarif','low tarif'],
    'bedienungszeiten': ['Montag - Mittwoch, 9:00 - 20:00 Uhr, Donnerstag - Sonntag, 9:00 - 9:00 Uhr','Montag - Samstag, 9:00 - 20:00 Uhr','Montag - Samstag, 9:00 - 20:00 Uhr',
                        'Montag - Samstag, 9:00 - 20:00 Uhr']
})


    

#########################################section 3: Plotting ################################################################
#########################################section 3: Plotting ################################################################
##########################################section 3: Plotting ################################################################

# st.header("")
st.header("Interactive map for nearby parking options")

# trace 1: plot base map with choropleth#
tarifzones = px.choropleth_mapbox(
    data,
    geojson=tarif,  # GeoJSON with region boundaries and properties
    locations="region_id",  # Identifier in your data
    featureidkey="properties.objectid",  # Identifier in GeoJSON matching your data
        color="value",  # Data values for coloring the regions
    color_continuous_scale="turbo",  # Choose a color scale
    mapbox_style="open-street-map",
    center={"lat": user_input_lat, "lon": user_input_lon},
    zoom=16,
    height=600,
    width=800,
    opacity=0.4,
    hover_data=['region', 'value','bedienungszeiten']
)
tarifzones.update_coloraxes(showscale=False)
tarifzones.update_layout(margin_l=0,margin_t=0,margin_b=0)

#  trace 2: plot added trace of on-street parking#
parking_colors={
    "Blue Zone": "blue",
    "White Zone": "white",
    "Disabled": "pink",
    "Only Taxi": "yellow",
    "Only Coaches":"yellow",
    "Only Electric vehicles":"yellow",
    "Temporary":"yellow"}

parking_markers=[parking_colors[i] for i in df_park["parking_kind"]]

# map_fig_onstreet = go.Scattermapbox(   
#     lat=df_park['lat'], 
#     lon=df_park['lon'], 
#     text=df_park.apply(lambda row: f"{row['parking_kind']} - {row['parking_duration']} minutes allowed", axis=1),
#     mode='markers',
#     name="On-street parking",
#     marker=dict(
#         size=10,
#         #symbol='square',-> this just does not work.
#         color=parking_markers))

#TRY: ONLY DISPLAY THE SPOTS IN SIDE THE RADIUS
map_fig_onstreet = go.Scattermapbox(   
    lat=df_park[df_park['in_radius']==1]['lat'], 
    lon=df_park[df_park['in_radius']==1]['lon'], 
    text=df_park.apply(lambda row: f"{row['parking_kind']} - {row['parking_duration']} minutes allowed", axis=1),
    mode='markers',
    name="On-street parking",
    marker=dict(
        size=10,
        #symbol='square',-> this just does not work.
        color=parking_markers))

tarifzones.add_trace(map_fig_onstreet)

# trace 3: added trace of destination on the map#
destination_trace = go.Scattermapbox(
    lat=[user_input_lat], 
    lon=[user_input_lon], 
    mode='markers', 
    name='Destination',
    marker=dict(size=40),
    hovertemplate="Travel destination"+"<extra></extra>"
    )
tarifzones.add_trace(destination_trace)


# trace 4: added trace parking houses #
if st.checkbox('Include parking houses',value=True):
    tarifzones.add_trace(parkinghouse_trace)

# display the graph with all traces#
st.plotly_chart(tarifzones)

####################################### display data of parking spots in radius ####################################################################################
if st.checkbox('Show the list of nearby parking spots'):
    st.dataframe(df_park[df_park['in_radius']==1])


################################### section 3: display data #######################################################
################################### section 3: display data #######################################################
################################### section 3: display data #######################################################
st.header("Raw data")
st.write('Copyright: all data from City of Zurich (DAV).')

if st.checkbox('Show on-street parking data below'):
    sentence=f"On-street data sheet contains {df_park.shape[0]} rows and {df_park.shape[1]} columns data."
    st.write(sentence)
    df_park
    

if st.checkbox('Show parking house data below'):
    sentence=f"On-street data sheet contains {df.shape[0]} rows and {df.shape[1]} columns data."
    st.write(sentence)
    df

if st.checkbox('Show parking tarif zones data below'):
    sentence=f"On-street data sheet contains {data.shape[0]} rows and {data.shape[1]} columns data."
    st.write(sentence)
    data

# from streamlit_discourse import st_discourse # https://where2park-zurich.streamlit.app/
# discourse_url = "http://localhost:8501/"
# topic_id = 8501
# st_discourse(discourse_url, topic_id)


# ################################### add destination circle############################################
# circle_center = (user_input_lat, user_input_lon)
# circle_radius = user_input_r
# m = folium.Map(location=circle_center, zoom_start=12)

# folium.Circle(
#     location=circle_center,
#     radius=circle_radius,
#     color='blue',  # Circle border color
#     fill=True,
#     fill_color='blue',  # Circle fill color
#     fill_opacity=0.3,  # Opacity of the circle fill
#     popup='My Circle'  # Popup text when clicking on the circle
# ).add_to(m)

st.header("Related")
st.write('To see page view analytics, append "?analytics=on" to URL')
st.write('Contact: jin.cao1988@gmail.com')

