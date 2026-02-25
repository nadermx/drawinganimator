# DrawingAnimator.com - Audit & Expansion Plan

## Project Overview

DrawingAnimator.com is an AI-powered image-to-video animation platform using Stable Video Diffusion on the GPU backend. Users upload ANY drawing (not just characters -- landscapes, objects, abstract art), select a motion preset and intensity, and the system generates an animated video. The platform features a curated gallery, user animation history, and a freemium model: Free users get 5 animations/day as GIF-only with watermark, Pro users get unlimited MP4/WebM without watermark.

**Server**: 140.82.28.166 (shared with animateadrawing)
**Local Path**: /home/john/drawinganimator
**Server Path**: /home/www/drawinganimator
**API**: api.drawinganimator.com (CNAME to GPU server 38.248.6.142)
**GPU Endpoint**: `/v1/animate/` on api.imageeditor.ai

---

## Current State

### Architecture
- Django-based frontend with `animator` app
- 3 models: AnimationPreset, Animation, GalleryItem
- Simpler than animateadrawing -- single-page workflow, no project/scene/timeline system
- Animation model tracks full lifecycle: PENDING > PROCESSING > COMPLETED/FAILED
- Polls GPU backend for status via `check_api_status()` using `/v1/animate/results/`
- Daily rate limiting per user/session/IP via `get_user_daily_count()`
- Gallery system with featured items for showcase
- Callback endpoint for GPU to push completion notifications

### Monetization
- Credits-based via CustomUser.credits (standard shared pattern)
- Free tier: `config.RATE_LIMIT` animations/day, GIF-only, with watermark
- Pro tier: `config.RATE_LIMIT_PRO` animations/day, MP4/WebM, no watermark
- Premium presets gated behind Pro plan
- Stripe, Square, PayPal payment processors

### Models Detail
- **AnimationPreset**: name, code_name, description, icon, motion_file, is_premium, is_active, sort_order
- **Animation**: uuid, user, session_key, input_image, preset, output_format, duration, fps, loop, add_watermark, output_file, output_url, thumbnail, status, progress, error_message, job_id, api_request_id, ip_address, user_agent
- **GalleryItem**: title, description, animation (FK), is_featured, is_active, sort_order

### Missing Features (vs. Other Projects)
- NO view tracking (no view_count, download_count, last_viewed)
- NO smart retention / smart_expire
- NO sitemap
- NO bot detection
- NO expired status on Animation model
- NO team/collaboration support
- NO SEO page for individual animations (no public result URLs)

---

## Bugs & Issues

### Critical
1. **No content expiration** -- Animation outputs (GIF/MP4/WebM files) accumulate on server disk. No `delete_expired` or `smart_expire` command. On shared server with animateadrawing, disk will fill up.
2. **Callback endpoint has no authentication** -- `animation_callback` is `@csrf_exempt` and accepts any POST with a valid animation UUID. An attacker could mark any animation as completed with a fake `output_url` pointing to malicious content. Should validate with `GPU_SHARED_SECRET`.
3. **Session creation race condition** -- In `AnimateAPI.post()`, if `session_key` is None, `request.session.create()` is called. But in concurrent requests, this could create duplicate sessions or lose the session key before the animation record is saved.

### Medium
4. **Progress estimation is fake** -- `AnimationStatus.get()` increments `animation.progress` by 10 on each poll (capping at 90). This has no relation to actual GPU processing progress. Users see a progress bar that moves in 10% jumps.
5. **No file size validation on uploads** -- `AnimateAPI` checks content type and size (10MB max), which is good. But `input_image_url` field exists on the model with no corresponding URL-based upload flow. Dead field.
6. **Gallery items hardcoded to 24** -- `GalleryPage` returns at most 24 items with no pagination. No way for users to browse a larger gallery.
7. **Rate limit bypassed by session clearing** -- Daily count is tracked per session_key OR user OR IP. Anonymous users can clear cookies to get a new session_key, bypassing the limit. IP-based fallback helps, but shared IPs (corporate/VPN) could unfairly limit legitimate users.
8. **Bare except clauses** -- Multiple bare `except:` in `accounts/models.py` (lines 107, 227, 367, 386, 394, 437, 444, 478, 485, 534). Should use `except Exception:`.
9. **API response format inconsistency** -- `send_to_api()` maps GPU response format but handles edge cases poorly. If `uuid` is missing from response AND no `error` key, it returns `{'success': True}` with empty request_id.

### Low
10. **No thumbnail generation** -- Animation model has a `thumbnail` field but nothing generates thumbnails. Could auto-generate from first frame of animation.
11. **User agent truncated to 500 chars** -- Truncation is fine for storage but the full user agent is still received and processed. Not a bug, just noted.

---

## Test Suite

All tests should be placed in `/home/john/drawinganimator/animator/tests.py`.

### Model Tests
```
test_animation_preset_creation
test_animation_preset_ordering_by_sort_order
test_animation_preset_premium_flag
test_animation_creation_with_defaults
test_animation_uuid_uniqueness
test_animation_status_choices
test_animation_format_choices
test_animation_processing_time_property
test_animation_processing_time_none_when_incomplete
test_animation_get_user_daily_count_by_user
test_animation_get_user_daily_count_by_session
test_animation_get_user_daily_count_by_ip
test_animation_get_user_daily_count_resets_daily
test_gallery_item_creation
test_gallery_item_ordering_featured_first
```

### View Tests
```
test_animate_page_get_shows_presets
test_animate_page_shows_daily_limit_for_free_user
test_animate_page_shows_pro_limit_for_pro_user
test_animate_page_calculates_remaining_correctly
test_animate_api_rejects_no_image
test_animate_api_rejects_invalid_file_type
test_animate_api_rejects_oversized_file
test_animate_api_enforces_daily_limit
test_animate_api_forces_gif_for_free_users
test_animate_api_allows_mp4_for_pro_users
test_animate_api_rejects_premium_preset_for_free_user
test_animate_api_adds_watermark_for_free_user
test_animate_api_no_watermark_for_pro_user
test_animate_api_creates_animation_record
test_animate_api_sends_to_gpu_backend
test_animate_api_handles_gpu_failure_gracefully
test_animation_status_returns_current_state
test_animation_status_polls_gpu_on_processing
test_animation_status_marks_completed_on_done
test_animation_status_marks_failed_on_error
test_animation_status_returns_output_url_when_complete
test_animation_status_404_for_nonexistent
test_animation_callback_marks_completed
test_animation_callback_marks_failed
test_animation_callback_updates_progress
test_animation_callback_rejects_invalid_json
test_animation_callback_404_for_unknown_uuid
test_gallery_page_shows_featured_items
test_gallery_page_limits_to_24_items
test_my_animations_requires_login
test_my_animations_shows_user_animations_only
test_my_animations_ordered_by_created_at
```

### Integration Tests
```
test_full_animation_lifecycle_free_user
test_full_animation_lifecycle_pro_user
test_rate_limit_blocks_after_daily_max
test_gpu_api_timeout_handling
test_gpu_api_malformed_response_handling
```

### Security Tests
```
test_callback_endpoint_should_validate_secret
test_animate_api_session_handling
test_my_animations_cannot_see_other_user_animations
test_animation_status_no_cross_user_access
```

---

## Monetization Fixes

### Credit-per-Operation Pricing
The current system uses daily count limits rather than credits for animation. This should be converted to credit-based:

| Operation | Credit Cost |
|-----------|------------|
| GIF animation (480p) | 1 |
| MP4 animation (720p) | 2 |
| WebM animation (720p) | 2 |
| High-res animation (1080p) | 5 |
| Premium preset animation | +2 extra |
| Long duration (>5s) | +1 per 5s |

### Watermark-Free Single Purchase
- Allow free users to remove watermark from a single animation for 3 credits
- Currently watermark removal requires full Pro subscription

### Gallery Submission Rewards
- Users who submit animations to the public gallery get 5 bonus credits
- Featured gallery items give the creator ongoing credits (1 per 100 views)

---

## Feature Expansion

### Phase 1: Style Library & Motion Intensity (Priority: HIGH)
- **Style presets**: Not just motion type, but visual style -- oil painting, watercolor, pixel art, anime, sketch
- **Motion intensity slider**: Fine control over SVD `motion_bucket_id` (currently fixed per preset)
- **Custom duration**: Let users specify exact duration (1-10 seconds) instead of preset-fixed
- **Aspect ratio options**: Square (1:1), Portrait (9:16), Landscape (16:9), Custom
- **Before/after comparison**: Side-by-side view of original drawing vs animation

### Phase 2: Music Sync & Audio (Priority: HIGH)
- **Background music library**: Royalty-free music tracks to add to animations
- **Beat-sync animation**: Upload music, animation timing syncs to beats
- **Sound effects**: Library of SFX (whoosh, pop, sparkle) triggered at keyframes
- **Voice narration**: Record or generate narration over animation
- **Audio visualization**: Waveform/spectrum overlay on animation

### Phase 3: Social Platform & Community (Priority: MEDIUM)
- **Public animation profiles**: User pages with their best animations
- **Like/favorite system**: Community engagement metrics
- **Animation challenges**: Weekly themes (e.g., "Animate a pet", "Spooky drawings")
- **Remix feature**: Animate someone else's shared drawing with different presets
- **Leaderboard**: Top creators by likes, views, challenge wins
- **Comments and feedback**: Community interaction on gallery items
- **Share links**: Direct share to Instagram, TikTok, Twitter with platform-optimized format

### Phase 4: Print & Digital Frames (Priority: MEDIUM)
- **Digital frame export**: Optimized infinite-loop animations for digital picture frames
- **Lenticular print prep**: Generate frame sequences for lenticular printing (animated print)
- **Cinemagraph mode**: Only animate part of the image (e.g., flowing water, flickering flame)
- **GIF wallpaper**: Export as Android/iOS live wallpaper format
- **Screensaver export**: Windows/Mac screensaver format

### Phase 5: Education & Physics (Priority: MEDIUM)
- **Physics presets**: Gravity, bounce, pendulum, wave motion -- for science education
- **Diagram animation**: Animate flowcharts, diagrams, anatomical drawings
- **Step-by-step reveal**: Progressive drawing reveal animation (like a hand drawing it)
- **Teaching mode**: Record narration while drawing, replay as animated tutorial
- **Export to LMS**: SCORM-compatible export for learning management systems

### Phase 6: Marketing & Infographics (Priority: MEDIUM)
- **Animated infographic templates**: Upload data, get animated chart/graph
- **Logo animation**: Upload logo, apply intro animation (spin, bounce, glow, particle)
- **Product showcase**: Upload product photo, apply 360-spin or zoom-in animation
- **Email-safe GIF export**: Compressed, optimized GIFs for email marketing (<5MB)
- **Social ad templates**: Pre-sized animated ad formats (Stories, Feed, Banner)

### Phase 7: Custom Art Style Training (Priority: LOW)
- **Style transfer from reference**: Upload 5-10 reference images to define a custom art style
- **Fine-tuned SVD models**: Train per-user SVD adapters for consistent animation style
- **Animation consistency**: Multiple frames of same character maintain style coherence
- **Studio accounts**: Shared custom styles across team members

---

## Infrastructure Notes

### Shared Server (140.82.28.166)
Same server as animateadrawing. Critical to:
- Monitor combined disk usage
- Ensure supervisor processes are properly isolated
- Both projects need content cleanup crons

### GPU Backend Dependency
- Uses `/v1/animate/` endpoint on GPU server
- Maps preset code_name to motion parameter
- Sends `source: 'drawinganimator'` to identify project for credit callbacks
- Need to verify credit callback domain resolution is correct (api.drawinganimator.com -> drawinganimator.com)

### Content Cleanup Priority
- Animation outputs (GIF/MP4/WebM) are the main disk consumers
- Input images are stored in `animations/inputs/YYYY/MM/`
- Output files in `animations/outputs/YYYY/MM/`
- Thumbnails in `animations/thumbnails/YYYY/MM/`
- Implement: keep completed animations 7 days for free users, 30 days for Pro
- Delete failed animations after 24 hours
- Consider implementing `smart_expire` with view tracking to keep popular animations
