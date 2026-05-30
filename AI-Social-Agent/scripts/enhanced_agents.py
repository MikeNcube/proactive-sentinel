import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from datetime import datetime
from scripts.helpers import query_ollama, load_prompt, save_to_memory
from scripts.data_sources import DataSources
import os

class EnhancedAgents:
    def __init__(self):
        self.data_sources = DataSources()
        self.memory_dir = "agents/memory"
        os.makedirs(self.memory_dir, exist_ok=True)
    
    def run_research_agent(self, topic="AI infrastructure"):
        """Enhanced research with real data"""
        print("ðŸ” Running Enhanced Research Agent...")
        
        # Collect real data
        research_data, data_file = self.data_sources.collect_all(topic)
        
        # Load and run research prompt
        prompt = load_prompt("research", 
                           current_date=datetime.now().strftime("%B %d, %Y"),
                           research_data=research_data)
        
        results = query_ollama(prompt, "llama3")
        
        # Save with metadata
        output = {
            "topic": topic,
            "source_data": data_file,
            "findings": results,
            "timestamp": datetime.now().isoformat()
        }
        
        filename = f"{self.memory_dir}/research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"âœ… Research complete - saved to {filename}")
        return results, filename
    
    def run_strategy_agent(self, research_findings):
        """Enhanced strategy with audience targeting"""
        print("ðŸ’¡ Running Enhanced Strategy Agent...")
        
        prompt = load_prompt("strategy",
                           current_date=datetime.now().strftime("%B %d, %Y"),
                           research_summary=research_findings)
        
        results = query_ollama(prompt, "llama3")
        
        # Save
        filename = save_to_memory(results, "strategy")
        print(f"âœ… Strategy complete - saved angles")
        
        # Parse angles
        angles = self.parse_angles(results)
        return results, angles
    
   def run_content_agent(self, angle, platform="linkedin"):
    """Enhanced content creation for multiple platforms"""
    print(f"ðŸ“ Running Enhanced Content Agent for {platform}...")
    
    # Platform-specific prompt loading
    if platform == "tiktok":
        prompt = load_prompt("tiktok", content_angle=angle)
    elif platform == "instagram":
        prompt = load_prompt("instagram", content_angle=angle)
    else:
        prompt = load_prompt("content", content_angle=angle, platform=platform)
    
    post = query_ollama(prompt, "llama3")
    
    # Save with metadata
    output = {
        "platform": platform,
        "angle": angle,
        "post": post,
        "timestamp": datetime.now().isoformat()
    }
    
    filename = f"{self.memory_dir}/{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"âœ… Content complete - saved to {filename}")
    return post, filename
    
    def parse_angles(self, strategy_output):
        """Simple angle parser"""
        angles = []
        lines = strategy_output.split('\n')
        current_angle = []
        
        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.', '-', 'â€¢')):
                if current_angle:
                    angles.append('\n'.join(current_angle))
                current_angle = [line]
            else:
                current_angle.append(line)
        
        if current_angle:
            angles.append('\n'.join(current_angle))
        
        return angles if angles else [strategy_output[:200]]

# Run the enhanced pipeline
if __name__ == "__main__":
    print("=" * 60)
    print("ðŸš€ ENHANCED AI SOCIAL MEDIA PIPELINE")
    print("=" * 60)
    
    agents = EnhancedAgents()
    
    # Step 1: Research with real data
    research, research_file = agents.run_research_agent("AI agents and automation tools")
    print(f"\nðŸ“Š Research summary:\n{research[:300]}...\n")
    
    # Step 2: Generate content angles
    strategy, angles = agents.run_strategy_agent(research)
    print(f"\nðŸ’¡ Generated {len(angles)} content angles")
    
    # Step 3: Create posts from angles
    for i, angle in enumerate(angles[:2]):  # Generate posts for first 2 angles
        print(f"\n--- Processing Angle {i+1} ---")
        post, post_file = agents.run_content_agent(angle, "linkedin")
        print(f"\nðŸ“± Post {i+1} preview:\n{post[:300]}...")
    
    print("\n" + "=" * 60)
    print("âœ… ENHANCED PIPELINE COMPLETE")
    print("=" * 60)
