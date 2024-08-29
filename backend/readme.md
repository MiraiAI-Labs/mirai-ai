### How to choose transcribe service
a. OpenAI
  - add this to .env = TRANSCRIPTION_SERVICE=openai

b. Huggingface
  - comment/erase TRANSCRIPTION_SERVICE=openai from .env, karena by default akan via huggingface

### How to pick position="Software Engineer"
a. Ganti di function get_ai_response
   - def get_ai_response(self, question, position="Software Engineer"):

### How to choose text-to-speech
a. di ai.py 
```py
class AIService:
    def __init__(
        self,
        transcription_client: TranscriptionClient,
        tts_service: str = "openai", # openai/elevenlabs
    ):
```