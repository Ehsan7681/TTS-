import subprocess
import os
import sys

def test_edge_tts():
    print("Testing edge-tts installation...")
    
    # Check if edge-tts is installed
    try:
        version_result = subprocess.run(['edge-tts', '--version'], 
                                       capture_output=True, text=True)
        print("edge-tts command exists")
    except Exception as e:
        print(f"Error running edge-tts: {e}")
        return False
    
    # Create a test text file
    test_text = "این یک آزمایش است"
    test_file = "test_text.txt"
    
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_text)
        
        print(f"Created test file: {test_file}")
        
        # Try to convert text to speech
        output_file = "test_output.mp3"
        print(f"Attempting to create audio file: {output_file}")
        
        cmd = [
            'edge-tts',
            '--file', test_file,
            '--voice', 'fa-IR-DilaraNeural',
            '--write-media', output_file
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False
        
        # Check if file was created
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"Successfully created audio file: {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print(f"Failed to create audio file or file is empty")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False
    finally:
        # Clean up
        try:
            if os.path.exists(test_file):
                os.remove(test_file)
            if os.path.exists(output_file):
                os.remove(output_file)
        except:
            pass

if __name__ == "__main__":
    success = test_edge_tts()
    print(f"Test {'succeeded' if success else 'failed'}")
    sys.exit(0 if success else 1)