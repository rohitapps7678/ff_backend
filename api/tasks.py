from celery import shared_task
from django.utils import timezone
from .models import Match

@shared_task
def update_match_status():
    now = timezone.now()
    
    # Running banane ke liye
    started_matches = Match.objects.filter(
        start_time__lte=now,
        is_completed=False,
        status='UPCOMING'  # agar aapke model mein status field hai
    )
    for m in started_matches:
        m.status = 'ONGOING'  # ya jo bhi aapka running status hai
        m.save()

    # Completed banane ke liye
    ended_matches = Match.objects.filter(
        end_time__lte=now,
        is_completed=False,
        status='ONGOING'
    )
    for m in ended_matches:
        m.is_completed = True
        m.status = 'COMPLETED'
        m.save()
        # Optional: yahan prize distribution ya result finalize logic daal sakte ho