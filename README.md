# AI Footfall Counter

## Description

This is an AI based application that uses Computer Vision - Object Detection and Tracking Models to count the number of people entering and exiting a location. It uses stored CCTV video footage as input to count incoming and outgoing people and logs the count at the given intervals.

## Installation

### Backend

- The backend is a FastAPI application that provides a API to upload a video file and configure the AI counting parameters.

- Run these commands to install the Python dependencies in a virtual environment.

```bash
cd backend/

python3 -m venv venv

source venv/bin/activate

pip3 install -r requirements.txt
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

python3 server.py
```

### Frontend

- Run the frontend application in a separate terminal.

```bash
cd frontend/

npm run dev
```

## Run CLI

- The application can also be run as a CLI application on a saved video file with the AI counting parameters.

### Activate virtual environment
```bash
cd backend/

source venv/bin/activate
```

### Run on samples videos
```bash
python3 counter.py --video ../input/short_video.mp4 --door_dir up --crop --interval 1
```
OR
```bash
python3 counter.py --video ../input/long_video.mp4 --door_dir left
```

## CLI Parameters:

- `--video`: Path to the input video file (required).
- `--door_dir`: Direction of the door (up, down, left, right) (required).
- `--output`: Path to the output video file (default: output.mp4).
- `--csv_output`: Path to the output CSV file (default: counts.csv).
- `--crop`: Enable the center crop in the input video (default: False).
- `--interval`: Interval between counts in seconds (default: 60).
- `--skip_frames`: Number of frames to skip (default: 0).
- `--conf`: Confidence threshold (default: 0.01).
- `--show`: Show preview of the output video (default: False).

### Folder Structure

- The `input` directory contains some sample input video files.
- The `output` directory will contain the output video and output CSV files.
- The `models` directory contain the AI models. Ultralytics YOLOv12n is used.
- The `counter_jobs.db` will contain the database of the AI counting jobs.
- The `.env` file contains the default values for the AI counting parameters.