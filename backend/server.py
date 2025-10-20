from fastapi import FastAPI, File, Form, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal
import sqlite3
import uuid
import os
import subprocess
import csv
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Directories
current_dir = os.getcwd()
# Get the parent directory
parent_dir = os.path.dirname(current_dir)

INPUT_DIR = os.path.join(parent_dir, os.getenv("INPUT_DIR"))
OUTPUT_DIR = os.path.join(parent_dir, os.getenv("OUTPUT_DIR"))
MODEL_DIR = os.path.join(parent_dir, os.getenv("MODEL_DIR"))

# Model Configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")
DEFAULT_CONFIDENCE = os.getenv("DEFAULT_CONFIDENCE")
DEFAULT_SKIP_FRAMES = os.getenv("DEFAULT_SKIP_FRAMES")
DEFAULT_DOOR_DIR = os.getenv("DEFAULT_DOOR_DIR")
DEFAULT_INTERVAL = os.getenv("DEFAULT_INTERVAL")

app = FastAPI(title="People Counter API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DB_PATH = "counter_jobs.db"
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            video_path TEXT,
            output_video_path TEXT,
            csv_path TEXT,
            status TEXT,
            door_direction TEXT,
            confidence REAL,
            skip_frames INTEGER,
            crop BOOLEAN,
            created_at TEXT,
            completed_at TEXT,
            error_message TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Request/Response Models
class CountingConfig(BaseModel):
    door_direction: Literal["up", "down", "left", "right"] = Field(DEFAULT_DOOR_DIR, description="Direction of the door")
    confidence: float = Field(DEFAULT_CONFIDENCE, ge=0.0, le=1.0, description="Confidence threshold")
    skip_frames: int = Field(DEFAULT_SKIP_FRAMES, ge=0, le=2, description="Number of frames to skip")
    crop: bool = Field(False, description="Enable center crop")
    show_preview: bool = Field(True, description="Show preview")
    interval: int = Field(DEFAULT_INTERVAL, ge=0, description="Interval between counts")

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class StatusResponse(BaseModel):
    job_id: str
    status: str
    video_path: Optional[str]
    output_video_path: Optional[str]
    csv_path: Optional[str]
    latest_data: Optional[dict]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]

# Helper functions
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def read_latest_csv_row(csv_path: str) -> Optional[dict]:
    """Read the last row from CSV file"""
    try:
        if not os.path.exists(csv_path):
            return None
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                return dict(rows[-1])
        return None
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

def process_video_task(job_id: str, video_path: str, config: CountingConfig, output_video_path: str, csv_path: str):
    """Background task to process video"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update status to processing
        cursor.execute("UPDATE jobs SET status = ? WHERE job_id = ?", ("processing", job_id))
        conn.commit()
        
        # Build command
        cmd = [
            "python3",
            "counter.py",
            "--video", video_path,
            "--door_dir", config.door_direction,
            "--output", output_video_path,
            "--csv_output", csv_path,
            "--skip_frames", str(config.skip_frames),
            "--conf", str(config.confidence),
            "--interval", str(config.interval)
        ]
        
        if config.crop:
            cmd.append("--crop")
        if config.show_preview:
            cmd.append("--show")
        
        # Run the counter script
        print("Command executed:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("Command output:", result.stdout)
        print("Command error:", result.stderr)

        if result.returncode == 0:
            # Success
            cursor.execute(
                "UPDATE jobs SET status = ?, completed_at = ? WHERE job_id = ?",
                ("completed", datetime.now().isoformat(), job_id)
            )
            conn.commit()
        else:
            # Error
            error_msg = result.stderr or "Unknown error occurred"
            cursor.execute(
                "UPDATE jobs SET status = ?, error_message = ?, completed_at = ? WHERE job_id = ?",
                ("failed", error_msg, datetime.now().isoformat(), job_id)
            )
            conn.commit()
        
    except Exception as e:
        # Handle exceptions
        cursor.execute(
            "UPDATE jobs SET status = ?, error_message = ?, completed_at = ? WHERE job_id = ?",
            ("failed", str(e), datetime.now().isoformat(), job_id)
        )
        conn.commit()
    
    finally:
        conn.close()

# API Endpoints
@app.post("/api/start-counting", response_model=JobResponse)
async def start_counting(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    door_direction: str = Form(...),
    confidence: float = Form(...),
    skip_frames: int = Form(...),
    crop: bool = Form(...),
    show_preview: bool = Form(...),
    interval: int = Form(...)
):
    """
    Start a new counting job with uploaded video
    """
    # Validate config
    try:
        config = CountingConfig(
            door_direction=door_direction,
            confidence=confidence,
            skip_frames=skip_frames,
            crop=crop,
            show_preview=show_preview,
            interval=interval,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded video
    video_filename = f"{job_id}_{video.filename}"
    video_path = os.path.join(INPUT_DIR, video_filename)
    
    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)
    
    # Define output paths
    output_video_path = os.path.join(OUTPUT_DIR, f"{job_id}_output.mp4")
    csv_path = os.path.join(OUTPUT_DIR, f"{job_id}_counts.csv")
    
    # Create database entry
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs (job_id, video_path, output_video_path, csv_path, status, 
                         door_direction, confidence, skip_frames, crop, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        str(video_path),
        output_video_path,
        csv_path,
        "queued",
        config.door_direction,
        config.confidence,
        config.skip_frames,
        config.crop,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    
    # Add background task
    print("Config:", config.__dict__)
    # background_tasks = BackgroundTasks()
    background_tasks.add_task(process_video_task , job_id, str(video_path), config, output_video_path, csv_path)
    # process_video_task(job_id, str(video_path), config, output_video_path, csv_path)
    
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Video processing started"
    )

@app.get("/api/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """
    Get the status of a counting job and latest data
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = dict(row)
    
    # Read latest CSV data if available
    latest_data = None
    if job['csv_path'] and os.path.exists(job['csv_path']):
        latest_data = read_latest_csv_row(job['csv_path'])
    
    return StatusResponse(
        job_id=job['job_id'],
        status=job['status'],
        video_path=job['video_path'],
        output_video_path=job['output_video_path'],
        csv_path=job['csv_path'],
        latest_data=latest_data,
        error_message=job['error_message'],
        created_at=job['created_at'],
        completed_at=job['completed_at']
    )

@app.get("/api/csv-data/{job_id}")
async def get_csv_data(job_id: str):
    """
    Get all CSV data for a job
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT csv_path FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    
    csv_path = row['csv_path']
    
    if not csv_path or not os.path.exists(csv_path):
        return {"data": []}
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV: {str(e)}")

@app.get("/")
async def root():
    return {"message": "People Counter API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)