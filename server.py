from main import app
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting OpenCode ↔ LRS-Agents Cognitive AI Hub...")
    print("🌐 Server will be available at: https://[your-replit-url]")
    print("🧠 Cognitive Demo: Click '🚀 Cognitive Demo' button")
    print("=" * 60)

    # Run with proper configuration for Replit
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8080,
        reload=False,
        log_level="info"
    )
