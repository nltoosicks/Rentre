from django import forms
from django.core.exceptions import ValidationError
from .models import Lease, Tenant, Property

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['property_name', 'address_line_1', 'address_line_2', 'city', 
                 'state', 'zip_code', 'square_footage', 'bedrooms', 'bathrooms']
        widgets = {
            'property_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'square_footage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.5'})
        }

class LeaseCreateForm(forms.ModelForm):
    tenant_emails = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Enter tenant email addresses separated by commas'
    )

    class Meta:
        model = Lease
        fields = ['tenant_emails', 'lease_start_date', 'lease_end_date', 'monthly_rent']
        widgets = {
            'lease_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'lease_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'monthly_rent': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'})
        }

    def clean_tenant_emails(self):
        emails = [email.strip() for email in self.cleaned_data['tenant_emails'].split(',')]
        tenants = []
        invalid_emails = []
        
        for email in emails:
            if not email:
                continue
            try:
                tenant = Tenant.objects.get(user__email=email)
                tenants.append(tenant)
            except Tenant.DoesNotExist:
                invalid_emails.append(email)
        
        if invalid_emails:
            raise ValidationError(
                f"No tenant accounts found for these emails: {', '.join(invalid_emails)}"
            )
        
        return emails

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('lease_start_date')
        end_date = cleaned_data.get('lease_end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date")
        
        return cleaned_data

class LeaseEditForm(forms.ModelForm):
    tenant_emails = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Enter tenant email addresses separated by commas'
    )
    
    class Meta:
        model = Lease
        fields = ['lease_start_date', 'lease_end_date', 'monthly_rent']
        widgets = {
            'lease_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'lease_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'monthly_rent': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            current_tenants = self.instance.leasetenant_set.all()
            self.fields['tenant_emails'].initial = ", ".join(
                [lt.tenant.user.email for lt in current_tenants]
            )
        self.order_fields(['tenant_emails', 'lease_start_date', 'lease_end_date', 'monthly_rent'])

    def clean_tenant_emails(self):
        emails = [email.strip() for email in self.cleaned_data['tenant_emails'].split(',')]
        tenants = []
        invalid_emails = []
        
        for email in emails:
            if not email:  # Skip empty emails
                continue
            try:
                tenant = Tenant.objects.get(user__email=email)
                tenants.append(tenant)
            except Tenant.DoesNotExist:
                invalid_emails.append(email)
        
        if invalid_emails:
            raise ValidationError(
                f"No tenant accounts found for these emails: {', '.join(invalid_emails)}"
            )
        
        return emails

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('lease_start_date')
        end_date = cleaned_data.get('lease_end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date")
        
        return cleaned_data
    
