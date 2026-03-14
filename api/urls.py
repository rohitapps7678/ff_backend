# urls.py (app level - jaise games/urls.py)

from django.urls import path
from .views import (
    # Profile
    ProfileView,
    UpdateProfileView,
    
    # Matches - public
    UpcomingMatchesList,
    MatchDetail,
    JoinMatchView,
    MatchRoomDetail,
    
    # History & Results
    MyMatchesHistory,
    PublicMatchResults,
    DepositUPIInfo,
    
    # Spin & Ads
    SpinAndWin,
    WatchAdAndEarn,
    AdminDashboardStats,
    RecentTransactions,
    
    # Withdrawal
    CreateWithdrawalRequest,
    
    # Leaderboard
    Leaderboard,
    CreateDepositRequest,
    UploadMatchProof,
    AdminDepositList,
    AdminProcessDeposit,
    AdminPendingWithdrawals,
    AdminProcessWithdrawal,
    # Admin
    AdminAllMatches,
    MatchParticipantsList,
    AdminUPIListCreate,
    AdminUPIDelete,
    AdminMatchDetail,
    AdminSubmitResults,
)

urlpatterns = [
    # =====================================
    # PROFILE
    # =====================================
    path('profile/', ProfileView.as_view(), name='user-profile'),
    path('profile/update/', UpdateProfileView.as_view(), name='update-profile'),
    
    # =====================================
    # MATCHES - PUBLIC / USER
    # =====================================
    path('matches/upcoming/', UpcomingMatchesList.as_view(), name='upcoming-matches'),
    path('matches/<int:pk>/', MatchDetail.as_view(), name='match-detail'),
    path('admin/recent-transactions/', RecentTransactions.as_view(), name='recent-transactions'),
    
    path('matches/join/', JoinMatchView.as_view(), name='join-match'),
    path('matches/<int:pk>/room/', MatchRoomDetail.as_view(), name='match-room-info'),
    
    # History & Results
    path('my-matches/', MyMatchesHistory.as_view(), name='my-match-history'),
    path('matches/<int:pk>/results/', PublicMatchResults.as_view(), name='public-match-results'),
    
    # =====================================
    # SPIN & ADS EARNING
    # =====================================
    path('spin/', SpinAndWin.as_view(), name='spin-wheel'),
    path('ad-reward/', WatchAdAndEarn.as_view(), name='watch-ad-reward'),
    
    # =====================================
    # WITHDRAWAL
    # =====================================
    path('withdraw/request/', CreateWithdrawalRequest.as_view(), name='withdraw-request'),
    path('admin/withdrawals/pending/', AdminPendingWithdrawals.as_view(), name='admin-pending-withdrawals'),
    path('admin/withdrawals/<int:pk>/process/', AdminProcessWithdrawal.as_view(), name='admin-process-withdrawal'),
    
    # =====================================
    # LEADERBOARD
    # =====================================
    path('leaderboard/', Leaderboard.as_view(), name='leaderboard'),
    # urls.py - add these paths

    # Manual Deposit
    path('deposit/upi-info/', DepositUPIInfo.as_view(), name='deposit-upi-info'),
    path('deposit/request/', CreateDepositRequest.as_view(), name='create-deposit-request'),

    # Upload proof after match
    path('matches/<int:match_id>/upload-proof/', UploadMatchProof.as_view(), name='upload-match-proof'),

    # Admin deposit management
    path('admin/deposits/pending/', AdminDepositList.as_view(), name='admin-pending-deposits'),
    path('admin/deposits/<int:deposit_id>/process/', AdminProcessDeposit.as_view(), name='admin-process-deposit'),
    # =====================================
    # ADMIN ENDPOINTS
    # =====================================
    path('admin/matches/', AdminAllMatches.as_view(), name='admin-matches-list-create'),
    # urls.py

    path('matches/<int:pk>/participants/', MatchParticipantsList.as_view(), name='match-participants'),
    path('admin/upi-list/', AdminUPIListCreate.as_view(), name='admin-upi-list'),
    path('admin/upi/<int:pk>/', AdminUPIDelete.as_view(), name='admin-upi-delete'),
    path('admin/matches/<int:pk>/', AdminMatchDetail.as_view(), name='admin-match-detail'),
    path('admin/matches/<int:pk>/results/', AdminSubmitResults.as_view(), name='admin-submit-results'),
    path('admin/dashboard-stats/', AdminDashboardStats.as_view(), name='admin-dashboard-stats'),
]