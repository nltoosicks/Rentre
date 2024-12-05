from django.contrib import admin
from .models import User, Landlord, Tenant, Property, Lease, LeaseTenant

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone')
    search_fields = ('email', 'first_name', 'last_name')

@admin.register(Landlord)
class LandlordAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__email',)

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__email',)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('landlord', 'address_line_1', 'city', 'state')
    search_fields = ('address_line_1', 'city')
    list_filter = ('state',)

@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ('property', 'lease_start_date', 'lease_end_date', 'monthly_rent', 'status')
    list_filter = ('status',)
    search_fields = ('property__address_line_1',)

@admin.register(LeaseTenant)
class LeaseTenantAdmin(admin.ModelAdmin):
    list_display = ('lease', 'tenant', 'confirmed')
    list_filter = ('confirmed',)
