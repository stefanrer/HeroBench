# HeroBench: A Benchmark for Long-Horizon Planning and Structured Reasoning in Virtual Worlds

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com/)

---

## Abstract

Large language models (LLMs) have shown remarkable capabilities in isolated step-by-step reasoning tasks such as mathematics and programming, but their proficiency in long-horizon planning, where solutions require extended, structured sequences of interdependent actions, remains underexplored. Existing benchmarks typically assess LLMs through abstract or low-dimensional algorithmic tasks, failing to capture the complexity of realistic planning environments. We introduce HeroBench, a novel benchmark designed specifically to evaluate long-horizon planning and structured reasoning within complex RPG-inspired virtual worlds. HeroBench provides a rigorously constructed dataset of tasks covering a wide range of difficulties, a simulated environment to execute and validate agent plans, and detailed analytical tools for evaluating model performance. Tasks challenge models to formulate strategic plans, efficiently gather resources, master necessary skills, craft equipment, and defeat adversaries, reflecting practical scenarios' layered dependencies and constraints. Our extensive evaluation of 20 state-of-the-art LLMs, including both open-source and proprietary models and agentic architectures, reveals significant performance disparities typically unseen in conventional reasoning benchmarks. Detailed error analysis further uncovers specific weaknesses in current models' abilities to generate robust high-level plans and reliably execute structured actions. HeroBench thus not only significantly advances the evaluation of LLM reasoning but also provides a flexible, scalable foundation for future research into advanced, autonomous planning in virtual environments.

---

<div align="center">

![Success rate on base tasks](figures/success_rate_improved1.png "Success rate on base tasks")

*Performance comparison across different LLM architectures on HeroBench tasks*

</div>

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)
- [Citation](#citation)

## Features

### 🎯 **Long-Horizon Planning Evaluation**
- Complex task decomposition and execution
- Multi-step planning with interdependencies
- Resource management

### 🏗️ **Modular Architecture**
- **Virtual Environment**: FastAPI-based game world simulation
- **Benchmark Suite**: Comprehensive task datasets and evaluation metrics
- **Analytics Tools**: Performance analysis and error categorization

### 🎮 **RPG-Inspired Game World**
- Rich virtual environment with resources and monsters
- Crafting system with skill requirements
- Combat mechanics and equipment management
- Character progression and inventory systems

### 🤖 **Advanced Agent System**
- **Multi-Agent Architecture**: Sophisticated system with specialized agents for different responsibilities
- **A1 Agent**: Hierarchical LLM agent with task decomposition and critic evaluation
- **A2 Agent**: Enhanced agent system using taskgen-ai framework with curriculum, decomposer, and action agents
- **Specialized Expert Agents**: Craft expert, map expert, and fight analytic agents for domain-specific knowledge

## Quick Start

### Prerequisites

- Python 3.8 or higher (Python 3.12.4 recommended)
- OpenAI API key
- Redis (optional, for faster performance)

### 1. Clone the Repository

```bash
git clone https://github.com/stefanrer/HeroBench
cd HeroBench
```

### 2. Set Up the Virtual Environment

```bash
cd Virtual_Environment/FastApi_Redis_Ver
pip install -r requirements.txt
```

### 3. Start the Environment Server

```bash
# For Redis version (recommended)
uvicorn main:app --host 127.0.0.1 --port 8000

# For SQLite version
cd ../FastApi_SQLite_Ver
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```


## Installation

### Detailed Setup Instructions

#### Option 1: Redis Version (Recommended)

1. **Install Redis**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   
   # Windows
   # Download from https://redis.io/download
   ```

2. **Start Redis**
   ```bash
   redis-server
   ```

3. **Set up the environment**
   ```bash
   cd Virtual_Environment/FastApi_Redis_Ver
   pip install -r requirements.txt
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```

#### Option 2: SQLite Version

```bash
cd Virtual_Environment/FastApi_SQLite_Ver
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Dependencies

#### A1 Agent Dependencies
- `langchain==0.3.17` - LLM framework integration
- `loguru==0.7.3` - Advanced logging
- `openai==1.42.0` - OpenAI API client
- `python-dotenv==1.0.1` - Environment variable management
- `strictjson==6.1.1` - Structured JSON output from LLMs

#### A2 Agent Dependencies
- `taskgen-ai==4.0.1` - Main framework used to build A2 agentic system
- `openai==1.59.9` - OpenAI API client
- `python-dotenv==1.0.1` - Environment variable management
- `requests==2.32.3` - HTTP client for API calls
- `strictjson==6.1.1` - Structured JSON output from LLMs

#### Virtual Environment Dependencies
- `fastapi==0.116.1` - Web framework
- `redis==6.2.0` - Redis client (Redis version)
- `uvicorn==0.35.0` - ASGI server
- `pydantic==2.11.7` - Data validation

## Project Structure

```
HeroBench/
├── README.md                           # This file
├── figures/                            # Images and visualizations
│   └── success_rate_improved1.png     # Benchmark results
│
├── A1_Agent/                           # Hierarchical LLM agent system
│   ├── agent.py                        # Main A1Agent implementation
│   ├── agent_demo.ipynb                # Interactive demo
│   ├── agent_settings.json             # Agent configuration
│   ├── tasks_executor.py               # Task execution orchestrator
│   ├── requirements.txt                # Python dependencies
│   │
│   ├── agents/                         # Agent implementations
│   │   ├── action_agent.py            # Task decomposition agent
│   │   ├── critic_agent.py            # Plan evaluation agent
│   │   └── prompts/                   # LLM prompt templates
│   │
│   ├── env_api/                       # Environment API integration
│   │   ├── api.py                     # Main API client
│   │   ├── api_calls_ext.py           # Extended API functionality
│   │   └── actions_executors.py       # Action execution handlers
│   │
│   ├── memory/                        # Knowledge and data storage
│   │   ├── MAPS.json                  # Game world map data
│   │   ├── available_items_craft.py   # Crafting item management
│   │   ├── craft_parser.py            # Crafting recipe parser
│   │   └── source_jsons/              # Game data sources
│   │
│   ├── tasks/                         # Task definitions
│   │   ├── combined_tasks8_small.json # Task dataset
│   │   └── combined_prompts8_2_small.json
│   │
│   ├── utils/                         # Utility modules
│   │   ├── agent_logger.py            # Logging system
│   │   ├── environment_state.py       # Environment state management
│   │   ├── llm_connect.py             # LLM connection utilities
│   │   └── state_parse.py             # State parsing utilities
│   │
│   └── results/                       # Execution results
│
├── A2_Agent/
│   ├── agent_demo.ipynb                 # Interactive demo notebook
│   ├── requirements.txt                 # Python dependencies
│   │
│   ├── agent/                           # Agent implementations
│   │   ├── agent.py                     # Main A2 agents system implementation
│   │   ├── task_knowledge.py            # Contains environment instance knowledge getters
│   │   └── agents_description/          # Agent prompts and functions to get task-dependent prompts
│   │
│   ├── utils/                           # Utility modules
│   │   ├── api.py                       # ArtifactsMMO API implementation
│   │   ├── crafting_tree.py             # Crafting tree generation for reward calculation
│   │   ├── reward.py                    # Reward calculation for task evaluation
│   │   └── data/                        # Contains environment data
│   │
│   ├── tasks/                           # Task datasets storage
│   │   └── combined_tasks8_small.json   # Standard dataset in a JSON format
│   │
│   └── results/                         # Execution results storage
│       └── [generated during execution]
│
└── Virtual_Environment/               # Game world simulation
    ├── FastApi_Redis_Ver/             # Redis-based implementation
    │   ├── app/
    │   │   ├── routers/               # API endpoints
    │   │   └── db.py                  # Database configuration
    │   ├── main.py                    # FastAPI application
    │   └── requirements.txt           # Dependencies
    │
    ├── FastApi_SQLite_Ver/            # SQLite-based implementation
    │   ├── app/
    │   │   ├── routers/               # API endpoints
    │   │   └── db.py                  # Database configuration
    │   ├── main.py                    # FastAPI application
    │   └── requirements.txt           # Dependencies
    │
    ├── Data/                          # Game data files
    │   ├── items.json                 # Item definitions
    │   ├── maps.json                  # Map definitions
    │   ├── monsters.json              # Monster definitions
    │   └── resources.json             # Resource definitions
    │
    └── world_map.png                  # Visual map representation
```

## Usage

### Running the Benchmark

1. **Start the environment server**
   ```bash
   cd Virtual_Environment/FastApi_Redis_Ver
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```

### Interactive Demo

- Fill here



### Task Types

HeroBench supports various task types:

- **Crafting Tasks**: Gather resources and craft items
- **Combat Tasks**: Navigate to monsters and engage in combat

## API Documentation

The virtual environment provides a comprehensive REST API for:

- **Character Management**: Create, delete, and manage characters
- **Movement**: Navigate the game world
- **Actions**: Gather resources, craft items, fight monsters
- **State Queries**: Check inventory, position, and status

### Key Endpoints

- `POST /characters/create` - Create a new character
- `POST /my/{name}/action/move` - Move character
- `POST /my/{name}/action/gathering` - Gather resources
- `POST /my/{name}/action/crafting` - Craft items
- `POST /my/{name}/action/fight` - Fight monsters
- `GET /maps/{x}/{y}` - Get map information
- `GET /items` - List available items

For complete API documentation, see [Virtual_Environment/README.md](Virtual_Environment/README.md).

## Contributing

We welcome contributions to HeroBench! Here's how you can help:

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Run tests** (if available)
5. **Submit a pull request**

### Areas for Contribution

- **New Task Types**: Add novel planning challenges
- **Environment Features**: Extend the virtual world
- **Evaluation Metrics**: Improve benchmark assessment
- **Documentation**: Enhance guides and examples

## License

Fill here

## Citation

If you use HeroBench in your research, please cite our work:

```bibtex
@article{HeroBench2025,
  title={HeroBench: A Benchmark for Long-Horizon Planning and Structured Reasoning in Virtual Worlds},
  author={Your Name and Co-authors},
  journal={arXiv preprint},
  year={2025}
}
```


For questions, issues, or contributions, please open an issue on GitHub or contact the maintainers.
