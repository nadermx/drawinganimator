from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from app.utils import Utils


class AnimationPreset(models.Model):
    """Pre-defined animation styles that can be applied to drawings."""
    name = models.CharField(max_length=100)
    code_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='bi-play-circle')
    motion_file = models.CharField(max_length=255, blank=True, help_text='Path to motion template video')
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Animation(models.Model):
    """Tracks individual animation jobs."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    )

    FORMAT_GIF = 'gif'
    FORMAT_MP4 = 'mp4'
    FORMAT_WEBM = 'webm'
    FORMAT_CHOICES = (
        (FORMAT_GIF, 'GIF'),
        (FORMAT_MP4, 'MP4'),
        (FORMAT_WEBM, 'WebM'),
    )

    uuid = models.CharField(default=Utils.generate_uuid, max_length=100, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True, help_text='For anonymous users')

    # Input
    input_image = models.ImageField(upload_to='animations/inputs/%Y/%m/')
    input_image_url = models.URLField(blank=True)

    # Processing settings
    preset = models.ForeignKey(AnimationPreset, on_delete=models.SET_NULL, null=True)
    output_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default=FORMAT_GIF)
    duration = models.FloatField(default=3.0, help_text='Animation duration in seconds')
    fps = models.IntegerField(default=24)
    loop = models.BooleanField(default=True)
    add_watermark = models.BooleanField(default=True)

    # Output
    output_file = models.FileField(upload_to='animations/outputs/%Y/%m/', blank=True)
    output_url = models.URLField(blank=True)
    thumbnail = models.ImageField(upload_to='animations/thumbnails/%Y/%m/', blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    progress = models.IntegerField(default=0, help_text='Progress percentage 0-100')
    error_message = models.TextField(blank=True)
    job_id = models.CharField(max_length=100, blank=True, help_text='Background job ID')

    # API tracking
    api_request_id = models.CharField(max_length=100, blank=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Analytics
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Animation {self.uuid[:8]} - {self.status}"

    @property
    def processing_time(self):
        """Returns processing time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @staticmethod
    def get_user_daily_count(user=None, session_key=None, ip_address=None):
        """Count animations created today by user/session/IP."""
        today = timezone.now().date()
        queryset = Animation.objects.filter(created_at__date=today)

        if user and user.is_authenticated:
            return queryset.filter(user=user).count()
        elif session_key:
            return queryset.filter(session_key=session_key).count()
        elif ip_address:
            return queryset.filter(ip_address=ip_address).count()
        return 0


class GalleryItem(models.Model):
    """Curated gallery of example animations."""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    animation = models.ForeignKey(Animation, on_delete=models.CASCADE)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-is_featured', 'sort_order', '-created_at']
        verbose_name_plural = 'Gallery Items'

    def __str__(self):
        return self.title
