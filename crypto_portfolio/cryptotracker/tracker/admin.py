from django.contrib import admin
from .models import Profile,Transaction,WatchlistItem
# Register your models here.
admin.site.register(Profile)
admin.site.register(Transaction)
admin.site.register(WatchlistItem)
