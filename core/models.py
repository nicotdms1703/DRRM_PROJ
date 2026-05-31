from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Item(models.Model):
    CATEGORY_CHOICES = [
        ('Equipment', 'Equipment'),
        ('Consumable', 'Consumable'),
        ('Medical', 'Medical'),
        ('Safety', 'Safety'),
        ('Tools', 'Tools'),
    ]
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Low Stock', 'Low Stock'),
        ('Out of Stock', 'Out of Stock'),
        ('Maintenance', 'Maintenance'),
    ]

    name = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="DRRM-XXX-000")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Equipment')
    barcode = models.CharField(max_length=100, unique=True, default='', help_text="QR or Barcode value")
    description = models.TextField(blank=True)
    quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)
    max_capacity = models.IntegerField(null=True, blank=True, help_text="Maximum inventory capacity for this item")
    # Lifecycle / integrity fields
    lifespan_days = models.IntegerField(null=True, blank=True, help_text="Approx lifespan in days (optional)")
    integrity_score = models.FloatField(default=100.0, help_text="0-100 integrity score; lower means more worn")
    last_inspection = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def qr_payload(self):
        """Format: Code|Name|Category|ID"""
        return f"{self.item_code}|{self.name}|{self.category}|{self.id}"

    def save(self, *args, **kwargs):
        # Ensure a unique item_code is generated if missing.
        if not self.item_code:
            prefix = "DRRM"
            cat_short = self.category[:3].upper()
            # Find the highest numeric suffix for this category.
            existing_codes = Item.objects.filter(category=self.category).values_list('item_code', flat=True)
            max_num = 0
            for code in existing_codes:
                try:
                    # Expected format: DRRM-XXX-###
                    num_part = code.split('-')[-1]
                    num = int(num_part)
                    if num > max_num:
                        max_num = num
                except Exception:
                    continue
            self.item_code = f"{prefix}-{cat_short}-{max_num + 1:03d}"
        
        # Preserve existing logic for status and other fields.
        if not self.barcode:
            self.barcode = self.item_code

        if self.quantity <= 0:
            self.status = 'Out of Stock'
        elif self.quantity <= self.low_stock_threshold:
            self.status = 'Low Stock'
        else:
            self.status = 'Available'

        # Integrity-based maintenance status
        try:
            if self.integrity_score is not None and self.integrity_score <= 30:
                self.status = 'Maintenance'
        except Exception:
            pass

        super().save(*args, **kwargs)

        # Check lifespan after initial save (created_at is available)
        try:
            if self.lifespan_days and self.created_at:
                age_days = (timezone.now().date() - self.created_at.date()).days
                if age_days >= self.lifespan_days:
                    # mark for maintenance if lifespan exceeded
                    if self.status != 'Maintenance':
                        self.status = 'Maintenance'
                        super().save(update_fields=['status', 'updated_at'])
        except Exception:
            pass

    def __str__(self):
        return f"{self.name} ({self.item_code})"

    @property
    def available_out_quantity(self):
        return max(0, self.quantity)

    @property
    def available_in_quantity(self):
        if self.max_capacity is None:
            return None
        return max(0, self.max_capacity - self.quantity)

    @property
    def stock_capacity_status(self):
        if self.max_capacity is None:
            return 'No capacity limit set.'
        return f"{self.quantity} / {self.max_capacity} currently stocked."

class StockTransaction(models.Model):
    TRANSACTION_TYPE = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=3, choices=TRANSACTION_TYPE)
    quantity = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.type} - {self.item.name} ({self.quantity})"

class Borrowing(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Returned', 'Returned'),
    ]
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='borrowings')
    borrower_name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=1)
    date_borrowed = models.DateTimeField(auto_now_add=True)
    return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    # Condition tracking for borrowed items
    wear_score = models.FloatField(null=True, blank=True, help_text='0-100 wear/damage score reported on return')
    condition_on_return = models.TextField(blank=True, help_text='Free-text condition notes on return')
    inspected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.borrower_name} borrowed {self.item.name}"



class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"

# Keeping Task and TaskItem for legacy/extra functionality if needed, or I can remove them.
# The user asked for specific models, so I'll prioritize those.
class Task(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('In Use', 'In Use'),
        ('Completed', 'Completed'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_by = models.CharField(max_length=100, default='Admin')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class TaskItem(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.item.name} for {self.task.title}"


# AI-POWERED ANALYTICS & CONSUMPTION TRACKING MODELS
class ConsumptionAnalytics(models.Model):
    """Weekly consumption tracking for AI-driven inventory management."""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='consumption_analytics')
    week_start = models.DateField()  # Monday of the week
    week_end = models.DateField()
    consumable_consumed = models.IntegerField(default=0)  # Units consumed from stock transactions
    borrowed_quantity = models.IntegerField(default=0)  # Units borrowed
    total_movement = models.IntegerField(default=0)  # Total units in/out
    avg_daily_consumption = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('item', 'week_start')
        ordering = ['-week_start']

    def __str__(self):
        return f"{self.item.name} - Week of {self.week_start}"


class RestockAlert(models.Model):
    """AI-Generated restock alerts based on consumption patterns."""
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical - Out of Stock Risk'),
        ('HIGH', 'High - Low Stock Warning'),
        ('MEDIUM', 'Medium - Preventive Restock'),
        ('LOW', 'Low - Routine Check'),
    ]
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESTOCKED', 'Restocked'),
        ('RESOLVED', 'Resolved'),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='restock_alerts')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    
    # AI Analysis
    current_quantity = models.IntegerField()
    predicted_quantity = models.IntegerField()  # Predicted quantity after 7 days
    recommended_restock = models.IntegerField()  # AI recommendation
    predicted_stockout_date = models.DateField(null=True, blank=True)  # When it will run out
    
    # Reasoning
    avg_weekly_consumption = models.FloatField()
    consumption_trend = models.CharField(max_length=20, choices=[
        ('STABLE', 'Stable'),
        ('INCREASING', 'Increasing'),
        ('DECREASING', 'Decreasing'),
    ])
    reason = models.TextField()  # Why this alert was generated
    
    alert_generated_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')

    class Meta:
        ordering = ['-alert_generated_at']

    def __str__(self):
        return f"{self.get_severity_display()} - {self.item.name}"


class MaintenanceAlert(models.Model):
    """AI-Generated maintenance alerts based on integrity and lifespan."""
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical - Replace Now'),
        ('HIGH', 'High - Replace Soon'),
        ('MEDIUM', 'Medium - Schedule Maintenance'),
        ('LOW', 'Low - Monitor'),
    ]
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('MAINTAINED', 'Maintained'),
        ('REPLACED', 'Replaced'),
        ('RESOLVED', 'Resolved'),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='maintenance_alerts')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')

    current_integrity = models.FloatField(null=True, blank=True)
    predicted_end_of_life = models.DateField(null=True, blank=True)
    recommended_action = models.CharField(max_length=200, blank=True)
    reason = models.TextField(blank=True)

    alert_generated_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_maintenance_alerts')

    class Meta:
        ordering = ['-alert_generated_at']

    def __str__(self):
        return f"{self.get_severity_display()} - {self.item.name}"


class SupplyConsumptionCycle(models.Model):
    """Monthly supply consumption cycle analysis for analytics engine."""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='supply_cycles')
    month_year = models.DateField()  # First day of the month
    
    # Consumption Metrics
    total_consumed = models.IntegerField(default=0)
    total_borrowed = models.IntegerField(default=0)
    total_restocked = models.IntegerField(default=0)
    restock_count = models.IntegerField(default=0)  # Number of restock events
    
    # Trend Analysis
    avg_daily_consumption = models.FloatField(default=0.0)
    consumption_variance = models.FloatField(default=0.0)  # Standard deviation
    peak_consumption_day = models.IntegerField(null=True, blank=True)  # Day of month with highest consumption
    
    # Category Analysis
    category = models.CharField(max_length=20)
    deployment_status = models.CharField(max_length=50, choices=[
        ('STABLE', 'Stable Supply'),
        ('CRITICAL', 'Critical Consumption'),
        ('BUILDING', 'Building Reserves'),
        ('TRANSITIONING', 'Transitioning'),
    ], default='STABLE')
    
    # Forecasting
    predicted_consumption_next_month = models.FloatField(default=0.0)
    min_restock_recommended = models.IntegerField(default=0)
    optimal_restock_quantity = models.IntegerField(default=0)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('item', 'month_year')
        ordering = ['-month_year']

    def __str__(self):
        return f"{self.item.name} - {self.month_year.strftime('%B %Y')}"


class LogisticsAnalytics(models.Model):
    """Logistics and deployment analytics with monthly updates."""
    month_year = models.DateField()  # First day of the month
    
    # Borrowing/Deployment Analytics
    total_borrowing_events = models.IntegerField(default=0)
    total_units_deployed = models.IntegerField(default=0)
    avg_deployment_duration_days = models.FloatField(default=0.0)
    active_deployments = models.IntegerField(default=0)
    
    # Return Rate Analytics
    on_time_returns = models.IntegerField(default=0)
    delayed_returns = models.IntegerField(default=0)
    return_rate_percentage = models.FloatField(default=0.0)
    
    # Category-wise Deployment
    equipment_deployed = models.IntegerField(default=0)
    consumable_deployed = models.IntegerField(default=0)
    medical_deployed = models.IntegerField(default=0)
    safety_deployed = models.IntegerField(default=0)
    tools_deployed = models.IntegerField(default=0)
    
    # Performance Metrics
    most_borrowed_item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='logistics_records')
    most_borrowed_category = models.CharField(max_length=20)
    logistics_efficiency_score = models.FloatField(default=0.0)  # 0-100
    
    # Trend
    trend = models.CharField(max_length=20, choices=[
        ('INCREASING', 'Increasing Deployment'),
        ('STABLE', 'Stable Operations'),
        ('DECREASING', 'Decreasing Deployment'),
    ], default='STABLE')
    
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month_year']

    def __str__(self):
        return f"Logistics Analytics - {self.month_year.strftime('%B %Y')}"


class Notification(models.Model):
    """Notification system for AI alerts and system events."""
    NOTIFICATION_TYPE = [
        ('RESTOCK_ALERT', 'Restock Alert'),
        ('LOW_STOCK', 'Low Stock Warning'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('OVERDUE_RETURN', 'Overdue Return'),
        ('ANALYTICS_UPDATE', 'Analytics Update'),
        ('SYSTEM', 'System Message'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_required = models.BooleanField(default=False)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.title}"


# RESPONDER ATTENDANCE MODELS
class Responder(models.Model):
    name = models.CharField(max_length=150)
    registration_no = models.CharField(max_length=100, unique=True, help_text="e.g. BLSHP-24-DOHCaraga-5407")
    qr_payload = models.CharField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.qr_payload:
            self.qr_payload = self.registration_no
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.registration_no})"

class ResponderLog(models.Model):
    responder = models.ForeignKey(Responder, on_delete=models.CASCADE, related_name='logs')
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    total_duration_seconds = models.IntegerField(default=0)
    
    @property
    def formatted_duration(self):
        if not self.logout_time:
            return "Active"
        sec = self.total_duration_seconds
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        
        parts = []
        if h > 0:
            parts.append(f"{h}h")
        if m > 0:
            parts.append(f"{m}m")
        if s > 0 or not parts:
            parts.append(f"{s}s")
        return " ".join(parts)
    
    def __str__(self):
        return f"{self.responder.name} Log - {self.login_time.date()}"


# PATIENT ASSESSMENT MODELS
class Patient(models.Model):
    full_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=20, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    age = models.IntegerField()
    cellphone_number = models.CharField(max_length=20)
    address = models.TextField()
    program_year = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

class PatientAssessment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='assessments')
    assessment_number = models.CharField(max_length=50, unique=True, blank=True)
    date = models.DateField(default=timezone.now)
    time = models.TimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Ongoing')
    
    # Section C - Complaints (Store as list of strings)
    complaints = models.JSONField(default=list, blank=True)
    
    # Section D - Symptoms (Store as list of strings)
    symptoms = models.JSONField(default=list, blank=True)
    
    # Section E - Vital Signs
    pulse = models.CharField(max_length=50, blank=True)
    spo2 = models.CharField(max_length=50, blank=True)
    respiration_rate = models.CharField(max_length=50, blank=True)
    blood_pressure = models.CharField(max_length=50, blank=True)
    temperature = models.CharField(max_length=50, blank=True)
    
    # Section F - DCAP-BTLS (Store as list of dicts: {'item': 'Deformities', 'remarks': '...'})
    dcap_btls = models.JSONField(default=list, blank=True)
    
    # Section G - Body Injury Diagram (Store coordinates & notes)
    body_assessment = models.JSONField(default=list, blank=True)
    
    # Section H - SAMPLE Assessment
    medical_history_checkboxes = models.JSONField(default=list, blank=True)
    signs_symptoms = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    medications = models.TextField(blank=True)
    past_medical_history = models.TextField(blank=True)
    last_oral_intake = models.TextField(blank=True)
    events_leading_to_incident = models.TextField(blank=True)
    
    # Section I - First Aid Notes
    first_aid_notes = models.TextField(blank=True)
    
    # Section J - Attending Personnel
    responder_name = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=100, blank=True)
    signature_data = models.TextField(blank=True)
    date_signed = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.assessment_number:
            current_year = timezone.now().year
            count = PatientAssessment.objects.filter(assessment_number__startswith=f'OFA-{current_year}').count()
            self.assessment_number = f"OFA-{current_year}-{(count + 1):06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.assessment_number} - {self.patient.full_name}"
