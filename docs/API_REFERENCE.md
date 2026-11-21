> **Verification status: experimental / historical (audited 2026-11-21).** The listed JWT authentication endpoints, rate limits and enterprise API contracts are not established by the six-route root FastAPI source. Treat these as proposed interfaces. See the [source-backed product README](../README.md) and the repository-wide audit. Do not use this page alone to establish scientific validity, secure deployment, or production readiness.

---

# 📚 API Reference

**Complete API Documentation for OpenCode LRS**

---

## 🌐 **Base Configuration**

### **Base URL**
```
Development: http://localhost:8000
Production:  https://api.opencode-lrs.com
```

### **Authentication**
```bash
# JWT Token required for protected endpoints
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/protected
```

### **Rate Limiting**
- **Public Endpoints**: 100 requests/minute
- **Authenticated**: 1000 requests/minute
- **Enterprise**: 10,000 requests/minute

---

## 🔐 **Authentication Endpoints**

### **POST /enterprise/auth/login**
**Description**: Authenticate user and receive JWT token

**Request Body**:
```json
{
    "username": "admin",
    "password": "admin123"
}
```

**Response**:
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
        "id": 1,
        "username": "admin",
        "role": "administrator"
    }
}
```

**Status Codes**:
- `200 OK` - Authentication successful
- `401 Unauthorized` - Invalid credentials
- `429 Too Many Requests` - Rate limit exceeded

### **POST /enterprise/auth/create-user**
**Description**: Create new user (admin only)

**Request Body**:
```json
{
    "username": "newuser",
    "password": "securepassword",
    "email": "user@example.com",
    "role": "developer"
}
```

**Response**:
```json
{
    "id": 2,
    "username": "newuser",
    "email": "user@example.com",
    "role": "developer",
    "created_at": "2025-01-01T12:00:00Z"
}
```

---

## 🧠 **Cognitive AI Endpoints**

### **GET /api/cognitive/status**
**Description**: Get cognitive AI system status

**Response**:
```json
{
    "status": "operational",
    "models_loaded": ["spiking_nn", "attention_network", "memory_system"],
    "performance": {
        "inference_time_ms": 1.2,
        "accuracy": 0.94,
        "memory_usage_mb": 256
    },
    "capabilities": [
        "code_analysis",
        "pattern_recognition",
        "anomaly_detection",
        "optimization_suggestions"
    ]
}
```

### **POST /api/cognitive/analyze**
**Description**: Analyze code with cognitive AI

**Request Body**:
```json
{
    "code": "def fibonacci(n):\n    return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
    "language": "python",
    "analysis_depth": "comprehensive"
}
```

**Response**:
```json
{
    "analysis_time_ms": 1.2,
    "patterns": {
        "functions": 1,
        "conditionals": 1,
        "recursion": true,
        "base_case": true
    },
    "cognitive_score": 0.87,
    "complexity_metrics": {
        "cyclomatic_complexity": 2,
        "cognitive_complexity": 3,
        "maintainability_index": 85
    },
    "suggestions": [
        {
            "type": "optimization",
            "message": "Consider memoization for better performance",
            "confidence": 0.92
        }
    ],
    "performance_metrics": {
        "time_complexity": "O(2^n)",
        "space_complexity": "O(n)",
        "estimated_runtime_ms": 0.001
    }
}
```

---

## 🤖 **Multi-Agent Coordination**

### **GET /api/multi-agent/status**
**Description**: Get multi-agent system status

**Response**:
```json
{
    "active_agents": 3,
    "coordinator_status": "active",
    "social_precision": 0.78,
    "active_workflows": 2,
    "completed_tasks": 47,
    "average_task_time_seconds": 2.3,
    "agents": [
        {
            "id": "agent_001",
            "type": "lrs_agent",
            "status": "active",
            "current_task": "code_analysis",
            "success_rate": 0.94
        },
        {
            "id": "agent_002", 
            "type": "cognitive_agent",
            "status": "idle",
            "current_task": null,
            "success_rate": 0.89
        }
    ]
}
```

### **POST /api/multi-agent/execute-workflow**
**Description**: Execute multi-agent workflow

**Request Body**:
```json
{
    "workflow_type": "code_review_and_optimization",
    "input_data": {
        "repository_path": "/path/to/codebase",
        "file_patterns": ["*.py", "*.js"],
        "analysis_depth": "comprehensive"
    },
    "agents": ["lrs_agent", "cognitive_agent"],
    "coordination_strategy": "hierarchical"
}
```

**Response**:
```json
{
    "workflow_id": "workflow_20250101_001",
    "status": "started",
    "estimated_duration_seconds": 120,
    "agents_assigned": [
        {
            "agent_id": "agent_001",
            "role": "primary_analyzer",
            "tasks": ["syntax_analysis", "pattern_detection"]
        },
        {
            "agent_id": "agent_002",
            "role": "cognitive_reviewer",
            "tasks": ["optimization_suggestions", "complexity_analysis"]
        }
    ]
}
```

### **GET /api/multi-agent/workflow/{workflow_id}/status**
**Description**: Get workflow execution status

**Response**:
```json
{
    "workflow_id": "workflow_20250101_001",
    "status": "completed",
    "progress": 100,
    "results": {
        "files_analyzed": 47,
        "issues_found": 12,
        "optimizations_suggested": 8,
        "total_analysis_time_seconds": 95.2
    },
    "agent_performance": {
        "agent_001": {
            "tasks_completed": 5,
            "success_rate": 1.0,
            "average_task_time_seconds": 2.1
        },
        "agent_002": {
            "tasks_completed": 3,
            "success_rate": 0.97,
            "average_task_time_seconds": 3.4
        }
    }
}
```

---

## 📊 **Integration Status**

### **GET /api/integration/status**
**Description**: Get integration system status

**Response**:
```json
{
    "bridge_status": "operational",
    "connected_systems": {
        "lrs_agents": "connected",
        "cognitive_architecture": "connected",
        "quantum_simulator": "connected",
        "neuro_symbiotic": "standby",
        "dimensional_computing": "standby"
    },
    "active_connections": 3,
    "message_rate_per_second": 47.2,
    "average_latency_ms": 12.3,
    "uptime_percentage": 99.98
}
```

---

## 🏢 **Enterprise Management**

### **GET /enterprise/security/status**
**Description**: Get security system status

**Response**:
```json
{
    "security_status": "secure",
    "active_sessions": 5,
    "failed_login_attempts_24h": 2,
    "security_events_24h": 1,
    "encryption_status": "active",
    "authentication_methods": ["jwt", "rbac"],
    "last_security_scan": "2025-01-01T10:30:00Z",
    "vulnerabilities": []
}
```

### **GET /enterprise/security/audit**
**Description**: Get security audit log

**Response**:
```json
{
    "audit_entries": [
        {
            "timestamp": "2025-01-01T12:00:00Z",
            "user": "admin",
            "action": "login",
            "ip_address": "192.168.1.100",
            "status": "success"
        },
        {
            "timestamp": "2025-01-01T11:45:00Z",
            "user": "developer",
            "action": "api_access",
            "endpoint": "/api/cognitive/analyze",
            "status": "success"
        }
    ],
    "total_entries": 1247,
    "page": 1,
    "total_pages": 25
}
```

---

## 📈 **Monitoring & Analytics**

### **GET /enterprise/monitoring/health**
**Description**: Get system health metrics

**Response**:
```json
{
    "overall_health": "healthy",
    "uptime_percentage": 99.98,
    "cpu_usage_percent": 23.4,
    "memory_usage_percent": 67.8,
    "disk_usage_percent": 45.2,
    "network_latency_ms": 12.3,
    "api_response_time_ms": {
        "p50": 15.2,
        "p95": 45.7,
        "p99": 89.3
    },
    "error_rate_24h": 0.002,
    "active_connections": 47
}
```

### **GET /enterprise/monitoring/performance**
**Description**: Get detailed performance metrics

**Response**:
```json
{
    "time_range": "24h",
    "metrics": {
        "api_requests_per_minute": [
            {"timestamp": "2025-01-01T12:00:00Z", "value": 145.2},
            {"timestamp": "2025-01-01T12:01:00Z", "value": 152.7}
        ],
        "cognitive_analysis_time_ms": {
            "average": 1.2,
            "minimum": 0.8,
            "maximum": 3.4,
            "p95": 2.1
        },
        "agent_coordination_latency_ms": {
            "average": 23.4,
            "minimum": 12.1,
            "maximum": 45.6,
            "p95": 35.2
        }
    }
}
```

### **GET /enterprise/monitoring/alerts**
**Description**: Get system alerts

**Response**:
```json
{
    "active_alerts": [
        {
            "id": "alert_001",
            "severity": "warning",
            "message": "High memory usage detected",
            "timestamp": "2025-01-01T11:45:00Z",
            "source": "system_monitor",
            "acknowledged": false
        }
    ],
    "alert_history": [
        {
            "id": "alert_000",
            "severity": "info",
            "message": "System backup completed successfully",
            "timestamp": "2025-01-01T10:00:00Z",
            "resolved_at": "2025-01-01T10:01:00Z"
        }
    ]
}
```

### **POST /enterprise/monitoring/alerts/{alert_id}/acknowledge**
**Description**: Acknowledge system alert

**Request Body**:
```json
{
    "acknowledged_by": "admin",
    "notes": "Investigating memory usage spike"
}
```

**Response**:
```json
{
    "alert_id": "alert_001",
    "acknowledged": true,
    "acknowledged_by": "admin",
    "acknowledged_at": "2025-01-01T12:00:00Z",
    "notes": "Investigating memory usage spike"
}
```

---

## 🧪 **Benchmarking System**

### **POST /benchmarks/run**
**Description**: Run performance benchmarks

**Request Body**:
```json
{
    "benchmark_type": "comprehensive",
    "target_system": "cognitive_ai",
    "parameters": {
        "iterations": 1000,
        "parallel_workers": 4,
        "test_data_size": "large"
    }
}
```

**Response**:
```json
{
    "benchmark_id": "bench_20250101_001",
    "status": "started",
    "estimated_duration_minutes": 15,
    "test_scenarios": [
        "code_analysis_performance",
        "pattern_recognition_accuracy",
        "multi_agent_coordination",
        "system_resource_usage"
    ]
}
```

### **GET /benchmarks/status/{benchmark_id}**
**Description**: Get benchmark status

**Response**:
```json
{
    "benchmark_id": "bench_20250101_001",
    "status": "completed",
    "started_at": "2025-01-01T12:00:00Z",
    "completed_at": "2025-01-01T12:14:23Z",
    "results": {
        "overall_performance_score": 94.7,
        "speed_improvement_factor": 264447,
        "accuracy_percentage": 98.2,
        "resource_efficiency": 89.3
    },
    "detailed_metrics": {
        "code_analysis": {
            "average_time_ms": 1.2,
            "accuracy": 0.94,
            "throughput_per_second": 833.3
        },
        "pattern_recognition": {
            "average_time_ms": 0.8,
            "accuracy": 0.96,
            "false_positive_rate": 0.02
        }
    }
}
```

---

## 🌐 **WebSocket Integration**

### **WebSocket Endpoint: /ws/realtime**
**Description**: Real-time monitoring and updates

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/realtime');

ws.onopen = function(event) {
    console.log('Connected to real-time updates');
    ws.send(JSON.stringify({
        action: 'subscribe',
        channels: ['system_metrics', 'agent_status', 'cognitive_analysis']
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Real-time update:', data);
};
```

**Message Format**:
```json
{
    "channel": "system_metrics",
    "timestamp": "2025-01-01T12:00:00Z",
    "data": {
        "cpu_usage_percent": 23.4,
        "memory_usage_percent": 67.8,
        "active_agents": 3,
        "requests_per_minute": 145.2
    }
}
```

---

## 📝 **Data Models & Schemas**

### **CognitiveAnalysisRequest**
```json
{
    "code": "string (required)",
    "language": "string (optional, auto-detected)",
    "analysis_depth": "string (basic|comprehensive|deep)",
    "options": {
        "include_suggestions": "boolean (default: true)",
        "include_metrics": "boolean (default: true)",
        "optimization_level": "string (conservative|aggressive)"
    }
}
```

### **CognitiveAnalysisResponse**
```json
{
    "analysis_time_ms": "number",
    "patterns": {
        "functions": "number",
        "classes": "number",
        "conditionals": "number",
        "loops": "number",
        "recursion": "boolean",
        "exceptions": "number"
    },
    "cognitive_score": "number (0-1)",
    "complexity_metrics": {
        "cyclomatic_complexity": "number",
        "cognitive_complexity": "number",
        "maintainability_index": "number (0-100)"
    },
    "suggestions": [
        {
            "type": "string (optimization|security|style|performance)",
            "message": "string",
            "confidence": "number (0-1)",
            "line_number": "number (optional)"
        }
    ]
}
```

### **WorkflowExecutionRequest**
```json
{
    "workflow_type": "string",
    "input_data": "object",
    "agents": "array of strings",
    "coordination_strategy": "string (hierarchical|peer_to_peer|centralized)",
    "timeout_seconds": "number (optional)",
    "priority": "string (low|normal|high|critical)"
}
```

---

## 🔧 **Error Handling**

### **Standard Error Response**
```json
{
    "error": {
        "code": "string",
        "message": "string",
        "details": "object (optional)",
        "timestamp": "string (ISO 8601)",
        "request_id": "string"
    }
}
```

### **Common Error Codes**
- `INVALID_REQUEST` - Malformed request body
- `UNAUTHORIZED` - Authentication required or failed
- `FORBIDDEN` - Insufficient permissions
- `RESOURCE_NOT_FOUND` - Requested resource doesn't exist
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server-side error
- `SERVICE_UNAVAILABLE` - System temporarily unavailable

---

## 📊 **Rate Limits & Quotas**

### **Rate Limiting by Tier**
| Tier | Requests/Minute | Concurrent Requests | Features |
|------|----------------|-------------------|----------|
| **Free** | 100 | 5 | Basic analysis |
| **Developer** | 1,000 | 20 | Cognitive AI |
| **Professional** | 5,000 | 50 | Multi-agent |
| **Enterprise** | 10,000 | 100 | Full platform |

### **Quota Headers**
```bash
# Response headers include quota information
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 947
X-RateLimit-Reset: 1640995200
```

---

## 🧪 **Testing Endpoints**

### **Health Check**
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "timestamp": "2025-01-01T12:00:00Z"}
```

### **Authentication Test**
```bash
curl -X POST http://localhost:8000/enterprise/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"test"}'
```

### **Cognitive Analysis Test**
```bash
curl -X POST http://localhost:8000/api/cognitive/analyze \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"code":"print(\'Hello World\')"}'
```

---

## 📚 **SDK Examples**

### **Python SDK**
```python
from opencode_lrs import OpenCodeClient

# Initialize client
client = OpenCodeClient(
    base_url="http://localhost:8000",
    api_key="your_jwt_token"
)

# Cognitive analysis
result = await client.cognitive.analyze(
    code="def hello(): return 'world'",
    language="python"
)

# Multi-agent workflow
workflow = await client.multi_agent.execute_workflow(
    workflow_type="code_review",
    input_data={"repository": "/path/to/repo"}
)
```

### **JavaScript SDK**
```javascript
import { OpenCodeClient } from '@opencode-lrs/javascript';

const client = new OpenCodeClient({
    baseURL: 'http://localhost:8000',
    apiKey: 'your_jwt_token'
});

// Cognitive analysis
const result = await client.cognitive.analyze({
    code: 'function hello() { return "world"; }',
    language: 'javascript'
});

// Real-time updates
client.websocket.connect();
client.websocket.subscribe('system_metrics', (data) => {
    console.log('System metrics:', data);
});
```

---

## 🔄 **Version History**

### **v1.0.0** (Current)
- All endpoints documented above
- JWT authentication
- Cognitive AI analysis
- Multi-agent coordination
- Enterprise monitoring

### **v0.9.0** (Previous)
- Basic cognitive analysis
- Simple authentication
- Limited monitoring

### **Upcoming v1.1.0**
- GraphQL API support
- Advanced quantum computing endpoints
- Enhanced neuro-symbiotic features

---

**🌟 This API represents the cutting edge of AI-assisted development platforms. Build amazing things with it!**