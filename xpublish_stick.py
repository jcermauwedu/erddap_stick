# -*- coding: utf-8 -*-
"""
Original file is located at
    https://colab.research.google.com/drive/1y44tXYsR1C7fYgaZUKAH3B6tetlBsR7w
"""

import yaml
#from erddapy import ERDDAP
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import date2num
from datetime import datetime
import xarray as xr

def fetch_and_plot(config):
    server_url = config['server_url']
    dataset_id = config['dataset_id']
    start_date = config['start_date']
    end_date = config['end_date']
    depth_range = tuple(config['depth_range'])
    height_per_plot = config['height_per_plot']
    color_pallete = config['color_pallete']
    arrow_head = config['arrow_head']
    output_filename = config['output_filename']
    instrument = config['instrument']
    suffix = f"{instrument}"

    '''
    e = ERDDAP(server=server_url, protocol="tabledap")
    e.response = "nc"
    e.dataset_id = dataset_id
    e.constraints = {
        "time>=": start_date,
        "time<=": end_date,
    }
    e.variables = [
        f"time",
        f"latitude",
        f"longitude",
        f"depth",
        f"ocean_currents_instrument_{suffix}",
        f"sea_water_speed_{suffix}",
        f"sea_water_direction_{suffix}",
        f"upward_sea_water_velocity_{suffix}",
    ]
    '''
    import zarr
    from fsspec.implementations.http import HTTPFileSystem

    fs = HTTPFileSystem()

    # The URL 'http://0.0.0.0:9000/zarr/' here serves one dataset
    http_map = fs.get_mapper("http://0.0.0.0:9000/zarr/")

    # open as a zarr group
    zg = zarr.open_consolidated(http_map, mode="r")

    # or open as another Xarray Dataset
    ds = xr.open_zarr(http_map, consolidated=True)

    # ERDDAP maps lat to latitude
    # ERDDAP maps lon to longitude
    extract_variables = [
        f"time",
        f"lat",
        f"lon",
        f"depth",
        f"ocean_currents_instrument_{suffix}",
        f"sea_water_speed_{suffix}",
        f"sea_water_direction_{suffix}",
        f"upward_sea_water_velocity_{suffix}",
    ]

    # Subset dataset by time
    # The Z ending is not iso compliant; drop the Z
    # https://github.com/pydata/xarray/issues/4337
    ds = ds.sel(time=slice(start_date[0:-1],end_date[0:-1]))

    # Subset variables
    dss = xr.Dataset()
    for evar in extract_variables:
        if evar in ds.variables:
            dss[evar] = ds[evar]

    # Convert to pandas
    df = dss.to_dataframe(dim_order=['time','depth'])

    # Remove time as an index
    df = df.reset_index()

    # Rename the columns so it matches the rest of the code below
    df = df.rename(columns={
        "time": "time (UTC)",
        "lat": "latitude (degrees_north)",
        "lon": "longitude (degrees_east)",
        "depth": "depth (m)",
        "sea_water_speed_1": "sea_water_speed_1 (cm s-1)",
        "sea_water_direction_1": "sea_water_direction_1 (degree)",
        "upward_sea_water_velocity_1": "upward_sea_water_velocity_1 (cm s-1)",
    })

    try:
        #df = e.to_pandas()
        # We already have a datetime object from above, no need to convert
        #df['time (UTC)'] = pd.to_datetime(df['time (UTC)'])
        df = df.dropna(subset=[f'sea_water_speed_{suffix} (cm s-1)', f'sea_water_direction_{suffix} (degree)'])
        df[f'sea_water_speed_{suffix} (cm s-1)'] /= 100.0  # Convert cm/s to m/s

        if df.empty:
            print(f"No data available for depths between {depth_range[0]}m and {depth_range[1]}m.")
            return
    except Exception as error:
        print(f"Failed to fetch or process data: {error}")
        return  # Return early if data cannot be fetched or processed

    df = df[(df['depth (m)'] >= depth_range[0]) & (df['depth (m)'] <= depth_range[1])]

    global_min_time = date2num(df['time (UTC)'].min())
    global_max_time = date2num(df['time (UTC)'].max())

    unique_depths = sorted(df['depth (m)'].unique(), reverse=True)
    plot_height_per_depth = height_per_plot
    total_height = plot_height_per_depth * len(unique_depths)

    fig, ax = plt.subplots(figsize=(20, total_height))

    y_offset_factor = 10.0

    for i, depth in enumerate(unique_depths):
        subset = df[df['depth (m)'] == depth]
        times = subset['time (UTC)']
        speeds = subset[f'sea_water_speed_{suffix} (cm s-1)']
        directions = subset[f'sea_water_direction_{suffix} (degree)']

        directions_rad = np.radians(directions)
        u = speeds * np.sin(directions_rad)
        v = speeds * np.cos(directions_rad)

        colors = np.where(speeds <= 0.10, color_pallete[0],
                          np.where(speeds <= 0.20, color_pallete[1],
                                   np.where(speeds <= 0.30, color_pallete[2],
                                            np.where(speeds <= 0.40, color_pallete[3],
                                                     np.where(speeds <= 0.50, color_pallete[4], color_pallete[5])))))

        if arrow_head:
            ax.quiver(date2num(times), np.full_like(times, i * y_offset_factor), u, v,
                      color=colors, scale=20, width=0.002, headlength=2, headwidth=2, headaxislength=2.5)
        else:
            ax.quiver(date2num(times), np.full_like(times, i * y_offset_factor), u, v,
                      color=colors, scale=20, width=0.001, headlength=0, headwidth=0, headaxislength=0)

        annotation_x_position = global_min_time - 0.15
        ax.text(annotation_x_position, i * y_offset_factor, f'{depth}m', horizontalalignment='right', verticalalignment='center', color="black")

    ax.set_xlim(annotation_x_position, global_max_time + 0.2)
    ax.set_ylim(-y_offset_factor, (len(unique_depths) - 1) * y_offset_factor + y_offset_factor)
    ax.axes.get_yaxis().set_visible(False)  # Hide y-axis
    ax.xaxis_date()

    plt.title(f'Stick Plot for Depths from {depth_range[0]}m to {depth_range[1]}m')
    plt.xticks(rotation=45)
    plt.draw()  # Ensure all elements are drawn

    plt.savefig(output_filename, dpi=300)  # Save the figure
    #plt.show()

if __name__ == "__main__":
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    fetch_and_plot(config)
