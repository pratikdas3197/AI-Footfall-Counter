# AI based People Counting and Forecasting Demo

### Overview

This application leverages Artificial Intelligence (AI) and Computer Vision to monitor and analyze visitor traffic in public facilities such as City Recreation Centres. It automates the process of counting how many people enter and exit the facility using video footage, eliminating the need for manual monitoring.

### Input Data

The system processes recorded CCTV video footage from the facility. This video file is used as input for the AI Computer Vision models for detection and tracking of individuals within the frame.

### Core Functionality

1. **Object Detection and Tracking**

    - The system uses AI Computer Vision models to detect and track each person visible in the video frame.

    - It identifies entry and exit movements of the people across the provided boundaries of the facility (e.g., doors, gates).

2. **Visitor Count Logging**

    - The model logs the count of incoming and outgoing visitors along with the total visitors present in the facility at a given time.

    - This data stored in CSV file provides accurate insights into peak hours, occupancy trends, and total footfall over specific timeframes.

### Predictive Analytics

3. **Visitor Forecasting**

    - A forecasting model estimates the expected visitor traffic by hour, day, or week, supporting better resource planning and facility management.

## Installation

### Backend

- The backend is a FastAPI application that provides a API to upload a video file and configure the AI counting parameters.

- Run these commands to install the Python dependencies in a virtual environment.

```bash
cd backend/

python -m venv venv
```

### Activate virtual environment
#### For Linux/Mac:
```bash
source venv/bin/activate
```
#### For Windows PowerShell (recommended):
```bash
.\venv\Scripts\Activate.ps1
```
#### For Windows CMD:
```bash
.\venv\Scripts\activate.bat
```

#### Install dependencies
```bash
pip install -r requirements.txt
```

### Frontend

- The frontend is a Next.js application that provides a web interface to select the video file and configure the AI counting parameters.

- Run these commands to install the Node.js dependencies.

```bash
cd frontend/

npm install
```

## Run Application

### Backend

- Run the backend server in a separate terminal.

```bash
cd backend/

python server.py
```

### Frontend

- Run the frontend application in a separate terminal.

```bash
cd frontend/

npm run dev
```

## Run CLI

- The AI counting can be executed via CLI for a saved CCTV video file and selected counting and tracking parameters.

### Activate virtual environment
```bash
cd backend/
```
#### For Linux/Mac:
```bash
source venv/bin/activate
```
#### For Windows PowerShell (recommended):
```bash
.\venv\Scripts\Activate.ps1
```
#### For Windows CMD:
```bash
.\venv\Scripts\activate.bat
```

## CLI Counting

### Run on samples videos
```bash
python counter.py ../input/short_video.mp4 up --crop --interval 1 --show
```
OR
```bash
python counter.py --video ../input/long_video.mp4 --door_dir left --show
```

#### CLI Counting Parameters:

- 1st argument: Path to the input video file (required).
- 2nd argument: Direction of the door (up, down, left, right) (required).
- `--output`: Path to the output video file (default: output.mp4).
- `--csv_output`: Path to the output CSV file (default: counts.csv).
- `--interval`: Interval between counts in seconds (default: 60).
- `--skip_frames`: Number of frames to skip (default: 0).
- `--conf`: Confidence threshold (default: 0.01).
- `--crop`: Enable the center crop in the input video (default: False).
- `--show`: Show preview of the output video (default: False).

## CLI Forecasting

- The AI forecasting can be executed via CLI for a saved counting CSV file and selected parameters.

### Run on a sample counting CSV file
```bash
python forecast.py ../input/count_data.csv
``` 

#### CLI Forecasting Parameters:

- `--csv`: Path to the input CSV file (required).
- `--output`: Path to the output CSV file (optional).

### Folder Structure

- The `input` directory contains some sample input video files.
- The `output` directory will contain the output video and output CSV files.
- The `models` directory contain the AI models. Ultralytics YOLOv12n is used.
- The `counter_jobs.db` will contain the database of the AI counting jobs.
- The `.env` file contains the default AI counting and tracking parameters.