"use client";

import React, { useEffect, useRef, useState } from 'react';

const Home: React.FC = () => {
  const [text, setText] = useState('');
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [recorder, setRecorder] = useState<MediaRecorder | null>(null);
  const [transcription, setTranscription] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [audioError, setAudioError] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [micDevices, setMicDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedMic, setSelectedMic] = useState('');
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<AudioBufferSourceNode | null>(null);

  useEffect(() => {
    // Initialize AudioContext
    audioContextRef.current = new AudioContext();
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    // Fetch available microphones
    navigator.mediaDevices.enumerateDevices().then(devices => {
      const mics = devices.filter(device => device.kind === 'audioinput');
      setMicDevices(mics);
      if (mics.length > 0) setSelectedMic(mics[0].deviceId); // Default to the first mic
    }).catch((error: Error) => {
      console.error('Error enumerating devices:', error.message);
      setAudioError(`Error enumerating devices: ${error.message}`);
    });
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: selectedMic ? { exact: selectedMic } : undefined }
      });
      setAudioStream(stream);

      const mediaRecorder = new MediaRecorder(stream);
      setRecorder(mediaRecorder);

      const audioChunks: Blob[] = [];

      mediaRecorder.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        sendAudioToBackend(audioBlob);
      };

      mediaRecorder.start();
    } catch (error) {
      if (error instanceof Error) {
        console.error('Error accessing microphone:', error.message);
        setAudioError(`Error accessing microphone: ${error.message}`);
      }
    }
  };

  const stopRecording = () => {
    if (recorder) {
      recorder.stop();
      setRecorder(null);
    }
  };

  const handleMicChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMic(event.target.value);
  };

  const sendAudioToBackend = async (audioBlob: Blob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob);

    try {
        const response = await fetch(process.env.NEXT_PUBLIC_API_URL + '/speak', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const jsonResponse = await response.json();
            setTranscription(jsonResponse.transcription);
            setAiResponse(jsonResponse.ai_response);

            // Log the audio URL to verify it's correct
            console.log('Backend Response:', jsonResponse);

            const audioUrl = process.env.NEXT_PUBLIC_API_URL + jsonResponse.audio_url;

            // Play audio
            const audio = new Audio(audioUrl);
            audio.play();
            setIsPlaying(true);

            audio.onended = () => {
                setIsPlaying(false);
            };
        } else {
            console.error("Server responded with status:", response.status);
            setAudioError(`Server error: ${response.status}`);
        }
    } catch (error) {
        if (error instanceof Error) {
            console.error('Error sending audio to backend:', error.message);
            setAudioError(`Error sending audio to backend: ${error.message}`);
        }
    }
};


  const stopAudio = () => {
    if (sourceNodeRef.current) {
      sourceNodeRef.current.stop();
      setIsPlaying(false);
    } else {
      const audio = document.querySelector("audio");
      if (audio) {
        audio.pause();
        audio.currentTime = 0;
        setIsPlaying(false);
      }
    }
  };

  return (
    <>
      <section className="bg-gradient-to-r from-blue-500 via-blue-400 to-blue-300 h-screen flex justify-center items-center">
        <div className="bg-white p-8 rounded-lg shadow-lg w-1/2 max-w-sm text-center">
          <h1 className="text-3xl font-extrabold text-gray-800 mb-4">Mock-Up Interview</h1>

          {/* Microphone Selection */}
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">Select Microphone:</label>
            <select value={selectedMic} onChange={handleMicChange} className="w-full p-2 border rounded text-black">
              {micDevices.map(mic => (
                <option key={mic.deviceId} value={mic.deviceId}>
                  {mic.label || `Microphone ${mic.deviceId}`}
                </option>
              ))}
            </select>
          </div>

          {/* Recording Button */}
          {
            recorder ? (
              <button onClick={stopRecording} className="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-full w-32 focus:outline-none">Stop</button>
            ) : (
              <button onClick={startRecording} className="bg-blue-500 hover:bg-blue-900 text-white font-semibold py-2 px-4 rounded-full w-32 focus:outline-none">Start</button>
            )
          }

          {/* Display transcription */}
          {transcription && (
            <div className="text-left mt-4">
              <p className="text-sm text-gray-600">Your transcription:</p>
              <div className="bg-gray-100 p-3 rounded-md text-black">{transcription}</div>
            </div>
          )}

          {/* Display AI response */}
          {aiResponse && (
            <div className="text-left mt-4">
              <p className="text-sm text-gray-600">AI Sales Agent Response:</p>
              <div id="ai-response" className="bg-gray-100 p-3 rounded-md text-black">{aiResponse}</div>
            </div>
          )}

          {/* Audio controls */}
          {isPlaying && (
            <button onClick={stopAudio} className="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-full mt-4">
              Stop Audio
            </button>
          )}

          {/* Error display */}
          {audioError && (
            <div className="text-red-500 mt-4">
              {audioError}
            </div>
          )}
        </div>
      </section>
    </>
  );
}

export default Home;
