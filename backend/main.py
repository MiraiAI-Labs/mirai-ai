import logging
import os
import uuid
from pathlib import Path

from ai import AIService, HuggingFaceWhisperClient, OpenAIWhisperClient
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

load_dotenv()

# Ensure the 'audios' directory exists
audios_dir = Path("./audios")
audios_dir.mkdir(parents=True, exist_ok=True)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "API key not found. Make sure to set it in your environment variables."
    )

transcription_service = os.getenv("TRANSCRIPTION_SERVICE", "huggingface").lower()

if transcription_service == "huggingface":
    transcription_client = HuggingFaceWhisperClient()
elif transcription_service == "openai":
    transcription_client = OpenAIWhisperClient(api_key=api_key)
else:
    raise ValueError(
        f"Invalid TRANSCRIPTION_SERVICE '{transcription_service}'. Must be 'huggingface' or 'openai'."
    )

ai_service = AIService(transcription_client=transcription_client)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.post("/speak")
async def speak(
    audio: UploadFile = File(...),
    position: str = Query(..., description="The position for the interview"),
    user_id: str = Query("userid", description="User identifier"),
):
    speech_file_path = None
    try:
        transcription = await ai_service.handle_audio_transcription(audio)
        logger.info(f"Transcription: {transcription}")

        ai_response = ai_service.openai_client.get_ai_response(transcription, position)
        logger.info(f"AI Response: {ai_response}")

        filename = f"audios/temp_audio_{user_id}_{uuid.uuid4()}.mp3"
        speech_file_path = ai_service.generate_speech(
            ai_response, user_id=user_id, filename=filename
        )

        return JSONResponse(
            {
                "transcription": transcription,
                "ai_response": ai_response,
                "audio_url": f"/audio/{Path(speech_file_path).name}",
            }
        )

    except Exception as e:
        logger.error(f"Error in /speak endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    finally:
        if speech_file_path:
            import threading
            import time

            def delete_file(path, delay):
                time.sleep(delay)
                try:
                    os.remove(path)
                    logger.info(f"Deleted temporary file: {path}")
                except Exception as e:
                    logger.error(f"Error deleting temporary file: {str(e)}")

            threading.Thread(target=delete_file, args=(speech_file_path, 300)).start()


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = Path(f"./audios/{filename}")
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")
