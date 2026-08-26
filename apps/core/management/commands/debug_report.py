from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Debug report query'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('REPORT QUERY DEBUG'))
        self.stdout.write('=' * 80)

        sql = """
        SELECT 
            DATE(created_at) as day,
            COUNT(id) as total_invoices,
            COUNT(CASE WHEN status IN ('paid', 'overpaid') THEN 1 END) as paid_invoices,
            SUM(amount) as total_amount,
            (SELECT SUM(credited_amount) FROM core_payment WHERE core_payment.invoice_id = core_invoice.id) as total_received,
            (SELECT SUM(amount) FROM core_ledgerentry 
             WHERE core_ledgerentry.invoice_id = core_invoice.id 
             AND core_ledgerentry.entry_type = 'fee') as total_fee
        FROM core_invoice
        WHERE project_id IN (SELECT id FROM core_project WHERE merchant_id = 1)
        GROUP BY DATE(created_at)
        ORDER BY day;
        """

        self.stdout.write(self.style.SUCCESS('SQL QUERY:'))
        self.stdout.write('-' * 80)
        self.stdout.write(sql)
        self.stdout.write('-' * 80)

        self.stdout.write(self.style.SUCCESS('\nEXPLAIN QUERY PLAN:'))
        self.stdout.write('-' * 80)
        
        with connection.cursor() as cursor:
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            rows = cursor.fetchall()
            for row in rows:
                self.stdout.write(str(row))

        self.stdout.write(self.style.SUCCESS('\nQUERY RESULT:'))
        self.stdout.write('-' * 80)
        
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            if rows:
                headers = ['day', 'total_invoices', 'paid_invoices', 'total_amount', 'total_received', 'total_fee']
                self.stdout.write(' | '.join(headers))
                self.stdout.write('-' * 80)
                for row in rows[:10]:  # Показываем первые 10 записей
                    self.stdout.write(' | '.join(str(col) for col in row))
            else:
                self.stdout.write('No data found')