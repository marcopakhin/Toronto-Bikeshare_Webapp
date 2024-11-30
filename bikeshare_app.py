import streamlit as st
import folium
from streamlit_folium import folium_static
from helpers import *

# getting data from the Toronto Open Data
station_url = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_status.json"
latlon_url = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information"

# data cleansing
df_station_status = query_station_status(station_url)
df_station_latlon = get_station_latlon(latlon_url)
data = join_latlon(df_station_status, df_station_latlon)


st.title("Toronto Bike Share Station Status")
st.markdown("This dashboard tracks bike availibility at each bike share station in Toronto")

# KPI metrics section
col1, col2, col3 = st.columns(3)

with col1:
    total_bike_available = sum(data["num_bikes_available"])
    st.metric(label="Bikes Available Now",
            value = total_bike_available)

    total_e_bike_available = sum(data["ebike"])
    st.metric(label="E-Bikes Available Now",
            value=total_e_bike_available)

with col2:
    total_station_w_av_bike = (data["num_bikes_available"] > 0).sum()
    st.metric(label="Stations w Available Bikes",
            value=total_station_w_av_bike)

    total_station_w_av_e_bike = (data["ebike"] > 0).sum()
    st.metric(label="Stations w Available E-Bikes",
            value=total_station_w_av_e_bike)

with col3:
    total_station_w_empty_docks = (data["num_docks_available"] > 0).sum()
    st.metric(label="Stations w Empty Docks",
            value=total_station_w_empty_docks)
    
# intial variables
current_location_rent = 0
current_location_return = 0
findbike = False
finddock = False
input_bike_mode = []

# side bar user input
with st.sidebar:
    # rent/return
    options = ["Rent", "Return"]
    order_selection = st.segmented_control(
        "Directions", options, selection_mode="single", default=options[0]
    )

    # renting a bike
    if order_selection == "Rent":
        bike_options = ["mechanical", "ebike"]
        input_bike_mode = st.segmented_control(
            "Direction", bike_options, selection_mode="multi"
        )

        # location information
        st.header("Where are you located?")

        input_address = st.text_input("Address", "")
        st.markdown("Example: 1 Yonge Street")
        input_city = st.text_input("City", "Toronto")
        input_country = st.text_input("Country", "Canada")

        input_driving = st.checkbox("I'm driving there.") # return true/false

        # go time
        findbike = st.button("Find me a bike!", type = "primary")
        if findbike:
            if input_address != "":
                current_location_rent = geocode(input_address+ " " + input_city + " " + input_country)
                if current_location_rent == "":
                    st.subheader(":red[Input address not valid!]")
            else:
                st.subheader(":red[Input address not valid!]")

    # returning a bikt
    elif order_selection == "Return":
        # location information
        st.header("Where are you located?")

        input_address = st.text_input("Address", "")
        st.markdown("Example: 1 Yonge Street")
        input_city = st.text_input("City", "Toronto")
        input_country = st.text_input("Country", "Canada")

        # go time
        finddock = st.button("Find me a dock!", type = "primary")
        if finddock:
            if input_address != "":
                current_location_return = geocode(input_address+ " " + input_city + " " + input_country)
                if current_location_return == "":
                    st.subheader(":red[Input address not valid!]")
            else:
                st.subheader(":red[Input address not valid!]")

# initial map
if findbike == False and finddock == False:
    toronto_center = [43.653908, -79.384293]
    map = folium.Map(location=toronto_center,
                    zoom_start=13,
                    tiles="cartodbpositron")

    # adding circle marks for each station
    for _, row in data.iterrows():
        marker_color = get_marker_color(row["num_bikes_available"])
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=3.5,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,
            popup=folium.Popup(f"Station ID: {row["station_id"]}<br>"
                            f"Total Bikes Available: {row["num_bikes_available"]}<br>"
                            f"Mechanical Bike Available: {row["mechanical"]}<br>"
                            f"eBike Available: {row["ebike"]}",
                            max_width=300)
        ).add_to(map)

    # display the map
    folium_static(map)

# finding the closest bike

if findbike:
    if input_address != "":
        current_location_rent = geocode(input_address+ " " + input_city + " " + input_country)
        if current_location_rent != "":
            chosen_station = get_bike_availability(current_location_rent, data, input_bike_mode)
            center = current_location_rent
            map1 = folium.Map(location=center, zoom_start=18, tiles="cartodbpositron")

            for _, row in data.iterrows():
                marker_color = get_marker_color(row["num_bikes_available"])
                # overall marker for each station
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=5,
                    color=marker_color,
                    fill=True,
                    fill_color=marker_color,
                    fill_opacity=0.7,
                    popup=folium.Popup(f"Station ID: {row["station_id"]}<br>"
                                        f"Total Bikes Available: {row["num_bikes_available"]}<br>"
                                        f"Mechanical Bike Available: {row["mechanical"]}<br>"
                                        f"eBike Available: {row["ebike"]}",
                                        max_width=300)
                ).add_to(map1)

            # marker for current location
            folium.Marker(
                location=current_location_rent,
                popup="Your current location.",
                icon=folium.Icon(color="blue", icon="person", prefix="fa")
            ).add_to(map1)

            # closest bike station
            folium.Marker(
                location=(chosen_station[1], chosen_station[2]),
                popup="Start Your Ride Today! Rent Your Bike Here!",
                icon=folium.Icon(color="red", icon="bicycle", prefix="fa")
            ).add_to(map1)

            # route: current location --> recommended bike station
            coordinates, duration = run_osrm(chosen_station, current_location_rent)
            folium.PolyLine(
                locations=coordinates,
                color="blue",
                weight=5,
                tooltip="Your ride will be here in just {} minutes!".format(duration)
            ).add_to(map1)

            folium_static(map1)

            with col3:
                st.metric(label=":green[Travel Time (min)]",
                          value=duration)

# finding the closest dock
if finddock:
    if input_address != "":
        current_location_return = geocode(input_address+ " " + input_city + " " + input_country)
        if current_location_return != "":
            chosen_station = get_dock_availability(current_location_return, data)
            center = current_location_return
            map1 = folium.Map(location=center, zoom_start=18, tiles="cartodbpositron")

            for _, row in data.iterrows():
                marker_color = get_marker_color(row["num_bikes_available"])
                # overall marker for each station
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=5,
                    color=marker_color,
                    fill=True,
                    fill_color=marker_color,
                    fill_opacity=0.7,
                    popup=folium.Popup(f"Station ID: {row["station_id"]}<br>"
                                        f"Total Bikes Available: {row["num_bikes_available"]}<br>"
                                        f"Mechanical Bike Available: {row["mechanical"]}<br>"
                                        f"eBike Available: {row["ebike"]}",
                                        max_width=300)
                ).add_to(map1)

            # marker for current location
            folium.Marker(
                location=current_location_return,
                popup="Your current location.",
                icon=folium.Icon(color="blue", icon="person", prefix="fa")
            ).add_to(map1)

            # marker for bike station
            folium.Marker(
                location=(chosen_station[1], chosen_station[2]),
                popup="Return your bike to this location.",
                icon=folium.Icon(color="red", icon="bicycle", prefix="fa")
            ).add_to(map1)

            # route
            coordinates, duration = run_osrm(chosen_station, current_location_return)
            folium.PolyLine(
                locations=coordinates,
                color="blue",
                weight=5,
                tooltip="Your ride will be here in just {} minutes!".format(duration)
            ).add_to(map1)

            folium_static(map1)

            with col3:
                st.metric(label=":red[Travel Time (min)]",
                          value=duration)