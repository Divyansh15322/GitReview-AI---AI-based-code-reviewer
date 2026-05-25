import os
import sys
import subprocess
import time
import shutil

def main():
    print("==============================================================================")
    print("                     🚀 Starting GitReview AI Launcher                        ")
    print("==============================================================================")
    
    # 1. Environment variables check
    root_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(root_dir, ".env")
    env_example = os.path.join(root_dir, ".env.example")
    
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            print("📝 Copying .env.example to .env ...")
            shutil.copy(env_example, env_file)
            print("💡 Created .env with default configurations (Running in DEMO/MOCK mode).")
        else:
            print("⚠️ Warning: .env.example missing. Please create a .env file at root manually.")
            
    # 2. Local database and directory setups
    os.makedirs(os.path.join(root_dir, "temp_repos"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "chroma_db"), exist_ok=True)

    print("\n📦 Launching Backend (FastAPI on http://127.0.0.1:8000)...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "backend.app.main:app", 
        "--host", "127.0.0.1", "--port", "8000", "--reload"
    ]
    backend_proc = subprocess.Popen(
        backend_cmd, 
        cwd=root_dir,
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # 3. Graceful check to wait for backend startup before launching Streamlit
    print("⏳ Waiting for backend API to initialize database tables...")
    time.sleep(3.0)

    print("\n🖥️ Launching Frontend (Streamlit on http://127.0.0.1:8501)...")
    frontend_cmd = [
        sys.executable, "-m", "streamlit", "run", "frontend/app.py",
        "--server.port", "8501", "--server.address", "127.0.0.1"
    ]
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=root_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print("\n==============================================================================")
    print("✅ System initialized successfully! Open http://127.0.0.1:8501 in your browser.")
    print("🛑 Press Ctrl+C to terminate both servers concurrently.")
    print("==============================================================================\n")

    try:
        # Stream logs in real-time or just keep active
        while True:
            # Check if either process failed unexpectedly
            backend_exit = backend_proc.poll()
            frontend_exit = frontend_proc.poll()
            
            if backend_exit is not None:
                print(f"❌ Backend exited unexpectedly with code: {backend_exit}")
                break
            if frontend_exit is not None:
                print(f"❌ Frontend exited unexpectedly with code: {frontend_exit}")
                break
                
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\n🛑 Interruption received. Terminating FastAPI and Streamlit servers...")
    finally:
        # Graceful cleanup
        backend_proc.terminate()
        frontend_proc.terminate()
        
        try:
            backend_proc.wait(timeout=3)
            frontend_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_proc.kill()
            frontend_proc.kill()
            
        print("🧹 Servers cleanly terminated. Thank you for using GitReview AI!")

if __name__ == "__main__":
    main()
