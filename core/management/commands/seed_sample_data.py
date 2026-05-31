from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Item, StockTransaction, Borrowing
from core.ai_analytics import AIAnalyticsEngine


class Command(BaseCommand):
    help = 'Seed sample consumable and borrowable items with transactions for demo/testing.'

    def handle(self, *args, **options):
        now = timezone.now()

        # Consumable items
        consumables = [
            {'name': 'Bottled Water', 'category': 'Consumable', 'quantity': 2, 'low_stock_threshold': 5, 'max_capacity': 4},
            {'name': 'First Aid Bandage', 'category': 'Medical', 'quantity': 10, 'low_stock_threshold': 8, 'max_capacity': 20},
            {'name': 'N95 Masks Box', 'category': 'Safety', 'quantity': 20, 'low_stock_threshold': 10, 'max_capacity': 30},
        ]

        for c in consumables:
            defaults = {
                'category': c['category'],
                'quantity': c['quantity'],
                'low_stock_threshold': c['low_stock_threshold'],
                'max_capacity': c['max_capacity'],
            }
            item = Item.objects.filter(name=c['name'], category=c['category']).first()
            if item:
                Item.objects.filter(name=c['name'], category=c['category']).update(**defaults)
            else:
                item = Item.objects.create(name=c['name'], **defaults)

            # Create a few stock out transactions to simulate consumption
            for i in range(3):
                StockTransaction.objects.create(
                    item=item,
                    type='OUT',
                    quantity=1 + i,
                    timestamp=now - timedelta(days=i + 1),
                )

        # Borrowable items (equipment/tools) with lifespan and integrity
        borrowables = [
            {'name': 'Portable Generator', 'category': 'Equipment', 'quantity': 2, 'lifespan_days': 3650, 'integrity_score': 50, 'max_capacity': 5},
            {'name': 'Chainsaw', 'category': 'Tools', 'quantity': 1, 'lifespan_days': 365, 'integrity_score': 25, 'max_capacity': 2},
            {'name': 'Handheld Radio', 'category': 'Equipment', 'quantity': 5, 'lifespan_days': 1825, 'integrity_score': 70, 'max_capacity': 10},
        ]

        for b in borrowables:
            defaults = {
                'category': b['category'],
                'quantity': b['quantity'],
                'lifespan_days': b['lifespan_days'],
                'integrity_score': b['integrity_score'],
                'max_capacity': b['max_capacity'],
            }
            item = Item.objects.filter(name=b['name'], category=b['category']).first()
            if item:
                Item.objects.filter(name=b['name'], category=b['category']).update(**defaults)
            else:
                item = Item.objects.create(name=b['name'], **defaults)

            # Create a returned borrowing with wear score to simulate condition reports
            Borrowing.objects.create(
                item=item,
                borrower_name='Seeder',
                quantity=1,
                date_borrowed=now - timedelta(days=10),
                return_date=now - timedelta(days=3),
                status='Returned',
                wear_score=max(0, b['integrity_score'] - 30),
                condition_on_return='Used in field; visible wear',
                inspected=True,
            )

        # Run weekly analytics to generate alerts based on seeded data
        self.stdout.write('Running weekly analytics to generate alerts...')
        AIAnalyticsEngine.calculate_weekly_consumption()
        restock_alerts = AIAnalyticsEngine.generate_restock_alerts()
        maintenance_alerts = AIAnalyticsEngine.generate_maintenance_alerts()

        self.stdout.write(self.style.SUCCESS(f'Created {restock_alerts} restock alerts'))
        self.stdout.write(self.style.SUCCESS(f'Created {maintenance_alerts} maintenance alerts'))
