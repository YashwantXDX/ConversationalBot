// Conversational Bot using MediaRecorder API
let mediaRecorder;
let audioChunks = [];
let autoConversation = true;

const recordBtn = document.getElementById('record-btn');
const echoAudioPlayer = document.getElementById('audio-playback');
const stopConversation = document.getElementById('stop-conversation');
const statusText = document.getElementById('transcript-status');

// Get session_id from URL
const urlParamaters = new URLSearchParams(window.location.search);
const sessionId = urlParamaters.get("session_id");

let isRecording = false;

// Function to Stop the Conversation
stopConversation.addEventListener('click', () => {
    autoConversation = false;
    isRecording = false;
    recordBtn.textContent = "🎙️ Start Recording";
    recordBtn.classList.remove('recording');
    statusText.textContent = "Conversation Stopped"
})

// Toggle Recording
recordBtn.addEventListener('click', async () => {
    if (!isRecording) {
        // Start Recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                sendToGemini(audioBlob);
            };

            mediaRecorder.start();
            isRecording = true;
            recordBtn.textContent = "⏹️ Stop Recording";
            recordBtn.classList.add('recording');
            recordBtn.disabled = false;

        } catch (error) {
            alert("Microphone access denied or not available");
            console.error(error);
        }
    } else {
        // Stop Recording
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        isRecording = false;
        recordBtn.textContent = "⏳ Wait for Response";
        recordBtn.disabled = true;
        recordBtn.classList.remove('recording');
    }
});

// Transcribe Audio and Send it to Gemini Functionality
function sendToGemini(audioBlob){

    const formData = new FormData();
    const filename = `recording_${Date.now()}.webm`;
    const file = new File([audioBlob], filename, {type: 'audio/webm'});
    formData.append('audio', file);

    statusText.textContent = 'Processing...';

    fetch(`http://localhost:8000/agent/chat/${sessionId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {

        // Handle API Level Errors
        if(data.error){
            console.error("Server Error: ", data.error);
            statusText.textContent = "Error: " + data.error;
            recordBtn.disabled = false;
            recordBtn.textContent = "🎙️ Start Recording";
            return;
        }
        
        // If Audio Urls Exists
        if(data.audio_urls && data.audio_urls.length > 0){
            
            statusText.textContent = "Playing Response";

            playSequentialAudio(data.audio_urls, () => {

                // Re-Enable button and show Stop Recording again
                recordBtn.disabled = false;
                recordBtn.textContent = "⏹️ Stop Recording";

                // Auto Start Recording again after bot finishes
                if(autoConversation)
                    recordBtn.click();

            });

        }
        
        else{
            statusText.textContent =  data.gemini_response || "No Response from Server";
            console.warn("No Audio Urls returned, showing text only.");
            autoConversation = false;
            recordBtn.disabled = false;
            recordBtn.textContent = "🎙️ Start Recording";
            console.error(data);
        }
    })
    .catch(err => {
        statusText.textContent = "Error Sending to Gemini";
        autoConversation = false;
        recordBtn.disabled = false;
        recordBtn.textContent = "🎙️ Start Recording";
        console.error(err);
    })

}

// Play All the Audio Urls Sequentially
function playSequentialAudio(audio_urls, onComplete){

    let index = 0;
    const audio = echoAudioPlayer;

    // Internal Function to play next audio url
    function playNext(){

        if(index < audio_urls.length){

            audio.src = audio_urls[index];
            audio.play();
            index++;

        }
        else{

            statusText.textContent = "Response Complete"
            if(onComplete && autoConversation) onComplete();

        }

    }

    // When the audio is finished, it will play the next audio
    audio.onended = playNext;
    playNext();

}