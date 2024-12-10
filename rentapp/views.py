# This file uses both Django ORM and raw SQL with prepared statements:

# ORM is used for:
# - Simple CRUD operations (create/read/update/delete) on models
# - Basic filtering and relationships
# - When security and SQL injection protection are handled automatically
# - When the queries are straightforward

# Prepared Statements are used for:
# - Complex analytics queries with dynamic filters
# - Performance-critical operations
# - Queries that are difficult to express in ORM
# - When we need fine-grained control over the SQL

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db import transaction, connection
from functools import wraps
from .forms import LeaseEditForm, PropertyForm, LeaseCreateForm
from .models import User, Landlord, Tenant, Property, Lease, LeaseTenant

def login_required_with_role(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('home')
        expected_role = view_func.__name__.split('_')[0]
        if expected_role in ['landlord', 'tenant']:
            if request.session.get('role') != expected_role:
                return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Authentication Views
def login_view(request):
    """Handle user login as either landlord or tenant"""
    # Redirect if already logged in
    if request.session.get('user_id'):
        if request.session.get('role') == 'landlord':
            return redirect('landlord_dashboard')
        return redirect('tenant_dashboard')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        
        try:
            custom_user = User.objects.get(email=email)
            # Get or create Django User for authentication
            django_user, created = DjangoUser.objects.get_or_create(
                username=email,
                defaults={'email': email}
            )
            if created:
                django_user.set_password(password)
                django_user.save()
            
            # Authenticate with Django's auth system
            user = authenticate(username=email, password=password)
            if user is not None:
                if role == 'landlord' and not hasattr(custom_user, 'landlord'):
                    messages.error(request, 'No landlord account found for this user')
                    return redirect('login')
                elif role == 'tenant' and not hasattr(custom_user, 'tenant'):
                    messages.error(request, 'No tenant account found for this user')
                    return redirect('login')
                
                login(request, user)
                request.session['user_id'] = str(custom_user.user_id)
                request.session['role'] = role
                
                if role == 'landlord':
                    return redirect('landlord_dashboard')
                else:
                    return redirect('tenant_dashboard')
            else:
                messages.error(request, 'Invalid credentials')
                
        except User.DoesNotExist:
            messages.error(request, 'Invalid credentials')
            
    return render(request, 'rentapp/login.html')

def signup_view(request):
    """Handle user signup as either landlord or tenant"""
    # Redirect if already logged in
    if request.session.get('user_id'):
        if request.session.get('role') == 'landlord':
            return redirect('landlord_dashboard')
        return redirect('tenant_dashboard')
    if request.method == 'POST':
        email = request.POST['email']
        
        # Check if user already exists
        if DjangoUser.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'rentapp/signup.html')
            
        with transaction.atomic():
            # Create Django User first
            django_user = DjangoUser.objects.create_user(
                username=email,
                email=email,
                password=request.POST['password']
            )
            
            # Create custom user
            user = User.objects.create(
                email=request.POST['email'],
                password=django_user.password,  # Store hashed password
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name'],
                phone=request.POST['phone']
            )
            
            role = request.POST['role']
            if role == 'landlord':
                Landlord.objects.create(
                    user=user
                )
            else:  # tenant
                Tenant.objects.create(
                    user=user
                )
            
            # Log the user in
            login(request, django_user)
            
            # Set session variables
            request.session['user_id'] = str(user.user_id)
            request.session['role'] = role
            
            messages.success(request, 'Account created successfully!')
            if role == 'landlord':
                return redirect('landlord_dashboard')
            return redirect('tenant_dashboard')
            
    return render(request, 'rentapp/signup.html')

def logout_view(request):
    """Handle user logout"""
    request.session.flush()
    messages.info(request, 'You have been logged out.')
    return redirect('login')

# Landlord Views
@login_required_with_role
def landlord_dashboard(request):
    """Show landlord's properties and management options"""
    if request.session.get('role') != 'landlord':
        return HttpResponseForbidden("Landlord access only")
        
    user = User.objects.get(user_id=request.session['user_id'])
    properties = Property.objects.filter(landlord=user.landlord)
    
    return render(request, 'rentapp/landlord_dashboard.html', {
        'properties': properties
    })

@login_required
def property_create(request):
    """
    Pure ORM approach for simple CRUD:
    - Basic foreign key relationships
    - Simple create/save operations
    - Automatic SQL injection protection
    """
    """Create a new property"""
    if request.session.get('role') != 'landlord':
        return HttpResponseForbidden("Landlord access only")
        
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            property = form.save(commit=False)
            user = User.objects.get(user_id=request.session['user_id'])
            property.landlord = user.landlord
            property.save()
            messages.success(request, 'Property created successfully')
            return redirect('landlord_dashboard')
    else:
        form = PropertyForm()
        
    return render(request, 'rentapp/add_property.html', {'form': form})

def get_landlord_analytics(landlord_id, city=None, state=None, status=None):
    """
    Complex analytics using prepared statements for:
    - Dynamic filtering with parameterized queries
    - Aggregations across multiple tables
    - Custom joins and subqueries
    - Performance optimization for large datasets
    """
    """Get analytics for a landlord using prepared statements with optional filters"""
    params = [landlord_id]
    filter_conditions = []
    
    if city:
        filter_conditions.append("p.city = %s")
        params.append(city)
    if state:
        filter_conditions.append("p.state = %s")
        params.append(state)
    if status:
        if status == 'no lease':
            filter_conditions.append("l.status IS NULL")
        else:
            filter_conditions.append("l.status = %s")
            params.append(status)
    
    filter_sql = " AND " + " AND ".join(filter_conditions) if filter_conditions else ""
    
    with connection.cursor() as cursor:
        # Get total properties and average rent for filtered results
        cursor.execute(f"""
            SELECT 
                COUNT(*),
                COALESCE(AVG(CASE WHEN l.monthly_rent IS NOT NULL THEN l.monthly_rent END), 0)
            FROM rentapp_property p
            LEFT JOIN (
                SELECT property_id, status, monthly_rent
                FROM rentapp_lease
                WHERE status = 'active'
                OR (status = 'inactive' AND property_id NOT IN (
                    SELECT property_id FROM rentapp_lease WHERE status = 'active'
                ))
            ) l ON p.property_id = l.property_id
            WHERE p.landlord_id = %s{filter_sql}
        """, params)
        filtered_count, avg_rent = cursor.fetchone()

        # Get total properties (unfiltered)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM rentapp_property 
            WHERE landlord_id = %s
        """, [landlord_id])
        total_properties = cursor.fetchone()[0]

        # Get properties with active leases (unfiltered)
        cursor.execute("""
            SELECT COUNT(DISTINCT p.property_id)
            FROM rentapp_property p
            JOIN rentapp_lease l ON p.property_id = l.property_id
            WHERE p.landlord_id = %s AND l.status = 'active'
        """, [landlord_id])
        active_leases = cursor.fetchone()[0]

        # Get total monthly income from active leases (unfiltered)
        cursor.execute("""
            SELECT COALESCE(SUM(l.monthly_rent), 0)
            FROM rentapp_property p
            JOIN rentapp_lease l ON p.property_id = l.property_id
            WHERE p.landlord_id = %s AND l.status = 'active'
        """, [landlord_id])
        monthly_income = cursor.fetchone()[0]

        # Get property details with lease status (filtered)
        cursor.execute(f"""
            SELECT 
                p.property_name,
                p.city,
                p.state,
                p.zip_code,
                CASE 
                    WHEN l.status IS NULL THEN 'no lease'
                    ELSE l.status 
                END as lease_status,
                l.monthly_rent
            FROM rentapp_property p
            LEFT JOIN (
                SELECT property_id, status, monthly_rent
                FROM rentapp_lease
                WHERE status = 'active'
                OR (status = 'inactive' AND property_id NOT IN (
                    SELECT property_id FROM rentapp_lease WHERE status = 'active'
                ))
            ) l ON p.property_id = l.property_id
            WHERE p.landlord_id = %s{filter_sql}
            ORDER BY p.property_name
        """, params)
        
        properties = [
            {
                'property_name': row[0],
                'city': row[1],
                'state': row[2],
                'zip_code': row[3],
                'lease_status': row[4],
                'monthly_rent': row[5]
            }
            for row in cursor.fetchall()
        ]

    return {
        'total_properties': total_properties,
        'active_leases': active_leases,
        'monthly_income': monthly_income,
        'properties': properties
    }

@login_required
def landlord_analytics(request):
    """View analytics dashboard for landlord"""
    if request.session.get('role') != 'landlord':
        return HttpResponseForbidden("Landlord access only")
        
    user = User.objects.get(user_id=request.session['user_id'])
    
    # Get filter parameters
    city = request.GET.get('city', '')
    state = request.GET.get('state', '')
    status = request.GET.get('status', '')
    
    # Get analytics with filters
    analytics = get_landlord_analytics(
        str(user.landlord.landlord_id),
        city=city if city else None,
        state=state if state else None,
        status=status if status else None
    )
    
    # Get all possible values for filters (unfiltered)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT city, state,
                   CASE 
                       WHEN l.status IS NULL THEN 'no lease'
                       ELSE l.status 
                   END as lease_status
            FROM rentapp_property p
            LEFT JOIN rentapp_lease l ON p.property_id = l.property_id
            WHERE p.landlord_id = %s
        """, [user.landlord.landlord_id])
        
        filter_values = cursor.fetchall()
        unique_cities = sorted(set(row[0] for row in filter_values))
        unique_states = sorted(set(row[1] for row in filter_values))
        unique_statuses = sorted(set(row[2] for row in filter_values))
    
    analytics.update({
        'unique_cities': unique_cities,
        'unique_states': unique_states,
        'unique_statuses': unique_statuses,
        'filtered_count': len(analytics['properties']),
        'avg_rent': sum((p['monthly_rent'] if p['lease_status'] == 'active' else 0) for p in analytics['properties']) / len(analytics['properties']) if analytics['properties'] else 0,
        'selected_city': city,
        'selected_state': state,
        'selected_status': status
    })
    
    return render(request, 'rentapp/landlord_analytics.html', analytics)

@login_required
def property_update(request, property_id):
    """Update existing property details"""
    if request.session.get('role') != 'landlord':
        return HttpResponseForbidden("Landlord access only")
    
    with transaction.atomic():
        property = get_object_or_404(
            Property.objects.select_for_update(),
            property_id=property_id
        )
        user = User.objects.get(user_id=request.session['user_id'])
        
        if property.landlord != user.landlord:
            return HttpResponseForbidden("Not your property")
            
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=property)
        if form.is_valid():
            with transaction.atomic():
                property = Property.objects.select_for_update().get(pk=property_id)
                form.save()
                messages.success(request, 'Property updated successfully')
                return redirect('landlord_dashboard')
    else:
        form = PropertyForm(instance=property)
        
    return render(request, 'rentapp/add_property.html', {
        'form': form,
        'property': property
    })

@login_required
def property_delete(request, property_id):
    """Delete a property"""
    if request.session.get('role') != 'landlord':
        return HttpResponseForbidden("Landlord access only")
        
    property = get_object_or_404(Property, property_id=property_id)
    user = User.objects.get(user_id=request.session['user_id'])
    
    if property.landlord != user.landlord:
        return HttpResponseForbidden("Not your property")
        
    property.delete()
    messages.success(request, 'Property deleted successfully')
    return redirect('landlord_dashboard')

@login_required
def add_lease_to_property(request, property_id):
    """Add new lease with multiple tenants to property"""
    if request.session.get('role') != 'landlord':
        return HttpResponseForbidden("Landlord access only")
        
    property = get_object_or_404(Property, property_id=property_id)
    user = User.objects.get(user_id=request.session['user_id'])
    
    if property.landlord != user.landlord:
        return HttpResponseForbidden("Not your property")
        
    if request.method == 'POST':
        form = LeaseCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    lease = form.save(commit=False)
                    lease.property = property
                    lease.status = 'inactive'
                    lease.save()
                    
                    tenant_emails = form.cleaned_data['tenant_emails']
                    for email in tenant_emails:
                        tenant = Tenant.objects.get(user__email=email)
                        LeaseTenant.objects.create(
                            lease=lease,
                            tenant=tenant,
                            confirmed=False
                        )
                    lease.update_status()
                    messages.success(request, 'Lease created successfully')
                    return redirect('landlord_dashboard')
            except Exception as e:
                messages.error(request, f'Error creating lease: {str(e)}')
    else:
        form = LeaseCreateForm()
        
    return render(request, 'rentapp/add_lease.html', {'form': form, 'property': property})

# Tenant Views
@login_required
def tenant_dashboard(request):
    """Show tenant's rented properties"""
    if request.session.get('role') != 'tenant':
        return HttpResponseForbidden("Tenant access only")
        
    user = User.objects.get(user_id=request.session['user_id'])
    lease_tenants = LeaseTenant.objects.filter(tenant=user.tenant)
    
    return render(request, 'rentapp/tenant_dashboard.html', {
        'lease_tenants': lease_tenants
    })

@login_required
def accept_lease(request, lease_id):
    """Accept a pending lease invitation"""
    if request.session.get('role') != 'tenant':
        return HttpResponseForbidden("Tenant access only")
        
    if request.method != 'POST':
        return HttpResponseForbidden("Invalid request method")
    
    with transaction.atomic():
        user = User.objects.get(user_id=request.session['user_id'])
        lease_tenant = get_object_or_404(
            LeaseTenant.objects.select_for_update(),
            lease__lease_id=lease_id,
            tenant=user.tenant,
            confirmed=False
        )
        
        # Lock the related lease to prevent concurrent status updates
        lease = Lease.objects.select_for_update().get(pk=lease_tenant.lease.pk)
        
        lease_tenant.confirmed = True
        lease_tenant.save()
        lease.update_status()
    
    messages.success(request, 'Lease accepted successfully')
    return redirect('tenant_dashboard')

@login_required
def decline_lease(request, lease_id):
    """Decline a pending lease invitation"""
    if request.session.get('role') != 'tenant':
        return HttpResponseForbidden("Tenant access only")
        
    if request.method != 'POST':
        return HttpResponseForbidden("Invalid request method")
        
    user = User.objects.get(user_id=request.session['user_id'])
    lease_tenant = get_object_or_404(
        LeaseTenant,
        lease__lease_id=lease_id,
        tenant=user.tenant,
        confirmed=False
    )
    
    lease = lease_tenant.lease
    lease_tenant.delete()
    lease.update_status()
    messages.success(request, 'Lease declined successfully')
    return redirect('tenant_dashboard')

@login_required
def break_lease(request, lease_id):
    """Break an active lease"""
    if request.session.get('role') != 'tenant':
        return HttpResponseForbidden("Tenant access only")
        
    if request.method != 'POST':
        return HttpResponseForbidden("Invalid request method")
    
    with transaction.atomic():
        user = User.objects.get(user_id=request.session['user_id'])
        lease_tenant = get_object_or_404(
            LeaseTenant.objects.select_for_update(),
            lease__lease_id=lease_id,
            tenant=user.tenant,
            confirmed=True
        )
        
        # Lock the lease to prevent concurrent status updates
        lease = Lease.objects.select_for_update().get(pk=lease_tenant.lease.pk)
        lease_tenant.delete()
        lease.update_status()
    
    messages.success(request, 'Lease broken successfully')
    return redirect('tenant_dashboard')

# Shared Views
@login_required
def view_lease_details(request, lease_id):
    """
    Hybrid approach using both prepared statements and ORM:
    - Prepared statements for complex authorization checks
    - Raw SQL for efficient data retrieval across multiple tables
    - Demonstrates when to choose each approach based on the query needs
    """
    """View lease details for both landlord and tenant"""
    user = User.objects.get(user_id=request.session['user_id'])
    
    with connection.cursor() as cursor:
        # First check authorization
        if request.session.get('role') == 'landlord':
            # Check if landlord owns the property this lease is for
            cursor.execute("""
                SELECT 1
                FROM rentapp_lease l
                JOIN rentapp_property p ON l.property_id = p.property_id
                WHERE l.lease_id = %s AND p.landlord_id = %s
            """, [lease_id, user.landlord.landlord_id])
            if not cursor.fetchone():
                return HttpResponseForbidden("Not your property's lease")
        else:  # tenant
            # Check if tenant is part of this lease
            cursor.execute("""
                SELECT 1
                FROM rentapp_leasetenant lt
                WHERE lt.lease_id = %s AND lt.tenant_id = %s
            """, [lease_id, user.tenant.tenant_id])
            if not cursor.fetchone():
                return HttpResponseForbidden("Not your lease")

        # Get lease details
        cursor.execute("""
            SELECT l.lease_id, l.lease_start_date, l.lease_end_date, 
                   l.monthly_rent, l.status, l.property_id
            FROM rentapp_lease l
            WHERE l.lease_id = %s
        """, [lease_id])
        
        row = cursor.fetchone()
        if not row:
            return HttpResponseForbidden("Lease not found")
            
        lease_dict = {
            'lease_id': row[0],
            'lease_start_date': row[1],
            'lease_end_date': row[2],
            'monthly_rent': row[3],
            'status': row[4],
            'property_id': row[5]
        }
        
        # Get lease tenants
        cursor.execute("""
            SELECT u.email, lt.confirmed, lt.tenant_id
            FROM rentapp_leasetenant lt
            JOIN rentapp_tenant t ON lt.tenant_id = t.tenant_id
            JOIN rentapp_user u ON t.user_id = u.user_id
            WHERE lt.lease_id = %s
        """, [lease_id])
        
        lease_tenants = [
            {'email': row[0], 'confirmed': row[1], 'tenant_id': row[2]}
            for row in cursor.fetchall()
        ]
        
        if request.session.get('role') == 'landlord':
            context = {
                'lease': lease_dict,
                'lease_tenants': lease_tenants
            }
        else:  # tenant
            # Get tenant's confirmation status
            cursor.execute("""
                SELECT lt.confirmed
                FROM rentapp_leasetenant lt
                WHERE lt.lease_id = %s AND lt.tenant_id = %s
            """, [lease_id, user.tenant.tenant_id])
            
            tenant_row = cursor.fetchone()
            context = {
                'lease': lease_dict,
                'lease_tenant': {'confirmed': tenant_row[0]},
                'lease_tenants': lease_tenants
            }
    
    return render(request, 'rentapp/lease_details.html', context)

def property_details(request, property_id):
    """View property details (different views for landlord/tenant)"""
    property = get_object_or_404(Property, property_id=property_id)
    user = User.objects.get(user_id=request.session['user_id'])
    role = request.session.get('role')
    
    if role == 'landlord':
        if property.landlord != user.landlord:
            return HttpResponseForbidden("Not your property")
        context = {'property': property}
    else:  # tenant
        # Check if tenant has a lease for this property
        lease_exists = LeaseTenant.objects.filter(
            tenant=user.tenant,
            lease__property=property
        ).exists()
        if not lease_exists:
            return HttpResponseForbidden("You don't have a lease for this property")
        context = {'property': property}
    
    return render(request, 'rentapp/property_details.html', context)

@login_required
def edit_lease(request, property_id):
    """Edit existing lease and tenant list with improved error handling and data persistence"""
    if request.session.get('role') != 'landlord':
        return HttpResponseForbidden("Landlord access only")
    
    with transaction.atomic():
        property = get_object_or_404(
            Property.objects.select_for_update(),
            property_id=property_id
        )
        user = User.objects.get(user_id=request.session['user_id'])
        
        if property.landlord != user.landlord:
            return HttpResponseForbidden("Not your property")
            
        lease = get_object_or_404(
            Lease.objects.select_for_update(),
            property=property
        )
    
    if request.method == 'POST':
        form = LeaseEditForm(request.POST, instance=lease)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save lease details
                    form.save()
                    
                    # Process tenants
                    new_tenant_emails = form.cleaned_data['tenant_emails']
                    current_tenants = lease.leasetenant_set.all()
                    
                    # Remove tenants not in new list
                    for lease_tenant in current_tenants:
                        if lease_tenant.tenant.user.email not in new_tenant_emails:
                            lease_tenant.delete()
                    
                    # Add new tenants
                    for email in new_tenant_emails:
                        tenant = Tenant.objects.get(user__email=email)
                        LeaseTenant.objects.get_or_create(
                            lease=lease,
                            tenant=tenant,
                            defaults={'confirmed': False}
                        )
                    
                    lease.update_status()
                    messages.success(request, 'Lease updated successfully')
                    return redirect('landlord_dashboard')
                    
            except Exception as e:
                messages.error(request, f'Error updating lease: {str(e)}')
    else:
        form = LeaseEditForm(instance=lease)
    
    return render(request, 'rentapp/edit_lease.html', {
        'property': property,
        'form': form
    })

@login_required
def cancel_lease(request, property_id):
    """Cancel/delete an existing lease"""
    if request.session.get('role') != 'landlord':
        return HttpResponseForbidden("Landlord access only")
        
    if request.method == 'POST':
        with transaction.atomic():
            property = get_object_or_404(
                Property.objects.select_for_update(),
                property_id=property_id
            )
            user = User.objects.get(user_id=request.session['user_id'])
            
            if property.landlord != user.landlord:
                return HttpResponseForbidden("Not your property")
            
            try:
                lease = Lease.objects.select_for_update().get(property=property)
                # Delete all associated lease tenants first
                LeaseTenant.objects.filter(lease=lease).delete()
                # Then delete the lease
                lease.delete()
                messages.success(request, 'Lease cancelled successfully')
            except Lease.DoesNotExist:
                messages.error(request, 'No lease found for this property')
        return redirect('landlord_dashboard')
    
    return HttpResponseForbidden("Invalid request method")

def user_profile(request):
    """View/edit user profile"""
    user = User.objects.get(user_id=request.session['user_id'])
    role = request.session.get('role')
    
    if request.method == 'POST':
        user.first_name = request.POST['first_name']
        user.last_name = request.POST['last_name']
        user.phone = request.POST['phone']
        user.save()
        
        if role == 'landlord':
            user.landlord.save()
        elif role == 'tenant':
            user.tenant.save()
            
        messages.success(request, 'Profile updated successfully')
        return redirect('user_profile')
        
    return render(request, 'rentapp/user_profile.html', {
        'user': user,
        'role': role
    })

@login_required
def tenant_details(request, tenant_id, lease_id):
    """View tenant details with proper authorization"""
    user = User.objects.get(user_id=request.session['user_id'])
    role = request.session.get('role')

    with connection.cursor() as cursor:
        # First verify the requested tenant is part of the specified lease
        cursor.execute("""
            SELECT 1 
            FROM rentapp_leasetenant lt
            WHERE lt.tenant_id = %s AND lt.lease_id = %s
        """, [tenant_id, lease_id])
        
        if not cursor.fetchone():
            return HttpResponseForbidden("Invalid tenant-lease combination")

        if role == 'landlord':
            # Verify landlord owns the property this lease is for
            cursor.execute("""
                SELECT 1
                FROM rentapp_lease l
                JOIN rentapp_property p ON l.property_id = p.property_id
                WHERE l.lease_id = %s AND p.landlord_id = %s
            """, [lease_id, user.landlord.landlord_id])
            
            if not cursor.fetchone():
                return HttpResponseForbidden("Not your property's lease")
        else:  # tenant
            # Verify requesting tenant is also part of this lease
            cursor.execute("""
                SELECT 1
                FROM rentapp_leasetenant lt
                WHERE lt.lease_id = %s AND lt.tenant_id = %s
            """, [lease_id, user.tenant.tenant_id])
            
            if not cursor.fetchone():
                return HttpResponseForbidden("Not your lease")

        # Get tenant details
        cursor.execute("""
            SELECT u.first_name, u.last_name, u.email, u.phone
            FROM rentapp_tenant t
            JOIN rentapp_user u ON t.user_id = u.user_id
            WHERE t.tenant_id = %s
        """, [tenant_id])
        
        row = cursor.fetchone()
        if not row:
            return HttpResponseForbidden("Tenant not found")

        tenant_dict = {
            'user': {
                'first_name': row[0],
                'last_name': row[1],
                'email': row[2],
                'phone': row[3]
            }
        }

    return render(request, 'rentapp/tenant_details.html', {
        'tenant': tenant_dict,
        'lease_id': lease_id
    })

@login_required
def landlord_details(request, landlord_id, property_id):
    """View landlord details with proper authorization"""
    user = User.objects.get(user_id=request.session['user_id'])
    role = request.session.get('role')

    with connection.cursor() as cursor:
        if role != 'tenant':
            return HttpResponseForbidden("Only tenants can view landlord details")

        # Verify tenant has a lease for a property owned by this landlord
        cursor.execute("""
            SELECT 1
            FROM rentapp_leasetenant lt
            JOIN rentapp_lease l ON lt.lease_id = l.lease_id
            JOIN rentapp_property p ON l.property_id = p.property_id
            WHERE lt.tenant_id = %s 
            AND p.landlord_id = %s
            AND p.property_id = %s
        """, [user.tenant.tenant_id, landlord_id, property_id])

        if not cursor.fetchone():
            return HttpResponseForbidden("Not authorized to view this landlord's details")

        # Get landlord details
        cursor.execute("""
            SELECT u.first_name, u.last_name, u.email, u.phone
            FROM rentapp_landlord l
            JOIN rentapp_user u ON l.user_id = u.user_id
            WHERE l.landlord_id = %s
        """, [landlord_id])

        row = cursor.fetchone()
        if not row:
            return HttpResponseForbidden("Landlord not found")

        landlord_dict = {
            'user': {
                'first_name': row[0],
                'last_name': row[1],
                'email': row[2],
                'phone': row[3]
            }
        }

    return render(request, 'rentapp/landlord_details.html', {
        'landlord': landlord_dict,
        'property_id': property_id
    })
