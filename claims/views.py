from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User, Group
from django.db.models import Sum, Q
from django.core.mail import send_mail
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Society, Claim, Receipt, Approval, SocietyMembership, BankDetails
from .serializers import (
    UserSerializer, GroupSerializer, SocietySerializer,
    ClaimSerializer, ClaimCreateSerializer,
    ReceiptSerializer, ApprovalSerializer, BankDetailsSerializer
)
from .signals import log_sensitive_data_access

class IsCommitteeMember(permissions.BasePermission):
    """
    Custom permission to only allow committee members to approve claims.
    """
    def has_permission(self, request, view):
        return SocietyMembership.objects.filter(
            user=request.user,
            is_committee_member=True
        ).exists()

    def has_object_permission(self, request, view, obj):
        society = getattr(obj, 'society', None)
        if not society:
            return False

        return SocietyMembership.objects.filter(
            user=request.user,
            society=society,
            is_committee_member=True
        ).exists()

class IsSUStaff(permissions.BasePermission):
    """
    Custom permission to only allow SU staff to approve claims.
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='SU Staff').exists()

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

class BankDetailsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to manage their bank details.
    """
    serializer_class = BankDetailsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BankDetails.objects.filter(user=self.request.user).select_related('user')
    
    def retrieve(self, request, *args, **kwargs):
        """Log when bank details are accessed"""
        instance = self.get_object()
        log_sensitive_data_access(
            user=request.user, 
            data_type='bank_details', 
            instance_id=instance.id, 
            action='viewed'
        )
        return super().retrieve(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        # Check if this is the first bank details for the user
        is_first = not BankDetails.objects.filter(user=self.request.user).exists()
        # If first account or explicitly set as default, make it default
        serializer.save(
            user=self.request.user, 
            is_default=is_first or serializer.validated_data.get('is_default', False)
        )
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        bank_details = self.get_object()
        bank_details.is_default = True
        bank_details.save()
        return Response({'status': 'default set'})
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get the user's default bank details"""
        try:
            default_bank_details = BankDetails.objects.get(user=request.user, is_default=True)
            serializer = self.get_serializer(default_bank_details)
            return Response(serializer.data)
        except BankDetails.DoesNotExist:
            return Response(
                {'detail': 'No default bank details found.'},
                status=status.HTTP_404_NOT_FOUND
            )


class SocietyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows societies to be viewed or edited.
    """
    queryset = Society.objects.all()
    serializer_class = SocietySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        """
        Only SU Staff can create, update or delete societies.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSUStaff()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        society = self.get_object()
        approved_claims = society.claims.filter(status__in=['APPROVED', 'PAID'])
        total_approved = approved_claims.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        balance = society.starting_budget - total_approved
        return Response({
            'starting_budget': society.starting_budget,
            'total_approved_claims': total_approved,
            'current_balance': balance
        })

"""class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    
    API endpoint that allows user profiles to be viewed.
    
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        profile = request.user.profile
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
"""
class ClaimViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows claims to be viewed or edited.
    """
    queryset = Claim.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['status', 'society', 'created_at']
    search_fields = ['description', 'submitter__username', 'status']

    def get_serializer_class(self):
        if self.action == 'create':
            return ClaimCreateSerializer
        return ClaimSerializer

    def get_queryset(self):
        """
        Filter claims based on user role:
        - Society Members: only their own claims
        - Committee Members: claims from their societies
        - SU Staff: all claims

        user = self.request.user
        base_queryset = Claim.objects.select_related(
            'submitter', 'society', 'saved_bank_details'
        ).prefetch_related(
            'receipts', 'approvals'
        ).order_by('-created_at')
    
        # SU Staff can see all claims
        if user.groups.filter(name='SU Staff').exists():
            return base_queryset
    
        # Committee Members can see claims from their societies
        if user.groups.filter(name='Committee Members').exists():
            society_ids = user.profile.societies.values_list('id', flat=True)
            return base_queryset.filter(society__id__in=society_ids)
    
        # Society Members can only see their own claims
        return base_queryset.filter(submitter=user)

        """
        user = self.request.user
        base_queryset = Claim.objects.select_related(
            'submitter', 'society', 'saved_bank_details'
        ).prefetch_related(
            'receipts', 'approvals'
        ).order_by('-created_at')

        if user.is_superuser or user.groups.filter(name='SU Staff').exists():
            return base_queryset

        committee_societies = SocietyMembership.objects.filter(
            user=user,
            is_committee_member=True
        ).values_list('society_id', flat=True)

        if committee_societies.exists():
            return base_queryset.filter(
                Q(submitter=user) | Q(society_id__in=committee_societies)
            )

        return base_queryset.filter(submitter=user)

    def notify_claim_status_change(self, claim, status_message, comment=None):
        """Send email notification about claim status change"""
        try:
            subject = f"Claim #{claim.id} status update: {status_message}"
            message = f"Your claim for {claim.description} has been {status_message.lower()}.\n"
            if comment:
                message += f"Comment: {comment}"
            
            # Add bank details if approved
            if status_message == 'APPROVED':
                if claim.saved_bank_details:
                    message += f"\n\nPayment will be sent to: {claim.saved_bank_details.account_name} (Account: ****{claim.saved_bank_details.account_number[-4:]})"
                else:
                    message += f"\n\nPayment will be sent to: {claim.account_name} (Account: ****{claim.account_number[-4:]})"
            
            send_mail(
                subject,
                message,
                'noreply@example.com',
                [claim.submitter.email],
                fail_silently=True,  # Set to False in production to catch errors
            )
        except Exception as e:
            # Log the error but don't break the flow
            print(f"Error sending notification: {e}")

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def committee_approval(self, request, pk=None):
        claim = self.get_object()

        # Check if claim is in the correct state
        if claim.status != 'PENDING_COMMITTEE':
            return Response(
                {'detail': 'This claim is not pending committee approval.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user is in the committee of the claim's society
        if not SocietyMembership.objects.filter(
            user=request.user,
            society=claim.society,
            is_committee_member=True
        ).exists():
            return Response(
                {'detail': 'You are not a committee member of this society.'},
                status=status.HTTP_403_FORBIDDEN
            )

        decision = request.data.get('decision')
        comment = request.data.get('comment', '')

        if decision not in ['APPROVED', 'REJECTED']:
            return Response(
                {'detail': 'Decision must be either APPROVED or REJECTED.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create approval record
        approval = Approval.objects.create(
            claim=claim,
            approver=request.user,
            approval_stage='COMMITTEE',
            decision=decision,
            comment=comment
        )

        # Update claim status
        if decision == 'APPROVED':
            claim.status = 'PENDING_SU'
            status_message = 'approved by committee and forwarded to SU for final approval'
        else:
            claim.status = 'REJECTED'
            status_message = 'rejected by committee'
        claim.save()
        
        # Send notification
        self.notify_claim_status_change(claim, status_message, comment)

        return Response(
            {'detail': f'Claim has been {decision.lower()} by committee.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSUStaff])
    def su_approval(self, request, pk=None):
        claim = self.get_object()

        # Check if claim is in the correct state
        if claim.status != 'PENDING_SU':
            return Response(
                {'detail': 'This claim is not pending SU approval.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        decision = request.data.get('decision')
        comment = request.data.get('comment', '')

        if decision not in ['APPROVED', 'REJECTED']:
            return Response(
                {'detail': 'Decision must be either APPROVED or REJECTED.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create approval record
        approval = Approval.objects.create(
            claim=claim,
            approver=request.user,
            approval_stage='SU',
            decision=decision,
            comment=comment
        )

        # Update claim status
        if decision == 'APPROVED':
            claim.status = 'APPROVED'
            status_message = 'APPROVED'
        else:
            claim.status = 'REJECTED'
            status_message = 'REJECTED'
        claim.save()
        
        # Send notification
        self.notify_claim_status_change(claim, status_message, comment)

        return Response(
            {'detail': f'Claim has been {decision.lower()} by SU staff.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSUStaff])
    def mark_as_paid(self, request, pk=None):
        claim = self.get_object()

        # Check if claim is in the correct state
        if claim.status != 'APPROVED':
            return Response(
                {'detail': 'Only approved claims can be marked as paid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update claim status
        claim.status = 'PAID'
        claim.save()

        # Send notification
        self.notify_claim_status_change(claim, 'PAID', 'Your payment has been processed.')
        
        return Response(
            {'detail': 'Claim has been marked as paid.'},
            status=status.HTTP_200_OK
        )

class ReceiptViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows receipts to be viewed or edited.
    """
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter receipts based on user role, similar to claims.
        """
        user = self.request.user

        # SU Staff can see all receipts
        if user.groups.filter(name='SU Staff').exists():
            return Receipt.objects.all()

        committee_societies = SocietyMembership.objects.filter(
            user=user,
            is_committee_member=True
        ).values_list('society_id', flat=True)

        if committee_societies.exists():
            return Receipt.objects.filter(
                Q(claim__submitter=user) |
                Q(claim__society_id__in=committee_societies)
            )

        return Receipt.objects.filter(claim__submitter=user)

    def perform_create(self, serializer):
        """
        Check if the user has permission to add a receipt to this claim.
        """
        claim_id = self.request.data.get('claim')
        claim = get_object_or_404(Claim, id=claim_id)

        # Only the submitter can add receipts, and only if the claim is not yet approved
        if claim.submitter != self.request.user or claim.status not in ['PENDING_COMMITTEE', 'PENDING_SU']:
            self.permission_denied(
                self.request, 
                message='You cannot add receipts to this claim.'
            )

        serializer.save()
