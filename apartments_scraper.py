import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

neighborhoods = pd.read_pickle('neighborhoods_database.pkl')
dankal = pd.read_excel('dankal.xlsx')

def fetch_apartments_data(row):
    area_id = row['area_id']
    city_id = row['city_id']
    neighborhood_id = row['neighborhood_id']
    
    url = f"https://gw.yad2.co.il/realestate-feed/rent/map?property=1&topArea=2&area={area_id}&city={city_id}&neighborhood={neighborhood_id}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    df = df[df.index == 'markers']
    df = pd.json_normalize(df['data'].item())
    return df
    
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_apartments_data, row) for index, row in neighborhoods.iterrows()]

apartments = pd.DataFrame()

for future in as_completed(futures):
    result = future.result()
    if result is not None:
        apartments = pd.concat((apartments, result))
    
# # Cleaning up the df
apartments = apartments.drop(['orderId', 'tags', 'subcategoryId',
                  'priority', 'additionalDetails.property.text',
                  'priceBeforeTag', 'customer.agencyName','inProperty.isAssetExclusive'],axis=1, errors='ignore')

apartments = apartments.rename(columns={'address.city.text':'city',
                            'address.neighborhood.text':'neighborhood',
                            'address.street.text':'street',
                            'address.house.number':'house_num',
                            'address.house.floor':'floor',
                            'address.coords.lon':'lon',
                            'address.coords.lat':'lat',
                            'additionalDetails.roomsCount':'rooms',
                            'additionalDetails.squareMeter':'sq_m',
                            'metaData.coverImage':'image',})

apartments['url'] = "https://www.yad2.co.il/realestate/item/" + apartments['token']

# # Analyzing data
average_price = apartments.groupby(['city', 'neighborhood', 'rooms'])[['price', 'sq_m']].agg(['mean', 'count'])
average_price.columns = ['_'.join(col).strip() for col in average_price.columns]
average_price = average_price.reset_index()
average_price = average_price.drop(['level_0_', 'index_', 'sq_m_count'], axis=1, errors='ignore')
average_price = average_price.rename(columns={'price_count':'count', 'rooms_':'rooms', 'neighborhood_':'neighborhood', 'city_':'city'})
average_price = average_price[['city', 'neighborhood', 'rooms', 'price_mean', 'sq_m_mean', 'count']]
average_price['price_per_sq_m'] = average_price['price_mean'] / average_price['sq_m_mean']
average_price[['price_mean', 'sq_m_mean', 'price_per_sq_m']] = average_price[['price_mean', 'sq_m_mean', 'price_per_sq_m']].astype(int)

def get_walking_distance_osrm(origin, destination):
    url = (
        f"http://router.project-osrm.org/route/v1/foot/"
        f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}?overview=false"
    )
    response = requests.get(url)
    data = response.json()

    if 'routes' in data and data['routes']:
        distance = data['routes'][0]['distance']
        return distance
    return None

closest_stations = []

for _, apt in apartments.iterrows():
    min_distance = float('inf')
    closest_stop = None

    for _, station in dankal.iterrows():
        origin = (apt['lat'], apt['lon'])
        destination = (station['lat'], station['lon'])
        
        # Get the walking distance from OSRM
        distance = get_walking_distance_osrm(origin, destination)
        if distance is not None and distance < min_distance:
            min_distance = distance
            closest_station = {
                'apartment': apt['token'],
                'station': station['station'],
                'distance_m': min_distance
            }

    if closest_station:
        closest_stations.append(closest_station)

closest_stations_df = pd.DataFrame(closest_stations)
apartments = apartments.merge(closest_stations_df, left_on='token', right_on='apartment', how='left')

# apartments.to_pickle('apartments_database.pkl')
# average_price.to_pickle('average_price_database.pkl')