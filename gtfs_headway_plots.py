#********************************************************************************************
# This tool is used to calculate headway and print transit routs
# Ann Arbor Area Transit GTFS data is at https://www.theride.org/business/software-developers
# Author: cliu / SEMCOG
#********************************************************************************************

import os
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString
import matplotlib.pyplot as plt
from gtfs_functions import Feed
import matplotlib.backends.backend_pdf as pdf_backend
from shapely.geometry import LineString
_join = os.path.join

gtfs_location = r'P:\Modeling and Mobility\Data_Requests\TransitDataRequested_bySEMCOG'
print (gtfs_location)
sub_path = r'AAATA\GTFSExportJan2023 Elyse Osterday'
routes_df = pd.read_csv(_join(gtfs_location, sub_path, 'routes.txt'))
stops_df = pd.read_csv(_join(gtfs_location, sub_path,'stops.txt'))
stop_times_df = pd.read_csv(_join(gtfs_location, sub_path,'stop_times.txt'))
trips_df = pd.read_csv(_join(gtfs_location, sub_path,'trips.txt'))

def headway(service = 2):
    '''
    Calculate route frequency
    
    '''
    print ('Calculating headway by time period...')

    merged_df = stop_times_df.merge(trips_df, on='trip_id')
    merged_df = merged_df.merge(stops_df, on='stop_id')
    merged_df = merged_df[merged_df['service_id'] == service] 

    # Only keep same stop_id with earlist arrival time   
    merged_df['arrival_time'] = pd.to_timedelta(merged_df['arrival_time'])
    earliest_indices = merged_df.groupby('shape_id')['arrival_time'].idxmin()
    earliest_rows = merged_df.loc[earliest_indices]  
    merged_df = pd.merge(merged_df, earliest_rows[['stop_id', 'shape_id']], on=['stop_id', 'shape_id'], suffixes=('_filtered', '_earliest'))

    # Function to convert time to timedelta, handling values greater than 24 hours
    def convert_to_timedelta(time_str):
        # Split the time string into hours, minutes, and seconds
        parts = time_str.split(':')
        hours, minutes, seconds = map(int, parts)
        
        # Calculate the total seconds for the time
        total_seconds = hours * 3600 + minutes * 60 + seconds
        
        # Create a timedelta object
        return pd.to_timedelta(total_seconds, unit='s')

    df = df2 =headway_df = pd.DataFrame()
    
    # Convert 'departure_time' to timedelta
    merged_df['departure_time'] = merged_df['departure_time'].apply(convert_to_timedelta) # Temperarily comment for LED!!!

    # EV1, NT1 represents the end of day service; while EV2, NT2 represents the beginning of day service
    time_dic = {'AM':['06:30:00', '08:59:59'],'MD':['09:00:00', '14:29:59'],'PM':['14:30:00', '18:29:59'],\
                    'EV1':['18:30:00', '26:59:59'], 'EV2':['0:00:00', '2:59:59'], 'NT1':['27:00:00', '30:29:59'], 'NT2':['3:00:00', '06:29:59']}
    
    # Assign time of day (TOD) to trips.
    for time in ['AM', 'MD', 'PM', 'EV1', 'EV2', 'NT1', 'NT2']:    
        
        # Define user-defined time period
        start_time = convert_to_timedelta(time_dic[time][0])
        end_time = convert_to_timedelta(time_dic[time][1])

        # Filter data within the time period
        filtered_df = merged_df[(merged_df['departure_time'] >= start_time) & (merged_df['departure_time'] <= end_time)]      

        # Sort the DataFrame by stop, and route
        filtered_df.sort_values(['stop_id', 'shape_id', 'direction_id', 'departure_time'], inplace=True)    
        
        most_common_stops = filtered_df.groupby(['shape_id', 'direction_id'])['stop_id'].agg(lambda x: x.value_counts().idxmax())
        filtered_df = filtered_df[filtered_df['stop_id'].isin(most_common_stops)]
        filtered_df['TOD'] = time[:2] # [:2] - assign EV1 and EV2 as EV, etc.
        df = df.append(filtered_df, ignore_index=True)
    
    # Calcuate headway
    for time, min in [['AM', 150], ['MD',300], ['PM', 240], ['EV',510], ['NT', 210]]:

        filtered_df2 = df[df['TOD'] == time]
        # Subtract one day for values greater than '1 days 03:00:00'
        threshold = pd.to_timedelta('1 days 03:00:00')
        filtered_df2.loc[df['departure_time'] > threshold, 'departure_time'] -= pd.to_timedelta('1 days')
        
        # Count number of buses    
        filtered_df2['buses'] = filtered_df2.groupby(['shape_id', 'direction_id', 'stop_id'])['shape_id'].transform('count')
        
        filtered_df2 = filtered_df2[['arrival_time','departure_time','stop_id','stop_sequence','timepoint',\
                                   'shape_id','trip_headsign','direction_id','stop_code','stop_name','buses']]   
            
        df2 = df2.append(filtered_df2, ignore_index=True)
        # Consolidate headways for each route/direction by time period
        grouped = filtered_df2.groupby(['shape_id', 'trip_headsign', 'direction_id', 'stop_id'])
        
        if not filtered_df2.empty:
            result_df = grouped.apply(lambda x:  int(min / len(x) + 0.5) if len(x) > 0 else 999).reset_index()
            result_df.columns = ['shape_id', 'trip_headsign', 'direction_id', 'stop_id', time]

            result_df = result_df.sort_values(by=[time], ascending=[False])
            result_df = result_df.drop_duplicates(subset=['shape_id', 'trip_headsign', 'direction_id'], keep='first')

            if time == 'AM':
                headway_df = headway_df.append(result_df[['shape_id', 'trip_headsign', 'direction_id', time]], ignore_index=True)
            else:
                headway_df = headway_df.merge(result_df[['shape_id', 'trip_headsign', 'direction_id', time]], \
                                            on = ['shape_id', 'trip_headsign', 'direction_id'], how = 'outer')
            # replace 0 with 999    
            headway_df[time]=headway_df[time].replace(0, 999) 


    headway_df.fillna(999, inplace=True) 
    
    # Drop records with headway 999 for all time period. Note: for weekends and holidays, some time period, e.g. NT, might not have service.
    time_columns = ['AM', 'MD', 'PM', 'EV', 'NT']
    existing_columns = [col for col in time_columns if col in headway_df.columns]
    if existing_columns:
        sum_columns = headway_df[existing_columns].sum(axis=1)
        threshold_value = len(existing_columns) * 999
        headway_df = headway_df.drop(headway_df[sum_columns == threshold_value].index)

    # Export headway result
    df2.to_csv( 'time_diff.csv', index=False)
    headway_df.to_csv('headway.csv', index=False)
    return headway_df

def plot_routes(headway_df, service = 2):
    print ('Reading in background map...')
    map_location = r'C:\Users\cliu\Work\Python Practice'
    street_map = gpd.read_file(_join(map_location, 'Shape File', 'All_Street.shp')) #Read in backgrourd map
    
    # Plot route itineraries with background street map
    print ('Plotting transit routes...')
    shapes_df = pd.read_csv(_join(gtfs_location, sub_path, 'shapes.txt'))
    shapes_df = trips_df.merge(shapes_df, on='shape_id', how='left')
    shapes_df = shapes_df[shapes_df['service_id'] == service]
    shapes_df = shapes_df.drop_duplicates(subset=['shape_id', 'shape_pt_sequence']) # removal candidate

    shapes_df['route_id'] = shapes_df['route_id'].astype(int) # placeholder, can be plotted.
    time_columns = ['shape_id', 'AM', 'MD', 'PM', 'EV', 'NT']
    existing_columns = [col for col in time_columns if col in headway_df.columns]

    if existing_columns:
        shapes_df = shapes_df.merge(headway_df[existing_columns], on='shape_id', how='left')
        existing_columns.remove('shape_id')
        shapes_df['freq'] = shapes_df[existing_columns].astype(str).apply(','.join, axis=1)
    
    # Create a PDF file to store the plots WITHOUT stops
    unique_routes = np.sort(shapes_df['shape_id'].unique())
    pdf_pages = pdf_backend.PdfPages(_join(map_location, 'output', 'plots_with_allstreet.pdf'))

    # Iterate over routes and plot their itineraries
    for route in unique_routes:
        # Filter route data
        route_data_df = shapes_df[shapes_df['shape_id'] == route]
        shape_id = route_data_df['shape_id'].iloc[0]
        route_name = route_data_df['trip_headsign'].iloc[0]
        route_freq = route_data_df['freq'].iloc[0].split(',')
        modified_values = [value.replace('.0', '') for value in route_freq]
        route_freq = ','.join(modified_values)       
        
        # Create a LineString geometry from route data
        route_geometry = LineString(zip(route_data_df['shape_pt_lon'], route_data_df['shape_pt_lat']))
        
        # Calculate bounding box (extent) of the route's geometry
        route_bbox = route_geometry.bounds
        
        # Crop the street map to the bounding box of the route
        cropped_map = street_map.cx[route_bbox[0]:route_bbox[2], route_bbox[1]:route_bbox[3]]
        
        # Plot the route line
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(route_data_df['shape_pt_lon'], route_data_df['shape_pt_lat'], color='blue')

        # Label the first segment with 'A' and the last segment with 'B'
        for i in range(len(route_data_df['shape_pt_lon'])):
            if i == 0:
                label = 'A'
                color = 'red'
                ax.text(route_data_df['shape_pt_lon'].iloc[i], route_data_df['shape_pt_lat'].iloc[i], label, fontsize=12, color=color, fontweight='bold')
            elif i == len(route_data_df['shape_pt_lon']) - 1:
                label = 'B'
                color = 'green'
                ax.text(route_data_df['shape_pt_lon'].iloc[i], route_data_df['shape_pt_lat'].iloc[i], label, fontsize=12, color=color, fontweight='bold')
            else:
                continue

        # Plot the cropped street map on top of the route line
        cropped_map.plot(ax=ax, color='lightgrey', linewidth=0.3)    
        
        ax.set_title(f'Route Itinerary: {shape_id, route_name, route_freq}')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.grid(False)
        
        # Save the plot as a PDF page
        pdf_pages.savefig()
        plt.show()
        plt.close()
    pdf_pages.close()                                                         
                                                         
if __name__ == '__main__':
    service = 1 # transit agency defined service date. Common practice: 1-Sunday, 2-weeday, 3-Saturday
    headway_df = headway(service) 
    plot_routes(headway_df, service)
