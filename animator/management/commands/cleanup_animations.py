from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from animator.models import Animation, GalleryItem


class Command(BaseCommand):
    help = 'Clean up old animations: delete files and DB records'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
        parser.add_argument('--days', type=int, default=14, help='Delete animations older than N days (default: 14)')
        parser.add_argument('--batch-size', type=int, default=500, help='Delete in batches of N (default: 500)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        batch_size = options['batch_size']

        cutoff = timezone.now() - timedelta(days=days)

        # Protect animations used in gallery
        gallery_animation_ids = set(
            GalleryItem.objects.filter(is_active=True).values_list('animation_id', flat=True)
        )

        candidates = Animation.objects.filter(
            created_at__lt=cutoff,
        ).exclude(
            id__in=gallery_animation_ids,
        )

        total = candidates.count()
        self.stdout.write(f"Found {total} animations older than {days} days")
        self.stdout.write(f"Protected gallery animations: {len(gallery_animation_ids)}")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to clean up"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN - Would delete {total} animations and their files"))
            return

        deleted_total = 0
        files_deleted = 0
        while True:
            batch = list(candidates[:batch_size])
            if not batch:
                break

            for animation in batch:
                # Delete actual files from disk
                for field in [animation.input_image, animation.output_file, animation.thumbnail]:
                    if field and field.name:
                        try:
                            field.delete(save=False)
                            files_deleted += 1
                        except Exception:
                            pass

            batch_ids = [a.id for a in batch]
            deleted, _ = Animation.objects.filter(id__in=batch_ids).delete()
            deleted_total += deleted
            self.stdout.write(f"  Deleted batch of {deleted} (total: {deleted_total})")

        self.stdout.write(self.style.SUCCESS(f"Cleaned up {deleted_total} animations, {files_deleted} files"))
