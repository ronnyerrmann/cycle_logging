from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('cycle_data', views.DataListView.as_view(), name='cycle_data'),
    path('cycle_dataw', views.DataWListView.as_view(), name='cycle_data_w'),
    path('cycle_datam', views.DataMListView.as_view(), name='cycle_data_m'),
    path('cycle_datay', views.DataYListView.as_view(), name='cycle_data_y'),
    path('cycle_data/<int:entryid>', views.data_detail_view, name='cycle-detail'),
    re_path(r'^cycle_data/(?P<date_wmy>[w,m,y]\d{4}-\d{2}-\d{2})/$', views.data_detail_view, name='cycle-detail'),
]