"use client";

import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';

interface AIResponse {
  status: string;
  skor?: {
    motivasi: number;
    technical_skills: number;
    pengalaman_proyek: number;
    pemecahan_masalah: number;
    kecocokan_budaya: number;
  };
  evaluasi_terperinci?: string;
  ai_response: string;
}

type SkorKeys = keyof AIResponse['skor'];

const MockInterview: React.FC = () => {
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [recorder, setRecorder] = useState<MediaRecorder | null>(null);
  const [transcription, setTranscription] = useState<string>('');
  const [aiResponse, setAiResponse] = useState<AIResponse | null>(null);
  const [audioError, setAudioError] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [micDevices, setMicDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedMic, setSelectedMic] = useState<string>('');
  const [isStartButtonDisabled, setIsStartButtonDisabled] = useState<boolean>(true);
  const [ttsService, setTtsService] = useState<string>('');

  const audioContextRef = useRef<AudioContext | null>(null);

  const searchParams = useSearchParams();
  const position = searchParams.get('position') || '';
  // Ambil interview_type dari URL, default nya HR
  const interviewType = searchParams.get('interview_type') || 'hr';


  useEffect(() => {
    const fetchTtsService = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config`);
        if (response.ok) {
          const config = await response.json();
          setTtsService(config.tts_service);
        } else {
          console.error("Failed to fetch tts_service from backend");
        }
      } catch (error) {
        console.error("Error fetching tts_service:", error);
      }
    };

    fetchTtsService();
  }, []);

  useEffect(() => {
    if (!ttsService) return;

    const baseUrl = process.env.NEXT_PUBLIC_API_URL;

    if (!baseUrl) {
      console.error("Backend URL is not defined in environment variables");
      return;
    }

    // Tentukan URL audio yang sesuai berdasarkan interviewType
    const welcomeAudioUrl = interviewType === "tech"
      ? ttsService === "openai"
        ? `${baseUrl}/static/welcoming/welcoming-tech-alloy.wav`
        : `${baseUrl}/static/welcoming/welcoming-tech-zephlyn.wav`
      : ttsService === "openai"
        ? `${baseUrl}/static/welcoming/welcoming-alloy.wav`
        : `${baseUrl}/static/welcoming/welcoming-zephlyn.wav`;

    console.log("Playing audio from URL:", welcomeAudioUrl);

    const welcomeAudio = new Audio(welcomeAudioUrl);

    welcomeAudio.play().catch(error => {
      console.error("Error playing the audio:", error);
      setAudioError("Failed to play welcoming audio.");
    });

    welcomeAudio.onplay = () => {
      setIsPlaying(true);
      setIsStartButtonDisabled(true);
    };

    welcomeAudio.onended = () => {
      setIsPlaying(false);
      setIsStartButtonDisabled(false);
    };

  }, [ttsService, interviewType]);


  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then(devices => {
      const mics = devices.filter(device => device.kind === 'audioinput');
      setMicDevices(mics);
      if (mics.length > 0) setSelectedMic(mics[0].deviceId);
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

  const userId = 'user_a'; // CONTOH DUMMY USER ID

  const sendAudioToBackend = async (audioBlob: Blob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/speak?position=${encodeURIComponent(position)}&user_id=${encodeURIComponent(userId)}`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const jsonResponse = await response.json();
        setTranscription(jsonResponse.transcription);

        // Pastikan ai_response diterima dan di-set dengan benar
        console.log("AI Response from Backend: ", jsonResponse.ai_response);
        setAiResponse(jsonResponse);  // Set seluruh respons ke aiResponse

        const audioUrl = `${process.env.NEXT_PUBLIC_API_URL}${jsonResponse.audio_url}`;

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



  return (
    <section className="bg-gradient-to-r from-blue-500 via-blue-400 to-blue-300 h-screen flex justify-center items-center">
      <div className="bg-white p-8 rounded-lg shadow-lg w-1/2 max-w-sm text-center">
        <h1 className="text-3xl font-extrabold text-gray-800 mb-4">Mock Interview</h1>
        <p className="text-lg text-gray-600 mb-4">Position: {position}</p>

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
        <button
          onClick={recorder ? stopRecording : startRecording}
          className={`font-semibold py-2 px-4 rounded-full w-32 focus:outline-none ${recorder ? 'bg-red-500 hover:bg-red-600 text-white' : `bg-blue-500 hover:bg-blue-600 text-white ${isStartButtonDisabled ? 'cursor-not-allowed opacity-50' : ''}`}`}
          disabled={!recorder && isStartButtonDisabled}
        >
          {recorder ? "Stop" : "Start"}
        </button>

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
          <p className="text-sm text-gray-600">AI Interviewer Response:</p>

          {/* Menampilkan ai_response walaupun skor belum muncul */}
          <div id="ai-response" className="bg-gray-100 p-3 rounded-md text-black">
            <p>{typeof aiResponse.ai_response === 'object' ? JSON.stringify(aiResponse.ai_response) : aiResponse.ai_response}</p>
          </div>

          {/* Menampilkan evaluasi dan skor jika sudah tersedia */}
          {aiResponse.skor && (
            <div className="mt-4">
              <p><strong>Status:</strong> {aiResponse.status}</p>
              <div>
                <p><strong>Skor:</strong></p>
                <ul>
                  {Object.keys(aiResponse.skor).map((key) => (
                    <li key={key}>
                      {key.replace(/_/g, ' ')}: {aiResponse.skor?.[key as SkorKeys]}
                    </li>
                  ))}
                </ul>
              </div>
              <p><strong>Evaluasi Terperinci:</strong> {aiResponse.evaluasi_terperinci}</p>
            </div>
          )}
        </div>
)}

        {/* Error display */}
        {audioError && (
          <div className="text-red-500 mt-4">
            {audioError}
          </div>
        )}
      </div>
    </section>
  );
}

export default MockInterview;
