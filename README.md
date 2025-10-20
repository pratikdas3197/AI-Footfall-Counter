# AI Footfall Counter

## Description

This is an AI based application that uses Computer Vision - Object Detection and Tracking Models to count the number of people entering and exiting a location. It uses the stored CCTV video footage to detect people and a CSV logger to log the counts at the given intervals.

## Installation

### Backend

```bash
cd backend/

python3 -m venv venv

source venv/bin/activate

pip3 install -r requirements.txt
```

### Frontend
```bash
cd frontend/

npm install
```

## Run Application

```bash
cd backend/

python3 server.py
```

### Frontend
```bash
cd frontend/

npm run dev
```

## Run CLI

### Activate the virtual environment
```bash
cd backend/

source venv/bin/activate
```

### Run the counter
```bash
python3 counter.py --video ../input/short_video.mp4 --door_dir up --crop --interval 1
```
OR
```bash
python3 counter.py --video ../input/long_video.mp4 --door_dir left
```