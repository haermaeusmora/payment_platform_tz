from django.core.management.base import BaseCommand
from ...services.rate_client import RateServiceClient
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test rate service client'

    def handle(self, *args, **options):
        self.stdout.write('Testing Rate Service...')

        self.stdout.write('\n1. Health check:')
        health = RateServiceClient.health_check()
        if health:
            self.stdout.write(self.style.SUCCESS('   ✅ Service is healthy'))
        else:
            self.stdout.write(self.style.WARNING('   ⚠️ Service is not available'))

        self.stdout.write('\n2. Getting rates:')
        
        test_pairs = [
            ('USD', 'EUR'),
            ('EUR', 'USD'),
            ('USD', 'RUB'),
            ('EUR', 'UAH'),
        ]
        
        for from_cur, to_cur in test_pairs:
            rate = RateServiceClient.get_rate(from_cur, to_cur)
            if rate:
                self.stdout.write(f'   {from_cur}/{to_cur} = {rate}')
            else:
                self.stdout.write(self.style.WARNING(f'   {from_cur}/{to_cur} = None'))

        self.stdout.write('\n3. Bulk rates:')
        rates = RateServiceClient.get_bulk_rates('USD', ['EUR', 'RUB', 'UAH', 'GBP'])
        for currency, rate in rates.items():
            self.stdout.write(f'   USD/{currency} = {rate}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Test complete!'))