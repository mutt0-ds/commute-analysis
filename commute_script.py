import os
import time
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
GOOGLE_API_KEY = os.environ.get("GOOGLE_DISTANCE_MATRIX_KEY")

# base URL that needs will have additional parameters concatenated to it
API_ENDPOINT = 'https://maps.googleapis.com/maps/api/distancematrix/json'
HOME_COORD = 45.000000, 45.000000
WORK_COORD = 45.000000, 45.000000


def generate_commute_df(start_hour: int, end_hour: int, days: int = 7) -> pd.DataFrame:
    """Creates a DataFrame given the starting and ending hour
    By default it returns the selected timeframes for the next 7 days
    It's based in the future so Google Maps can use past data for predicting"""
    res = pd.DatetimeIndex([])

    for day in range(days + 1, days + 8):
        starting_day = datetime.today() + timedelta(days=day)
        start = starting_day.replace(
            hour=start_hour, minute=0, second=0, microsecond=0)
        end = starting_day.replace(
            hour=end_hour, minute=0, second=0, microsecond=0)

        intervals = pd.date_range(start, end, freq='5T')
        res = res.append(intervals)

    commute_data = pd.DataFrame({"datetime": res})
    commute_data['time'] = commute_data.datetime.dt.time.apply(
        lambda x: str(x))
    commute_data['week_day'] = commute_data.datetime.dt.day_name()

    # we can exclude Saturday and Sunday
    commute_data = commute_data[~commute_data['week_day'].isin(
        ['Sunday', 'Saturday'])]
    return commute_data


def get_maps_data(commute_data: pd.DataFrame) -> pd.DataFrame:
    """queries the Distance Matrix API with the coordinates and times given"""
    for ind, row in tqdm(commute_data.iterrows(), total=commute_data.shape[0]):
        # convert datetime to UNIX timestamp
        unix_departure_time = time.mktime(row.datetime.timetuple())

        origin = f'{row.start_coord_x},{row.start_coord_y}'
        destination = f'{row.end_coord_x},{row.end_coord_y}'
        request_url = f"{API_ENDPOINT}?origins={origin}&destinations={destination}&departure_time={int(unix_departure_time)}&key={GOOGLE_API_KEY}"

        result = requests.get(request_url).json()

        # get duration in traffic in seconds based on the time of departure
        commute_data.loc[ind, 'duration_in_traffic_seconds'] = result['rows'][0]['elements'][0]['duration_in_traffic']['value']
        commute_data['duration_in_traffic_minutes'] = commute_data['duration_in_traffic_seconds']/60
    return commute_data


def plot_results(commute_data: pd.DataFrame, title: str = "Time in traffic") -> None:
    plt.clf()
    plt.figure(figsize=(22, 10))
    plt.title(title, fontdict={'fontsize': 30})
    sns.set_style('darkgrid', {"axes.facecolor": ".9"})
    sns.set_context("notebook", font_scale=2, rc={'lines.linewidth': 2.2})
    sns.lineplot(data=commute_data, x='time',
                 y='duration_in_traffic_minutes', hue='week_day', palette='deep')
    plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1))
    plt.tick_params(axis='x', rotation=70)
    plt.xlabel('Departure time')
    plt.ylabel('Commute time (minutes)')


# morning
morning_commute = generate_commute_df(6, 10)
morning_commute["start_coord_x"], morning_commute["start_coord_y"] = HOME_COORD
morning_commute["end_coord_x"], morning_commute["end_coord_y"] = WORK_COORD
morning_commute = get_maps_data(morning_commute)

plot_results(morning_commute, 'Commute time - Home to Work')


# evening
evening_commute = generate_commute_df(16, 20)
evening_commute["start_coord_x"], evening_commute["start_coord_y"] = WORK_COORD
evening_commute["end_coord_x"], evening_commute["end_coord_y"] = HOME_COORD
evening_commute = get_maps_data(evening_commute)

plot_results(evening_commute, 'Commute time - Work to Home')
