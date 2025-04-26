from rest_framework import serializers
from django.contrib.auth.models import User, Group
from django.db.models import Sum
from .models import Society, Claim, Receipt, Approval, BankDetails, SocietyMembership

class BankDetailsSerializer(serializers.ModelSerializer):
    account_number_masked = serializers.SerializerMethodField()
    sort_code_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = BankDetails
        fields = ['id', 'nickname', 'account_name', 'account_number', 
                 'account_number_masked', 'sort_code', 'sort_code_formatted', 
                 'is_default', 'created_at', 'updated_at']
        extra_kwargs = {
            'account_number': {'write_only': True},
            'sort_code': {'write_only': True},
        }
    
    def get_account_number_masked(self, obj):
        """Return masked account number (only last 4 digits visible)"""
        if obj.account_number:
            return f"****{obj.account_number[-4:]}"
        return None
    
    def get_sort_code_formatted(self, obj):
        """Return sort code with hyphens for display"""
        if obj.sort_code and len(obj.sort_code) == 6:
            return f"{obj.sort_code[0:2]}-{obj.sort_code[2:4]}-{obj.sort_code[4:6]}"
        return obj.sort_code
    
    def validate_account_number(self, value):
        """Validate account number format"""
        if len(value) != 8 or not value.isdigit():
            raise serializers.ValidationError("Account number must be 8 digits")
        # Additional UK-specific validation could be added here
        # For example, modulus checking for UK bank accounts
        return value
    
    def validate_sort_code(self, value):
        """Validate sort code format"""
        if len(value) != 6 or not value.isdigit():
            raise serializers.ValidationError("Sort code must be 6 digits without hyphens")
        return value

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'groups']
        read_only_fields = ['groups']

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class SocietySerializer(serializers.ModelSerializer):
    class Meta:
        model = Society
        fields = ['id', 'name', 'description', 'starting_budget', 'created_at', 'updated_at']

class SocietyMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    society = SocietySerializer(read_only=True)

    class Meta:
        model = SocietyMembership
        fields = ['id', 'user', 'society', 'is_committee_member']

class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ['id', 'claim', 'file', 'description', 'uploaded_at']
        read_only_fields = ['uploaded_at']

class ApprovalSerializer(serializers.ModelSerializer):
    approver = UserSerializer(read_only=True)
    
    class Meta:
        model = Approval
        fields = ['id', 'claim', 'approver', 'approval_stage', 'decision', 'comment', 'timestamp']
        read_only_fields = ['timestamp']

class ClaimSerializer(serializers.ModelSerializer):
    receipts = ReceiptSerializer(many=True, read_only=True)
    approvals = ApprovalSerializer(many=True, read_only=True)
    submitter = UserSerializer(read_only=True)
    society = SocietySerializer(read_only=True)
    saved_bank_details = BankDetailsSerializer(read_only=True)
    bank_details_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Claim
        fields = [
            'id', 'submitter', 'society', 'description', 'total_amount', 
            'status', 'saved_bank_details', 'account_name', 'account_number', 'sort_code', 
            'bank_details_info', 'created_at', 'updated_at', 'receipts', 'approvals'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'account_number': {'write_only': True},
            'sort_code': {'write_only': True},
        }
    
    def get_bank_details_info(self, obj):
        """Return masked bank details for display"""
        if obj.saved_bank_details:
            return {
                'account_name': obj.saved_bank_details.account_name,
                'account_number_masked': f"****{obj.saved_bank_details.account_number[-4:]}",
                'sort_code_formatted': f"{obj.saved_bank_details.sort_code[0:2]}-{obj.saved_bank_details.sort_code[2:4]}-{obj.saved_bank_details.sort_code[4:6]}",
                'is_saved': True,
                'nickname': obj.saved_bank_details.nickname
            }
        elif obj.account_number and obj.sort_code:
            return {
                'account_name': obj.account_name,
                'account_number_masked': f"****{obj.account_number[-4:]}",
                'sort_code_formatted': f"{obj.sort_code[0:2]}-{obj.sort_code[2:4]}-{obj.sort_code[4:6]}",
                'is_saved': False
            }
        return None

class ClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = [
            'society', 'description', 'total_amount', 
            'saved_bank_details', 'account_name', 'account_number', 'sort_code'
        ]
    
    def create(self, validated_data):
        # Set the submitter to the current user
        validated_data['submitter'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate(self, data):
        # Check for either saved bank details OR one-time details
        saved_details = data.get('saved_bank_details')
        account_name = data.get('account_name')
        account_number = data.get('account_number')
        sort_code = data.get('sort_code')


        if not saved_details and not (account_name and account_number and sort_code):
            raise serializers.ValidationError("Either saved bank details or one-time bank details must be provided")
        
        if saved_details and (account_name or account_number or sort_code):
            raise serializers.ValidationError("Cannot provide both saved bank details and one-time bank details")
        
        # Validate that the bank details belong to the user
        if saved_details and self.context['request'].user != saved_details.user:
            raise serializers.ValidationError("You can only use your own saved bank details")
        
        # Check society balance
        society = data.get('society')
        amount = data.get('total_amount')
        
        if society and amount:
            approved_claims = society.claims.filter(status__in=['APPROVED', 'PAID'])
            total_approved = approved_claims.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            balance = society.starting_budget - total_approved
            
            if amount > balance:
                raise serializers.ValidationError(
                    f"Claim amount (£{amount}) exceeds available society balance (£{balance})"
                )

        society= data.get('society')
        user = self.context['request'].user
        if society and not SocietyMembership.objects.filter(
            user=self.context['request'].user,
            society=society
        ).exists():
            raise serializers.ValidationError("You must be a member of the society to submit a claim")

        return data