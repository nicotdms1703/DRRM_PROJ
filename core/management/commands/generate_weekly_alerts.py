"""
Management command to run weekly AI analytics for consumption tracking and restock alerts.
Usage: python manage.py generate_weekly_alerts
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.ai_analytics import AIAnalyticsEngine
from core.models import Notification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate weekly consumption analytics and restock alerts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Starting weekly AI analytics...'))
        
        try:
            # Calculate weekly consumption
            self.stdout.write('📊 Calculating weekly consumption patterns...')
            AIAnalyticsEngine.calculate_weekly_consumption()
            self.stdout.write(self.style.SUCCESS('✓ Weekly consumption data calculated'))
            
            # Generate restock alerts
            self.stdout.write('⚠️  Generating restock alerts...')
            alerts_created = AIAnalyticsEngine.generate_restock_alerts()
            self.stdout.write(self.style.SUCCESS(f'✓ Created/Updated {alerts_created} alerts'))

            # Generate maintenance/integrity alerts
            self.stdout.write('🛠️  Generating maintenance/integrity alerts...')
            maintenance_created = AIAnalyticsEngine.generate_maintenance_alerts()
            self.stdout.write(self.style.SUCCESS(f'✓ Created/Updated {maintenance_created} maintenance alerts'))
            
            # Create notifications for critical/high alerts
            from core.models import RestockAlert
            critical_alerts = RestockAlert.objects.filter(
                status='ACTIVE',
                severity__in=['CRITICAL', 'HIGH']
            )
            
            for alert in critical_alerts:
                Notification.objects.update_or_create(
                    notification_type='RESTOCK_ALERT',
                    item=alert.item,
                    defaults={
                        'title': f'{alert.get_severity_display()}: {alert.item.name}',
                        'message': alert.reason,
                        'action_required': True,
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'✓ Created {critical_alerts.count()} notifications'))
            self.stdout.write(self.style.SUCCESS('✅ Weekly AI analytics completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error during analytics: {str(e)}'))
            logger.error(f'Error in generate_weekly_alerts: {str(e)}', exc_info=True)
