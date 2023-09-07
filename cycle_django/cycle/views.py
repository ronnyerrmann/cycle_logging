import ast
import abc
import copy
from math import log10, radians, sin, cos, acos
import numpy
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
from .forms import PlotDataForm, PlotDataFormSummary
from my_base import Logging

logger = Logging.setup_logger(__name__)

FIELDS_TO_LABELS = {"date": "Date", "distance": "Distance [km]", "duration": "Duration", "speed": "Speed [km/h]", "days": "Days"}


def update_database(func):
    """ Unused currently, as I put the code into PreDatabaseMiddleware"""
    def wrapper(*args, **kwargs):
        # Code to be executed before the decorated function
        #from .backup import Backup
        #Backup().load_backup()

        # Call the decorated function
        result = func(*args, **kwargs)

        # Code to be executed after the decorated function

        return result

    return wrapper


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
    context_object_name = 'cycle_data_list'     # This is used as variable in cycle_data_list.html
    template_name = 'cycle_data/cycle_data_list.html'   # https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Generic_views
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
                data_frame[col+"_td"] = pandas.to_timedelta(data_frame[col])
                data_frame[col] = data_frame[col+"_td"] + pandas.to_datetime('1970/01/01')
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
    #model = CycleRides
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
        CycleWeeklySummary.update_fields()
        return CycleWeeklySummary.objects.all()


class DataMListView(DataSummaryView):
    context_dataset = "month"

    def get_queryset(self):
        CycleMonthlySummary.update_fields()
        return CycleMonthlySummary.objects.all()


class DataYListView(DataSummaryView):
    context_dataset = "year"

    def get_queryset(self):
        CycleYearlySummary.update_fields()
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
        range_dist = int(max(data)-min(data))
        fig_hist_dist = go.Figure()
        fig_hist_dist.add_trace(go.Histogram(x=data, nbinsx=int(range_dist/2), name="Distance (4km bins)"))
        fig_hist_dist.add_trace(go.Histogram(x=data, nbinsx=range_dist*2, name="Distance (1km bins)"))
        fig_hist_dist.add_trace(go.Histogram(x=data, nbinsx=range_dist*10, name="Distance (200m bins)"))
        fig_hist_dist.update_layout(
            # Overlay both histograms
            barmode='overlay',
            xaxis=dict(title="Distance [km]"),
            yaxis=dict(title="Number of occurrences of Distance values"),
        )
        data = self.data_frame["duration_td"].dt.total_seconds()/60
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
        frac_km, int_km = numpy.modf(self.data_frame["distance"])
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
            raise ValueError('date_wmy has an unknown start: '+date_wmy)
    else:
        raise ValueError('Both date_wmy and entryid are none.')

    context = {'cycle': cycleThisData, 'dataType': dataType}
    gps_objs = cycleThisData.get_gps_objs()
    gps_context = analyse_gps_data_sets(gps_objs)
    context.update(gps_context)

    return render(request, 'cycle_data/cycle_detail.html', context=context)


def analyse_gps_data_sets(objs: List[GPSData]) -> Dict:
    """ Be careful to apply sin/cos only on radians!
    """
    if not objs:
        return {}
    def check_no_go(nogos, lats, lons, index):
        for ii in range(len(lats)):
            lat = radians(lats[index])      # radians
            lon = radians(lons[index])      # radians
            for nogo in nogos:
                # Followed https://www.geeksforgeeks.org/program-distance-two-points-earth/
                if acos((sin(lat) * nogo[0]) + cos(lat) * nogo[1] * cos(lon - nogo[2])) < nogo[3]:
                    del lats[index]
                    del lons[index]
                    # logger.info(f"Deleted {ii} because of {nogo}")
                    break
                # else:
                #    logger.info(f"not del {ii} for {nogo}")
            else:
                # logger.info(f"stopped deleting")
                break

    all_positions = []
    max_lat = -90
    min_lat = 90
    max_lon = -180
    min_lon = 180
    earth_radius = 6371.0
    nogos = []
    for nogo in NoGoAreas.objects.all():
        lat = radians(nogo.latitude)
        lon = radians(nogo.longitude)
        nogos.append([sin(lat), cos(lat), lon, nogo.radius / earth_radius])
    number_of_files = len(objs)
    slice_ending = 'th'
    if number_of_files > 10:
        slice = max(2, min(10, int(number_of_files / 30) + 1))
        if slice == 2:
            slice_ending = 'nd'
        elif slice == 3:
            slice_ending = 'rd'
    else:
        slice = 1
    settings = {'slice': slice, 'slice_ending': slice_ending}
    for obj in objs:
        lats = ast.literal_eval(obj.latitudes)      # degrees
        lons = ast.literal_eval(obj.longitudes)     # degrees
        if slice > 1:
            lats = lats[::slice]
            lons = lons[::slice]
        check_no_go(nogos, lats, lons, 0)
        check_no_go(nogos, lats, lons, -1)

        number_data_points = len(lats)

        max_lat = max(max_lat, max(lats))
        min_lat = min(min_lat, min(lats))
        max_lon = max(max_lon, max(lons))
        min_lon = min(min_lon, min(lons))

        # Add markers for each GPS data point
        positions = [[]] * number_data_points
        for ii in range(number_data_points):
            positions[ii] = [lats[ii], lons[ii]]
        all_positions.append(positions)
    map_center = [0.5 * (min_lat + max_lat), 0.5 * (min_lon + max_lon)]
    zoom = int(round(-3.2 * log10(max(max_lat - min_lat, (max_lon-min_lon)*sin(radians(map_center[0])))) + 8.9))
    context = {'gps': None, 'gps_positions': all_positions, 'center': map_center, 'zoom': zoom, 'settings': settings}

    return context


def gps_detail_view(request, filename=None):
    if filename == "all":
        gpsData = GPSData.objects.all()
    elif filename is not None:
        gpsData = [get_object_or_404(GPSData, pk=filename)]
    else:
        raise ValueError('Parameter unknown.')
    context = analyse_gps_data_sets(gpsData)

    return render(request, 'cycle_data/cycle_detail.html', context=context)


class GPSDataListView(generic.ListView):
    context_object_name = 'gps_data_list'     # This is used as variable in cycle_data_list.html
    template_name = 'cycle_data/gps_data_list.html'

    def get_queryset(self):
        # executed when the page is opened
        return GPSData.objects.all()
