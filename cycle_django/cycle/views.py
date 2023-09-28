import abc
import copy
import datetime
from math import log10, radians, sin, cos, acos
import numpy as np
import pandas
from plotly.offline import plot
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List

from django.shortcuts import render
from django.core import serializers
from django.db.models import Avg, Max, Min, Sum
from django.views import generic
from django.shortcuts import get_object_or_404

from .models import CycleRides, CycleWeeklySummary, CycleMonthlySummary, CycleYearlySummary, GPSData, NoGoAreas
from .forms import PlotDataForm, PlotDataFormSummary, GpsDateRangeForm
from my_base import Logging

logger = Logging.setup_logger(__name__)

FIELDS_TO_LABELS = {"date": "Date", "distance": "Distance [km]", "duration": "Duration", "speed": "Speed [km/h]",
                    "days": "Days"}


def index(request):
    """View function for home page of site."""

    # Find the minimum date:
    start_date = CycleRides.objects.all().aggregate(Min('date'))["date__min"]
    end_date = CycleRides.objects.all().aggregate(Max('date'))["date__max"]
    number_of_days = CycleRides.objects.all().count()
    number_of_weeks = CycleWeeklySummary.objects.all().count()
    number_of_months = CycleMonthlySummary.objects.all().count()
    number_of_years = CycleYearlySummary.objects.all().count()
    number_of_gps_files = GPSData.objects.all().count()

    context = {
        'start_date': start_date.strftime('%Y-%m-%d') if start_date is not None else None,
        'end_date': end_date.strftime('%Y-%m-%d') if end_date is not None else None,
        'number_of_days': number_of_days,
        'number_of_weeks': number_of_weeks,
        'number_of_months': number_of_months,
        'number_of_years': number_of_years,
        'number_of_gps_files': number_of_gps_files
    }

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)


class BaseDataListView(generic.ListView):
    context_object_name = 'cycle_data_list'  # This is used as variable in cycle_data_list.html
    template_name = 'cycle_data/cycle_data_list.html'  # https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Generic_views
    context_dataset = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_frame = None

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        # Better instead of copy and replace: https://www.valentinog.com/blog/drf-request/
        request_get = copy.copy(self.request.GET)
        if not self.request.GET:
            # should be a django.http.request.QueryDict instead
            # if self.request.GET is empty (first time, it doesn't use the set initial values in ChoiceField
            request_get = {}
        for key, value in {'x_data': 'date', 'y_data': 'distance', 'z_data': 'speed'}.items():
            if not request_get.get(key):
                request_get.update({key: value})
        self.request.GET = request_get
        # Create any data and add it to the context
        context['dataset'] = self.context_dataset
        context['plot_div'] = self.create_plot()

        return context

    @property
    def data_frame(self):
        if self._data_frame is None:
            self._data_frame = self.create_data_frame()
        return self._data_frame

    @abc.abstractmethod
    def add_data_serialized_models(self, serialized_models):
        pass

    def create_data_frame(self):
        queryset = self.get_queryset()

        if queryset.exists():
            serialized_models = serializers.serialize(format='python', queryset=queryset)
            self.add_data_serialized_models(serialized_models)
            serialized_objects = [s['fields'] for s in serialized_models]
            data = [x.values() for x in serialized_objects]
            columns = serialized_objects[0].keys()

            data_frame = pandas.DataFrame(data, columns=columns)
            # Convert the duration fields from string into timedelta fields
            columns_time = [col for col in columns if col.find("duration") != -1]
            for col in columns_time:
                data_frame[col + "_td"] = pandas.to_timedelta(data_frame[col])
                data_frame[col] = data_frame[col + "_td"] + pandas.to_datetime('1970/01/01')
            return data_frame[data_frame['distance'] > 0.01]

    def create_plot(self):
        x = self.request.GET.get("x_data", "date")
        y = self.request.GET.get("y_data", "distance")
        z = self.request.GET.get("z_data", "speed")
        xl = FIELDS_TO_LABELS[x]
        yl = FIELDS_TO_LABELS[y]
        plot_args = {"x": x, "y": y, "labels": {x: xl, y: yl}}
        if z != "none":
            zl = FIELDS_TO_LABELS[z]
            plot_args["color"] = z
            plot_args["labels"][z] = zl

        if self.data_frame is not None:
            fig = px.scatter(self.data_frame, **plot_args)
            # fig.update_yaxes(autorange="reversed")
            return plot(fig, output_type="div")


class DataListView(BaseDataListView):
    # executed when server is initialised
    # model = CycleRides
    context_dataset = "day"
    paginate_by = 200

    def get_queryset(self):
        # executed when the page is opened
        return CycleRides.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plotdataform"] = PlotDataForm(self.request.GET)

        return context

    def add_data_serialized_models(self, serialized_models):
        pass


class DataSummaryView(BaseDataListView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plotdataform"] = PlotDataFormSummary(self.request.GET)

        return context

    def add_data_serialized_models(self, serialized_models):
        # The primary key is not included in the serialized data
        for s in serialized_models:
            s["fields"]["date"] = s['pk']


class DataWListView(DataSummaryView):
    paginate_by = 100
    context_dataset = "week"

    def get_queryset(self):
        return CycleWeeklySummary.objects.all()


class DataMListView(DataSummaryView):
    context_dataset = "month"

    def get_queryset(self):
        return CycleMonthlySummary.objects.all()


class DataYListView(DataSummaryView):
    context_dataset = "year"

    def get_queryset(self):
        return CycleYearlySummary.objects.all()


class ExtraPlots(BaseDataListView):
    """ Use the Base view to not need to worry how to grab the data"""
    context_object_name = None
    template_name = 'cycle_data/cycle_extra_plots.html'
    context_dataset = None

    def get_queryset(self):
        # executed when the page is opened
        return CycleRides.objects.all()

    def get_context_data(self, **kwargs):
        context = self.create_extra_plots()
        dist_per_days = []
        self.data_frame['Date_datetime'] = pandas.to_datetime(self.data_frame['date'])
        self.data_frame.set_index('Date_datetime', inplace=True)
        self.data_frame['Date_dt'] = pandas.to_datetime(self.data_frame['date'])
        for days in (list(range(1, 8)) + [10, 14, 21] + list(range(30, 91, 20)) + list(range(120, 181, 30)) +
                     [270, 365, 365 * 2, 365 * 4 + 1]):
            dist = self.data_frame['distance'].rolling(window=f'{days}D').sum()  # this is only consecutive days
            dist_sort = dist.sort_values(ascending=False)
            result = []
            diff = datetime.timedelta(days=days - 1)
            for date, value in dist_sort.items():
                date_start = self.data_frame['Date_dt'][(self.data_frame['Date_dt'] >= date-diff)].min()
                for start, end, _ in result:
                    if date >= start and date_start <= end:
                        break
                else:
                    result.append([date_start, date, value])
                    if len(result) == 5:
                        break
            if result:
                result = [{'start': start.strftime('%Y-%m-%d'), 'end': end.strftime('%Y-%m-%d'), 'distance': value}
                          for start, end, value in result]
                dist_per_days.append({'days': days, 'dist_sort': result})

        context['dist_per_days'] = dist_per_days

        return context

    def add_data_serialized_models(self, serialized_models):
        pass

    def create_extra_plots(self) -> Dict:
        if self.data_frame is None:
            return {}
        ax = "date"
        ay1 = "totalspeed"
        ay2 = "totaldistance"
        ay3 = "totalduration"
        fig_total = go.Figure()
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay1], name="Speed"))
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay2], name="Distance", yaxis="y2"))
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay3], name="Duration", yaxis="y3"))
        fig_total.update_layout(
            xaxis=dict(title="Date", domain=[0.0, 0.85]),
            yaxis=dict(
                title="Cumulative speed [km/h]",
                titlefont=dict(color="#1f77b4"),
                tickfont=dict(color="#1f77b4")
            ),
            yaxis2=dict(
                title="Cumulative Distance [km]",
                titlefont=dict(color="#cc0000"),
                tickfont=dict(color="#cc0000"),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.85
            ),
            yaxis3=dict(
                title="Cumulative Duration [hh:mm]",
                titlefont=dict(color="#009973"),
                tickfont=dict(color="#009973"),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.92
            ),
        )

        # Histogram plots
        data = self.data_frame["distance"]
        range_dist = int(max(data) - min(data))
        fig_hist_dist = go.Figure()
        fig_hist_dist.add_trace(go.Histogram(x=data, nbinsx=int(range_dist / 2), name="Distance (4km bins)"))
        fig_hist_dist.add_trace(go.Histogram(x=data, nbinsx=range_dist * 2, name="Distance (1km bins)"))
        fig_hist_dist.add_trace(go.Histogram(x=data, nbinsx=range_dist * 10, name="Distance (200m bins)"))
        fig_hist_dist.update_layout(
            # Overlay both histograms
            barmode='overlay',
            xaxis=dict(title="Distance [km]"),
            yaxis=dict(title="Number of occurrences of Distance values"),
        )
        data = self.data_frame["duration_td"].dt.total_seconds() / 60
        range_dur = int(max(data) - min(data))
        fig_hist_dur = go.Figure()
        fig_hist_dur.add_trace(go.Histogram(x=data, nbinsx=int(range_dur / 5), name="Duration (10 min bins)"))
        fig_hist_dur.add_trace(go.Histogram(x=data, nbinsx=range_dur * 2, name="Duration (1min bins)"))
        fig_hist_dur.update_layout(
            # Overlay both histograms
            barmode='overlay',
            xaxis=dict(title="Duration [min]"),
            yaxis=dict(title="Number of occurrences of Duration values"),
        )
        data = self.data_frame["speed"]
        range_spd = int(max(data) - min(data))
        fig_hist_spd = go.Figure()
        fig_hist_spd.add_trace(go.Histogram(x=data, nbinsx=range_spd * 4, name="Speed (500 m/s bins)"))
        fig_hist_spd.add_trace(go.Histogram(x=data, nbinsx=range_spd * 40, name="Duration (50 m/s bins)"))
        fig_hist_spd.update_layout(
            # Overlay both histograms
            barmode='overlay',
            xaxis=dict(title="Speed [km/s]"),
            yaxis=dict(title="Number of occurrences of Speed values"),
        )

        bx = "date"
        by1 = "diffkm"
        by2 = "diffsec"
        self.data_frame[by1] = self.data_frame["totaldistance"] - self.data_frame["cumdistance"]
        self.data_frame[by2] = pandas.to_numeric(
            self.data_frame["totalduration"] - self.data_frame["cumduration"]
        ) * 1E-9  # From mu sec to seconds

        fig_diff = go.Figure()
        fig_diff.add_trace(go.Scatter(x=self.data_frame[bx], y=self.data_frame[by1], name="Distance"))
        fig_diff.add_trace(go.Scatter(x=self.data_frame[bx], y=self.data_frame[by2], name="Duration", yaxis="y2"))
        fig_diff.update_layout(
            xaxis=dict(title="Date", domain=[0.0, 0.9]),
            yaxis=dict(
                title="Diff between Total and Cumulative Distance [km]",
                titlefont=dict(color="#1f77b4"),
                tickfont=dict(color="#1f77b4")
            ),
            yaxis2=dict(
                title="Diff between Total and Cumulative Duration [sec]",
                titlefont=dict(color="#cc0000"),
                tickfont=dict(color="#cc0000"),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.9
            ),
        )

        # Frac of km, Seconds histogram
        frac_km, int_km = np.modf(self.data_frame["distance"])
        frac_km *= 1E2
        frac_sec = ((self.data_frame["duration_td"]) % (60 * 1E9)).dt.total_seconds()
        fig_frac = go.Figure()
        fig_frac.add_trace(go.Histogram(x=frac_sec, nbinsx=60, name="Duration"))
        fig_frac.add_trace(go.Histogram(x=frac_km, nbinsx=100, name="Distance"))
        # Reduce opacity to see both histograms
        # fig_frac.update_traces(opacity=0.75)
        fig_frac.update_layout(
            # Overlay both histograms
            barmode='overlay',
            xaxis=dict(title="Fraction of Distance [m * 10] / Fraction of Duration [s]", domain=[0.0, 0.9]),
            yaxis=dict(title="Number of occurrences in data"),
        )

        plot_dict = {
            "plot_total_div": plot(fig_total, output_type="div"),
            "plot_hist_dist": plot(fig_hist_dist, output_type="div"),
            "plot_hist_dur": plot(fig_hist_dur, output_type="div"),
            "plot_hist_speed": plot(fig_hist_spd, output_type="div"),
            "plot_diff_div": plot(fig_diff, output_type="div"),
            "plot_frac_div": plot(fig_frac, output_type="div"),
        }

        return plot_dict


def data_detail_view(request, date_wmy=None, entryid=None):
    if entryid is not None:
        cycleThisData = get_object_or_404(CycleRides, pk=entryid)
        dataType = "d"
    elif date_wmy is not None:
        dataType = "wmy"
        if date_wmy[0] == "w":
            cycleThisData = get_object_or_404(CycleWeeklySummary, pk=date_wmy[1:])
        elif date_wmy[0] == "m":
            cycleThisData = get_object_or_404(CycleMonthlySummary, pk=date_wmy[1:])
        elif date_wmy[0] == "y":
            cycleThisData = get_object_or_404(CycleYearlySummary, pk=date_wmy[1:])
        else:
            raise ValueError('date_wmy has an unknown start: ' + date_wmy)
    else:
        raise ValueError('Both date_wmy and entryid are none.')

    context = {'cycle': cycleThisData, 'dataType': dataType}

    # Deal with the GPS Data: first the form
    form = GpsDateRangeForm(request.GET)
    if form.is_valid():
        begin_date = form.cleaned_data['begin_date']
        end_date = form.cleaned_data['end_date'] + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
        gps_objs = GPSData.objects.filter(start__gte=begin_date, end__lte=end_date).order_by('start')
    else:
        gps_objs = cycleThisData.get_gps_objs()
        begin_date = gps_objs[0].start
        end_date = gps_objs[0].end
        for obj in gps_objs:
            if obj.start < begin_date:
                begin_date = obj.start
            if obj.end > end_date:
                end_date = obj.end

        initial_values = {'begin_date': begin_date, 'end_date': end_date}
        form = GpsDateRangeForm(initial=initial_values)
    # And then the data
    gps_context = analyse_gps_data_sets(gps_objs)
    gps_context['gpsdatarangeform'] = form
    context.update(gps_context)

    return render(request, 'cycle_data/cycle_detail.html', context=context)


def analyse_gps_data_sets(objs: List[GPSData]) -> Dict:
    """ Be careful to apply sin/cos only on radians!
    """
    if not objs:
        return {}

    def check_no_go(nogos, df: pandas.DataFrame, position: str):
        steps = 10
        if position == 'begin':
            my_range = list(range(0, df.shape[0], steps))
            my_range[-1] = df.shape[0] - steps
        elif position == 'end':
            my_range = list(range(df.shape[0] - steps, steps, -steps))
            if len(my_range) > 0:
                my_range[-1] = 0
        else:
            raise TypeError(f"Coding error: position {position} is not know")
        tokeep = np.ones(df.shape[0], dtype=bool)
        for ii in my_range:
            subset = df.iloc[ii:ii + steps]
            sin_lats = subset['sin_lat'].to_numpy()
            cos_lats = subset['cos_lat'].to_numpy()
            lons = subset['Longitudes_rad'].to_numpy()
            for nogo in nogos:
                temp = np.arccos(sin_lats * nogo[0] + cos_lats * nogo[1] * np.cos(lons - nogo[2]))
                if np.min(temp) < nogo[3]:
                    tokeep[ii:ii + steps] = np.zeros(steps, dtype=bool)
                    break
            else:  # Stop deleting (no break)
                break

        return df.iloc[tokeep]

    all_positions = []
    all_df = pandas.DataFrame({'Duration': [], 'Distance': [], 'Altitudes': [], 'Speed_5': [], 'Speed_50': []})
    min_time = 1E99
    max_time = 0
    max_lat = -90
    min_lat = 90
    max_lon = -180
    min_lon = 180
    earth_radius = 6371.009
    nogos = []
    for nogo in NoGoAreas.objects.all():
        lat = radians(nogo.latitude)
        lon = radians(nogo.longitude)
        nogos.append([sin(lat), cos(lat), lon, nogo.radius / earth_radius])
    number_of_files = len(objs)
    if number_of_files > 10:
        slice = max(2, min(10, int(number_of_files / 30) + 1))
    else:
        slice = 1
    settings = {'slice': slice}
    for obj in objs:
        times = np.array(obj.datetimes[1:-1].split(", "), dtype=np.float64)  # e.g. 1269530756.0
        lats = np.array(obj.latitudes[1:-1].split(", "), dtype=np.float64)  # degrees
        lons = np.array(obj.longitudes[1:-1].split(", "), dtype=np.float64)  # degrees
        elev = np.array(obj.altitudes[1:-1].split(", "), dtype=np.float64)
        data = {'Times': times, 'Latitudes_deg': lats, 'Longitudes_deg': lons, 'Altitudes': elev}
        df = pandas.DataFrame(data)
        if slice > 1:
            df = df.iloc[::slice]
        df['Latitudes_rad'] = np.radians(df['Latitudes_deg'])
        df['Longitudes_rad'] = np.radians(df['Longitudes_deg'])
        df['sin_lat'] = np.sin(df['Latitudes_rad'])
        df['cos_lat'] = np.cos(df['Latitudes_rad'])

        df = check_no_go(nogos, df, 'begin')
        df = check_no_go(nogos, df, 'end')

        if df.shape[0] < 10:
            continue
        window_med_duration = 50
        paused_after = 30 * slice  # assume a pause if the next data point took 30s to appear
        min_consecutive_points = 10  # exclude sections with breaks within min_consecutive_points points
        min_periods = 3  # to calculate rolling median/sum at least these number of datapoints should not be nans
        # Duration
        df['Duration'] = np.zeros(df.shape[0])
        df['Duration'][1:] = (df['Times'].shift(-1) - df['Times'])[:-1]  # in Seconds
        ## Exclude datapoints after/during a stop
        df['Duration'][df['Duration'] > paused_after] = np.nan
        duration_rolling_median = df['Duration'].rolling(
            window=window_med_duration, min_periods=int(0.1 * window_med_duration)
        ).median().to_numpy()
        df['Duration'][df['Duration'] > 3 * duration_rolling_median] = np.nan
        duration_is_nan = np.where(df['Duration'].isna().to_numpy())[0]
        if duration_is_nan.shape[0] >= 1:
            if duration_is_nan[0] <= min_consecutive_points:
                df['Duration'][0:duration_is_nan[0]] = np.nan
            if duration_is_nan[-1] >= df.shape[0] - min_consecutive_points:
                df['Duration'][duration_is_nan[-1]:] = np.nan
            # Indexes, where gap between spaces <= min_consecutive_points:
            space_nan = np.where(duration_is_nan[1:] - duration_is_nan[:-1] <= min_consecutive_points)[0]
            for index in space_nan:
                index_df_beg = duration_is_nan[index]
                index_df_end = duration_is_nan[index + 1]
                df['Duration'][index_df_beg:index_df_end] = np.nan
        df['Altitudes'][df['Duration'].isna()] = np.nan
        # Distance
        df['Distance'] = np.zeros(df.shape[0])
        df['Distance'][1:] = (np.arccos(
            df['sin_lat'] * df['sin_lat'].shift(-1) +
            df['cos_lat'] * df['cos_lat'].shift(-1) * np.cos(df['Longitudes_rad'] - df['Longitudes_rad'].shift(-1))
        ) * earth_radius)[:-1]
        df['Distance'][df['Duration'].isna()] = np.nan
        # Speed
        duration_rolling_sum = df['Duration'].rolling(window=5, min_periods=min_periods).sum().to_numpy()
        distance_rolling_sum = df['Distance'].rolling(window=5, min_periods=min_periods).sum().to_numpy()
        df['Speed_5'] = distance_rolling_sum / duration_rolling_sum * 3600
        duration_rolling_sum = df['Duration'].rolling(window=50, min_periods=min_periods).sum().to_numpy()
        distance_rolling_sum = df['Distance'].rolling(window=50, min_periods=min_periods).sum().to_numpy()
        df['Speed_50'] = distance_rolling_sum / duration_rolling_sum * 3600

        max_time = max(max_time, df['Times'].max())
        min_time = min(min_time, df['Times'].min())
        max_lat = max(max_lat, df['Latitudes_deg'].max())
        min_lat = min(min_lat, df['Latitudes_deg'].min())
        max_lon = max(max_lon, df['Longitudes_deg'].max())
        min_lon = min(min_lon, df['Longitudes_deg'].min())
        # Add markers for each GPS data point
        positions = df[['Latitudes_deg', 'Longitudes_deg']].values.tolist()

        all_positions.append(positions)
        all_df = pandas.concat(
            [all_df, df[['Duration', 'Distance', 'Altitudes', 'Speed_5', 'Speed_50']][~df['Duration'].isna()]]
        )

    all_df['Culm_dist'] = all_df['Distance'].cumsum()
    culm_duration = all_df['Duration'].cumsum()
    all_df['Culm_speed'] = all_df['Culm_dist'] / culm_duration * 3600
    alt_rolling_median = all_df['Altitudes'].rolling(window=5).median().to_numpy()
    alt_diff = alt_rolling_median[1:] - alt_rolling_median[:-1]
    ax = "Culm_dist"
    ay1 = "Altitudes"
    ay2 = "Speed_5"
    ay3 = "Speed_50"
    ay4 = "Culm_speed"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay1], name="Elevation [m]",
                             mode='lines', marker=dict(color='#FF0000')))
    fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay2], name="Speed (5 points)", yaxis="y2",
                             mode='lines', marker=dict(color='#00FF00'), opacity=0.5))
    fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay3], name="Speed (50 points)", yaxis="y2",
                             mode='lines', marker=dict(color='#00AF00'), opacity=0.7))
    fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay4], name="Cumlative Speed", yaxis="y2",
                             mode='lines', marker=dict(color='#005F00')))
    # fig.data = (fig.data[1], fig.data[2], fig.data[3], fig.data[0]) # also resorts the colors
    fig.update_layout(
        title=(f"{datetime.datetime.fromtimestamp(min_time)} to {datetime.datetime.fromtimestamp(max_time)} : "
               f"{all_df['Culm_dist'].iloc[-1]:.2f} km, "
               f"{datetime.timedelta(seconds=culm_duration.iloc[-1])} moving, "
               f"{all_df['Culm_speed'].iloc[-1]:.2f} km/h, "
               f"{alt_diff[alt_diff > 0].sum():.0f} m up, {alt_diff[alt_diff < 0].sum():.0f} m down"),
        xaxis=dict(title="Distance [km]", domain=[0.0, 0.92]),
        yaxis=dict(
            title="Elevation [m]",
            titlefont=dict(color="#FF0000"),
            tickfont=dict(color="#FF0000")
        ),
        yaxis2=dict(
            title="Speed [km/h]",
            titlefont=dict(color="#00AF00"),
            tickfont=dict(color="#00AF00"),
            anchor="free",
            overlaying="y",
            side="right",
            position=0.92
        ),
    )

    map_center = [0.5 * (min_lat + max_lat), 0.5 * (min_lon + max_lon)]
    zoom = int(round(-3.2 * log10(max(max_lat - min_lat, (max_lon - min_lon) * sin(radians(map_center[0])))) + 8.9))
    context = {'gps': None, 'gps_positions': all_positions, 'center': map_center, 'zoom': zoom, 'settings': settings,
               "plot_div": plot(fig, output_type="div")}

    return context


def gps_detail_view(request, filename=None):
    # Not executed for plots for Cycle Detail View: see data_detail_view
    form = GpsDateRangeForm(request.GET)
    if form.is_valid():
        begin_date = form.cleaned_data['begin_date']
        end_date = form.cleaned_data['end_date'] + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
        gpsData = GPSData.objects.filter(start__gte=begin_date, end__lte=end_date).order_by('start')
    else:
        if filename == "all":
            gpsData = GPSData.objects.all()
            begin_date = GPSData.objects.all().aggregate(Min('start'))['start__min']
            end_date = GPSData.objects.all().aggregate(Max('end'))['end__max']
            initial_values = {'begin_date': begin_date, 'end_date': end_date}
        elif filename is not None:
            gpsData = [get_object_or_404(GPSData, pk=filename)]
            initial_values = None
        else:
            raise ValueError('Parameter unknown.')
        form = GpsDateRangeForm(initial=initial_values)
    context = analyse_gps_data_sets(gpsData)
    context['gpsdatarangeform'] = form

    return render(request, 'cycle_data/cycle_detail.html', context=context)


class GPSDataListView(generic.ListView):
    context_object_name = 'gps_data_list'  # This is used as variable in cycle_data_list.html
    template_name = 'cycle_data/gps_data_list.html'

    def get_queryset(self):
        # executed when the page is opened
        return GPSData.objects.all()
