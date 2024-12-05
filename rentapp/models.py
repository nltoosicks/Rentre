from django.db import models
from django.core.validators import MinValueValidator

class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class Landlord(models.Model):
    landlord_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Tenant(models.Model):
    tenant_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Property(models.Model):
    property_id = models.AutoField(primary_key=True)
    landlord = models.ForeignKey(Landlord, on_delete=models.CASCADE)
    address_line_1 = models.CharField(max_length=200)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)
    square_footage = models.IntegerField()
    bedrooms = models.IntegerField()
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1)

    def __str__(self):
        return f"{self.address_line_1}, {self.city}, {self.state}"

    class Meta:
        verbose_name_plural = "Properties"

class Lease(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    lease_id = models.AutoField(primary_key=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    lease_start_date = models.DateField()
    lease_end_date = models.DateField()
    monthly_rent = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')

    def __str__(self):
        return f"Lease for {self.property} ({self.status})"
        
    def update_status(self):
        """Update lease status based on tenant confirmations"""
        lease_tenants = self.leasetenant_set.all()
        if not lease_tenants.exists():
            self.status = 'inactive'
        else:
            self.status = 'active' if all(lt.confirmed for lt in lease_tenants) else 'inactive'
        self.save()

class LeaseTenant(models.Model):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    confirmed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['lease', 'tenant'],
                name='unique_lease_tenant'
            )
        ]

    def __str__(self):
        return f"{self.tenant} - {self.lease}"
