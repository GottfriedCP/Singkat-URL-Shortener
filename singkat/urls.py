from django.contrib import admin
from django.urls import path
from . import views

app_name = 'singkat'
urlpatterns = [
    path('', views.home, name='home'),
    path('client-area/', views.client_area, name='client-area'),
    path('client-area/detail/<str:keyword>/', views.detail, name='singkat-detail'),
    path('create-new/', views.create_new_singkat, name='create-new'),
    path('create-new-random/', views.create_new_singkat_rand_keyword, name='create-new-random'),
    #path('finalize/', views.finalize_new_singkat, name='finalize-new'),

    # User registration and auth
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Path to handle requests to preview a Singkat object
    path('<str:keyword>+/', views.click_preview, name='click-preview'),
    # Path to handle clicked singkat URL
    path('<str:keyword>/', views.click, name='click'),
]
