# games/management/commands/update_match_status.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Match  # apne app ka name 'games' assume kiya hai

class Command(BaseCommand):
    help = 'Automatically update match status: ongoing if started, completed if ended'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        updated = 0

        # 1. Jo matches abhi start ho chuke hain (start_time aa gaya)
        started_matches = Match.objects.filter(
            start_time__lte=now,
            is_completed=False
            # Agar aapke model mein status field hai to yahan add kar sakte ho:
            # status='UPCOMING'
        )

        for match in started_matches:
            match.is_completed = False  # ya status = 'ONGOING' agar field hai
            # Optional: yahan room_id/password show karne ka logic daal sakte ho
            match.save()
            updated += 1

        # 2. Jo matches end ho chuke hain (end_time aa gaya)
        ended_matches = Match.objects.filter(
            end_time__lte=now,
            is_completed=False
        )

        for match in ended_matches:
            match.is_completed = True
            # Optional: yahan prize distribution, winner declare, etc. logic daal sakte ho
            match.save()
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully updated {updated} matches at {now}'
        ))