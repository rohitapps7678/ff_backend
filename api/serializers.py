from rest_framework import serializers
from .models import *

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Profile
        fields = ['username', 'mobile', 'upi_id', 'wallet_balance', 'referral_code', 'total_kills', 'total_wins', 'total_matches']


class MatchSerializer(serializers.ModelSerializer):
    joined_count = serializers.SerializerMethodField()
    def get_joined_count(self, obj):
        return obj.participants.count()
    class Meta:
        model  = Match
        fields = '__all__'


class MatchParticipantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = MatchParticipant
        fields = ['username', 'kills', 'rank', 'is_winner', 'joined_at']


class ScreenshotProofSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='participant.user.username', read_only=True)
    class Meta:
        model = ScreenshotProof
        fields = ['id', 'username', 'image', 'uploaded_at', 'note']


class TransactionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Transaction
        fields = ['id', 'username', 'amount', 'transaction_type', 'status', 'payment_id', 'screenshot', 'upi_id_used', 'created_at', 'note']

class DepositRequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = DepositRequest
        fields = ['id', 'username', 'amount', 'upi_used', 'transaction_ref', 'screenshot', 'status', 'requested_at']

class MatchProofSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='participant.user.username', read_only=True)
    match_title = serializers.CharField(source='participant.match.title', read_only=True)
    class Meta:
        model = MatchProof
        fields = ['id', 'username', 'match_title', 'screenshot', 'uploaded_at', 'note']

class AdminUPISerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUPI
        fields = ['id', 'upi_id', 'created_at', 'is_active']