from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, timedelta
from ...utils import generate_sessions_from_coursegroups

class Command(BaseCommand):
    help = 'Generate sessions from CourseGroup schedules for a date range or next N weeks'

    def add_arguments(self, parser):
        parser.add_argument('--start', type=str, help='Start date YYYY-MM-DD')
        parser.add_argument('--end', type=str, help='End date YYYY-MM-DD')
        parser.add_argument('--weeks', type=int, default=4, help='Number of weeks from today to generate if start/end not provided')
        parser.add_argument('--force', action='store_true', help='Force updates of existing sessions when different')

    def handle(self, *args, **options):
        start = options.get('start')
        end = options.get('end')
        weeks = options.get('weeks')
        force = options.get('force')

        if start and end:
            try:
                start_date = datetime.strptime(start, '%Y-%m-%d').date()
                end_date = datetime.strptime(end, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Dates must be in YYYY-MM-DD format')
        else:
            today = timezone.now().date()
            start_date = today
            end_date = today + timedelta(weeks=weeks)

        self.stdout.write(self.style.NOTICE(f'Generating sessions from {start_date} to {end_date} (force={force})'))
        summary = generate_sessions_from_coursegroups(start_date, end_date, force=force)

        self.stdout.write(self.style.SUCCESS('Generation complete:'))
        for k, v in summary.items():
            self.stdout.write(f'  {k}: {v}')
