# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Drawing Animator** (drawinganimator.com) is a web application that brings hand-drawn sketches, doodles, and artwork to life through AI-powered animation. Users upload a drawing, select an animation style (walk, dance, jump, etc.), and the system generates an animated version.

### Tech Stack
- **Framework**: Django 5.x
- **Frontend**: Bootstrap 5 + Bootstrap Icons
- **Database**: PostgreSQL (production) / SQLite (development)
- **Queue**: Redis + django-rq
- **Payments**: Stripe (primary)
- **GPU Processing**: api.imageeditor.ai (Wan2.2-Animate, MediaPipe, DWPose)

### Architecture
```
User → drawinganimator.com (Django Frontend)
         ↓ API Call
      api.imageeditor.ai (GPU Backend)
         ↓ Processing
      Wan2.2-Animate + Motion Templates
         ↓
      Animated Output (GIF/MP4/WebM)
```

## Quick Reference

| What | Where |
|------|-------|
| Animation logic | `animator/views.py` |
| Animation models | `animator/models.py` |
| Main animate page | `templates/animate.html` |
| Landing page | `templates/index.html` |
| Animation presets | `animator/management/commands/seed_presets.py` |
| Config (secrets) | `config.py` (gitignored) |

## Common Commands

```bash
# Development
source venv/bin/activate
python manage.py runserver

# Database
python manage.py migrate
python manage.py createsuperuser

# Seed data
python manage.py seed_presets     # Animation presets
python manage.py set_languages    # Languages for i18n

# Deployment
cd ansible
ansible-playbook -i servers gitpull.yml
```

## Key Models

### AnimationPreset
Pre-defined animation styles (walk, run, dance, etc.) with:
- `code_name`: Unique identifier sent to API
- `motion_file`: Path to motion template video
- `is_premium`: Requires Pro subscription
- `icon`: Bootstrap icon class

### Animation
Tracks individual animation jobs:
- `input_image`: User's uploaded drawing
- `preset`: Selected animation style
- `output_format`: gif/mp4/webm
- `status`: pending/processing/completed/failed
- `output_url`: URL to completed animation

### GalleryItem
Curated showcase of example animations.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/animate/` | GET | Main animation page |
| `/animate/api/animate/` | POST | Create new animation |
| `/animate/api/animation/status/<id>/` | GET | Check animation status |
| `/animate/api/animation/callback/` | POST | Callback from GPU API |
| `/animate/gallery/` | GET | Gallery page |
| `/animate/my-animations/` | GET | User's animation history |

## Rate Limiting

- **Free users**: 5 animations per day (config.RATE_LIMIT)
- **Pro users**: 1000 per day (config.RATE_LIMIT_PRO)
- Tracked by: user ID, session key, or IP address

## Premium Features

Pro users get:
- Unlimited animations
- MP4/WebM output formats
- No watermark
- Premium animation styles (dab, zombie, backflip, etc.)

## Configuration

Copy `config_example.py` to `config.py` and set:
- `API_BACKEND`: URL to api.imageeditor.ai
- `API_KEY`: Authentication key for API
- `DATABASE`: PostgreSQL connection (production)
- `STRIPE`: Payment keys

## Deployment

### Server Details
- **Domain**: drawinganimator.com
- **API Domain**: api.drawinganimator.com (CNAME to api.imageeditor.ai)
- **Frontend Server**: 140.82.28.166
- **API Server**: 38.248.6.142 (api.imageeditor.ai)
- **Server User**: drawinganimator
- **Deploy Path**: /home/www/drawinganimator
- **Supervisor Process**: drawinganimator
- **Gunicorn Port**: 127.0.0.1:8001
- **DNS**: DigitalOcean (ns1.digitalocean.com, ns2.digitalocean.com, ns3.digitalocean.com)

### Deploy Commands
```bash
# Via SSH (root access via key)
ssh root@140.82.28.166

# Via Ansible (requires group_vars/all setup)
cd ansible
ansible-playbook -i servers gitpull.yml           # Quick deploy
ansible-playbook -i servers djangodeployubuntu20.yml  # Full deploy

# Check status
supervisorctl status drawinganimator
tail -f /var/log/drawinganimator/gunicorn.log
```

## GPU API Integration

The frontend sends animation requests to the GPU backend:

```python
# Request to api.imageeditor.ai
POST /v1/animate-drawing/
{
    'image': <file>,
    'animation_type': 'walk',
    'output_format': 'gif',
    'duration': 3.0,
    'fps': 24,
    'loop': true,
    'add_watermark': false,
    'callback_url': 'https://drawinganimator.com/api/animation/callback/',
    'animation_id': 'uuid'
}
```

The API processes asynchronously and calls back when complete.

## Animation Pipeline (GPU Side)

1. **Character Segmentation**: rembg/SAM isolates character from background
2. **Pose Estimation**: MediaPipe/DWPose detects skeleton
3. **Motion Transfer**: Wan2.2-Animate applies motion from template video
4. **Video Encoding**: FFmpeg generates GIF/MP4/WebM output

## GPU Infrastructure

This project uses the shared GPU server at api.imageeditor.ai for animation processing.

### GPU Server Details
- **Server**: 38.248.6.142 (api.imageeditor.ai)
- **Hardware**: 4x Tesla P40 (24GB VRAM each)
- **API Endpoint**: https://api.imageeditor.ai/v1/animate/

### Central Documentation
For complete GPU infrastructure documentation, see:
- `/home/john/ai/CLAUDE.md` - Central GPU infrastructure docs
- `/home/john/PycharmProjects/api.imageeditor.ai/CLAUDE.md` - API server docs

### Error Handling

The GPU API now supports OOM detection and automatic retry:
- If GPU runs out of memory, job retries on a different GPU
- GPU health tracking temporarily blacklists problematic GPUs
- Pre-flight memory checks prevent jobs from starting on low-memory GPUs

### Monitoring

```bash
# Check GPU status
cd /home/john/PycharmProjects/api.imageeditor.ai/ansible
ansible -i servers server -m shell -a "nvidia-smi" --become

# GPU status dashboard
# Visit: https://api.imageeditor.ai/gpu/

# Check animation logs
ansible -i servers server -m shell -a "tail -50 /var/log/api.imageeditor.ai/api.err.log" --become
```

### Related Projects
- `/home/john/animateadrawing/` - Similar animation site using same GPU backend
- `/home/john/texttospeechai/` - TTS processing using same GPU server
- `/home/john/PycharmProjects/api.imageeditor.ai/` - The GPU API server itself

## Brand Positioning & Differentiation

**drawinganimator.com** is positioned differently from competitors like animateadrawing.com:

### Key Differentiators
1. **Works with ANY drawing** - Not just characters/stick figures
   - Landscapes, nature scenes
   - Abstract art & patterns
   - Still life & objects
   - Portraits & faces
   - Architecture

2. **Stable Video Diffusion AI** - State-of-the-art image-to-video model
   - Creates natural, flowing motion
   - Motion intensity control (1-255 scale)
   - HD 1024px output at 25fps

3. **Target Audience** - Artists, designers, content creators
   - Professional/sophisticated positioning
   - Dark, gallery-like visual design

### Animation Capabilities
The API supports TWO animation approaches:
1. **Character Animation** (skeletal) - walk, run, dance, jump, wave, idle, kick, punch
2. **Stable Video Diffusion** - AI-generated motion for any image type

### Static Files Issue
The staticfiles directory has root ownership, preventing collectstatic. To fix (requires sudo):
```bash
chown -R drawinganimator:drawinganimator /home/www/drawinganimator/staticfiles
python manage.py collectstatic --noinput
```

## Inherited from DjangoBase

This project inherits standard patterns from djangobase:
- Custom user model with email auth
- Credits-based billing system
- Multi-processor payments (Stripe primary)
- Database-driven translation system
- Ansible deployment playbooks
