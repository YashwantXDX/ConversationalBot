let ws;
let isRecording = false;
let audioContext, sourceNode, processorNode;

const recordBtn = document.getElementById('record-btn');
const stopConversation = document.getElementById('stop-conversation');
const statusText = document.getElementById('transcript-status');

function setStatus(msg) {
  if (statusText) statusText.textContent = msg;
  console.log(msg);
}

stopConversation?.addEventListener('click', () => {
  stopStreaming();
  setStatus("Conversation Stopped");
});

// --- PCM helpers ---
function downsampleBuffer(buffer, inputSampleRate, outSampleRate = 16000) {
  if (outSampleRate === inputSampleRate) return buffer;
  const sampleRateRatio = inputSampleRate / outSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  let offsetResult = 0, offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0, count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = accum / count || 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  let offset = 0;
  for (let i = 0; i < float32Array.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  return buffer;
}

// --- Start streaming ---
async function startStreaming() {
  if (isRecording || ws) return;

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${protocol}://${location.host}/ws/audio`);

  ws.onopen = async () => {
    setStatus("Connected. Requesting microphone...");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      sourceNode = audioContext.createMediaStreamSource(stream);
      processorNode = audioContext.createScriptProcessor(4096, 1, 1);

      processorNode.onaudioprocess = (event) => {
        if (!isRecording || ws.readyState !== WebSocket.OPEN) return;
        const input = event.inputBuffer.getChannelData(0);
        const downsampled = downsampleBuffer(input, audioContext.sampleRate, 16000);
        const pcm16 = floatTo16BitPCM(downsampled);
        ws.send(new Uint8Array(pcm16));
      };

      sourceNode.connect(processorNode);
      processorNode.connect(audioContext.destination); // optional for monitoring

      ws.onmessage = (evt) => setStatus(evt.data);

      ws.onclose = () => {
        setStatus("WebSocket closed");
        ws = null;
        isRecording = false;
        recordBtn.textContent = "🎙️ Start Streaming";
        recordBtn.classList.remove("recording");
      };

      ws.onerror = (e) => console.error("WebSocket error", e);

      isRecording = true;
      recordBtn.textContent = "⏹️ Stop Streaming";
      recordBtn.classList.add("recording");
      setStatus("Streaming audio...");
    } catch (err) {
      console.error(err);
      alert("Microphone access denied or unavailable");
    }
  };
}

// --- Stop streaming ---
function stopStreaming() {
  if (!isRecording) return;

  // stop sending audio
  if (processorNode) {
    processorNode.disconnect();
    processorNode.onaudioprocess = null;
    processorNode = null;
  }
  if (sourceNode) {
    sourceNode.disconnect();
    sourceNode = null;
  }

  // instead of closing AudioContext, just suspend it
  if (audioContext) {
    audioContext.suspend();
    audioContext = null;
  }

  // close WebSocket safely
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }

  isRecording = false;
  setStatus("Stopped streaming");
}

// --- Toggle button ---
recordBtn.addEventListener("click", async () => {
  if (!isRecording) {
    await startStreaming();
  } else {
    stopStreaming();
  }
});
