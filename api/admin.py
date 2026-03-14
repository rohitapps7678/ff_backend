from django.contrib import admin
from .models import Profile, Match, MatchParticipant, Transaction

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('title', 'game_mode', 'entry_fee', 'is_completed')
    list_editable = ('is_completed',)

admin.site.register(Profile)
admin.site.register(MatchParticipant)
admin.site.register(Transaction)