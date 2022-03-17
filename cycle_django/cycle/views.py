from django.shortcuts import render
from django.db.models import Avg, Max, Min, Sum
from .models import FahrradRides, FahrradWeeklySummary, FahrradMonthlySummary, FahrradYearlySummary

def index(request):
    """View function for home page of site."""

    # Find the minimum date:
    start_date = FahrradRides.objects.all().aggregate(Min('date'))
    end_date = FahrradRides.objects.all().aggregate(Max('date'))
    # {'date__min': datetime.date(2008, 6, 6)}
    number_of_days = FahrradRides.objects.all().count()
    number_of_weeks = FahrradWeeklySummary.objects.all().count()
    number_of_months = FahrradMonthlySummary.objects.all().count()
    number_of_years = FahrradYearlySummary.objects.all().count()
    # Available books (status = 'a')
    #num_instances_available = BookInstance.objects.filter(status__exact='a').count()

    # The 'all()' is implied by default.
    #num_authors = Author.objects.count()

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

from django.views import generic

class DataListView(generic.ListView):
    model = FahrradRides
    context_object_name = 'cycle_list'
    template_name = 'cycle/cycle_list.html'   # https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Generic_views