"""
Management command to run monthly supply consumption cycle and logistics analytics.
Usage: python manage.py generate_monthly_analytics
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.ai_analytics import AIAnalyticsEngine
from core.models import Notification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate monthly supply consumption cycles and logistics analytics'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📈 Starting monthly analytics generation...'))
        
        try:
            # Generate monthly analytics
            self.stdout.write('📊 Analyzing supply consumption cycles...')
            AIAnalyticsEngine.generate_monthly_analytics()
            self.stdout.write(self.style.SUCCESS('✓ Supply consumption cycles updated'))
            
            # Create system notification
            Notification.objects.create(
                notification_type='ANALYTICS_UPDATE',
                title='Monthly Analytics Updated',
                message='Supply Consumption Cycles and Logistics Analytics have been updated for the previous month.',
                action_required=False,
            )
            
            self.stdout.write(self.style.SUCCESS('✓ Monthly analytics notification created'))
            self.stdout.write(self.style.SUCCESS('✅ Monthly analytics completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error during analytics: {str(e)}'))
            logger.error(f'Error in generate_monthly_analytics: {str(e)}', exc_info=True)
