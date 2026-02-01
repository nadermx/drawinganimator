from django.core.management.base import BaseCommand
from animator.models import AnimationPreset


class Command(BaseCommand):
    help = 'Seeds the database with default animation presets'

    def handle(self, *args, **options):
        presets = [
            {
                'code_name': 'walk',
                'name': 'Walking',
                'description': 'A natural walking cycle animation',
                'icon': 'bi-person-walking',
                'is_premium': False,
                'sort_order': 1,
            },
            {
                'code_name': 'run',
                'name': 'Running',
                'description': 'A running cycle animation',
                'icon': 'bi-person-running',
                'is_premium': False,
                'sort_order': 2,
            },
            {
                'code_name': 'jump',
                'name': 'Jumping',
                'description': 'A jump animation',
                'icon': 'bi-arrow-up-circle',
                'is_premium': False,
                'sort_order': 3,
            },
            {
                'code_name': 'wave',
                'name': 'Waving',
                'description': 'A friendly wave animation',
                'icon': 'bi-hand-wave',
                'is_premium': False,
                'sort_order': 4,
            },
            {
                'code_name': 'dance',
                'name': 'Dancing',
                'description': 'A fun dance animation',
                'icon': 'bi-music-note-beamed',
                'is_premium': False,
                'sort_order': 5,
            },
            {
                'code_name': 'dab',
                'name': 'Dabbing',
                'description': 'The classic dab move',
                'icon': 'bi-star',
                'is_premium': True,
                'sort_order': 6,
            },
            {
                'code_name': 'zombie',
                'name': 'Zombie Walk',
                'description': 'Spooky zombie walking animation',
                'icon': 'bi-person-arms-up',
                'is_premium': True,
                'sort_order': 7,
            },
            {
                'code_name': 'backflip',
                'name': 'Backflip',
                'description': 'An impressive backflip',
                'icon': 'bi-arrow-clockwise',
                'is_premium': True,
                'sort_order': 8,
            },
            {
                'code_name': 'cartwheel',
                'name': 'Cartwheel',
                'description': 'A cartwheel animation',
                'icon': 'bi-circle',
                'is_premium': True,
                'sort_order': 9,
            },
            {
                'code_name': 'gangnam',
                'name': 'Gangnam Style',
                'description': 'The iconic dance move',
                'icon': 'bi-music-note',
                'is_premium': True,
                'sort_order': 10,
            },
            {
                'code_name': 'clap',
                'name': 'Clapping',
                'description': 'A clapping animation',
                'icon': 'bi-hand-thumbs-up',
                'is_premium': True,
                'sort_order': 11,
            },
            {
                'code_name': 'spin',
                'name': 'Spin',
                'description': 'A spinning animation',
                'icon': 'bi-arrow-repeat',
                'is_premium': True,
                'sort_order': 12,
            },
        ]

        created = 0
        updated = 0

        for preset_data in presets:
            preset, was_created = AnimationPreset.objects.update_or_create(
                code_name=preset_data['code_name'],
                defaults=preset_data
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully seeded presets: {created} created, {updated} updated')
        )
