"""
AI Person Counter

Created by: Pratik Das
Date: 2025-10-21
Version: 1.0
"""

import os
import argparse
import logging
from tqdm import tqdm
import cv2
from typing import Literal
import numpy as np
from collections import defaultdict
from ultralytics import YOLO
from pydantic import BaseModel
from dotenv import load_dotenv

from csv_logger import CSVLogger

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
CUSTOM_TRACKER = os.getenv("CUSTOM_TRACKER")

# Disable verbose logging from ultralytics
logging.getLogger('ultralytics').setLevel(logging.WARNING)

class PositionConfig(BaseModel):
    line_orientation: Literal["horizontal", "vertical"] 
    door_direction: Literal["up", "down", "left", "right"]
    boundary_cords: int

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Person tracking and counting system')
    parser.add_argument('video', type=str, help='Path to input video')
    parser.add_argument('door_dir', type=str, choices=["up", "down", "left", "right"], help='Direction of the Door')
    parser.add_argument('--output', type=str, default=False, help='Path to output video')
    parser.add_argument('--csv_output', type=str, default=False, help='Path to output CSV file')
    parser.add_argument('--skip_frames', type=int, default=DEFAULT_SKIP_FRAMES, help='Number of frames to skip between processing')
    parser.add_argument('--conf', type=float, default=DEFAULT_CONFIDENCE, help='Confidence threshold')
    parser.add_argument('--crop', action='store_true', default=False, help='Crop video while processing')
    parser.add_argument('--show', action='store_true', default=False, help='Show video while processing')
    parser.add_argument('--interval', type=int, default=DEFAULT_INTERVAL, help='Interval in seconds for logging counts')
    parser.add_argument('--model', type=str, default=f"{MODEL_DIR}/{DEFAULT_MODEL}", help='Path to YOLO model')
    return parser.parse_args()

class PersonTracker:
    def __init__(self, model_path, confidence=0.2):
        """Initialize the person tracker with a YOLO model"""
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.track_history = defaultdict(lambda: [])
        self.crossing_records = defaultdict(lambda: {'first_position': None, 'last_position': None, 'counted': False})
        self.counts = {'total': 0, 'incoming': 0, 'outgoing': 0}
        
        # Parameters for track quality
        self.min_track_length = 3
        self.max_disappeared = 90
        self.disappeared_tracks = defaultdict(int)
        
    def reset_track(self, track_id):
        """Reset a track if it disappears for too long"""
        if track_id in self.track_history:
            del self.track_history[track_id]
        if track_id in self.crossing_records:
            del self.crossing_records[track_id]
        if track_id in self.disappeared_tracks:
            del self.disappeared_tracks[track_id]
    
    def update_disappeared_tracks(self, active_track_ids):
        """Update and manage disappeared tracks"""
        all_tracks = set(self.track_history.keys())
        
        for track_id in all_tracks:
            if track_id not in active_track_ids:
                self.disappeared_tracks[track_id] += 1
                
                if self.disappeared_tracks[track_id] > self.max_disappeared:
                    self.reset_track(track_id)
            else:
                self.disappeared_tracks[track_id] = 0

    def process_frame(self, frame, position):
        """Process a single frame for person tracking and counting"""
        results = self.model.track(frame, persist=True, classes=0, tracker=CUSTOM_TRACKER)
        #   half=True, device="mps")
        
        active_track_ids = []
        
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            
            for box, track_id in zip(boxes, track_ids):
                active_track_ids.append(track_id)
                x1, y1, x2, y2 = box
                
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                self.track_history[track_id].append((center_x, center_y))
                
                if len(self.track_history[track_id]) > self.max_disappeared:
                    self.track_history[track_id].pop(0)
                
                # Determine current position
                if position.line_orientation == "horizontal":
                    if position.door_direction == "down":
                        current_position = 'outside' if center_y < position.boundary_cords else 'inside'
                    elif position.door_direction == "up":
                        current_position = 'outside' if center_y > position.boundary_cords else 'inside'
                elif position.line_orientation == "vertical":
                    if position.door_direction == "right":
                        current_position = 'outside' if center_x < position.boundary_cords else 'inside'
                    elif position.door_direction == "left":
                        current_position = 'outside' if center_x > position.boundary_cords else 'inside'
                
                if track_id not in self.crossing_records or self.crossing_records[track_id]['first_position'] is None:
                    self.crossing_records[track_id]['first_position'] = current_position
                
                self.crossing_records[track_id]['last_position'] = current_position
                
                # Check for crossing
                if (self.crossing_records[track_id]['counted'] is False and 
                    self.crossing_records[track_id]['first_position'] != current_position and
                    len(self.track_history[track_id]) >= self.min_track_length):
                    
                    if self._verify_crossing(track_id, position, 1):
                        if self.crossing_records[track_id]['first_position'] == 'outside' and current_position == 'inside':
                            self.counts['incoming'] += 1
                            self.counts['total'] += 1
                        elif self.crossing_records[track_id]['first_position'] == 'inside' and current_position == 'outside':
                            self.counts['outgoing'] += 1
                            self.counts['total'] -= 1
                        self.crossing_records[track_id]['counted'] = True

                # Draw visualizations
                cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), -1)
                cv2.putText(frame, f"{track_id}", (center_x - 20, center_y - 0), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                points = np.hstack(self.track_history[track_id][-10:]).astype(np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [points], isClosed=False, color=(0, 255, 0), thickness=2)
        
        self.update_disappeared_tracks(active_track_ids)
        
        return frame
    
    def _verify_crossing(self, track_id, position, min_required=1):
        """Verify that a crossing is legitimate by checking the trajectory"""
        track = self.track_history[track_id]
        if len(track) < self.min_track_length:
            return False
        
        if position.line_orientation == "horizontal":
            if position.door_direction == "down":
                positions_outside = sum(1 for x, y in track if y > position.boundary_cords)
            elif position.door_direction == "up":
                positions_outside = sum(1 for x, y in track if y > position.boundary_cords)
        elif position.line_orientation == "vertical":
            if position.door_direction == "right":
                positions_outside = sum(1 for x, y in track if x < position.boundary_cords)
            elif position.door_direction == "left":
                positions_outside = sum(1 for x, y in track if x > position.boundary_cords)
        positions_inside = len(track) - positions_outside
               
        return positions_outside >= min_required and positions_inside >= min_required

def process_video(args):
    """Process video with person tracking and counting"""
    cap = cv2.VideoCapture(args.video)

    if not cap.isOpened():
        print(f"Error: Could not open video {args.video}")
        return
    
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if args.crop:
        crop_top = int(frame_height * 0.25)
        crop_bottom = int(frame_height * 0.75)
        crop_left = int(frame_width * 0.25)
        crop_right = int(frame_width * 0.75)
        frame_width = frame_width // 2
        frame_height = frame_height // 2

    mid_height = frame_height // 2
    mid_width = frame_width // 2

    # Configure position
    if args.door_dir in ["up", "down"]:
        position = PositionConfig(line_orientation="horizontal", door_direction=args.door_dir, boundary_cords=frame_height // 2)
    elif args.door_dir in ["left", "right"]:
        position = PositionConfig(line_orientation="vertical", door_direction=args.door_dir, boundary_cords=frame_width // 2)
    
    # Initialize CSV logger
    csv_logger = None
    if args.csv_output:
        csv_filepath = args.csv_output
    else:
        csv_filename = os.path.basename(args.video).split(".")[0] + ".csv"
        csv_filepath = os.path.join(OUTPUT_DIR, csv_filename)
        
    csv_logger = CSVLogger(csv_filepath, fps, args.interval)
    
    # Set output video path
    if args.output:
        output_filepath = args.output
        output_dir = os.path.dirname(output_filepath)
    else:
        output_dir = OUTPUT_DIR
        output_filename = os.path.basename(args.video)
        output_filepath = os.path.join(output_dir, output_filename)
    
    os.makedirs(output_dir, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_filepath, fourcc, fps, (frame_width, frame_height))

    tracker = PersonTracker(args.model, args.conf)
    
    frame_count = 0
    pbar = tqdm(total=total_frames, desc="Processing frames")
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        if args.crop:
            frame = frame[crop_top:crop_bottom, crop_left:crop_right]

        frame_count += 1
        pbar.update(1)
        
        if args.skip_frames != 0 and (frame_count - 1) % args.skip_frames != 0:
            continue
        
        # Draw boundary line
        if position.line_orientation == "horizontal":
            cv2.line(frame, (0, mid_height), (frame_width, mid_height), (255, 0, 0), 2)
            quater_height = frame_height // 4
            if position.door_direction == "down":
                cv2.putText(frame, "Outside", (mid_width, mid_height - quater_height), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, "Inside", (mid_width, mid_height + quater_height), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            elif position.door_direction == "up":
                cv2.putText(frame, "Outside", (mid_width, mid_height + quater_height), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, "Inside", (mid_width, mid_height - quater_height), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        elif position.line_orientation == "vertical":
            cv2.line(frame, (mid_width, 0), (mid_width, frame_height), (255, 0, 0), 2)
            quater_width = frame_width // 4
            if position.door_direction == "right":
                cv2.putText(frame, "Outside", (mid_width - quater_width, mid_height), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, "Inside", (mid_width + quater_width, mid_height), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            elif position.door_direction == "left":
                cv2.putText(frame, "Outside", (mid_width + quater_width, mid_height), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, "Inside", (mid_width - quater_width, mid_height), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        frame = tracker.process_frame(frame, position)
        
        # Log to CSV if needed
        if csv_logger:
            csv_logger.log_counts(frame_count, tracker.counts)
        
        count_text = f"Total: {tracker.counts['total']} | In: {tracker.counts['incoming']} | Out: {tracker.counts['outgoing']}"
        cv2.putText(frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        cv2.putText(frame, f"Frame: {frame_count}/{total_frames}", (10, frame_height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        if args.output:
            out.write(frame)
        
        if args.show:
            cv2.imshow("People Counter", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    pbar.close()
    
    cap.release()
    if args.output:
        out.release()
    if args.show:
        cv2.destroyAllWindows()
    
    print(f"Counting completed. Results: {tracker.counts}")
    if args.csv_output:
        print(f"CSV data saved to {args.csv_output}")
    if args.output:
        print(f"Output video saved to {args.output}")

if __name__ == "__main__":
    args = parse_arguments()
    # validate_arguments(args)
    process_video(args)