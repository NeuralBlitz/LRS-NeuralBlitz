from main import app
import uvicorn

if __name__ == "__main__":
    print("Starting experimental LRS-NeuralBlitz FastAPI gateway (pre-production)")
    print("Local gateway: http://127.0.0.1:8080")
    print("Requires compatible optional backend dependencies; see docs/production-readiness.md")
    print("=" * 60)

    # Run with proper configuration for Replit
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8080,
        reload=False,
        log_level="info"
    )
