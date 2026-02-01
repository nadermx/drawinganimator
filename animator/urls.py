from django.urls import path
from animator.views import (
    AnimatePage,
    AnimateAPI,
    AnimationStatus,
    animation_callback,
    GalleryPage,
    MyAnimations,
)

urlpatterns = [
    path('', AnimatePage.as_view(), name='animate'),
    path('gallery/', GalleryPage.as_view(), name='gallery'),
    path('my-animations/', MyAnimations.as_view(), name='my_animations'),

    # API endpoints
    path('api/animate/', AnimateAPI.as_view(), name='api_animate'),
    path('api/animation/status/<str:animation_id>/', AnimationStatus.as_view(), name='api_animation_status'),
    path('api/animation/callback/', animation_callback, name='api_animation_callback'),
]
