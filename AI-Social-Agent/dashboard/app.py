import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import json
import glob
from datetime import datetime
import shutil
import uvicorn

app = FastAPI(title="AI Content Dashboard")
templates = Jinja2Templates(directory="dashboard/templates")
templates.env.auto_reload = os.getenv("TEMPLATES_AUTO_RELOAD", "false").lower() == "true"

# Add this function to show current time in templates
from datetime import datetime

def now():
    return datetime.now()

# Make the function available in all templates
templates.env.globals['now'] = now

def get_posts(status=None):
    """Get all posts from memory folder, filtered by status if specified"""
    posts = []
    memory_files = glob.glob("agents/memory/*.json")
    
    for filepath in memory_files:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            filename = os.path.basename(filepath)
            
            # Skip test and research files
            if any(skip in filename.lower() for skip in ['test', 'research_', 'strategy_']):
                continue
            
            # IMPROVED: Better platform detection
            # Determine platform from filename
            platform = "unknown"
            filename_lower = filename.lower()

            # Check for various platform indicators
            if 'linkedin' in filename_lower:
                platform = "linkedin"
            elif 'x_' in filename_lower or 'twitter' in filename_lower or '_x_' in filename_lower or filename_lower.startswith('x_'):
                platform = "x"
            elif 'instagram' in filename_lower:
                platform = "instagram"
            elif 'tiktok' in filename_lower:
                platform = "tiktok"
            
            # Get content - prioritize 'post' field, then 'content'
            content = data.get('post', data.get('content', ''))
            if not content:
                continue
            
            # If platform still unknown, check content for hints
            if platform == "unknown":
                content_lower = str(content).lower()
                if 'linkedin' in content_lower or '#linkedin' in content_lower:
                    platform = "linkedin"
                elif 'tweet' in content_lower or '#x' in content_lower:
                    platform = "x"
            
            # Check if approved
            approved_file = f"agents/memory/approved_{filename}"
            approved = os.path.exists(approved_file)
            
            # Check if scheduled
            scheduled_file = f"agents/memory/scheduled_{filename}"
            scheduled_time = None
            if os.path.exists(scheduled_file):
                with open(scheduled_file, 'r') as sf:
                    sched_data = json.load(sf)
                    scheduled_time = sched_data.get('scheduled_time')
            
            # Determine status
            if scheduled_time:
                post_status = 'scheduled'
            elif approved:
                post_status = 'approved'
            else:
                post_status = 'pending'
            
            # Filter by status if specified
            if status and post_status != status:
                continue
            
            # Format timestamp
            timestamp = data.get('timestamp', '')
            if not timestamp and '_' in filename:
                # Try to extract from filename (format: platform_YYYYMMDD_HHMMSS.json)
                parts = filename.split('_')
                if len(parts) >= 3:
                    date_part = parts[-2]
                    time_part = parts[-1].split('.')[0]
                    if len(date_part) == 8 and len(time_part) == 6:
                        try:
                            dt = datetime.strptime(f"{date_part}_{time_part}", "%Y%m%d_%H%M%S")
                            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            timestamp = filename
                else:
                    timestamp = filename
            elif timestamp:
                # Try to format ISO timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            posts.append({
                'filename': filename,
                'platform': platform,
                'content': str(content)[:150] + "..." if len(str(content)) > 150 else str(content),
                'full_content': str(content),
                'timestamp': timestamp,
                'approved': approved,
                'scheduled': scheduled_time,
                'status': post_status
            })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue
    
    # Sort by timestamp (newest first)
    posts.sort(key=lambda x: x['timestamp'], reverse=True)
    return posts

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, filter: str = "all"):
    """Main dashboard with optional filtering"""
    if filter == "pending":
        posts = get_posts(status='pending')
    elif filter == "approved":
        posts = get_posts(status='approved')
    elif filter == "scheduled":
        posts = get_posts(status='scheduled')
    else:
        posts = get_posts()
    
    # Calculate stats
    all_posts = get_posts()
    stats = {
        'pending': len([p for p in all_posts if p['status'] == 'pending']),
        'approved': len([p for p in all_posts if p['status'] == 'approved']),
        'scheduled': len([p for p in all_posts if p['status'] == 'scheduled']),
        'total': len(all_posts),
        'current_filter': filter
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "posts": posts[:50],  # Show up to 50 posts
        "stats": stats
    })

@app.get("/post/{filename}")
async def view_post(request: Request, filename: str):
    """View full post content"""
    filepath = f"agents/memory/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Post not found")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Check if approved
    approved_file = f"agents/memory/approved_{filename}"
    approved = os.path.exists(approved_file)
    
    # Check if scheduled
    scheduled_file = f"agents/memory/scheduled_{filename}"
    scheduled_time = None
    if os.path.exists(scheduled_file):
        with open(scheduled_file, 'r') as sf:
            sched_data = json.load(sf)
            scheduled_time = sched_data.get('scheduled_time')
    
    return templates.TemplateResponse("view_post.html", {
        "request": request, 
        "post": data, 
        "filename": filename,
        "approved": approved,
        "scheduled": scheduled_time
    })

@app.post("/approve/{filename}")
async def approve_post(filename: str):
    """Approve a post for publishing"""
    approval_file = f"agents/memory/approved_{filename}"
    with open(approval_file, 'w') as f:
        json.dump({
            "approved": True, 
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    return RedirectResponse(url="/", status_code=303)

@app.post("/reject/{filename}")
async def reject_post(filename: str):
    """Reject a post (move to rejected folder)"""
    os.makedirs("agents/rejected", exist_ok=True)
    
    # Move the post
    if os.path.exists(f"agents/memory/{filename}"):
        shutil.move(f"agents/memory/{filename}", f"agents/rejected/{filename}")
    
    # Remove any associated metadata files
    for f in glob.glob(f"agents/memory/*_{filename}"):
        try:
            os.remove(f)
        except:
            pass
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/schedule/{filename}")
async def schedule_post(
    filename: str, 
    schedule_date: str = Form(...),
    schedule_time: str = Form(...)
):
    """Schedule a post for publishing"""
    scheduled_time = f"{schedule_date} {schedule_time}"
    schedule_file = f"agents/memory/scheduled_{filename}"
    
    # Determine platform from filename
    platform = "unknown"
    filename_lower = filename.lower()
    if 'linkedin' in filename_lower:
        platform = "linkedin"
    elif 'x_' in filename_lower or 'twitter' in filename_lower:
        platform = "x"
    elif 'instagram' in filename_lower:
        platform = "instagram"
    elif 'tiktok' in filename_lower:
        platform = "tiktok"
    
    with open(schedule_file, 'w') as f:
        json.dump({
            "scheduled_time": scheduled_time,
            "platform": platform,
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/filter/{status}")
async def filter_by_status(request: Request, status: str):
    """Filter posts by status"""
    return await dashboard(request, filter=status)

@app.get("/run-pipeline")
async def run_pipeline():
    """Manually trigger the agent pipeline"""
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/enhanced_agents.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        return {"status": "success", "output": result.stdout[-500:]}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/stats")
async def get_stats():
    """Return JSON stats for API"""
    posts = get_posts()
    return {
        "pending": len([p for p in posts if p['status'] == 'pending']),
        "approved": len([p for p in posts if p['status'] == 'approved']),
        "scheduled": len([p for p in posts if p['status'] == 'scheduled']),
        "total": len(posts)
    }
@app.get("/analytics")
async def analytics(request: Request):
    """Show content analytics"""
    posts = get_posts()
    
    # Calculate metrics
    total_posts = len(posts)
    by_platform = {
        'linkedin': len([p for p in posts if p['platform'] == 'linkedin']),
        'x': len([p for p in posts if p['platform'] == 'x']),
        'instagram': len([p for p in posts if p['platform'] == 'instagram']),
        'tiktok': len([p for p in posts if p['platform'] == 'tiktok'])
    }
    
    by_status = {
        'pending': len([p for p in posts if p['status'] == 'pending']),
        'approved': len([p for p in posts if p['status'] == 'approved']),
        'scheduled': len([p for p in posts if p['status'] == 'scheduled'])
    }
    
    # Posts by day of week
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    by_day = {day: 0 for day in days}
    
    for post in posts:
        if post['timestamp'] != 'Unknown':
            try:
                dt = datetime.strptime(str(post['timestamp']), "%Y-%m-%d %H:%M:%S")
                day_idx = dt.weekday()
                by_day[days[day_idx]] += 1
            except:
                pass
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "total_posts": total_posts,
        "by_platform": by_platform,
        "by_status": by_status,
        "by_day": by_day
    })
@app.post("/bulk-approve")
async def bulk_approve(request: Request):
    """Approve multiple posts at once"""
    try:
        data = await request.json()
        files = data.get('files', [])
        
        for filename in files:
            approval_file = f"agents/memory/approved_{filename}"
            with open(approval_file, 'w') as f:
                json.dump({
                    "approved": True, 
                    "timestamp": datetime.now().isoformat(),
                    "bulk": True
                }, f, indent=2)
        
        return {"status": "success", "count": len(files)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/bulk-schedule")
async def bulk_schedule(request: Request):
    """Schedule multiple posts at once"""
    try:
        data = await request.json()
        files = data.get('files', [])
        schedule_date = data.get('schedule_date')
        schedule_time = data.get('schedule_time')
        scheduled_time = f"{schedule_date} {schedule_time}"
        
        for filename in files:
            schedule_file = f"agents/memory/scheduled_{filename}"
            with open(schedule_file, 'w') as f:
                json.dump({
                    "scheduled_time": scheduled_time,
                    "filename": filename,
                    "timestamp": datetime.now().isoformat(),
                    "bulk": True
                }, f, indent=2)
        
        return {"status": "success", "count": len(files)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AI CONTENT DASHBOARD")
    print("=" * 60)
    print("📱 Open http://localhost:8000 in your browser")
    print("📊 Stats available at http://localhost:8000/stats")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
