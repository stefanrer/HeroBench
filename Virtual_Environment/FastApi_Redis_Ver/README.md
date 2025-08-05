# Virtual Environment - Redis Version (Fast)

## Project Description

Local Python Virtual Environment based on https://www.artifactsmmo.com project, leveraging the FastAPI framework for efficient API handling and Redis for low-latency data storage and caching.

### Key Features

- **FastAPI-Powered Backend**: A high-performance, asynchronous REST API for handling game-related requests with automatic OpenAPI/Swagger documentation.
- **Redis-Powered Storage**: Leverage Redis as a primary datastore for blazing-fast key-value operations, session caching, and pub/sub functionality.
- **Lightweight & Portable**: Easy to deploy locally for development or testing without complex infrastructure.

## Installation Guide

### Prerequisites

- Python 3.8 or higher (Python 3.12.4 recommended) 
- Local Redis instance running on Port `6379`

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/stefanrer/ArtifactsBench
   cd Virtual_Environment
   cd FastApi_Redis_Ver
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
3. **Start the environment server**
   - Development mode
      ````bash
      fastapi dev
      ```` 
   - Production mode
      ```bash
      fastapi run
      ``` 
4. Ensure the environment server is running on `http://127.0.0.1:8000`
5. API docs: `http://127.0.0.1:8000/docs`