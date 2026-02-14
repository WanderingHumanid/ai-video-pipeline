"""
Test script for Edge-TTS connectivity and functionality.
Verifies installation and generates a sample audio file.
"""

import asyncio
import os
import sys

# Fix Windows console encoding for emoji/unicode output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def test_import():
    """Test if edge-tts is installed."""
    try:
        import edge_tts
        print("✅ edge-tts library imported successfully")
        return True
    except ImportError:
        print("❌ edge-tts not installed. Run: pip install edge-tts")
        return False

async def test_voice_list():
    """Test if we can retrieve available voices."""
    try:
        import edge_tts
        voices = await edge_tts.VoicesManager.create()
        voice_list = voices.voices
        
        print(f"✅ Retrieved {len(voice_list)} voices from Edge-TTS")
        
        # Show a few English voices
        en_voices = [v for v in voice_list if v['Locale'].startswith('en-')]
        print(f"\n📋 Sample English Voices (showing first 5):")
        for voice in en_voices[:5]:
            print(f"  - {voice['ShortName']}: {voice['Locale']} ({voice['Gender']})")
        
        return True
    except Exception as e:
        print(f"❌ Failed to retrieve voices: {e}")
        return False

async def test_audio_generation():
    """Test generating a sample audio file."""
    try:
        import edge_tts
        
        text = "Hello! This is a test of the Edge TTS system."
        voice = "en-US-AriaNeural"
        output_path = ".tmp/test_audio.mp3"
        
        # Create .tmp directory
        os.makedirs(".tmp", exist_ok=True)
        
        print(f"\n🎤 Generating test audio with voice: {voice}")
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        
        # Check if file was created
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Audio generated successfully: {output_path} ({file_size} bytes)")
            
            # Measure duration (requires pydub)
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(output_path)
                duration = len(audio) / 1000.0
                print(f"   Duration: {duration:.2f} seconds")
            except ImportError:
                print("   (Install pydub to measure duration: pip install pydub)")
            
            return True
        else:
            print("❌ Audio file not created")
            return False
            
    except Exception as e:
        print(f"❌ Audio generation failed: {e}")
        return False

def main():
    """Run all Edge-TTS tests."""
    print("=" * 60)
    print("🧪 Edge-TTS Connectivity Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Import
    results.append(test_import())
    
    if results[0]:
        # Test 2: Voice list
        results.append(asyncio.run(test_voice_list()))
        
        # Test 3: Audio generation
        results.append(asyncio.run(test_audio_generation()))
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Summary: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("✅ Edge-TTS is fully operational!")
        return 0
    else:
        print("❌ Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
