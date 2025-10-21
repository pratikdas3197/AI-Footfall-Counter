from datetime import datetime, timedelta
import csv

class CSVLogger:
    """Handles CSV logging of counting data at some intervals"""
    def __init__(self, csv_path, fps, interval_seconds=60):
        self.start_time = datetime.now()
        self.csv_path = csv_path
        self.fps = fps
        self.last_interval = 0
        self.interval_start_counts = {'total': 0, 'incoming': 0, 'outgoing': 0}
        self.interval_seconds = interval_seconds
        
        # Initialize CSV file with headers
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'total_present_inside', 'incoming_last_interval', 'outgoing_last_interval'])
    
    def get_timestamp(self, frame_count):
        """Convert frame count to timestamp in HH:MM:SS format"""
        seconds = int(frame_count / self.fps)
        timestamp = self.start_time + timedelta(seconds=seconds)
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    def should_log(self, frame_count):
        """Check if we've passed a interval boundary"""
        current_interval = int(frame_count / self.fps / self.interval_seconds) # Log every interval seconds
        return current_interval > self.last_interval
    
    def log_counts(self, frame_count, current_counts, force=False):
        """Log counts to CSV at interval intervals"""
        if self.should_log(frame_count) or force:
            timestamp = self.get_timestamp(frame_count)
            
            # Calculate changes in last interval
            incoming_last_interval = current_counts['incoming'] - self.interval_start_counts['incoming']
            outgoing_last_interval = current_counts['outgoing'] - self.interval_start_counts['outgoing']
            
            # Write to CSV
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    current_counts['total'],
                    incoming_last_interval,
                    outgoing_last_interval
                ])
            
            # Update tracking variables
            self.last_interval = int(frame_count / self.fps / self.interval_seconds) # Log every interval seconds
            self.interval_start_counts = current_counts.copy()
            
            return True
        return False