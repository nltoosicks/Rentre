from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # Landlord URLs
    path('landlord/dashboard/', views.landlord_dashboard, name='landlord_dashboard'),
    path('landlord/analytics/', views.landlord_analytics, name='landlord_analytics'),
    path('landlord/property/create/', views.property_create, name='property_create'),
    path('landlord/property/<int:property_id>/update/', views.property_update, name='property_update'),
    path('landlord/property/<int:property_id>/delete/', views.property_delete, name='property_delete'),
    path('landlord/property/<int:property_id>/add-lease/', views.add_lease_to_property, name='add_lease_to_property'),
    path('landlord/property/<int:property_id>/edit-lease/', views.edit_lease, name='edit_lease'),
    path('landlord/property/<int:property_id>/cancel-lease/', views.cancel_lease, name='cancel_lease'),

    # Tenant URLs
    path('tenant/dashboard/', views.tenant_dashboard, name='tenant_dashboard'),
    path('tenant/lease/<int:lease_id>/accept/', views.accept_lease, name='accept_lease'),
    path('tenant/lease/<int:lease_id>/decline/', views.decline_lease, name='decline_lease'),
    path('tenant/lease/<int:lease_id>/break/', views.break_lease, name='break_lease'),

    # Shared URLs
    path('property/<int:property_id>/', views.property_details, name='property_details'),
    path('lease/<int:lease_id>/', views.view_lease_details, name='view_lease_details'),
    path('profile/', views.user_profile, name='user_profile'),
    path('tenant/<int:tenant_id>/<int:lease_id>/', views.tenant_details, name='tenant_details'),
    path('landlord/<int:landlord_id>/<int:property_id>/', views.landlord_details, name='landlord_details'),

    # Default landing page (redirect to login)
    path('', views.login_view, name='home'),
]
