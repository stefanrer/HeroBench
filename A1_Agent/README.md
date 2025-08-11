# A1 Agent - Hierarchical LLM Agent System

## Project Description

A1 Agent is an advanced hierarchical LLM agent system designed for automated task execution in HeroBench environment. The system uses a multi-agent architecture with task decomposition capabilities to handle complex objectives like crafting items and fighting monsters.

### Key Features

- **Hierarchical Task Decomposition**: Breaks down high-level tasks into subtasks and executable actions
- **Multi-Agent Architecture**: Uses specialized agents for different responsibilities
  - **ActionAgent**: Handles task decomposition and action execution
  - **CriticAgent**: Evaluates and critiques proposed plans
- **Environment Integration**: Connects to a game environment API for real-time task execution
- **Retry Logic**: Implements robust error handling and retry mechanisms
- **Comprehensive Logging**: Detailed logging system for debugging and analysis

### Supported Task Types

- **Crafting Tasks**: Automatically gather resources and craft items
- **Combat Tasks**: Navigate to monsters and engage in combat

## Installation Guide

### Prerequisites

- Python 3.8 or higher (Python 3.12.4 recommended)
- OpenAI API key (for LLM integration)
- Game environment server running on `http://127.0.0.1:8000`

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/stefanrer/HeroBench
   cd A1_Agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. **Start the environment server**
   Ensure the environment server is running on `http://127.0.0.1:8000`

### Dependencies

The project requires the following Python packages:
- `langchain==0.3.17` - LLM framework integration
- `loguru==0.7.3` - Advanced logging
- `openai==1.42.0` - OpenAI API client
- `python-dotenv==1.0.1` - Environment variable management
- `requests==2.32.3` - HTTP client for API calls
- `strictjson==6.1.1` - Structured JSON output from LLMs

## Project Structure

```
A1_Agent/
├── agent.py                          # Main A1Agent class implementation
├── agent_demo.ipynb                  # Interactive demo notebook
├── agent_settings.json               # Agent configuration settings
├── tasks_executor.py                 # Task execution orchestrator
├── requirements.txt                  # Python dependencies
│
├── agents/                           # Agent implementations
│   ├── action_agent.py              # ActionAgent for task decomposition
│   ├── critic_agent.py              # CriticAgent for plan evaluation
│   └── prompts/                     # LLM prompt templates
│       ├── prompts_2/               # User prompts (updated)
│       └── system_prompts_2/        # System prompts (updated)
│
├── env_api/                         # Environment API integration
│   ├── api.py                       # Main API client functions
│   ├── api_calls_ext.py             # Extended API functionality
│   └── actions_executors.py         # Action execution handlers
│
├── memory/                          # Knowledge and data storage
│   ├── MAPS.json                    # Game world map data
│   ├── MAPS.txt                     # Map data in text format
│   ├── available_items_craft.py     # Crafting item management
│   ├── craft_parser.py              # Crafting recipe parser
│   ├── entity_description_generator.py  # Entity description generation
│   ├── name_formater.py             # Name formatting utilities
│   └── source_jsons/                # Game data sources
│       ├── armor_weapon_db.json     # Equipment database
│       ├── items.json               # Item definitions
│       ├── maps.json                # Map definitions
│       ├── monsters.json            # Monster definitions
│       └── resources.json           # Resource definitions
│
├── tasks/                           # Task definitions and prompts
│   ├── combined_tasks8_small.json   # Task dataset
│   └── combined_prompts8_2_small.json  # Character prompts
│
├── utils/                           # Utility modules
│   ├── agent_logger.py              # Logging system
│   ├── environment_state.py         # Environment state management
│   ├── llm_connect.py               # LLM connection utilities
│   └── state_parse.py               # State parsing utilities
│
└── results/                         # Execution results storage
    └── [generated during execution]
```

## Usage

### Quick Start

1. **Run the demo notebook**
   ```bash
   jupyter notebook agent_demo.ipynb
   ```

### Configuration

The agent behavior can be customized through `agent_settings.json`:

```json
{
    "subtasks_decomposition_attempts_limit": 10,
    "actions_decomposition_attempts_limit": 10,
    "execute_actions_chains": false,
    "console_verbose": true
}
```

## Architecture Overview

### Agent Hierarchy

1. **A1Agent** (Main Controller)
   - Orchestrates the entire task execution process
   - Manages state transitions between decomposition phases
   - Handles retry logic and error recovery

2. **ActionAgent** (Task Decomposer)
   - Converts high-level tasks into subtasks
   - Decomposes subtasks into executable actions
   - Executes actions in the environment

3. **CriticAgent** (Plan Evaluator)
   - Evaluates proposed action plans
   - Provides feedback for plan improvement
   - Ensures plan feasibility and correctness

### Task Execution Flow

1. **Task Input**: High-level task (e.g., "Craft Iron Sword")
2. **Subtask Decomposition**: Break into subtasks (gather resources, craft item)
3. **Action Decomposition**: Convert subtasks to actions (move, gather, craft)
4. **Plan Evaluation**: CriticAgent validates the plan
5. **Execution**: Execute actions in the environment
6. **Validation**: Verify task completion

## Environment Integration

The system integrates with a game environment through REST API calls:

- **Character Management**: Create, delete, and manage characters
- **Movement**: Navigate the game world
- **Actions**: Gather resources, craft items, fight monsters
- **State Queries**: Check inventory, position, and status
