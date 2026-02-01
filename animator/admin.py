from django.contrib import admin
from animator.models import Animation, AnimationPreset, GalleryItem


@admin.register(AnimationPreset)
class AnimationPresetAdmin(admin.ModelAdmin):
    list_display = ['name', 'code_name', 'is_premium', 'is_active', 'sort_order']
    list_filter = ['is_premium', 'is_active']
    search_fields = ['name', 'code_name']
    ordering = ['sort_order', 'name']


@admin.register(Animation)
class AnimationAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'user', 'preset', 'status', 'output_format', 'created_at']
    list_filter = ['status', 'output_format', 'preset', 'add_watermark']
    search_fields = ['uuid', 'user__email', 'ip_address']
    readonly_fields = ['uuid', 'created_at', 'started_at', 'completed_at', 'processing_time']
    date_hierarchy = 'created_at'


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'animation', 'is_featured', 'is_active', 'sort_order']
    list_filter = ['is_featured', 'is_active']
    search_fields = ['title', 'description']
