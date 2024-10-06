import abc
import copy
import datetime
from math import log10, radians, sin, cos, acos
import numpy as np
import pandas
from plotly.offline import plot
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Union

from django.shortcuts import get_object_or_404, render, redirect
from django.core import serializers
from django.db.models import Avg, Max, Min, Sum
from django.http import HttpResponse
from django.views import generic

from .models import (
    CycleRides, CycleWeeklySummary, CycleMonthlySummary, CycleYearlySummary, GPSData, NoGoAreas, GeoLocateData,
    PhotoData
)
from .forms import PlotDataForm, PlotDataFormSummary, GpsDateRangeForm
from my_base import Logging, create_timezone_object, photoStorage

logger = Logging.setup_logger(__name__)

FIELDS_TO_LABELS = {"date": "Date", "distance": "Distance [km]", "duration": "Duration", "speed": "Speed [km/h]",
                    "days": "Days", "numberofdays": "Number of Days", "bicycle": "Bicycle"}


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

    # This is overwritten by the child get_queryset, use the sort_queryset instead
    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     sort_by = self.request.GET.get('sort', 'date')  # Default sort by 'date'
    #     return queryset.order_by(sort_by)

    def sort_queryset(self, queryset):
        sort_by = self.request.GET.get('sort', 'date')  # Default sort by 'date'
        return queryset.order_by(sort_by)

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
        context['sort_by'] = self.request.GET.get('sort', 'date')

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
        return self.sort_queryset(CycleRides.objects.all())

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
        return self.sort_queryset(CycleWeeklySummary.objects.all())


class DataMListView(DataSummaryView):
    context_dataset = "month"

    def get_queryset(self):
        return self.sort_queryset(CycleMonthlySummary.objects.all())


class DataYListView(DataSummaryView):
    context_dataset = "year"

    def get_queryset(self):
        return self.sort_queryset(CycleYearlySummary.objects.all())


class ExtraPlots(BaseDataListView):
    """ Use the Base view to not need to worry how to grab the data"""
    context_object_name = None
    template_name = 'cycle_data/cycle_extra_plots.html'
    context_dataset = None

    def get_queryset(self):
        # executed when the page is opened
        return CycleRides.objects.all()

    def get_context_data(self, **kwargs):
        if self.data_frame is None:
            return {}
        context = self.create_extra_plots()
        data_frame = self.data_frame[['distance', 'duration_td', 'date']].copy()
        data_frame['duration'] = data_frame['duration_td'].dt.total_seconds()
        data_frame['Date_datetime'] = pandas.to_datetime(data_frame['date'])
        data_frame.set_index('Date_datetime', inplace=True)
        data_frame['Date_dt'] = pandas.to_datetime(data_frame['date'])

        context['dist_per_days'] = self.get_dist_time_per_days(data_frame)
        context['same_numbers'] = self.get_same_numbers()
        context['same_digits'] = self.get_same_digits()

        return context

    def get_dist_time_per_days(self, data_frame):
        dist_per_days = []
        for days in (list(range(1, 8)) + [10, 14, 21] + list(range(30, 91, 20)) + list(range(120, 181, 30)) +
                     [270, 365, 365 * 2, 365 * 4 + 1]):
            result_all = {'days': days}
            for data_source in ['distance', 'duration']:
                if days < 10:       # needed because of no daily data before that date
                    dist = data_frame[data_frame['Date_dt'] >= pandas.to_datetime('2006-12-06')][data_source].rolling(window=f'{days}D').sum()  # this is only consecutive days
                else:
                    dist = data_frame[data_source].rolling(window=f'{days}D').sum()  # this is only consecutive days
                dist_sort = dist.sort_values(ascending=False)
                result = []
                diff = datetime.timedelta(days=days - 1)
                for date, value in dist_sort.items():
                    date_start = data_frame['Date_dt'][(data_frame['Date_dt'] >= date-diff)].min()
                    for start, end, _ in result:
                        if date >= start and date_start <= end:
                            break
                    else:
                        result.append([date_start, date, value])
                        if len(result) == 5:
                            break
                if result:
                    result = [{'start': start.strftime('%Y-%m-%d'), 'end': end.strftime('%Y-%m-%d'), data_source: value}
                              for start, end, value in result]
                    result_all[data_source] = result
            if len(result_all.keys()) > 1:
                dist_per_days.append(result_all)

        return dist_per_days

    def get_same_numbers(self):
        same_numbers = dict()
        for column in ['distance', 'duration_td', 'speed']:
            if column in ['distance', 'speed']:
                # Round to 2 digits and then count same values
                count_entries = self.data_frame[column].round(2).value_counts()
            else:
                count_entries = self.data_frame[column].value_counts()
            # counted values are sorted from highest down
            # keep the counted values that are one higher than the 20th highest
            threshold = count_entries.iloc[min(20, count_entries.count())]
            count_filtered = count_entries[count_entries > threshold]
            result = []
            for value, count in count_filtered.items():
                if column in ['distance', 'speed']:
                    dates = self.data_frame.loc[self.data_frame[column].round(2) == value, 'date'].sort_values().tolist()
                else:
                    dates = self.data_frame.loc[self.data_frame[column] == value, 'date'].sort_values().tolist()
                result. append({
                    'count': count, 'value': value,
                    'cycle_obj': [CycleRides.objects.filter(date=date)[0] for date in dates]
                })
            same_numbers[column] = result

        return same_numbers

    def get_same_digits(self):
        def convert_number_to_hms(number):
            m, s = divmod(number, 100)
            if m > 100:
                h, m = divmod(m, 100)
            else:
                h = 0
            if s < 60 and m < 60 and h < 24:
                return h * 3600 + m * 60 + s
            return None

        def convert_number_to_dhm(number):
            h, m = divmod(number, 100)
            if h > 100:
                d, h = divmod(h, 100)
            else:
                d = 0
            if m < 60 and h < 24:
                return (d * 24 + h) * 3600 + m * 60
            return None

        def convert_number_to_hm(number):
            h, m = divmod(number, 100)
            if m < 60:
                return h * 3600 + m * 60
            return None

        def add_results(key, this_table):
            if key not in this_table.keys():
                this_table[key] = []
            this_table[key].append(obj)

        possible_numbers = {
            31415, 314159, 3141592, 31415926, 314159265, 27182, 271828, 2718281, 27182818, 271828182,
            2468, 8642, 86420, 1357, 7531, 13579, 97531
        }
        possible_times_s = {convert_number_to_hms(i) for i in possible_numbers}
        possible_times_s_total = {convert_number_to_dhm(i) for i in possible_numbers}
        possible_times_s_total.update({convert_number_to_hm(i) for i in possible_numbers})
        """ Add all the numbers with the same digit for 4 to 7 digits: 1111 to 9999999 """
        for i in range(1, 10):
            number = 0
            for repeat in range(7):
                number += int(i * 10**repeat)
                if repeat >= 3:
                    possible_numbers.add(number)
                    possible_times_s_total.add(convert_number_to_hm(number))
        for i in range(1, 6):
            possible_times_s.add(671 * i)        # (11 * i) * (60 + 1), e.g. 22:22
            possible_times_s.add(4271 * i)       # (11 * i) * (60 + 1) + 3600 * i, e.g 5:55:55
            if i <= 2:
                possible_times_s.add(40271 * i)  # (11 * i) * (3600 + 60 + 1), e.g. 11:11:11
                days = 0
                for j in range(5):
                    days += int(i * 10**j)
                    possible_times_s_total.add(40260 * i + 86400 * days)  # (11 * i) * (60 + 3600) + 24 * 3600 * days
        """ All the number with increasing digits 3210, 9876543, 9876 and the reverses"""
        for i in range(7):
            number = 0
            for repeat in range(min(10 if i == 0 else 9, 10-i)):     # for i == 0 create a 10 digit number, as the inverse would start with a 0
                number += int((i + repeat) * 10**repeat)
                if repeat < 3:
                    continue
                possible_numbers.add(number)
                possible_times_s.add(convert_number_to_hms(number))
                possible_times_s_total.add(convert_number_to_dhm(number))
                possible_times_s_total.add(convert_number_to_hm(number))
                if i == 0 and repeat < 4:   # don't use 0123
                    continue
                number_r = int(str(number)[::-1])   # reverse number
                possible_numbers.add(number_r)
                possible_times_s.add(convert_number_to_hms(number_r))
                possible_times_s_total.add(convert_number_to_dhm(number_r))
                possible_times_s_total.add(convert_number_to_hm(number_r))
        possible_numbers.update(
            {round(0.1 * number, 1) for number in possible_numbers} |
            {round(0.01 * number, 2) for number in possible_numbers}
        )

        distances = dict()
        totaldistances = dict()
        times = dict()
        totaltimes = dict()
        speeds = dict()
        for obj in CycleRides.objects.all():
            if obj.distance in possible_numbers:
                add_results(obj.distance, distances)
            if obj.duration.total_seconds() in possible_times_s:
                add_results(obj.duration, times)
            if obj.totaldistance in possible_numbers:
                add_results(obj.totaldistance, totaldistances)
            if obj.totalduration.total_seconds() in possible_times_s_total:
                add_results(obj.totalduration, totaltimes)
            obj_speed = round(obj.speed, 2)
            if obj_speed in possible_numbers:
                add_results(obj_speed, speeds)

        same_digits = {
            'distances': distances, 'totaldistances': totaldistances, 'times': times, 'totaltimes': totaltimes,
            'speeds': speeds
        }
        return same_digits

    def add_data_serialized_models(self, serialized_models):
        pass

    def create_extra_plots(self) -> Dict:
        ax = "date"
        ay1 = "totalspeed"
        ay2 = "totaldistance"
        ay3 = "totalduration"
        ay1c = "cumspeed"
        ay2c = "cumdistance"
        ay3c = "cumduration"
        fig_total = go.Figure()
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay1], name="T Speed"))
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay2], name="T Distance", yaxis="y2"))
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay3], name="T Duration", yaxis="y3"))
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay1c], name="C Speed"))
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay2c], name="C Distance", yaxis="y2"))
        fig_total.add_trace(go.Scatter(x=self.data_frame[ax], y=self.data_frame[ay3c], name="C Duration", yaxis="y3"))
        fig_total.update_layout(
            xaxis=dict(title="Date", domain=[0.0, 0.85]),
            yaxis=dict(
                title="Total/Cumulative speed [km/h]",
                titlefont=dict(color="#1f77b4"),
                tickfont=dict(color="#1f77b4")
            ),
            yaxis2=dict(
                title="Total/Cumulative Distance [km]",
                titlefont=dict(color="#cc0000"),
                tickfont=dict(color="#cc0000"),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.85
            ),
            yaxis3=dict(
                title="Total/Cumulative Duration [hh:mm]",
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
        fig_hist_dist.add_trace(go.Histogram(x=data, nbinsx=int(range_dist / 2), name="Distance (5km bins)"))
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
        fig_hist_dur.add_trace(go.Histogram(x=data, nbinsx=range_dur * 1, name="Duration (2 min bins)"))
        fig_hist_dur.add_trace(go.Histogram(x=data, nbinsx=range_dur * 4, name="Duration (30 second bins)"))
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
        self.data_frame[by1] = self.data_frame["totaldistance"] - self.data_frame["cumbicycledistance"]
        self.data_frame[by2] = pandas.to_numeric(
            self.data_frame["totalduration"] - self.data_frame["cumbicycleduration"]
        ) * 1E-9  # From mu sec to seconds
        logger.info(f"111, {self.data_frame.tail(10)}")
        self.data_frame.loc[self.data_frame["cumbicycleduration"].isna(), by2] = np.nan # Restore NaNs
        logger.info(f"112, {self.data_frame.tail(10)}")
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
    form, gps_objs, coords, initial_values = read_GpsDateRangeForm(request)
    if not gps_objs:
        gps_objs = cycleThisData.get_gps_objs()
        if gps_objs:
            begin_date = gps_objs[0].start
            end_date = gps_objs[0].end
            for obj in gps_objs:
                if obj.start < begin_date:
                    begin_date = obj.start
                if obj.end > end_date:
                    end_date = obj.end
            initial_values['begin_date'] = begin_date
            initial_values['end_date'] = end_date
        form = GpsDateRangeForm(initial=initial_values)

    # And then the data
    gps_context = analyse_gps_data_sets(gps_objs, coords, admin=request.user.is_superuser)
    gps_context['gpsdatarangeform'] = form
    context.update(gps_context)

    # Add the images
    if 'min_max_coords' in gps_context:
        coords = gps_context['min_max_coords']
        context['photo_data'] = PhotoData.objects.filter(
            latitude__gte=coords[0], latitude__lte=coords[1], longitude__gte=coords[2], longitude__lte=coords[3])

    return render(request, 'cycle_data/cycle_detail.html', context=context)


def analyse_gps_data_sets(
        objs_in: List[GPSData],
        coords: Union[None, Dict] = None,
        plot_graphs: bool = True,
        admin: bool = False
) -> Dict:
    """ Be careful to apply sin/cos only on radians!
    """
    if not objs_in:
        return {}

    if coords:
        # This won't work for +/- 180 deg longitude
        delta_lat = 0.5 * 10**((coords['zoom'] - 9.5) / -3.2)
        delta_lon = delta_lat / sin(radians(coords['cenLat']))
        lat_min = coords['cenLat'] - delta_lat
        lat_max = coords['cenLat'] + delta_lat
        lon_min = coords['cenLng'] - delta_lon
        lon_max = coords['cenLng'] + delta_lon

    objs = []
    individual_gps_list = []
    for obj in objs_in:
        lats = np.array(obj.latitudes[1:-1].split(", "), dtype=np.float64)  # degrees
        lons = np.array(obj.longitudes[1:-1].split(", "), dtype=np.float64)  # degrees
        # This won't work for +/- 180 deg longitude
        if coords and not (np.max(lats) > lat_min and np.min(lats) < lat_max and
                           np.max(lons) > lon_min and np.min(lons) < lon_max):
            continue
        objs.append({
            'Times': np.array(obj.datetimes[1:-1].split(", "), dtype=int),  # e.g. 1269530756
            'Latitudes_deg': lats,
            'Longitudes_deg': lons,
            'Altitudes': np.array(obj.altitudes[1:-1].split(", ") if len(obj.alt_srtm[1:-1]) else lats * 0, dtype=int),
            'Altitudes_srtm':
                np.array(obj.alt_srtm[1:-1].split(", ") if len(obj.alt_srtm[1:-1]) else lats * 0, dtype=int),
        })
        individual_gps_list.append({'url': obj.get_absolute_url(), 'start': obj.start, 'end': obj.end})

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
    all_df = pandas.DataFrame({
        'Duration': [], 'Distance': [], 'Altitudes': [], 'Altitudes_srtm': [], 'Speed_5': [], 'Speed_50': [],
        'Times': [], 'Latitudes_deg': [], 'Longitudes_deg': [], 'Longitudes_rad': [], 'sin_lat': [], 'cos_lat': []
    })

    earth_radius = 6371.009
    nogos = []
    if not admin:
        for nogo in NoGoAreas.objects.all():
            lat = radians(nogo.latitude)
            lon = radians(nogo.longitude)
            nogos.append([sin(lat), cos(lat), lon, nogo.radius / earth_radius])

    df_geoloc = pandas.DataFrame.from_records(list(GeoLocateData.objects.all().values()))
    radius_deg = df_geoloc['radius'] / (earth_radius * radians(1))
    radius_deg_lat = radius_deg / np.cos(np.radians(df_geoloc['latitude']))
    # Doesn't work for longitudes at +- 180 and poles
    df_geoloc['lat_min'] = df_geoloc['latitude'] - radius_deg
    df_geoloc['lat_max'] = df_geoloc['latitude'] + radius_deg
    df_geoloc['lon_min'] = df_geoloc['longitude'] - radius_deg_lat
    df_geoloc['lon_max'] = df_geoloc['longitude'] + radius_deg_lat
    df_geoloc['Latitudes_rad'] = np.radians(df_geoloc['latitude'])
    df_geoloc['Longitudes_rad'] = np.radians(df_geoloc['longitude'])
    df_geoloc['sin_lat'] = np.sin(df_geoloc['Latitudes_rad'])
    df_geoloc['cos_lat'] = np.cos(df_geoloc['Latitudes_rad'])

    number_of_files = len(objs)
    if number_of_files > 20:
        slice = max(2, min(10, int(number_of_files / 60) + 1))
    else:
        slice = 1
    settings = {'slice': slice}
    for obj_index, data in enumerate(objs):
        df = pandas.DataFrame(data)
        if slice > 1:
            df = df.iloc[::slice]
        df['Latitudes_rad'] = np.radians(df['Latitudes_deg'])
        df['Longitudes_rad'] = np.radians(df['Longitudes_deg'])
        df['sin_lat'] = np.sin(df['Latitudes_rad'])
        df['cos_lat'] = np.cos(df['Latitudes_rad'])
        if not admin:
            df = check_no_go(nogos, df, 'begin')
            df = check_no_go(nogos, df, 'end')

        if df.shape[0] < 10:
            continue
        window_med_duration = 50
        paused_after = 30 * slice  # assume a pause if the next data point took 30s to appear
        min_consecutive_points = 10  # exclude sections with breaks within min_consecutive_points points
        min_periods = 3  # to calculate rolling median/sum at least these number of datapoints should not be nans
        # Duration
        duration = np.zeros(df.shape[0])
        duration[1:] = (df['Times'].shift(-1) - df['Times'])[:-1]  # in Seconds
        df['Duration'] = duration
        ## Exclude datapoints after/during a stop
        df.loc[df['Duration'] > paused_after, 'Duration'] = np.nan
        duration_rolling_median = df['Duration'].rolling(
            window=window_med_duration, min_periods=int(0.1 * window_med_duration)
        ).median().to_numpy()
        df.loc[df['Duration'] > 3 * duration_rolling_median, 'Duration'] = np.nan
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
        df.loc[df['Duration'].isna(), 'Altitudes'] = np.nan
        # Distance
        distance = np.zeros(df.shape[0])
        distance[1:] = (np.arccos(
            df['sin_lat'] * df['sin_lat'].shift(-1) +
            df['cos_lat'] * df['cos_lat'].shift(-1) * np.cos(df['Longitudes_rad'] - df['Longitudes_rad'].shift(-1))
        ) * earth_radius)[:-1]
        df['Distance'] = distance
        df.loc[df['Duration'].isna(), 'Distance'] = np.nan
        # Speed
        duration_rolling_sum = df['Duration'].rolling(window=5, min_periods=min_periods).sum().to_numpy()
        distance_rolling_sum = df['Distance'].rolling(window=5, min_periods=min_periods).sum().to_numpy()
        df['Speed_5'] = distance_rolling_sum / duration_rolling_sum * 3600
        duration_rolling_sum = df['Duration'].rolling(window=50, min_periods=min_periods).sum().to_numpy()
        distance_rolling_sum = df['Distance'].rolling(window=50, min_periods=min_periods).sum().to_numpy()
        df['Speed_50'] = distance_rolling_sum / duration_rolling_sum * 3600

        # Add markers for each GPS data point
        positions = df[['Latitudes_deg', 'Longitudes_deg']].values.tolist()

        distance = df['Distance'].sum()
        duration = df['Duration'].sum()
        individual_gps_list[obj_index]['Distance'] = distance
        individual_gps_list[obj_index]['Duration'] = duration
        individual_gps_list[obj_index]['Speed'] = distance / duration * 3600

        all_positions.append(positions)
        all_df = pandas.concat(
            [all_df, df[[
                'Duration', 'Distance', 'Altitudes', 'Altitudes_srtm', 'Speed_5', 'Speed_50', 'Times',
                'Latitudes_deg', 'Longitudes_deg', 'Longitudes_rad', 'sin_lat', 'cos_lat'
            ]][~df['Duration'].isna()]], ignore_index=True
        )

    if all_df.shape[0] == 0:
        return {'gps': None}

    context = {'gps': None, 'gps_positions': all_positions, 'individual_gps_list': individual_gps_list}

    if plot_graphs:
        all_df['Cum_dist'] = all_df['Distance'].cumsum()
        cum_duration = all_df['Duration'].cumsum()
        all_df['Cum_speed'] = all_df['Cum_dist'] / cum_duration * 3600
        alt_rolling_median = all_df['Altitudes'].rolling(window=5).median().to_numpy()
        alt_diff = alt_rolling_median[1:] - alt_rolling_median[:-1]
        alt_rolling_median = all_df['Altitudes_srtm'].rolling(window=5).median().to_numpy()
        alt_srtm_diff = alt_rolling_median[1:] - alt_rolling_median[:-1]
        ax = "Cum_dist"
        ay1 = "Altitudes"
        ay1s = "Altitudes_srtm"
        ay2 = "Speed_5"
        ay3 = "Speed_50"
        ay4 = "Cum_speed"
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay1s], name="SRTM Elevation [m]",
                                 mode='lines', marker=dict(color='#FF9999')))
        fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay1], name="Elevation [m]",
                                 mode='lines', marker=dict(color='#FF0000')))

        covered_time_d = (all_df['Times'].max() - all_df['Times'].min()) / 3600 / 24
        if all_df.shape[0] < 30000:
            prev_time = 0
            min_alt = all_df['Altitudes'].min()
            max_alt = all_df['Altitudes'].max()

            diff_dist = all_df['Cum_dist'].max() / 200.
            diff_sec = all_df.shape[0] / 15
            # make dependent on number of datapoints
            if covered_time_d < 1:
                time_str = '%H:%M'
            elif covered_time_d < 30:
                time_str = '%d %H:%M'
            elif covered_time_d < 365:
                time_str = '%Y-%m-%d'
            else:
                time_str = '%Y-%m-%d'
            for index, row in all_df.iterrows():
                if row['Times'] > prev_time:
                    prev_time = row['Times'] + diff_sec
                    fig.add_annotation(go.layout.Annotation(
                        x=row[ax], y=min_alt,
                        text=datetime.datetime.utcfromtimestamp(row['Times']).strftime(time_str),
                        align='center', showarrow=False, yanchor='bottom', textangle=90, clicktoshow=False,
                        font=dict(color='rgb(125,125,125)', size=10)
                    ))
            font_places = dict(color='rgb(125,125,125)', size=10)
            df10th = all_df.iloc[::10].copy()
            df10th['place_sep'] = np.zeros(df10th.shape[0]) + earth_radius
            df10th['places'] = df10th.apply(lambda _: '', axis=1)
            for index_geo, geoloc in df_geoloc.iterrows():
                sub_sec = ((geoloc['lat_min'] < df10th['Latitudes_deg']) & (df10th['Latitudes_deg'] < geoloc['lat_max']) &
                           (geoloc['lon_min'] < df10th['Longitudes_deg']) & (df10th['Longitudes_deg'] < geoloc['lon_max'])).to_numpy()
                if not sub_sec.any():
                    # All false
                    continue
                separation = np.arccos(
                    df10th.loc[sub_sec, 'sin_lat'] * geoloc['sin_lat'] +
                    df10th.loc[sub_sec, 'cos_lat'] * geoloc['cos_lat'] * np.cos(df10th.loc[sub_sec, 'Longitudes_rad'] - geoloc['Longitudes_rad'])
                ).to_numpy()
                sub_sub_sec = (separation < df10th.loc[sub_sec, 'place_sep']) & (separation < geoloc['radius'] / earth_radius)
                if not sub_sub_sec.all():
                    index_to_false = np.where(sub_sec)[0][~sub_sub_sec]
                    sub_sec[index_to_false] = False
                df10th.loc[sub_sec, 'place_sep'] = separation[sub_sub_sec]
                df10th.loc[sub_sec, 'places'] = geoloc['name']
            df10th.loc[df10th['Distance'].isna(), 'place_sep'] = np.nan
            while df10th['place_sep'].min() < earth_radius:
                index = df10th['place_sep'].idxmin()
                cum_dist = df10th['Cum_dist'][index]
                name = df10th['places'][index]
                if isinstance(cum_dist, pandas.core.series.Series):
                    cum_dist = cum_dist.to_numpy()[0]
                    name = name.to_numpy()[0]
                df10th.loc[((cum_dist - diff_dist) < df10th['Cum_dist']) &
                           (df10th['Cum_dist'] < (cum_dist + diff_dist)), 'place_sep'] = earth_radius
                fig.add_annotation(go.layout.Annotation(
                    x=cum_dist, y=max_alt, text=name,
                    align='center', showarrow=False, yanchor='top', textangle=90, clicktoshow=False,
                    font=font_places
                ))

        fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay2], name="Speed (5 points)", yaxis="y2",
                                 mode='lines', marker=dict(color='#00FF00'), opacity=0.5))
        fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay3], name="Speed (50 points)", yaxis="y2",
                                 mode='lines', marker=dict(color='#00AF00'), opacity=0.7))
        fig.add_trace(go.Scatter(x=all_df[ax], y=all_df[ay4], name="Cumlative Speed", yaxis="y2",
                                 mode='lines', marker=dict(color='#005F00')))
        # fig.data = (fig.data[1], fig.data[2], fig.data[3], fig.data[0]) # also resorts the colors
        fig.update_layout(
            title=(f"{datetime.datetime.fromtimestamp(all_df['Times'].min())} to "
                   f"{datetime.datetime.fromtimestamp(all_df['Times'].max())} : "
                   f"{all_df['Cum_dist'].iloc[-1]:.2f} km, "
                   f"{datetime.timedelta(seconds=cum_duration.iloc[-1])} moving, "
                   f"{all_df['Cum_speed'].iloc[-1]:.2f} km/h, "
                   f"{alt_diff[alt_diff > 0].sum():.0f} m up, {alt_diff[alt_diff < 0].sum():.0f} m down, "
                   f" SRTM: {alt_srtm_diff[alt_srtm_diff > 0].sum():.0f} m up, "
                   f"{alt_srtm_diff[alt_srtm_diff < 0].sum():.0f} m down"
                   ),
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
        context["plot_div"] = plot(fig, output_type="div")
    # map_center and zoom won't work for +/- 180 deg longitude
    max_lat = all_df['Latitudes_deg'].max()
    min_lat = all_df['Latitudes_deg'].min()
    max_lon = all_df['Longitudes_deg'].max()
    min_lon = all_df['Longitudes_deg'].min()
    map_center = [0.5 * (min_lat + max_lat), 0.5 * (min_lon + max_lon)]
    zoom = int(round(-3.2 * log10(max(max_lat - min_lat, (max_lon - min_lon) * sin(radians(map_center[0])))) + 8.9))
    context['center'] = map_center
    context['zoom'] = zoom
    context['min_max_coords'] = [min_lat, max_lat, min_lon, max_lon]
    context['settings'] = settings

    return context


def read_GpsDateRangeForm(request):
    initial_values = {'use_date': True}
    gpsData = None
    coords = None
    form = GpsDateRangeForm(request.GET)
    if form.is_valid():
        begin_date = form.cleaned_data['begin_date']
        end_date = form.cleaned_data['end_date']
        use_date = form.cleaned_data['use_date']
        # initial_values['use_date'] = use_date
        zoom = form.cleaned_data['zoom']
        cenLat = form.cleaned_data['cenLat']
        cenLng = form.cleaned_data['cenLng']
        if begin_date and end_date and use_date:
            initial_values['begin_date'] = begin_date
            initial_values['end_date'] = end_date
            beg_date = create_timezone_object(begin_date)
            end_date = create_timezone_object(end_date) + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
            gpsData = GPSData.objects.filter(end__gte=beg_date, start__lte=end_date).order_by('start')
        if zoom:
            # only if the user selects to use coordinates
            coords = {'zoom': int(zoom), 'cenLat': float(cenLat), 'cenLng': float(cenLng)}
    return form, gpsData, coords, initial_values


def gps_detail_view(request, filename=None):
    # Not executed for plots for Cycle Detail View: see data_detail_view
    form, gpsData, coords, initial_values = read_GpsDateRangeForm(request)
    if not gpsData:
        if filename == "all":
            gpsData = GPSData.objects.all()
            begin_date = GPSData.objects.all().aggregate(Min('start'))['start__min']
            end_date = GPSData.objects.all().aggregate(Max('end'))['end__max']
            initial_values['begin_date'] = begin_date
            initial_values['end_date'] = end_date
        elif filename is not None:
            gpsData = [get_object_or_404(GPSData, pk=filename)]
        else:
            raise ValueError('Parameter unknown.')
        form = GpsDateRangeForm(initial=initial_values)

    context = analyse_gps_data_sets(gpsData, coords, admin=request.user.is_superuser)
    context['gpsdatarangeform'] = form

    return render(request, 'cycle_data/cycle_detail.html', context=context)


def thumbnail_view(request, filename=None):
    photo = get_object_or_404(PhotoData, filename=filename)
    return HttpResponse(photo.thumbnail, content_type='image/jpeg')


class GPSDataListView(generic.ListView):
    context_object_name = 'gps_data_list'  # This is used as variable in cycle_data_list.html
    template_name = 'cycle_data/gps_data_list.html'

    def get_queryset(self):
        # executed when the page is opened
        return GPSData.objects.all()


def add_places_admin_view(request):
    if not request.user.is_superuser:
        return redirect("index")

    if request.GET.items():
        places = GeoLocateData.objects.all()
        photos = PhotoData.objects.all()
        for key, value in request.GET.items():
            if key.startswith('geolocate'):
                key = key[9:]
                [name, lat, lon, radius] = value.split('@')
                for obj in places:
                    if key == obj.identifier:
                        obj.name = name
                        obj.latitude = lat
                        obj.longitude = lon
                        obj.radius = radius
                        obj.save()
                        break
                else:
                    obj = GeoLocateData(name=name, latitude=lat, longitude=lon, radius=radius)
                    obj.save()
            elif key.startswith('photo'):
                key = key[5:]
                [filename, desc, lat, lon] = value.split('@')
                for obj in photos:
                    if key == obj.identifier:
                        obj.filename = filename
                        obj.description = desc
                        obj.latitude = lat
                        obj.longitude = lon
                        obj.save()
                        break
                else:
                    if photoStorage.full_fillname_or_false(filename):
                        obj = PhotoData(
                            filename=filename, description=desc, latitude=lat, longitude=lon,
                            thumbnail=photoStorage.create_thumbnail(filename)
                        )
                        obj.save()
                    else:
                        logger.warning(
                            f"No file found for {filename}, description was: {desc}, lat/lon: {lat:.7f}/{lon:.7f}"
                        )

    gpsData = GPSData.objects.all()
    context = analyse_gps_data_sets(gpsData, coords=None, plot_graphs=False, admin=request.user.is_superuser)

    context['markers'] = GeoLocateData.objects.all()
    context['photos'] = PhotoData.objects.all()
    context['adminView'] = True

    return render(request, 'cycle_data/cycle_detail.html', context=context)
