import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import folium
from io import BytesIO
import requests

apartments_url = "https://github.com/OmerS16/neighborhoods/blob/main/apartments_database.pkl?raw=true"
average_price_url = "https://github.com/OmerS16/neighborhoods/blob/main/average_price_database.pkl?raw=true"
apartments_file = BytesIO(requests.get(apartments_url).content)
average_price_file = BytesIO(requests.get(average_price_url).content)
apartments = pd.read_pickle(apartments_file)
average_price = pd.read_pickle(average_price_file)

st.title("Find the best neighborhood for your budget")
st.sidebar.header("Input your preferences")

min_price, max_price = st.sidebar.select_slider("Budget (in shekels):", options=[i for i in range(1000, 10000, 1000)], value=(5000, 6000))
num_rooms = st.sidebar.pills("number of rooms:", [i for i in range(1, 6)], selection_mode='multi', default=2)
walking_time = st.sidebar.number_input("Maximum walking distance from light rail stations (in minutes):", min_value=0, value=5, step=1)

filtered_average_price = average_price[(average_price['rooms'].isin(num_rooms)) & (average_price['price_mean'] >= min_price) & (average_price['price_mean'] <= max_price)]
filtered_average_price = filtered_average_price.sort_values('price_per_sq_m')
filtered_apartments = apartments[(apartments['rooms'].isin(num_rooms)) & (average_price['price'] >= min_price) & (average_price['price'] <= max_price) & (apartments['walking_time'] <= walking_time)]

if not filtered_average_price.empty:
    st.subheader("Best neighborhoods in Tel Aviv area for your budget")
    st.dataframe(filtered_average_price[['city', 'neighborhood', 'rooms', 'price_mean', 'sq_m_mean', 'price_per_sq_m']])
else:
    st.write("No neighborhoods match your criteria. Try adjusting your budget or number of rooms.")

map_center = [apartments['lat'].mean(), apartments['lon'].mean()]
m = folium.Map(location=map_center, zoom_start=12)

for _, row in filtered_apartments.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=5,
        color='orange',
        fill=True,
        fill_color='white',
        fill_opacity=0.8,
        popup=f"<a href='{row['url']}' target='_blank'>Click here for details</a>",
        tooltip=row.get('price')
        ).add_to(m)
    
st_folium(m, width=700, height=500)