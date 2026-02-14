"""
Test script for Pexels API connectivity.
Verifies API key and search functionality.
"""

import os
import sys
import requests
from dotenv import load_dotenv

def test_env_loading():
    """Test if .env file exists and loads."""
    load_dotenv()
    
    api_key = os.getenv("PEXELS_API_KEY")
    
    if api_key and api_key != "your_pexels_api_key_here":
        print(f"✅ Pexels API key loaded from .env")
        return True, api_key
    else:
        print("❌ Pexels API key not found or not configured")
        print("   Please add PEXELS_API_KEY to your .env file")
        print("   Get a free API key at: https://www.pexels.com/api/")
        return False, None

def test_api_connection(api_key):
    """Test basic API connectivity with a simple search."""
    try:
        base_url = "https://api.pexels.com/v1/"
        headers = {"Authorization": api_key}
        
        # Test with a simple search
        endpoint = f"{base_url}search"
        params = {
            "query": "ocean",
            "per_page": 5,
            "orientation": "landscape"
        }
        
        print("\n🔍 Testing Pexels search: 'ocean'")
        response = requests.get(endpoint, headers=headers, params=params)
        
        if response.status_code == 200:
            print(f"✅ API connection successful (Status: {response.status_code})")
            return True, response.json()
        elif response.status_code == 401:
            print(f"❌ Authentication failed (Status: 401)")
            print("   Check your API key")
            return False, None
        elif response.status_code == 429:
            print(f"⚠️  Rate limit exceeded (Status: 429)")
            print("   You've hit the hourly limit. Try again later.")
            return False, None
        else:
            print(f"❌ Unexpected response (Status: {response.status_code})")
            return False, None
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False, None

def test_video_search(api_key):
    """Test video search endpoint."""
    try:
        base_url = "https://api.pexels.com/v1/"
        headers = {"Authorization": api_key}
        
        endpoint = f"{base_url}videos/search"
        params = {
            "query": "space",
            "per_page": 3,
            "orientation": "landscape"
        }
        
        print("\n🎬 Testing Pexels video search: 'space'")
        response = requests.get(endpoint, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            
            print(f"✅ Found {len(videos)} videos")
            
            if videos:
                sample_video = videos[0]
                print(f"\n📹 Sample Video:")
                print(f"   ID: {sample_video['id']}")
                print(f"   Duration: {sample_video['duration']} seconds")
                print(f"   By: {sample_video['user']['name']}")
                print(f"   Files available: {len(sample_video['video_files'])}")
            
            return True
        else:
            print(f"❌ Video search failed (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Video search failed: {e}")
        return False

def check_rate_limits(response_headers):
    """Display rate limit information from response headers."""
    try:
        print("\n📊 Rate Limit Status:")
        
        # Pexels doesn't always return these headers, so check if they exist
        if 'X-Ratelimit-Limit' in response_headers:
            limit = response_headers.get('X-Ratelimit-Limit', 'N/A')
            remaining = response_headers.get('X-Ratelimit-Remaining', 'N/A')
            print(f"   Limit: {limit} requests/hour")
            print(f"   Remaining: {remaining} requests")
        else:
            print("   Default: 200 requests/hour, 20,000/month")
    except Exception as e:
        print(f"   Could not retrieve rate limit info: {e}")

def main():
    """Run all Pexels API tests."""
    print("=" * 60)
    print("🧪 Pexels API Connectivity Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Environment variables
    success, api_key = test_env_loading()
    results.append(success)
    
    if not success:
        print("\n❌ Cannot proceed without API key")
        return 1
    
    # Test 2: API connection
    success, data = test_api_connection(api_key)
    results.append(success)
    
    if success and data:
        # Show rate limits
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": "test", "per_page": 1}
        )
        check_rate_limits(response.headers)
        
        # Test 3: Video search
        results.append(test_video_search(api_key))
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Summary: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("✅ Pexels API is fully operational!")
        return 0
    else:
        print("❌ Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
