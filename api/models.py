from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    referral_code = models.CharField(max_length=12, unique=True, blank=True)
    upi_id = models.CharField(max_length=100, blank=True, null=True)  # user's preferred UPI for faster withdrawal

    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')
    
    # Stats
    total_kills = models.IntegerField(default=0)
    total_wins = models.IntegerField(default=0)
    total_matches = models.IntegerField(default=0)
    
    upi_id = models.CharField(max_length=100, blank=True, null=True)   # for faster withdrawals
    
    def __str__(self):
        return f"{self.user.username} - ₹{self.wallet_balance}"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4()).replace('-', '')[:8].upper()
        super().save(*args, **kwargs)


class Match(models.Model):
    MODE_CHOICES = [
    ('BR_SOLO',  'Battle Royale — Solo'),
    ('BR_DUO',   'Battle Royale — Duo'),
    ('BR_SQUAD', 'Battle Royale — Squad'),
    ('CS_SOLO',  'Clash Squad — Solo'),
    ('CS_DUO',   'Clash Squad — Duo'),
    ('CS_SQUAD', 'Clash Squad — Squad'),
    ('LW_1V1',   'Lone Wolf 1v1'),
    ('LW_2V2',   'Lone Wolf 2v2'),
]
    title = models.CharField(max_length=150)
    rules = models.TextField(blank=True, default="Standard BGMI rules apply. No cheating, etc.")
    image = models.ImageField(upload_to='match_banners/', null=True, blank=True)
    game_mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    entry_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    prize_pool = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    per_kill = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField(null=True, blank=True)          # ← added
    
    room_id = models.CharField(max_length=50, blank=True, null=True)
    room_password = models.CharField(max_length=50, blank=True, null=True)
    
    is_completed = models.BooleanField(default=False)
    youtube_link = models.URLField(blank=True, null=True)
    max_players = models.IntegerField(default=52)

    def __str__(self):
        return self.title


class MatchParticipant(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    kills = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    is_winner = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('match', 'user')


class ScreenshotProof(models.Model):
    participant = models.ForeignKey(MatchParticipant, on_delete=models.CASCADE, related_name='deposit_proofs')
    image = models.ImageField(upload_to='proof_screenshots/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"Proof - {self.participant.user.username}"


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('ADD', 'Deposit'),
        ('WITHDRAW', 'Withdrawal'),
        ('MATCH_FEE', 'Match Entry Fee'),
        ('WINNING', 'Match Winning'),
        ('AD_REWARD', 'Ad Earning'),
        ('SPIN', 'Spin Reward'),
        ('REFERRAL', 'Referral Bonus')
    ]
    STATUS_CHOICES = [('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    screenshot = models.ImageField(upload_to='transactions/%Y/%m/%d/', null=True, blank=True)  # for manual deposit proof
    upi_id_used = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='processed_transactions')


class DailySpin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    spins_done = models.IntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')

# Add these fields / new models

# In Profile model (optional but useful)
# New model for manual deposits
class DepositRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    upi_used = models.CharField(max_length=100, blank=True)          # which UPI user paid to
    transaction_ref = models.CharField(max_length=100, blank=True)   # UTR / ref number
    screenshot = models.ImageField(upload_to='deposit_proofs/%Y/%m/%d/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='processed_deposits')
    
    def __str__(self):
        return f"Deposit ₹{self.amount} - {self.user.username} ({self.status})"

# New model for match result proofs (screenshot after match)
class MatchProof(models.Model):
    participant = models.ForeignKey(MatchParticipant, on_delete=models.CASCADE, related_name='match_proofs')
    screenshot = models.ImageField(upload_to='match_proofs/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Proof by {self.participant.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()  # in case user is updated

class AdminUPI(models.Model):
    upi_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.upi_id