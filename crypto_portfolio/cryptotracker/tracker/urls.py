from django.urls import path
from . import views
from django.contrib.auth.views import LoginView
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('accounts/login/', LoginView.as_view(template_name='tracker/login.html'), name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('add-money/', views.add_money, name='add_money'),
    path('buy/', views.buy_crypto, name='buy_crypto'),
    path('sell/', views.sell_crypto, name='sell_crypto'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('watchlist/', views.watchlist, name='watchlist'),
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('add-to-watchlist/<str:uuid>/', views.add_to_watchlist, name='add_to_watchlist'),
    path('remove-from-watchlist/<str:uuid>/', views.remove_from_watchlist, name='remove_from_watchlist'),
    path('toggle-currency/', views.toggle_currency, name='toggle_currency'),
]