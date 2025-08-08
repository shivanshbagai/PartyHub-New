import os
import time
import subprocess
from flask import Flask, render_template
import re
from datetime import datetime

app = Flask(__name__)

EXTRACTOR_PATH = 'multi_account_event_extractor.py'
EVENTS_TXT = 'multi_account_events.txt'
UPDATE_INTERVAL_SECONDS = 1800  # 30 minutes

# Helper function to parse events from the txt file
def parse_events(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading events file: {e}")
        return []
    
    events = []
    try:
        event_blocks = re.split(r'EVENT #\d+\n-+\n', content)[1:]  # Skip header
        for block in event_blocks:
            event = {}
            # Extract fields
            name_match = re.search(r'Event Name: (.*)', block)
            date_match = re.search(r'Date: (.*)', block)
            time_match = re.search(r'Time: (.*)', block)
            location_match = re.search(r'Location: (.*)', block)
            sources_match = re.search(r'Sources?: (.*)', block)
            days_match = re.search(r'Days until event: (.*)', block)
            caption_match = re.search(r'Full caption:\n([\s\S]*?)(?:-+|$)', block)
            event['name'] = name_match.group(1).strip() if name_match else ''
            event['date'] = date_match.group(1).strip() if date_match else ''
            event['time'] = time_match.group(1).strip() if time_match else ''
            event['location'] = location_match.group(1).strip() if location_match else ''
            event['sources'] = sources_match.group(1).strip() if sources_match else ''
            event['days_until'] = days_match.group(1).strip() if days_match else ''
            event['caption'] = caption_match.group(1).strip() if caption_match else ''
            # Extract Instagram post link
            ig_link_match = re.search(r'Instagram Post: (https://www.instagram.com/p/[^\s]+)', block)
            event['instagram_url'] = ig_link_match.group(1).strip() if ig_link_match else ''
            # Only include events today or in the future
            try:
                event_date = datetime.strptime(event['date'], '%Y-%m-%d')
                if event_date >= datetime.now():
                    events.append(event)
            except Exception:
                continue
    except Exception as e:
        print(f"Error parsing events: {e}")
        return []
    
    return events

def should_update_events():
    if not os.path.exists(EVENTS_TXT):
        return True
    last_modified = os.path.getmtime(EVENTS_TXT)
    return (time.time() - last_modified) > UPDATE_INTERVAL_SECONDS

@app.route('/')
def index():
    # Only run the extractor if the data is stale
    if should_update_events():
        try:
            subprocess.run(['python3', EXTRACTOR_PATH], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Event extractor failed: {e}")
            # Continue with existing data if available
        except FileNotFoundError:
            print(f"Warning: Event extractor script not found: {EXTRACTOR_PATH}")
            # Continue with existing data if available
    
    # Try to parse events, but don't fail if file doesn't exist
    try:
        events = parse_events(EVENTS_TXT)
    except FileNotFoundError:
        print(f"Warning: Events file not found: {EVENTS_TXT}")
        events = []
    except Exception as e:
        print(f"Warning: Error parsing events: {e}")
        events = []
    
    return render_template('site.html', events=events)

if __name__ == '__main__':
    app.run(debug=True) 