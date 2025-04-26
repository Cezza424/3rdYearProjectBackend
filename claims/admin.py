from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Society, Claim, Receipt, Approval, BankDetails, SocietyMembership

"""
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'
    filter_horizontal = ('societies',)
"""
# Define a new User admin
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_societies')

    def get_societies(self, obj):
        societies = SocietyMembership.objects.filter(
            user=obj,
            is_committee_member=True
        ).values_list('society__name', flat=True)
        return ",".join(societies)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Society)
class SocietyAdmin(admin.ModelAdmin):
    list_display = ('name', 'starting_budget', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)

class ReceiptInline(admin.TabularInline):
    model = Receipt
    extra = 0

class ApprovalInline(admin.TabularInline):
    model = Approval
    extra = 0
    readonly_fields = ('timestamp',)

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'submitter', 'society', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'society', 'created_at')
    search_fields = ('description', 'submitter__username', 'society__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (ReceiptInline, ApprovalInline)
    fieldsets = (
        (None, {
            'fields': ('submitter', 'society', 'description', 'total_amount', 'status')
        }),
        ('Bank Details', {
            'fields': ('account_name', 'account_number', 'sort_code')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'claim', 'description', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('description', 'claim__description')

@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ('id', 'claim', 'approver', 'approval_stage', 'decision', 'timestamp')
    list_filter = ('approval_stage', 'decision', 'timestamp')
    search_fields = ('comment', 'approver__username', 'claim__description')
    readonly_fields = ('timestamp',)

@admin.register(BankDetails)
class BankDetailsAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname', 'account_name', 'is_default', 'created_at')
    list_filter = ('is_default', 'created_at')
    search_fields = ('user__username', 'nickname', 'account_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'nickname', 'is_default')
        }),
        ('Bank Details', {
            'fields': ('account_name', 'account_number', 'sort_code')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(SocietyMembership)
class SocietyMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'society', 'is_committee_member')
    list_filter = ('is_committee_member','society')
    search_fields = ('user__username', 'society__name')