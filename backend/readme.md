### How to choose transcribe service
a. OpenAI
  - add this to .env = TRANSCRIPTION_SERVICE=openai

b. Huggingface
  - comment/erase TRANSCRIPTION_SERVICE=openai from .env, karena by default akan via huggingface

### How to pick position="Software Engineer"
a. Ganti di function get_ai_response
   - def get_ai_response(self, question, position="Software Engineer"):
