# AI Social Media Agent System

An agentic AI system that researches AI infrastructure trends and creates optimized LinkedIn content.

## Architecture
- 5+ specialized agents (Research, Strategy, Content, Video, Publishing)
- Hybrid model approach: Ollama (local) + Groq (cloud)
- n8n orchestration
- SQLite for research storage
- Vector DB for brand memory (coming soon)

## Setup
1. Install Docker and Ollama
2. Copy `.env.example` to `.env` and add your keys
3. Run `docker-compose up -d` in the docker folder
4. Access n8n at http://localhost:5678

## Agents
- Research Agent: Daily monitoring of GitHub, ArXiv, tech news
- Strategy Agent: Identifies content angles from research
- Content Agent: Generates platform-optimized posts
- [More coming]

## Workflows
All n8n workflows are in the `/workflows` folder.