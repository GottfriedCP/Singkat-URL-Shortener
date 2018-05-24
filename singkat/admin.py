from django.contrib import admin
from .models import Singkat, Clicker, Click, ClickDetail, RandomKeywordId

class SingkatAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'target', 'title', 'owner', 'created_at')
    list_filter = ('created_at', 'owner')
    ordering = ('-created_at', 'keyword')

class ClickerAdmin(admin.ModelAdmin):
    list_display = ('ip', 'city', 'country', 'continent', 'latitude', 'longitude')

# Register your models here.
admin.site.register(Singkat, SingkatAdmin)
admin.site.register(Clicker, ClickerAdmin)
admin.site.register(RandomKeywordId)
#admin.site.register(Click, ClickAdmin)
#admin.site.register(ClickDetail)