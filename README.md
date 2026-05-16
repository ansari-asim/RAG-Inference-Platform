# RAG Inference Platform - Distributed Multi-LLM Architecture

A production-grade distributed RAG + multi-LLM inference platform using FastAPI, Ollama, and modern infrastructure.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           OpenWebUI                                      │
│                              ↓                                           │
┌──────────────────────────────────────────────────────────────────────────┐
│                    Central FastAPI Middleware                             │
│  ┌────────────┬────────────┬────────────┬────────────┬────────────┐       │
│  │API Gateway │Model Router│ RAG Pipeline│Memory Layer│ Load Balancer│     │
│  └────────────┴────────────┴────────────┴────────────┴────────────┘       │
│  ┌────────────┬────────────┬────────────┬────────────┬────────────┐       │
│  │Auth & Rate │Health Monitor│ Cache(Redis)│Metrics    │Context Inject│    │
│  └────────────┴────────────┴────────────┴────────────┴────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘
                              ↓
    ┌─────────────────────────────────────────────────────────────────┐
    │                  Distributed Services                            │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
    │  │ Redis   │  │PostgreSQL│ │ Qdrant  │  │Prometheus│            │
    │  │ Cache   │  │   DB    │  │ Vector  │  │ Metrics │            │
    │  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
    └─────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────┬──────────────────┬──────────────────┐
│   Server A       │   Server B       │   Server C        │
│   Ollama Model A │   Ollama Model B │   Ollama Model C   │
│   (deepseek-coder)│   (llama3.2)    │   (qwen2.5)        │
└──────────────────┴──────────────────┴──────────────────┘
```

## Key Features

### 1. Multi-Server Ollama Cluster
- Distribute inference across multiple servers
- Automatic health monitoring and failover
- Weighted load balancing
- Model-specific routing

### 2. Intelligent Model Routing
- **Coding tasks** → deepseek-coder
- **Reasoning/Math** → qwen2.5
- **General chat** → llama3.2
- Custom routing rules support

### 3. RAG Pipeline
- Document ingestion with chunking
- Semantic search using Qdrant
- Context injection into prompts
- Memory retrieval

### 4. Persistence & Caching
- **Redis**: Session cache, rate limiting
- **PostgreSQL**: User data, chat history, metrics
- **Qdrant**: Vector storage for RAG

### 5. Production Features
- JWT Authentication
- Rate limiting
- Metrics collection
- Health monitoring
- Request logging
- Error handling

## Network Design

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Server A   │     │  Server B   │     │  Server C   │
│  Ollama     │     │  Ollama     │     │  Ollama     │
│  :11434     │     │  :11434     │     │  :11434     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Middleware │
                    │   (FastAPI)  │
                    └──────┬──────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
│   Qdrant    │     │    Redis    │     │  PostgreSQL │
│   :6333     │     │   :6379     │     │   :5432     │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Multiple Ollama servers running on different machines

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone and navigate to project
cd /home/asim/asim/RAG

# 2. Start all services
docker-compose up -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f rag-api
```

### Option 2: Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Start required services (Redis, PostgreSQL, Qdrant)
docker run -d --name redis -p 6379:6379 redis:7-alpine
# ... start other services

# 4. Run the application
python -m app.main
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_SERVERS` | Comma-separated Ollama URLs | localhost:11434 |
| `MODEL_SERVER_MAP` | JSON mapping models to servers | {} |
| `DEFAULT_MODEL` | Default model to use | llama3.2 |
| `LOAD_BALANCING_STRATEGY` | round_robin, weighted, least_load | weighted |
| `HEALTH_CHECK_INTERVAL` | Seconds between health checks | 30 |
| `RATE_LIMIT_REQUESTS` | Requests per window | 100 |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | 60 |

## API Endpoints

### Chat
- `POST /api/v1/chat` - Send chat message with RAG augmentation
- `GET /api/v1/chat/history/{session_id}` - Get chat history
- `DELETE /api/v1/chat/history/{session_id}` - Delete session

### Models
- `GET /api/v1/models` - List all available models
- `GET /api/v1/models/servers/status` - Server status

### Documents
- `POST /api/v1/documents/ingest` - Ingest document
- `POST /api/v1/documents/ingest/file` - Upload file

### Memory
- `POST /api/v1/memory/search` - Search memories
- `POST /api/v1/memory` - Store memory

### Health & Metrics
- `GET /api/v1/health` - Health check
- `GET /api/v1/health/servers` - Server health
- `GET /api/v1/metrics` - Application metrics

## OpenWebUI Integration

1. Open OpenWebUI Admin Panel
2. Go to **Settings** → **External Ollama**
3. Set API URL:
```
http://localhost:8000/api/v1/chat
```
4. Save and use normally

## Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Scale horizontally
kubectl scale deployment rag-inference-platform --replicas=5
```

## Monitoring

- **Prometheus**: http://localhost:9091
- **API Metrics**: GET /api/v1/metrics
- **Health**: GET /api/v1/health

## Scaling Recommendations

### Horizontal Scaling
- Deploy multiple replicas of the FastAPI middleware
- Use Kubernetes HPA for automatic scaling
- Load balance across replicas

### Vertical Scaling
- Increase CPU/memory limits in deployment
- Adjust Ollama server resources

### Model Distribution
- Spread models across servers
- Use dedicated GPUs for large models

## Security Best Practices

1. **Change default secrets** in production
2. **Enable authentication** for production use
3. **Configure rate limits** appropriately
4. **Use TLS** for external connections
5. **Implement network policies** in Kubernetes
6. **Regular security audits**

## Project Structure

```
/home/asim/asim/RAG/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration
│   ├── exceptions.py        # Custom exceptions
│   ├── core/                # Ollama cluster, router, etc.
│   ├── services/            # RAG, memory, metrics
│   ├── middleware/          # Auth, rate limiting
│   ├── api/routes/          # API endpoints
│   └── models/              # Schemas, DB models
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── k8s/
│   ├── deployment.yaml
│   └── ingress.yaml
├── scripts/
│   └── init_db.py
├── requirements.txt
└── README.md
```

## Troubleshooting

### Ollama Connection Issues
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify server URLs in .env
```

### Vector Store Issues
```bash
# Check Qdrant
curl http://localhost:6333/collections
```

### Performance Issues
- Check metrics endpoint for bottlenecks
- Review server load distribution
- Adjust rate limits if needed

## License

MIT License