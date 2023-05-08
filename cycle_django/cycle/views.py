from django.shortcuts import render
from django.db.models import Avg, Max, Min, Sum
from .models import FahrradRides, FahrradWeeklySummary, FahrradMonthlySummary, FahrradYearlySummary
from django.views import generic
from django.shortcuts import get_object_or_404


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

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        # Create any data and add it to the context
        context['dataset'] = self.context_dataset
        return context


class DataListView(BaseDataListView):
    # executed when server is initialised
    #model = FahrradRides
    context_dataset = "day"
    paginate_by = 200

    def get_queryset(self):
        # executed when the page is opened
        return FahrradRides.objects.all()


class DataWListView(BaseDataListView):
    context_dataset = "week"
    paginate_by = 100

    def get_queryset(self):
        return FahrradWeeklySummary.objects.all()


class DataMListView(BaseDataListView):
    context_dataset = "month"

    def get_queryset(self):
        return FahrradMonthlySummary.objects.all()


class DataYListView(BaseDataListView):
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
    return render(request, 'cycle_data/cycle_detail.html', context={'cycle': cycleThisData, 'dataType':dataType})
