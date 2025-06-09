from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import subprocess
import uuid
import time
import logging
import sys

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(sys.stdout),
                        logging.FileHandler('app.log')
                    ])
logger = logging.getLogger(__name__)

# Ensure audio directory exists
os.makedirs('static/audio', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    try:
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'fa-IR-DilaraNeural')
        rate = data.get('rate', '+0%')
        pitch = data.get('pitch', '+0Hz')
        
        # No longer need to fix 0% or 0Hz as min value is now 1
        # if rate == '0%':
        #     rate = '0'
        # if pitch == '0Hz':
        #     pitch = '0'
        
        logger.debug(f"Received request: text={text[:20]}..., voice={voice}, rate={rate}, pitch={pitch}")
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate a unique filename
        filename = f"{uuid.uuid4()}.mp3"
        output_path = os.path.abspath(os.path.join('static', 'audio', filename))
        
        logger.debug(f"Output path: {output_path}")
        
        # Save text to a temporary file to avoid command-line issues with special characters
        temp_text_file = os.path.abspath(os.path.join('static', 'audio', f"{uuid.uuid4()}.txt"))
        with open(temp_text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        logger.debug(f"Created temporary text file: {temp_text_file}")
        
        # Construct and execute edge-tts command
        cmd = [
            'edge-tts',
            '--file', temp_text_file,
            '--voice', voice,
            '--rate', rate,
            '--pitch', pitch,
            '--write-media', output_path
        ]
        
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        # Use Popen to get real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        stdout, stderr = process.communicate()
        
        # Clean up temporary file
        try:
            os.remove(temp_text_file)
            logger.debug(f"Deleted temporary text file: {temp_text_file}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file: {e}")
        
        if process.returncode != 0:
            logger.error(f"Edge-TTS failed with return code {process.returncode}")
            logger.error(f"STDERR: {stderr}")
            logger.error(f"STDOUT: {stdout}")
            return jsonify({'error': stderr or 'Unknown error occurred'}), 500
        
        # Check if file was actually created
        if not os.path.exists(output_path):
            logger.error(f"Output file {output_path} was not created")
            return jsonify({'error': 'Failed to generate audio file - file not created'}), 500
            
        if os.path.getsize(output_path) == 0:
            logger.error(f"Output file {output_path} is empty")
            return jsonify({'error': 'Failed to generate audio file - file is empty'}), 500
        
        logger.debug(f"Successfully created audio file: {output_path} (size: {os.path.getsize(output_path)} bytes)")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'file_url': f'/static/audio/{filename}'
        })
    
    except Exception as e:
        logger.exception("Exception in text_to_speech:")
        return jsonify({'error': str(e)}), 500

@app.route('/voices')
def get_voices():
    try:
        result = subprocess.run(['edge-tts', '--list-voices'], capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            logger.error(f"Failed to get voices: {result.stderr}")
            return jsonify({'error': result.stderr}), 500
        
        # Parse the output to extract voice information
        voice_lines = result.stdout.strip().split('\n')
        voices = []
        current_voice = None
        
        for line in voice_lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Name:'):
                if current_voice:
                    voices.append(current_voice)
                name_parts = line.split(':', 1)
                if len(name_parts) > 1:
                    voice_name = name_parts[1].strip()
                    current_voice = {
                        'name': voice_name,
                        'language': '',
                        'display_name': voice_name,
                        'gender': ''
                    }
            elif line.startswith('Gender:') and current_voice:
                gender_parts = line.split(':', 1)
                if len(gender_parts) > 1:
                    current_voice['gender'] = gender_parts[1].strip()
                    
                    # Extract language code from name
                    name_parts = current_voice['name'].split('-')
                    if len(name_parts) >= 2:
                        current_voice['language'] = f"{name_parts[0]}-{name_parts[1]}"
                        
                    # Set display name
                    if '-' in current_voice['name']:
                        current_voice['display_name'] = current_voice['name'].split('-')[-1].replace('Neural', '')
        
        # Add the last voice
        if current_voice:
            voices.append(current_voice)
        
        logger.debug(f"Found {len(voices)} voices")
        return jsonify(voices)
    
    except Exception as e:
        logger.exception("Exception in get_voices:")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('static/audio', filename, as_attachment=True)

@app.route('/clean-audio', methods=['POST'])
def clean_audio():
    try:
        # Get list of audio files
        audio_dir = os.path.join('static', 'audio')
        files = os.listdir(audio_dir)
        
        # Keep only files older than 1 hour
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        deleted_count = 0
        for file in files:
            file_path = os.path.join(audio_dir, file)
            if os.path.isfile(file_path):
                file_creation_time = os.path.getctime(file_path)
                if file_creation_time < one_hour_ago:
                    os.remove(file_path)
                    deleted_count += 1
        
        return jsonify({'success': True, 'deleted_count': deleted_count})
    
    except Exception as e:
        logger.exception("Exception in clean_audio:")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting application...")
    app.run(debug=True) 