import json
import os
import tempfile
import uuid
from io import BytesIO
from pathlib import Path

import librosa
import torch
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from fastapi import HTTPException, UploadFile
from openai import OpenAI
from rag_service import rag_service
from transformers import WhisperForConditionalGeneration, WhisperProcessor

load_dotenv()


class TranscriptionClient:
    def transcribe(self, audio_file_path, language="id"):
        raise NotImplementedError("This method should be overridden in subclasses")


class HuggingFaceWhisperClient(TranscriptionClient):
    def __init__(self, model_name="openai/whisper-small", device="cpu"):
        self.processor = WhisperProcessor.from_pretrained(model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_name)
        self.device = torch.device(device)
        self.model.to(self.device)
        print(f"Model berjalan di {self.device.type.upper()}.")

    def transcribe(self, audio_file_path, language="id"):
        try:
            audio_input, sample_rate = librosa.load(audio_file_path, sr=16000)

            input_features = self.processor(
                audio_input, sampling_rate=16000, return_tensors="pt"
            ).input_features

            input_features = input_features.to(self.device)
            generated_ids = self.model.generate(
                input_features,
                forced_decoder_ids=self.processor.get_decoder_prompt_ids(
                    language=language
                ),
            )

            transcription = self.processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]
            return transcription

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error in transcription: {str(e)}"
            )


class OpenAIWhisperClient(TranscriptionClient):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def transcribe(self, audio_file_path, language="id"):
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",
                    language=language,
                )

            if hasattr(transcription, "text"):
                return transcription.text
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected transcription response: {transcription}",
                )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error in transcription: {str(e)}"
            )


class OpenAIClient:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def get_ai_response(self, question, position, interview_type="hr"):
        try:
            ai_response = rag_service.get_ai_response(
                question, position, interview_type
            )
            return ai_response
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error in AI response: {str(e)}"
            )


class AIService:
    def __init__(
        self,
        transcription_client: TranscriptionClient,
        tts_service: str = "openai",
    ):
        self.transcription_client = transcription_client
        self.tts_service = tts_service.lower()
        self.openai_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
        self.elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    async def handle_audio_transcription(self, audio: UploadFile):
        if not audio:
            raise HTTPException(status_code=400, detail="No audio file provided")

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_name = temp_file.name

            audio_content = await audio.read()

            with open(temp_file_name, "wb") as f:
                f.write(audio_content)

            transcription = self.transcription_client.transcribe(
                temp_file_name, language="id"
            )

            os.remove(temp_file_name)

            if transcription:
                return transcription
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected transcription response: {transcription}",
                )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error in transcription: {str(e)}"
            )

    def generate_speech(self, text: str, user_id: str, filename: str = None) -> str:
        if filename is None:
            filename = f"temp_audio_{user_id}_{uuid.uuid4()}.mp3"

        if isinstance(text, dict):
            text = json.dumps(text, ensure_ascii=False)

        if self.tts_service == "elevenlabs":
            response = self.elevenlabs_client.text_to_speech.convert(
                voice_id="3mAVBNEqop5UbHtD8oxQ",
                output_format="mp3_22050_32",
                text=text,
                model_id="eleven_turbo_v2_5",
                language_code="id",
                voice_settings=VoiceSettings(
                    stability=0.1,
                    similarity_boost=0.3,
                    style=0.0,
                    use_speaker_boost=True,
                ),
            )

            audio_stream = BytesIO()

            for chunk in response:
                if chunk:
                    audio_stream.write(chunk)

            with open(filename, "wb") as audio_file:
                audio_file.write(audio_stream.getvalue())

            return filename

        elif self.tts_service == "openai":
            speech_file_path = Path(filename)

            response = self.openai_client.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
            )

            # Simpan hasil speech ke file
            response.stream_to_file(speech_file_path)
            return str(speech_file_path)

        else:
            raise ValueError(f"Unsupported TTS service: {self.tts_service}")
