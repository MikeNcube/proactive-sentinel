"""
Content Scheduler for AI Social Media Agent
Posts approved content on weekdays only
"""

import schedule
import time
import json
import os
import glob
from datetime import datetime
import sys

class ContentScheduler:
    def __init__(self):
        self.posted_today = []
        print("ðŸš€ Content Scheduler Initialized")
        
    def is_weekday(self):
        """Check if today is Monday-Friday"""
        weekday = datetime.now().weekday()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        is_weekday = weekday < 5
        print(f"ðŸ“… Today is {days[weekday]} - {'Weekday' if is_weekday else 'Weekend'}")
        return is_weekday
    
    def get_pending_posts(self):
        """Get approved posts that aren't scheduled yet"""
        posts = []
        memory_files = glob.glob("agents/memory/*.json")
        
        for filepath in memory_files:
            filename = os.path.basename(filepath)
            
            # Skip if not a content post
            if not any(p in filename for p in ['linkedin_', 'x_', 'instagram_', 'tiktok_']):
                continue
            
            # Check if approved
            approved_file = f"agents/memory/approved_{filename}"
            if not os.path.exists(approved_file):
                continue
            
            # Check if already scheduled
            scheduled_file = f"agents/memory/scheduled_{filename}"
            if os.path.exists(scheduled_file):
                continue
            
            # Check if already published
            published_file = f"agents/memory/published_{filename}"
            if os.path.exists(published_file):
                continue
            
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                content = data.get('post', data.get('content', ''))
                if not content:
                    continue
                
                # Determine platform
                if 'linkedin' in filename:
                    platform = 'linkedin'
                elif 'x_' in filename:
                    platform = 'x'
                elif 'instagram' in filename:
                    platform = 'instagram'
                elif 'tiktok' in filename:
                    platform = 'tiktok'
                else:
                    continue
                
                posts.append({
                    'filename': filename,
                    'platform': platform,
                    'content': content,
                    'filepath': filepath
                })
                print(f"ðŸ“ Found pending post: {filename}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")
        
        return posts
    
    def get_scheduled_posts(self):
        """Get posts scheduled for today"""
        posts = []
        today = datetime.now().strftime("%Y-%m-%d")
        memory_files = glob.glob("agents/memory/scheduled_*.json")
        
        for filepath in memory_files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                scheduled_time = data.get('scheduled_time', '')
                if scheduled_time.startswith(today):
                    filename = data.get('filename')
                    posts.append({
                        'filename': filename,
                        'platform': data.get('platform', 'unknown'),
                        'scheduled_time': scheduled_time
                    })
            except:
                pass
        
        return posts
    
    def post_to_linkedin(self, content):
        """Post to LinkedIn (simulated)"""
        print(f"ðŸ“± LinkedIn post would be: {content[:100]}...")
        print("âœ… LinkedIn post successful (simulated)")
        return True
    
    def post_to_x(self, content):
        """Post to X/Twitter (simulated)"""
        print(f"ðŸ¦ X post would be: {content[:100]}...")
        print("âœ… X post successful (simulated)")
        return True
    
    def post_to_instagram(self, content):
        """Post to Instagram (simulated)"""
        print(f"ðŸ“¸ Instagram post would be: {content[:100]}...")
        print("âœ… Instagram post successful (simulated)")
        return True
    
    def post_to_tiktok(self, content):
        """Post to TikTok (simulated)"""
        print(f"ðŸŽµ TikTok post would be: {content[:100]}...")
        print("âœ… TikTok post successful (simulated)")
        return True
    
    def run_daily(self):
        """Run daily at scheduled time on weekdays"""
        print(f"\n{'='*60}")
        print(f"ðŸ• Running scheduler at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*60)
        
        if not self.is_weekday():
            print("ðŸ“… Weekend - skipping posts")
            return
        
        # First, check for scheduled posts
        scheduled = self.get_scheduled_posts()
        if scheduled:
            print(f"\nðŸ“… Found {len(scheduled)} posts scheduled for today")
            for post in scheduled:
                print(f"   - {post['platform']}: {post['filename']} at {post['scheduled_time']}")
        
        # Then check for approved posts to schedule
        pending = self.get_pending_posts()
        if pending:
            print(f"\nðŸ“ Found {len(pending)} approved posts ready for scheduling")
            for post in pending:
                print(f"   - {post['platform']}: {post['filename']}")
        
        print("\nâœ… Daily check complete")
        print(f"ðŸ’¡ Use dashboard to schedule posts for specific dates/times")

# Run the scheduler
if __name__ == "__main__":
    scheduler = ContentScheduler()
    
    print("\n" + "="*60)
    print("ðŸš€ AI CONTENT SCHEDULER")
    print("="*60)
    print("ðŸ“… Running in SIMULATION mode (no real posting)")
    print("â° Checking for scheduled posts...")
    print("Press Ctrl+C to stop\n")
    
    # Run once immediately
    scheduler.run_daily()
    
    # Then schedule to run every hour (for testing)
    schedule.every(1).hours.do(scheduler.run_daily)
    # For production, use:
    # schedule.every().day.at("09:00").do(scheduler.run_daily)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\nðŸ‘‹ Scheduler stopped")
