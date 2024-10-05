import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from ai import AIService, HuggingFaceWhisperClient, OpenAIWhisperClient
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from llama_index.llms.openai import OpenAI
from openai import OpenAI
from pydantic import BaseModel
from rag_service import rag_service

load_dotenv()
logger = logging.getLogger(__name__)

audios_dir = Path("./audios")
audios_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI()

welcoming_dir = Path(__file__).parent / "audios" / "welcoming"

if not welcoming_dir.exists():
    raise RuntimeError(f"Directory '{welcoming_dir}' does not exist")

app.mount(
    "/static/welcoming", StaticFiles(directory=welcoming_dir), name="static_welcoming"
)

sessions = {}
SESSION_EXPIRY = 3600  # 1 hour session expiry time


def cleanup_expired_sessions():
    current_time = time.time()
    expired_sessions = [
        userid
        for userid, session in sessions.items()
        if current_time - session["timestamp"] > SESSION_EXPIRY
    ]

    for userid in expired_sessions:
        del sessions[userid]
        logger.info(f"Session for userid {userid} expired and was removed.")


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/generate_quiz")
async def generate_quiz(
    position: str = Query(
        ..., description="The position for which the quiz will be generated"
    ),
):
    try:
        quiz_json = rag_service.generate_quiz(position)
        return JSONResponse(content=quiz_json)
    except Exception as e:
        logger.error(f"Error in /generate_quiz endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/speak")
async def speak(
    audio: UploadFile = File(...),
    position: str = Query(..., description="The position for the interview"),
    user_id: str = Query(..., description="User identifier"),
    interview_type: str = Query(
        "tech", description="Type of interview: 'hr' or 'tech'"
    ),
):
    cleanup_expired_sessions()

    if user_id not in sessions:
        sessions[user_id] = {
            "conversation_history": [],
            "current_question_index": 0,
            "timestamp": time.time(),
            "file_names": [],
        }
        logger.info(f"Created new session for user_id={user_id}")
    else:
        logger.info(f"Using existing session for user_id={user_id}")

    session = sessions[user_id]

    speech_file_path = None
    try:
        transcription = await ai_service.handle_audio_transcription(audio)
        logger.info(f"Transcription: {transcription}")

        ai_response = ai_service.openai_client.get_ai_response(
            transcription, position, interview_type
        )
        logger.info(f"AI Response: {ai_response}")

        filename = f"audios/temp_audio_{user_id}_{uuid.uuid4()}.mp3"
        speech_file_path = ai_service.generate_speech(
            ai_response, user_id=user_id, filename=filename
        )

        sessions[user_id]["file_names"].append(Path(speech_file_path).name)
        session["conversation_history"].append(f"Kandidat: {transcription}")
        session["conversation_history"].append(f"HR: {ai_response}")
        session["current_question_index"] += 1
        session["timestamp"] = time.time()

        return JSONResponse(
            {
                "transcription": transcription,
                "ai_response": ai_response,
                "audio_url": f"/audio/{Path(speech_file_path).name}?user_id={user_id}",
            }
        )

    except Exception as e:
        logger.error(f"Error in /speak endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    finally:
        if speech_file_path:
            import threading

            def delete_file(path, delay):
                time.sleep(delay)
                try:
                    os.remove(path)
                    logger.info(f"Deleted temporary file: {path}")
                except Exception as e:
                    logger.error(f"Error deleting temporary file: {str(e)}")

            threading.Thread(target=delete_file, args=(speech_file_path, 300)).start()


@app.get("/audio/{filename}")
async def get_audio(filename: str, user_id: str = Query(...)):
    logger.info(f"Request to get audio: filename={filename}, user_id={user_id}")
    if user_id in sessions:
        logger.info(f"Session found for user_id={user_id}")
        if filename in sessions[user_id]["file_names"]:
            logger.info(f"Filename {filename} found in session for user_id={user_id}")
            file_path = Path(f"./audios/{filename}")
            if file_path.exists():
                logger.info(f"File {filename} exists, returning file.")
                return FileResponse(file_path, media_type="audio/mpeg")
            else:
                logger.error(f"File {filename} does not exist on disk.")
                raise HTTPException(status_code=404, detail="File not found")
        else:
            logger.error(
                f"Filename {filename} not found in session for user_id={user_id}"
            )
            raise HTTPException(status_code=403, detail="Unauthorized access")
    else:
        logger.error(f"No session found for user_id={user_id}")
        raise HTTPException(status_code=403, detail="Unauthorized access")


@app.get("/config")
async def get_config():
    return {"tts_service": ai_service.tts_service}


######################## JobSeeker Advice ########################
from fastapi import Body, Query


@app.post("/jobseeker_advice")
async def jobseeker_advice(
    job_title: str = Query(
        ..., description="Job title for which advice will be provided"
    ),
    data: dict = Body(..., description="JSON data containing job-related information"),
):
    logger.info(f"Received request for job title: {job_title}")

    try:
        logger.info(f"Received JSON data: {data}")

        if "wordcloud_data" not in data:
            logger.error(f"Invalid JSON structure: {data}")
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON structure, 'wordcloud_data' missing",
            )

        wordcloud_data = data.get("wordcloud_data", {})
        logger.info(f"Extracted wordcloud data: {wordcloud_data}")

        advice_prompt = f"""
        TOLONG SELALU JAWAB DENGAN BAHASA INDONESIA.

        Anda adalah seorang penasihat karir advance yang membantu pencari kerja yang ingin menjadi seorang {job_title} handal.
        Berdasarkan tren industri saat ini, keterampilan utama yang dibutuhkan untuk posisi ini adalah: {', '.join(wordcloud_data.keys())}.

        Mohon berikan advice/saran untuk mendapatkan pekerjaan impian nya sesuai dengan job {job_title}

        Buat dalam 2 kalimat saja
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": advice_prompt}],
            temperature=0.7,
        )

        response_text = response.choices[0].message.content.strip()

        logger.info(f"AI Response: {response_text}")

        return JSONResponse(content={"advice": response_text})

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON data")
        raise HTTPException(status_code=400, detail="Failed to parse JSON data")
    except Exception as e:
        logger.error(f"Error generating jobseeker advice: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


######################## Quiz Roadmap ########################


class QuizRequest(BaseModel):
    title: str
    description: Optional[str] = None


client = OpenAI(api_key=api_key)


@app.post("/roadmap_quiz")
async def roadmap_quiz(request: QuizRequest):
    """
    Generate 1 soal quiz based on title & description (optional)
    """
    try:
        title = request.title
        description = (
            request.description if request.description else "Deskripsi tidak tersedia"
        )

        quiz_prompt = f"""
        TOLONG SELALU JAWAB DENGAN BAHASA INDONESIA

        You are a domain expert creating a quiz for the topic "{title}".
        Description: {description}

        Tolong buat 1 pertanyaan yang relevan dengan description tersebut. Include 4 multiple-choice options tanpa keterangan A B C D and indicate the correct answer index.

        Format the output in JSON with the following structure:
        {{
          "question": "Your generated question",
          "choices": ["Option 1", "Option 2", "Option 3", "Option 4"],
          "answer": CorrectAnswerIndex
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": quiz_prompt}],
            temperature=0.7,
            max_tokens=300,
        )

        response_text = response.choices[0].message.content.strip()

        start_index = response_text.find("{")
        end_index = response_text.rfind("}") + 1
        quiz_json = json.loads(response_text[start_index:end_index])

        return JSONResponse(content=quiz_json)

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from OpenAI response")
        raise HTTPException(status_code=400, detail="Failed to parse JSON response")
    except Exception as e:
        logger.error(f"Error generating quiz using OpenAI API: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        ssl_keyfile="/etc/letsencrypt/live/mirai.ahli-waris.my.id/privkey.pem",
        ssl_certfile="/etc/letsencrypt/live/mirai.ahli-waris.my.id/fullchain.pem",
    )
