import requests
import urllib.parse
import json
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

from dotenv import load_dotenv
import os




class MultiAccountEventExtractor:
    def __init__(self, api_token: str):
        """
        Initialize the multi-account Instagram event extractor with Scrape.do API token.
        
        Args:
            api_token (str): Your Scrape.do API token
        """
        self.api_token = api_token
        self.base_url = "https://api.scrape.do"
        
        # Common event-related keywords
        self.event_keywords = [
            'event', 'party', 'concert', 'show', 'festival', 'gathering', 'meetup',
            'launch', 'opening', 'premiere', 'exhibition', 'workshop', 'seminar',
            'conference', 'meet', 'celebration', 'ceremony', 'reception', 'dinner',
            'lunch', 'brunch', 'drunch', 'ball', 'masquerade', 'karaoke', 'live',
            'performance', 'gig', 'tour', 'tournament', 'competition', 'race',
            'marathon', 'walk', 'run', 'challenge', 'contest', 'auction', 'sale',
            'fair', 'market', 'bazaar', 'expo', 'convention', 'summit', 'forum'
        ]
        
        # Date patterns for event detection
        self.date_patterns = [
            # DD/MM/YYYY or DD-MM-YYYY
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',
            # DD/MM or DD-MM (current year)
            r'\b(\d{1,2})[/-](\d{1,2})\b',
            # Month DD, YYYY
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})\b',
            # DD Month YYYY
            r'\b(\d{1,2})\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b',
            # Month DD
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})\b',
            # DD Month
            r'\b(\d{1,2})\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            # Today, tomorrow, next week, etc.
            r'\b(today|tomorrow|next\s+(?:week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b',
            # This weekend, next weekend
            r'\b(this|next)\s+weekend\b',
            # Specific days
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            # Time patterns
            r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b',
            r'\b(\d{1,2})\s*(am|pm)\b'
        ]
        
    def get_user_profile(self, username: str) -> Dict[str, Any]:
        """
        Get the complete user profile information including recent posts.
        
        Args:
            username (str): Instagram username
            
        Returns:
            Dict: User profile data including posts
        """
        profile_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        encoded_url = urllib.parse.quote_plus(profile_url)
        api_url = f"{self.base_url}/?token={self.api_token}&url={encoded_url}"
        
        try:
            print(f"Fetching profile data for @{username}...")
            response = requests.get(api_url)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data and 'user' in data['data']:
                user_data = data['data']['user']
                print(f"✓ User found: {user_data.get('username', 'Unknown')}")
                print(f"  Posts count: {user_data.get('edge_owner_to_timeline_media', {}).get('count', 0)}")
                return user_data
            else:
                print(f"✗ Could not extract user data for @{username}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error getting user profile for @{username}: {e}")
            return None
    
    def get_user_posts(self, username: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get user posts by extracting them from the profile page.
        
        Args:
            username (str): Instagram username
            count (int): Number of posts to retrieve
            
        Returns:
            List[Dict]: List of post data
        """
        user_data = self.get_user_profile(username)
        if not user_data:
            return []
        
        timeline_media = user_data.get('edge_owner_to_timeline_media', {})
        edges = timeline_media.get('edges', [])
        
        print(f"  Found {len(edges)} posts in profile data")
        return edges[:count]
    
    def extract_date_from_text(self, text: str) -> Optional[datetime]:
        """
        Extract date information from text using various patterns.
        
        Args:
            text (str): Text to extract date from
            
        Returns:
            datetime: Parsed date or None if not found
        """
        text_lower = text.lower()
        current_date = datetime.now()
        
        # Try different date patterns
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                try:
                    if pattern == r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b':
                        # DD/MM/YYYY or DD-MM-YYYY
                        day, month, year = matches[0]
                        return datetime(int(year), int(month), int(day))
                    
                    elif pattern == r'\b(\d{1,2})[/-](\d{1,2})\b':
                        # DD/MM or DD-MM (current year)
                        day, month = matches[0]
                        year = current_date.year
                        parsed_date = datetime(year, int(month), int(day))
                        # If the date has passed, assume next year
                        if parsed_date < current_date:
                            parsed_date = datetime(year + 1, int(month), int(day))
                        return parsed_date
                    
                    elif 'month' in pattern:
                        # Month-based patterns
                        if 'january' in text_lower: month = 1
                        elif 'february' in text_lower: month = 2
                        elif 'march' in text_lower: month = 3
                        elif 'april' in text_lower: month = 4
                        elif 'may' in text_lower: month = 5
                        elif 'june' in text_lower: month = 6
                        elif 'july' in text_lower: month = 7
                        elif 'august' in text_lower: month = 8
                        elif 'september' in text_lower: month = 9
                        elif 'october' in text_lower: month = 10
                        elif 'november' in text_lower: month = 11
                        elif 'december' in text_lower: month = 12
                        else: continue
                        
                        # Extract day and year
                        day_match = re.search(r'\b(\d{1,2})\b', text)
                        year_match = re.search(r'\b(20\d{2})\b', text)
                        
                        if day_match:
                            day = int(day_match.group(1))
                            year = int(year_match.group(1)) if year_match else current_date.year
                            parsed_date = datetime(year, month, day)
                            if parsed_date < current_date and not year_match:
                                parsed_date = datetime(year + 1, month, day)
                            return parsed_date
                    
                    elif pattern == r'\b(today|tomorrow|next\s+(?:week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b':
                        # Relative dates
                        if 'tomorrow' in text_lower:
                            return current_date + timedelta(days=1)
                        elif 'next week' in text_lower:
                            return current_date + timedelta(weeks=1)
                        elif 'next month' in text_lower:
                            return current_date + relativedelta(months=1)
                        elif 'next year' in text_lower:
                            return current_date + relativedelta(years=1)
                        elif 'next monday' in text_lower:
                            days_ahead = 7 - current_date.weekday()
                            return current_date + timedelta(days=days_ahead)
                        elif 'next tuesday' in text_lower:
                            days_ahead = (8 - current_date.weekday()) % 7
                            return current_date + timedelta(days=days_ahead)
                        elif 'next wednesday' in text_lower:
                            days_ahead = (9 - current_date.weekday()) % 7
                            return current_date + timedelta(days=days_ahead)
                        elif 'next thursday' in text_lower:
                            days_ahead = (10 - current_date.weekday()) % 7
                            return current_date + timedelta(days=days_ahead)
                        elif 'next friday' in text_lower:
                            days_ahead = (11 - current_date.weekday()) % 7
                            return current_date + timedelta(days=days_ahead)
                        elif 'next saturday' in text_lower:
                            days_ahead = (12 - current_date.weekday()) % 7
                            return current_date + timedelta(days=days_ahead)
                        elif 'next sunday' in text_lower:
                            days_ahead = (13 - current_date.weekday()) % 7
                            return current_date + timedelta(days=days_ahead)
                    
                    elif pattern == r'\b(this|next)\s+weekend\b':
                        # Weekend patterns
                        if 'next weekend' in text_lower:
                            days_until_saturday = (5 - current_date.weekday()) % 7
                            if days_until_saturday == 0:
                                days_until_saturday = 7
                            return current_date + timedelta(days=days_until_saturday)
                        elif 'this weekend' in text_lower:
                            days_until_saturday = (5 - current_date.weekday()) % 7
                            if days_until_saturday == 0:
                                return current_date
                            return current_date + timedelta(days=days_until_saturday)
                    
                    elif pattern == r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b':
                        # Day of week
                        day_map = {
                            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                            'friday': 4, 'saturday': 5, 'sunday': 6
                        }
                        for day_name, day_num in day_map.items():
                            if day_name in text_lower:
                                days_ahead = (day_num - current_date.weekday()) % 7
                                if days_ahead == 0:
                                    days_ahead = 7  # Next week
                                return current_date + timedelta(days=days_ahead)
                
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def extract_time_from_text(self, text: str) -> Optional[str]:
        """
        Extract time information from text.
        
        Args:
            text (str): Text to extract time from
            
        Returns:
            str: Time in HH:MM format or None if not found
        """
        # Time patterns
        time_patterns = [
            r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b',
            r'\b(\d{1,2})\s*(am|pm)\b'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                match = matches[0]
                if len(match) == 3:
                    # HH:MM AM/PM format
                    hour, minute, period = match
                elif len(match) == 2:
                    # HH AM/PM format
                    hour, period = match
                    minute = '00'
                else:
                    continue
                
                hour = int(hour)
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
                
                return f"{hour:02d}:{minute}"
        
        return None
    
    def is_future_event(self, caption: str) -> bool:
        """
        Check if a caption contains information about a future event.
        
        Args:
            caption (str): Caption text
            
        Returns:
            bool: True if it's a future event, False otherwise
        """
        caption_lower = caption.lower()
        
        # Check for event keywords
        has_event_keyword = any(keyword in caption_lower for keyword in self.event_keywords)
        
        # Check for date/time information
        has_date = self.extract_date_from_text(caption) is not None
        has_time = self.extract_time_from_text(caption) is not None
        
        # Additional indicators
        has_location = any(word in caption_lower for word in ['at ', 'in ', 'venue', 'location', 'place', 'club', 'restaurant', 'cafe', 'bar'])
        has_action_words = any(word in caption_lower for word in ['join', 'come', 'attend', 'be there', 'don\'t miss', 'save the date', 'rsvp'])
        
        return has_event_keyword and (has_date or has_time or has_location or has_action_words)
    
    def extract_event_details(self, caption: str, username: str, instagram_url: str = None) -> Optional[Dict[str, Any]]:
        """
        Extract detailed event information from a caption.
        
        Args:
            caption (str): Caption text
            username (str): Instagram username
            
        Returns:
            Dict: Event details or None if not a valid event
        """
        if not self.is_future_event(caption):
            return None
        
        # Extract date
        event_date = self.extract_date_from_text(caption)
        if not event_date:
            return None
        
        # Check if it's in the future
        if event_date < datetime.now():
            return None
        
        # Extract time
        event_time = self.extract_time_from_text(caption)
        
        # Extract location
        location = None
        location_patterns = [
            r'at\s+([^,\n]+)',
            r'in\s+([^,\n]+)',
            r'venue[:\s]+([^,\n]+)',
            r'location[:\s]+([^,\n]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, caption, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                break
        
        # Extract event name/title
        event_name = None
        # Look for capitalized phrases that might be event names
        name_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Party|Ball|Event|Show|Concert|Festival|Meet|Gathering)',
            r'(?:Join us for|Don\'t miss|Be there for)\s+([^,\n]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Edition'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, caption)
            if match:
                event_name = match.group(1).strip()
                break
        
        # If no specific name found, use first line or first sentence
        if not event_name:
            lines = caption.split('\n')
            if lines:
                first_line = lines[0].strip()
                if len(first_line) > 5 and len(first_line) < 100:
                    event_name = first_line
        
        event = {
            'event_name': event_name or 'Untitled Event',
            'date': event_date.strftime('%Y-%m-%d'),
            'time': event_time or 'TBD',
            'location': location or 'TBD',
            'caption': caption,
            'source_account': username,
            'days_until_event': (event_date - datetime.now()).days
        }
        if instagram_url:
            event['instagram_url'] = instagram_url
        return event
    
    def extract_events_from_account(self, username: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Extract future events from a single Instagram account.
        
        Args:
            username (str): Instagram username
            count (int): Number of posts to analyze
            
        Returns:
            List[Dict]: List of future events from this account
        """
        print(f"\n📱 Analyzing @{username}...")
        
        posts = self.get_user_posts(username, count)
        if not posts:
            print(f"  ✗ No posts found for @{username}")
            return []
        
        events = []
        for i, post in enumerate(posts, 1):
            node = post['node']
            
            # Extract caption text
            caption_text = ""
            if 'edge_media_to_caption' in node and node['edge_media_to_caption']['edges']:
                caption_text = node['edge_media_to_caption']['edges'][0]['node']['text']
            
            # Extract Instagram post URL
            instagram_url = None
            if 'shortcode' in node:
                instagram_url = f"https://www.instagram.com/p/{node['shortcode']}/"
            
            if caption_text:
                # Check if it's a future event
                event_details = self.extract_event_details(caption_text, username, instagram_url)
                if event_details:
                    events.append(event_details)
                    print(f"  ✓ Found event: {event_details['event_name']} on {event_details['date']}")
        
        print(f"  📊 Total events found for @{username}: {len(events)}")
        return events
    
    def extract_events_from_multiple_accounts(self, usernames: List[str], posts_per_account: int = 10) -> List[Dict[str, Any]]:
        """
        Extract future events from multiple Instagram accounts.
        
        Args:
            usernames (List[str]): List of Instagram usernames
            posts_per_account (int): Number of posts to analyze per account
            
        Returns:
            List[Dict]: Combined list of future events from all accounts
        """
        print(f"🎯 Starting multi-account event extraction...")
        print(f"📋 Accounts to analyze: {len(usernames)}")
        print(f"📊 Posts per account: {posts_per_account}")
        print("="*60)
        
        all_events = []
        current_date = datetime.now()
        
        for username in usernames:
            try:
                events = self.extract_events_from_account(username, posts_per_account)
                all_events.extend(events)
                
                # Add a small delay between accounts to be respectful
                time.sleep(1)
                
            except Exception as e:
                print(f"  ✗ Error processing @{username}: {e}")
                continue
        
        # Remove duplicates and filter future events
        unique_events = self.remove_duplicate_events(all_events)
        future_events = self.filter_future_events(unique_events)
        
        # Sort all events by date
        future_events.sort(key=lambda x: x['date'])
        
        print("\n" + "="*60)
        print(f"🎉 EXTRACTION COMPLETE!")
        print(f"📊 Total events found: {len(all_events)}")
        print(f"🔄 After removing duplicates: {len(unique_events)}")
        print(f"📅 Future events only: {len(future_events)}")
        print("="*60)
        
        return future_events
    
    def remove_duplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate events based on event name, date, and location.
        Also, merge events if both contain 'karaoke' and 'wednesday' in their event name or caption.
        Args:
            events (List[Dict]): List of events
        Returns:
            List[Dict]: List of unique events
        """
        seen_events = set()
        unique_events = []

        def is_karaoke_wednesday(event):
            text = (event.get('event_name', '') + ' ' + event.get('caption', '')).lower()
            return 'karaoke' in text and 'wednesday' in text

        for event in events:
            # Special merge for karaoke wednesday events
            if is_karaoke_wednesday(event):
                merged = False
                for existing_event in unique_events:
                    if is_karaoke_wednesday(existing_event):
                        # Merge sources
                        if 'source_accounts' in existing_event:
                            if 'source_account' in event:
                                if event['source_account'] not in existing_event['source_accounts']:
                                    existing_event['source_accounts'].append(event['source_account'])
                        else:
                            existing_event['source_accounts'] = [existing_event['source_account']]
                            if 'source_account' in event and event['source_account'] != existing_event['source_accounts'][0]:
                                existing_event['source_accounts'].append(event['source_account'])
                        merged = True
                        break
                if merged:
                    continue
            # Default duplicate logic
            event_key = (
                event['event_name'].lower().strip(),
                event['date'],
                event['location'].lower().strip() if event['location'] != 'TBD' else 'TBD'
            )
            if event_key not in seen_events:
                seen_events.add(event_key)
                unique_events.append(event)
            else:
                # If duplicate found, merge source accounts
                for existing_event in unique_events:
                    existing_key = (
                        existing_event['event_name'].lower().strip(),
                        existing_event['date'],
                        existing_event['location'].lower().strip() if existing_event['location'] != 'TBD' else 'TBD'
                    )
                    if existing_key == event_key:
                        if 'source_accounts' not in existing_event:
                            existing_event['source_accounts'] = [existing_event['source_account']]
                            del existing_event['source_account']
                        existing_event['source_accounts'].append(event['source_account'])
                        break
        return unique_events
    
    def filter_future_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter events to only include those happening in the future.
        
        Args:
            events (List[Dict]): List of events
            
        Returns:
            List[Dict]: List of future events only
        """
        current_date = datetime.now()
        future_events = []
        
        for event in events:
            try:
                event_date = datetime.strptime(event['date'], '%Y-%m-%d')
                if event_date >= current_date:
                    future_events.append(event)
            except ValueError:
                # If date parsing fails, keep the event
                future_events.append(event)
        
        return future_events
    
    def print_events_summary(self, events: List[Dict[str, Any]]):
        """
        Print a formatted summary of future events from all accounts.
        
        Args:
            events (List[Dict]): List of events
        """
        if not events:
            print("\n" + "="*60)
            print("NO FUTURE EVENTS FOUND")
            print("="*60)
            print("No upcoming events were detected across all analyzed accounts.")
            return
        
        print("\n" + "="*60)
        print("UPCOMING EVENTS SUMMARY")
        print("="*60)
        print(f"Total future events found: {len(events)}")
        print("="*60)
        
        # Group events by account (this is now handled in the account counts section below)
        pass
        
        for i, event in enumerate(events, 1):
            print(f"\n📅 EVENT #{i}")
            print("-" * 50)
            print(f"🎯 Event Name: {event['event_name']}")
            print(f"📅 Date: {event['date']}")
            print(f"⏰ Time: {event['time']}")
            print(f"📍 Location: {event['location']}")
            
            # Handle both single source and multiple sources
            if 'source_accounts' in event:
                sources = ', '.join([f"@{acc}" for acc in event['source_accounts']])
                print(f"📱 Sources: {sources}")
            else:
                print(f"📱 Source: @{event['source_account']}")
            
            print(f"⏳ Days until event: {event['days_until_event']}")
            print(f"📝 Caption preview: {event['caption'][:150]}{'...' if len(event['caption']) > 150 else ''}")
            print("-" * 50)
        
        # Summary by account
        print(f"\n📊 EVENTS BY ACCOUNT:")
        print("-" * 30)
        
        # Count events per account (including merged duplicates)
        account_counts = {}
        for event in events:
            if 'source_accounts' in event:
                for account in event['source_accounts']:
                    account_counts[account] = account_counts.get(account, 0) + 1
            else:
                account = event['source_account']
                account_counts[account] = account_counts.get(account, 0) + 1
        
        for account, count in sorted(account_counts.items()):
            print(f"@{account}: {count} events")
        
        print("\n" + "="*60)
    
    def save_events_to_json(self, events: List[Dict[str, Any]], filename: str):
        """
        Save events to a JSON file.
        
        Args:
            events (List[Dict]): List of events
            filename (str): Output filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"Events saved to {filename}")

def configure():
    load_dotenv()

def main():
    """
    Main function to run the multi-account Instagram event extraction.
    """
    
    configure()
    # List of Instagram usernames to analyze
    
    
    # Number of posts to analyze per account
    POSTS_PER_ACCOUNT = 10
    
    # Initialize the extractor
    extractor = MultiAccountEventExtractor(os.getenv('API_TOKEN'))

    USERNAMES = [
        "blackout.cal",
        "overhype.ccu",
        "iammissginko",
        "vybe.cal",
        "mbarkitchen",
        "thenewmadamg"
    ]
    # Extract events from all accounts
    events = extractor.extract_events_from_multiple_accounts(USERNAMES, POSTS_PER_ACCOUNT)
    
    if events:
        # Save to JSON file
        output_filename = "multi_account_events.json"
        extractor.save_events_to_json(events, output_filename)
        
        # Print summary
        extractor.print_events_summary(events)
        
        # Also save to text file
        with open("multi_account_events.txt", 'w', encoding='utf-8') as f:
            f.write("UPCOMING EVENTS FROM MULTIPLE INSTAGRAM ACCOUNTS\n")
            f.write("="*60 + "\n\n")
            
            for i, event in enumerate(events, 1):
                f.write(f"EVENT #{i}\n")
                f.write("-" * 50 + "\n")
                f.write(f"Event Name: {event['event_name']}\n")
                f.write(f"Date: {event['date']}\n")
                f.write(f"Time: {event['time']}\n")
                f.write(f"Location: {event['location']}\n")
                # Handle both single source and multiple sources
                if 'source_accounts' in event:
                    sources = ', '.join([f"@{acc}" for acc in event['source_accounts']])
                    f.write(f"Sources: {sources}\n")
                else:
                    f.write(f"Source: @{event['source_account']}\n")
                f.write(f"Days until event: {event['days_until_event']}\n")
                f.write(f"Full caption:\n{event['caption']}\n")
                if 'instagram_url' in event:
                    f.write(f"Instagram Post: {event['instagram_url']}\n")
                f.write("-" * 50 + "\n\n")
        
        print(f"\nEvents saved to multi_account_events.txt")
    else:
        print("No future events found across all analyzed accounts.")


if __name__ == "__main__":
    main() 