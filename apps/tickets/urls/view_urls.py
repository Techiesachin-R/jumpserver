# coding:utf-8
#

from django.urls import path

from .. import views

app_name = 'tickets'

urlpatterns = [
    path('direct-approve/', views.TicketDirectApproveView.as_view(), name='direct-approve'),
]
