# views.py
import random
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import date
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from rest_framework.parsers import MultiPartParser, FormParser

from .models import (
    Profile, Match, MatchParticipant, Transaction, DailySpin, DepositRequest, MatchProof, AdminUPI
)
from .serializers import (
    ProfileSerializer, MatchSerializer,
    TransactionSerializer, MatchParticipantSerializer, DepositRequestSerializer, AdminUPISerializer
)

from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        referral_code = request.data.get('referral_code', '')

        if not username or not password:
            return Response({"error": "Username aur password required hai"}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken hai"}, status=400)

        user = User.objects.create_user(
            username=username, email=email, password=password
        )

        # Referral handle karo
        if referral_code:
            try:
                referrer = Profile.objects.get(referral_code=referral_code)
                user.profile.referred_by = referrer
                user.profile.save()
                # Referrer ko bonus do
                referrer.wallet_balance += Decimal('10.00')
                referrer.save()
                Transaction.objects.create(
                    user=referrer.user,
                    amount=Decimal('10.00'),
                    transaction_type='REFERRAL',
                    status='SUCCESS'
                )
            except Profile.DoesNotExist:
                pass  # Invalid referral code — ignore karo

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key}, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print("AUTH HEADER:", request.headers.get('Authorization'))  # ← add karo
        print("USER:", request.user)
        print("=== RAW HEADERS DEBUG ===")
        print("All headers:", dict(request.headers))           # ← yeh sab headers dikha dega
        print("Authorization header raw:", request.META.get('HTTP_AUTHORIZATION'))
        print("Authorization (get):", request.headers.get('Authorization'))
        print("Current user:", request.user)
        print("Is authenticated?", request.user.is_authenticated)
        print("Auth header exists?", 'Authorization' in request.headers)
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"error": "Wrong username ya password"}, status=401)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({"message": "Logged out"})
# ────────────────────────────────────────────────
#  PERMISSIONS
# ────────────────────────────────────────────────

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


# ────────────────────────────────────────────────
#  PROFILE
# ────────────────────────────────────────────────

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        print("AUTH HEADER:", request.headers.get('Authorization'))  # ← add karo
        print("USER:", request.user)
        print("=== RAW HEADERS DEBUG ===")
        print("All headers:", dict(request.headers))           # ← yeh sab headers dikha dega
        print("Authorization header raw:", request.META.get('HTTP_AUTHORIZATION'))
        print("Authorization (get):", request.headers.get('Authorization'))
        print("Current user:", request.user)
        print("Is authenticated?", request.user.is_authenticated)
        print("Auth header exists?", 'Authorization' in request.headers)
        profile = request.user.profile
        serializer = ProfileSerializer(profile)
        return Response({
            **serializer.data,
            "user_id": request.user.id,
            "email": request.user.email,
        })


class UpdateProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        profile = request.user.profile
        allowed_fields = ['mobile', 'upi_id']  # agar model mein upi_id add kiya hai

        updated = False
        for field in allowed_fields:
            if field in request.data:
                setattr(profile, field, request.data[field])
                updated = True

        if updated:
            profile.save()

        return Response(ProfileSerializer(profile).data)


# ────────────────────────────────────────────────
#  MATCH - PUBLIC
# ────────────────────────────────────────────────

class UpcomingMatchesList(generics.ListAPIView):
    # Sirf wahi matches jo abhi start nahi hue
    queryset = Match.objects.filter(
        is_completed=False,
        start_time__gt=timezone.now()   # ← start_time future mein hona chahiye
    ).order_by('start_time')
    serializer_class = MatchSerializer
    permission_classes = [permissions.AllowAny]


class MatchDetail(generics.RetrieveAPIView):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [permissions.AllowAny]


class JoinMatchView(APIView):
    def post(self, request):
        match_id = request.data.get("match_id")  # ✅ yaha add karo

        if not match_id:
            return Response({"error": "match_id required"}, status=400)

        match = get_object_or_404(Match, id=match_id)

        # ← Yeh add karo — start ke baad join band
        if timezone.now() >= match.start_time:
            return Response({"error": "Match shuru ho chuka hai, ab join nahi kar sakte"}, status=400)

        if match.is_completed:
            return Response({"error": "Match already over"}, status=410)

        current_participants = match.participants.count()
        if current_participants >= match.max_players:
            return Response({"error": "Match full ho gaya hai"}, status=400)

        if MatchParticipant.objects.filter(match=match, user=request.user).exists():
            return Response({"error": "Aap already join kar chuke hain"}, status=400)

        profile = request.user.profile

        if profile.wallet_balance < match.entry_fee:
            return Response({
                "error": "Insufficient balance",
                "required": float(match.entry_fee),
                "available": float(profile.wallet_balance)
            }, status=400)

        profile.wallet_balance -= match.entry_fee
        profile.total_matches += 1
        profile.save(update_fields=['wallet_balance', 'total_matches'])

        participant = MatchParticipant.objects.create(match=match, user=request.user)

        Transaction.objects.create(
            user=request.user,
            amount=match.entry_fee,
            transaction_type='MATCH_FEE',
            status='SUCCESS'
        )

        return Response({
            "message": "Match join ho gaya!",
            "entry_fee_paid": float(match.entry_fee),
            "new_balance": float(profile.wallet_balance),
            "participants_now": current_participants + 1
        })


class MatchRoomDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        match = get_object_or_404(Match, pk=pk)

        if not MatchParticipant.objects.filter(match=match, user=request.user).exists():
            return Response({"error": "Aap is match mein nahi hain"}, status=403)

        now = timezone.now()

        if match.is_completed:
            return Response({
                "status": "completed",
                "youtube_link": match.youtube_link or "",
                "message": "Match khatam ho chuka hai"
            })

        if now < match.start_time - timezone.timedelta(minutes=30):
            return Response({
                "status": "too_early",
                "message": "Room details sirf 30 minute pehle dikhenge"
            })

        return Response({
            "status": "ready",
            "room_id": match.room_id,
            "room_password": match.room_password,
            "start_time": match.start_time.isoformat()
        })


# ────────────────────────────────────────────────
#  MATCH HISTORY + RESULTS
# ────────────────────────────────────────────────

class MyMatchesHistory(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        parts = MatchParticipant.objects.filter(user=request.user)\
            .select_related('match')\
            .order_by('-joined_at')

        data = []
        for p in parts:
            data.append({
                "match_id": p.match.id,
                "title": p.match.title,
                "mode": p.match.game_mode,
                "entry_fee": float(p.match.entry_fee),
                "kills": p.kills,
                "rank": p.rank,
                "won": p.is_winner,
                "date": p.joined_at.date().isoformat(),
                "youtube": p.match.youtube_link if p.match.is_completed else None
            })

        return Response(data)


class PublicMatchResults(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        if not match.is_completed:
            return Response({"error": "Results abhi nahi aaye"}, status=404)

        participants = match.participants.order_by('rank')
        ser = MatchParticipantSerializer(participants, many=True)

        return Response({
            "title": match.title,
            "mode": match.game_mode,
            "prize_pool": float(match.prize_pool),
            "results": ser.data,
            "youtube_link": match.youtube_link or ""
        })


# ────────────────────────────────────────────────
#  SPIN + ADS
# ────────────────────────────────────────────────

class SpinAndWin(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        MAX_SPINS = 5
        today = timezone.now().date()
        record, _ = DailySpin.objects.get_or_create(user=request.user, date=today)

        if record.spins_done >= MAX_SPINS:
            return Response({"error": f"Aaj ke {MAX_SPINS} spins khatam ho gaye"}, status=429)

        rewards = [0, 0, 1, 2, 3, 5, 10, 15]
        win = Decimal(random.choice(rewards))

        with transaction.atomic():
            record.spins_done += 1
            record.save()

            profile = request.user.profile

            if win > 0:
                profile.wallet_balance += win
                profile.save()

                Transaction.objects.create(
                    user=request.user,
                    amount=win,
                    transaction_type='SPIN',
                    status='SUCCESS'
                )

        return Response({
            "won": float(win),
            "spins_left": MAX_SPINS - record.spins_done,
            "balance": float(profile.wallet_balance)
        })


class WatchAdAndEarn(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Real mein: ad verification karna padega
        reward = Decimal('2.00')

        with transaction.atomic():
            profile = request.user.profile
            profile.wallet_balance += reward
            profile.save()

            Transaction.objects.create(
                user=request.user,
                amount=reward,
                transaction_type='AD_REWARD',
                status='SUCCESS'
            )

        return Response({
            "message": f"₹{reward} add ho gaya",
            "new_balance": float(profile.wallet_balance)
        })


# ────────────────────────────────────────────────
#  WITHDRAWAL REQUEST
# ────────────────────────────────────────────────

class CreateWithdrawalRequest(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            amount = Decimal(request.data['amount'])
        except:
            return Response({"error": "Amount number mein daaliye"}, status=400)

        if amount < 50:
            return Response({"error": "Minimum withdrawal ₹50 hai"}, status=400)

        profile = request.user.profile

        if profile.wallet_balance < amount:
            return Response({"error": "Itna balance nahi hai"}, status=400)

        profile.wallet_balance -= amount
        profile.save()

        tx = Transaction.objects.create(
            user=request.user,
            amount=amount,
            transaction_type='WITHDRAW',
            status='PENDING',
            note=request.data.get('upi_id', '') or request.data.get('bank_details', '')
        )

        return Response({
            "message": "Withdrawal request bhej diya gaya",
            "request_id": tx.id,
            "amount": float(amount),
            "status": "pending"
        })


# ────────────────────────────────────────────────
#  LEADERBOARD
# ────────────────────────────────────────────────

class Leaderboard(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        top = Profile.objects.order_by('-total_wins', '-total_kills')[:30]

        return Response([{
            "name": p.user.username,
            "wins": p.total_wins,
            "kills": p.total_kills,
            "matches": p.total_matches
        } for p in top])


# ────────────────────────────────────────────────
#  ADMIN SECTION
# ────────────────────────────────────────────────

class AdminAllMatches(generics.ListCreateAPIView):
    queryset = Match.objects.all().order_by('-start_time')
    serializer_class = MatchSerializer
    permission_classes = [IsAdminUser]


class AdminMatchDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsAdminUser]


class AdminSubmitResults(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        match = get_object_or_404(Match, pk=pk)

        if match.is_completed:
            return Response({"error": "Results already submitted"}, status=400)

        results = request.data.get('results', [])

        if not results:
            return Response({"error": "Koi result data nahi diya"}, status=400)

        for r in results:
            try:
                participant = MatchParticipant.objects.get(
                    match=match,
                    user__id=r['user_id']
                )
            except MatchParticipant.DoesNotExist:
                continue

            participant.kills = int(r.get('kills', 0))
            participant.rank = int(r.get('rank', 99))
            participant.is_winner = bool(r.get('is_winner', False))
            participant.save()

            profile = participant.user.profile
            profile.total_kills += participant.kills
            profile.total_matches += 1

            prize = Decimal('0')

            if participant.is_winner:
                profile.total_wins += 1
                prize += match.prize_pool

            prize += match.per_kill * Decimal(participant.kills)

            if prize > 0:
                profile.wallet_balance += prize
                Transaction.objects.create(
                    user=profile.user,
                    amount=prize,
                    transaction_type='WINNING',
                    status='SUCCESS'
                )

            profile.save()

        match.is_completed = True
        match.youtube_link = request.data.get('youtube_link', '')
        match.save()

        return Response({"message": "Results save + prize distribute ho gaya"})

# ────────────────────────────────────────────────
#  MANUAL DEPOSIT + PROOF UPLOAD
# ────────────────────────────────────────────────

class DepositUPIInfo(APIView):
    """
    User ko admin ke UPI IDs dikhane ke liye (hardcoded ya future me setting se)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        upi_list = [
            "yourgame@upi",
            "rohitgaming@okaxis",
            "support@phonepe",
        ]
        return Response({
            "message": "In UPI IDs par payment karein aur screenshot upload karein",
            "upi_ids": upi_list
        })


class CreateDepositRequest(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def post(self, request):
        try:
            amount = Decimal(request.data.get('amount'))
            if amount <= 0:
                raise ValueError
        except:
            return Response({"error": "Valid amount daaliye (> 0)"}, status=400)

        deposit = DepositRequest.objects.create(
            user=request.user,
            amount=amount,
            upi_used=request.data.get('upi_used', ''),
            transaction_ref=request.data.get('transaction_ref', ''),
        )

        if 'screenshot' in request.FILES:
            deposit.screenshot = request.FILES['screenshot']
            deposit.save()

        return Response({
            "message": "Deposit request submit ho gayi",
            "deposit_id": deposit.id,
            "amount": float(amount),
            "status": deposit.status
        })


class UploadMatchProof(APIView):
    def post(self, request, match_id):
        match = get_object_or_404(Match, id=match_id)
        now   = timezone.now()

        # ✅ Allow upload if end_time passed OR is_completed
        match_ended = match.is_completed or (match.end_time and now >= match.end_time)
        if not match_ended:
            return Response({"error": "Match abhi complete nahi hua"}, status=403)

        # Also accept screenshot_url (Cloudinary URL from Flutter)
        screenshot_url = request.data.get('screenshot_url', '')
        participant = get_object_or_404(
            MatchParticipant,
            match=match,
            user=request.user
        )

        if 'screenshot' not in request.FILES:
            return Response({"error": "Screenshot file chahiye"}, status=400)

        proof = MatchProof.objects.create(
            participant=participant,
            screenshot=request.FILES['screenshot'],
            note=request.data.get('note', '')
        )

        return Response({
            "message": "Proof upload ho gaya",
            "proof_id": proof.id
        })


# ────────────────────────────────────────────────
#  ADMIN - DEPOSIT APPROVAL
# ────────────────────────────────────────────────

class AdminDepositList(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = DepositRequestSerializer

    def get_queryset(self):
        return DepositRequest.objects.filter(status='PENDING').order_by('-requested_at')


class AdminProcessDeposit(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, deposit_id):
        deposit = get_object_or_404(DepositRequest, id=deposit_id, status='PENDING')

        action = request.data.get('action')  # 'approve' or 'reject'

        if action == 'approve':
            deposit.status = 'APPROVED'
            deposit.processed_by = request.user
            deposit.processed_at = timezone.now()
            deposit.save()

            profile = deposit.user.profile
            profile.wallet_balance += deposit.amount
            profile.save()

            Transaction.objects.create(
                user=deposit.user,
                amount=deposit.amount,
                transaction_type='ADD',
                status='SUCCESS',
                payment_id=f"manual_{deposit.id}",
                note=f"Approved by {request.user.username}"
            )

            return Response({"message": "Deposit approved → wallet updated"})

        elif action == 'reject':
            deposit.status = 'REJECTED'
            deposit.processed_by = request.user
            deposit.processed_at = timezone.now()
            deposit.save()
            return Response({"message": "Deposit rejected"})

        return Response({"error": "action 'approve' ya 'reject' bhejiye"}, status=400)

class AdminDashboardStats(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = date.today()
        
        stats = {
            "today_matches": Match.objects.filter(
                start_time__date=today
            ).count(),
            "pending_deposits": DepositRequest.objects.filter(
                status='PENDING'
            ).count(),
            "pending_withdrawals": Transaction.objects.filter(
                transaction_type='WITHDRAW',
                status='PENDING'
            ).count(),
        }
        return Response(stats)

class RecentTransactions(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Last 10 transactions, newest first
        transactions = Transaction.objects.select_related('user__profile').order_by('-created_at')[:10]
        
        data = []
        for t in transactions:
            data.append({
                "id": t.id,
                "transaction_type": t.transaction_type,
                "amount": str(t.amount),
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "username": t.user.username,
            })
        
        return Response(data)

class AdminPendingWithdrawals(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TransactionSerializer  # or make a WithdrawalRequestSerializer if you have separate model

    def get_queryset(self):
        return Transaction.objects.filter(
            transaction_type='WITHDRAW',
            status='PENDING'
        ).select_related('user__profile').order_by('-created_at')

class AdminProcessWithdrawal(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        tx = get_object_or_404(Transaction, pk=pk, transaction_type='WITHDRAW', status='PENDING')
        action = request.data.get('action')

        if action == 'approve':
            tx.status = 'APPROVED'
            tx.processed_by = request.user
            tx.save()
            # Here you can trigger real payment (manual for now)
            return Response({"message": "Withdrawal approved"})

        elif action == 'reject':
            tx.status = 'REJECTED'
            tx.save()
            # Refund wallet
            profile = tx.user.profile
            profile.wallet_balance += tx.amount
            profile.save()
            return Response({"message": "Withdrawal rejected & amount refunded"})
        
        return Response({"error": "Invalid action"}, status=400)

class AdminUPIListCreate(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        upis = AdminUPI.objects.filter(is_active=True).order_by('-created_at')
        serializer = AdminUPISerializer(upis, many=True)
        return Response(serializer.data)

    def post(self, request):
        upi_id = request.data.get('upi_id')
        if not upi_id:
            return Response({"error": "UPI ID required"}, status=400)
        
        if AdminUPI.objects.filter(upi_id=upi_id).exists():
            return Response({"error": "This UPI ID already exists"}, status=400)
        
        upi = AdminUPI.objects.create(upi_id=upi_id)
        serializer = AdminUPISerializer(upi)
        return Response(serializer.data, status=201)


class AdminUPIDelete(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        try:
            upi = AdminUPI.objects.get(pk=pk)
            upi.delete()  # or set is_active=False if soft delete
            return Response({"message": "UPI removed"})
        except AdminUPI.DoesNotExist:
            return Response({"error": "UPI not found"}, status=404)

class MatchParticipantsList(APIView):
    permission_classes = [AllowAny]  # change to IsAuthenticated if needed

    def get(self, request, pk):
        try:
            match = Match.objects.get(pk=pk)
        except Match.DoesNotExist:
            return Response({"error": "Match not found"}, status=404)

        participants = MatchParticipant.objects.filter(match=match).select_related('user__profile')
        
        serializer = MatchParticipantSerializer(participants, many=True)
        return Response(serializer.data)

class HealthView(APIView):
    """
    GET /api/health/
    Auth nahi chahiye — load balancer / uptime checks ke liye
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # DB check
        db_ok = True
        try:
            User.objects.exists()
        except Exception:
            db_ok = False

        all_ok = db_ok

        return Response(
            {
                "status":    "ok" if all_ok else "degraded",
                "timestamp": timezone.now().isoformat(),
                "checks": {
                    "database": "ok" if db_ok else "error",
                    "api":      "ok",
                },
                "version": "1.0.0",
            },
            status=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )