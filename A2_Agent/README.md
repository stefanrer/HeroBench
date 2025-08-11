# A2 Agent - Hierarchical LLM Agent System

## Project Description

A2 Agent is modification of A1 agent. The main principle of the design was to add more agents with a one-bite size tasks.

### Multi-agent architecture

- **Curriculum Agent**: Analyze the global goal, character status and equipment to create tasks. Has a helping agent Fight Analytic to simulate fight outcomes during the combat tasks.
    - **Fight Analytic**: Simulates the outcome of the fight considering the characters equipment and craftable equipment.
- **Decomposer Agent**: Decomposes the tasks into small one-bite subtasks with the help of the expert agents.
    - **Craft expert**: Outputs the recipe for the items based on the current environment instance knowledge.
    - **Map expert**: Outputs map coordinates for the every location based on the current environment instance knowledge.
- **Critic**: Checks the output of the decomposer and tries to correct it if any errors found.
- **Action Agent**: Generate a Python code to control the character based on the acquired subtasks list. 

### Supported Task Types

- **Crafting Tasks**: Automatically gather resources and craft items
- **Combat Tasks**: Navigate to monsters and engage in combat

## Installation Guide

### Prerequisites

- Python 3.8 or higher
- OpenAI or OpenRouter API key
- Game environment server running

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/stefanrer/HeroBench
   cd A2_Agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   Create a `.env` file in the root directory with your OpenAI/OpenRouter API key or assign environment variable by yourself:
   ```
   OPENAI_API_KEY=your_api_key_here
   OPENROUTER_API_KEY=your_api_key_here
   ```

4. **Start the environment server**
   Ensure the environment server is running and you know the url (default is `http://127.0.0.1:8000`)

### Dependencies

The project requires the following Python packages:
- `taskgen-ai==4.0.1` - Main framework used to build A2 agentic system
- `openai==1.59.9` - OpenAI API client
- `python-dotenv==1.0.1` - Environment variable management
- `requests==2.32.3` - HTTP client for API calls
- `strictjson==6.1.1` - Structured JSON output from LLMs

## Project Structure

```
A2_Agent/
├── agent_demo.ipynb                 # Interactive demo notebook
├── requirements.txt                 # Python dependencies
│
├── agent/                           # Agent implementations
│   ├── agent.py                     # Main A2 agents system implementation
│   ├── task_knowledge.py            # Contains environment instance knowledge getters
│   └── agents_description/          # Agent prompts and functions to get task-dependent prompts
│
├── utils/                           # Utility modules
│   ├── api.py                       # ArtifactsMMO API implementation
│   ├── crafting_tree.py             # Crafting tree generation for reward calculation
│   ├── reward.py                    # Reward calculation for task evaluation
│   └── data/                        # Contains environment data
│
├── tasks/                           # Task datasets storage
│   └── combined_tasks8_small.json   # Standard dataset in a JSON format
│
└── results/                         # Execution results storage
    └── [generated during execution]
```

## Quick Start

**Run the demo notebook**
```bash
jupyter notebook agent_demo.ipynb
```