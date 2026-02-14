"""
Test script for FFmpeg availability.
Verifies FFmpeg is installed and accessible.
"""

import subprocess
import sys
import os

# Fix Windows console encoding for emoji/unicode output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def test_ffmpeg_installed():
    """Test if FFmpeg is installed and in PATH."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Parse version info
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg is installed: {version_line}")
            return True
        else:
            print("❌ FFmpeg command failed")
            return False
            
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        print("\n📥 Installation Instructions:")
        print("   Windows: Download from https://ffmpeg.org/download.html")
        print("            Add to PATH or use Chocolatey: choco install ffmpeg")
        print("   Linux:   sudo apt-get install ffmpeg")
        print("   Mac:     brew install ffmpeg")
        return False
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False

def test_ffmpeg_codecs():
    """Test if required codecs are available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-codecs"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        codecs = result.stdout
        required_codecs = {
            "libx264": "H.264 video encoder",
            "aac": "AAC audio encoder"
        }
        
        print("\n🎬 Checking required codecs:")
        
        all_found = True
        for codec, description in required_codecs.items():
            if codec in codecs:
                print(f"   ✅ {codec} ({description})")
            else:
                print(f"   ❌ {codec} ({description}) - NOT FOUND")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ Codec check failed: {e}")
        return False

def test_ffmpeg_simple_operation():
    """Test a simple FFmpeg operation (create a test video)."""
    try:
        # Create .tmp directory
        os.makedirs(".tmp", exist_ok=True)
        
        output_file = ".tmp/test_video.mp4"
        
        # Create a 1-second black video
        print("\n🎥 Testing video creation (1-second black screen)...")
        
        result = subprocess.run([
            "ffmpeg",
            "-f", "lavfi",
            "-i", "color=c=black:s=1920x1080:d=1",
            "-c:v", "libx264",
            "-t", "1",
            "-pix_fmt", "yuv420p",
            "-y",  # Overwrite without asking
            output_file
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Test video created: {output_file} ({file_size} bytes)")
            
            # Clean up
            os.remove(output_file)
            print("   (Test file cleaned up)")
            
            return True
        else:
            print(f"❌ Video creation failed")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg operation timed out")
        return False
    except Exception as e:
        print(f"❌ Video creation test failed: {e}")
        return False

def main():
    """Run all FFmpeg tests."""
    print("=" * 60)
    print("🧪 FFmpeg Connectivity Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Installation
    installed = test_ffmpeg_installed()
    results.append(installed)
    
    if not installed:
        print("\n❌ Cannot proceed without FFmpeg")
        return 1
    
    # Test 2: Codecs
    results.append(test_ffmpeg_codecs())
    
    # Test 3: Simple operation
    results.append(test_ffmpeg_simple_operation())
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Summary: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("✅ FFmpeg is fully operational!")
        return 0
    else:
        print("❌ Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
