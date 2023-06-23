import abc
import pandas
from plotly.offline import plot
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict

from django.shortcuts import render
from django.core import serializers
from django.db.models import Avg, Max, Min, Sum
from django.views import generic
from django.shortcuts import get_object_or_404

from .models import FahrradRides, FahrradWeeklySummary, FahrradMonthlySummary, FahrradYearlySummary
from .forms import PlotDataForm, PlotDataFormSummary
from my_base import Logging

logger = Logging.setup_logger(__name__)

FIELDS_TO_LABELS = {"date": "Date", "km": "Distance [km]", "seconds": "Duration", "kmh": "Speed [km/h]", "days": "Days"}

def index(request):
    """View function for home page of site."""

    # Find the minimum date:
    start_date = FahrradRides.objects.all().aggregate(Min('date'))["date__min"].strftime('%Y-%m-%d')
    end_date = FahrradRides.objects.all().aggregate(Max('date'))["date__max"].strftime('%Y-%m-%d')
    number_of_days = FahrradRides.objects.all().count()
    number_of_weeks = FahrradWeeklySummary.objects.all().count()
    number_of_months = FahrradMonthlySummary.objects.all().count()
    number_of_years = FahrradYearlySummary.objects.all().count()

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'number_of_days': number_of_days,
        'number_of_weeks': number_of_weeks,
        'number_of_months': number_of_months,
        'number_of_years': number_of_years,
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
        if not self.request.GET:
            # should be a django.http.request.QueryDict instead
            # if self.request.GET is empty (first time, it doesn't use the set initial values in ChoiceField
            self.request.GET = {'x_data': 'date', 'y_data': 'km', 'z_data': 'kmh'}
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
            columns_time = [col for col in columns if col.find("seconds") != -1]
            for col in columns_time:
                # convert string to timedelta object, same as models.TimeInSecondsField.to_datetime_timedelta
                data_frame[col] = pandas.to_timedelta(data_frame[col]) + pandas.to_datetime('1970/01/01')
            return data_frame

    def create_plot(self):

        def add_context_dataset(entry):
            if entry.startswith("km") or entry.startswith("seconds") or entry.startswith("days"):
                return f"{self.context_dataset}{entry}"
            return entry

        x = self.request.GET.get("x_data", "date")
        y = self.request.GET.get("y_data", "km")
        z = self.request.GET.get("z_data", "kmh")
        xl = FIELDS_TO_LABELS[x]
        yl = FIELDS_TO_LABELS[y]
        x = add_context_dataset(x)
        y = add_context_dataset(y)
        plot_args = {"x": x, "y": y, "labels": {x: xl, y: yl}}
        if z != "none":
            zl = FIELDS_TO_LABELS[z]
            z = add_context_dataset(z)
            plot_args["color"] = z
            plot_args["labels"][z] = zl

        if self.data_frame is not None:
            fig = px.scatter(self.data_frame, **plot_args)
            # fig.update_yaxes(autorange="reversed")
            return plot(fig, output_type="div")


class DataListView(BaseDataListView):
    # executed when server is initialised
    #model = FahrradRides
    context_dataset = "day"
    paginate_by = 200

    def get_queryset(self):
        # executed when the page is opened
        return FahrradRides.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plotdataform"] = PlotDataForm(self.request.GET)
        context.update(self.create_extra_plots())

        return context

    def add_data_serialized_models(self, serialized_models):
        pass

    def create_extra_plots(self) -> Dict:

        if self.data_frame is not None:
            ax = "date"
            ay1 = "totalkmh"
            ay2 = "totalkm"
            ay3 = "totalseconds"
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


            bx = "date"
            by1 = "diffkm"
            by2 = "diffsec"
            self.data_frame[by1] = self.data_frame["totalkm"] - self.data_frame["culmkm"]
            self.data_frame[by2] = pandas.to_numeric(
                self.data_frame["totalseconds"] - self.data_frame["culmseconds"]
            ) * 1E-9        # From mu sec to seconds

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

            plot_dict = {
                "plot_total_div": plot(fig_total, output_type="div"),
                "plot_diff_div": plot(fig_diff, output_type="div")
            }

            return plot_dict

        return {}


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
    context_dataset = "week"
    paginate_by = 100

    def get_queryset(self):
        return FahrradWeeklySummary.objects.all()


class DataMListView(DataSummaryView):
    context_dataset = "month"

    def get_queryset(self):
        return FahrradMonthlySummary.objects.all()


class DataYListView(DataSummaryView):
    context_dataset = "year"

    def get_queryset(self):
        return FahrradYearlySummary.objects.all()


def data_detail_view(request, date_wmy=None, entryid=None):
    if entryid is not None:
        cycleThisData = get_object_or_404(FahrradRides, pk=entryid)
        dataType = "d"
    elif date_wmy is not None:
        dataType = date_wmy[0]
        if date_wmy[0] == "w":
            cycleThisData = get_object_or_404(FahrradWeeklySummary, pk=date_wmy[1:])
        elif date_wmy[0] == "m":
            cycleThisData = get_object_or_404(FahrradMonthlySummary, pk=date_wmy[1:])
        elif date_wmy[0] == "y":
            cycleThisData = get_object_or_404(FahrradYearlySummary, pk=date_wmy[1:])
        else:
            raise ValueError('date_wmy has an unknown start: '+date_wmy)
    else:
        raise ValueError('Both date_wmy and entryid are none.')

    return render(request, 'cycle_data/cycle_detail.html', context={'cycle': cycleThisData, 'dataType': dataType})
