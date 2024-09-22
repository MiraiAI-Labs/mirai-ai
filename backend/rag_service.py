import json
import os

from dotenv import load_dotenv
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

load_dotenv()


class RAGService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key not found. Make sure to set it in your environment variables."
            )

        Settings.llm = OpenAI(model="gpt-4o-mini", api_key=self.api_key)
        self.embed_model = OpenAIEmbedding(
            model="text-embedding-3-small", api_key=self.api_key
        )

        self.PERSIST_DIR = "./storage"
        self.index = self._load_or_create_index()
        self.conversation_history = []
        self.current_question_index = 0
        self.position = ""
        self.evaluation_scores = {}
        self.evaluation_text = ""
        self.is_evaluation_done = False
        self.interview_type = "hr"

    def _load_or_create_index(self):
        if not os.path.exists(self.PERSIST_DIR):
            documents = SimpleDirectoryReader("data").load_data()
            index = VectorStoreIndex.from_documents(
                documents, embed_model=self.embed_model
            )
            index.storage_context.persist(persist_dir=self.PERSIST_DIR)
        else:
            storage_context = StorageContext.from_defaults(persist_dir=self.PERSIST_DIR)
            index = load_index_from_storage(storage_context)
        return index

    def create_system_prompt(self):
        if self.interview_type == "hr":
            return f"""
            Nama anda adalah Mirai, seorang profesional HR yang berpengalaman dan sedang melakukan wawancara untuk posisi {self.position}.

            Sebelumnya, Anda sudah melakukan opening dengan statement sebagai berikut "Terima kasih karena telah mempunyai ketertarikan pada perusahaan kami, Nama saya Mirai dari tim rekrutmen. Terima kasih sudah meluangkan waktu untuk mengikuti sesi wawancara ini. Kami sangat senang bisa mengenal Anda lebih dekat hari ini. Semoga kita bisa melalui sesi ini dengan lancar dan nyaman. Jika ada hal yang ingin ditanyakan selama wawancara, jangan ragu untuk mengatakannya. Mari kita mulai dengan perkenalan diri anda secara kreatif"
            Jadi, tolong lanjutkan sesuai dengan konteks dan hasil dari jawaban kandidat sebagai "PERTANYAAN KEDUA"

            Ikuti panduan berikut:
            1. Berikan respons singkat dan relevan terhadap jawaban kandidat.
            2. Ajukan satu pertanyaan pada satu waktu, yang relevan dengan posisi {self.position}.
            3. Pastikan untuk mencakup pertanyaan tentang:
            - Motivasi kandidat
            - Technical skills yang relevan dengan posisi {self.position}
            - Pengalaman proyek yang relevan dengan posisi {self.position}
            - Kemampuan pemecahan masalah
            - Kecocokan budaya kerja
            4. Gunakan konteks dari jawaban sebelumnya untuk membuat pertanyaan yang relevan.
            5. Pertahankan nada profesional sepanjang wawancara.
            6. Setelah 5 pertanyaan, berikan evaluasi yang sejujur-jujurnya mengenai jawaban kandidat, apakah sudah sesuai dengan STAR method, dan apakah kandidat sesuai dengan posisi {self.position}.
            """
        elif self.interview_type == "tech":
            return f"""
            Nama anda adalah Mirai, Anda adalah seorang User pada suatu perusahaan yang sedang melakukan wawancara teknis yang sedang melakukan wawancara untuk posisi {self.position}.

            Sebelumnya, Anda sudah melakukan opening dengan statement sebagai berikut "Terima kasih karena telah mempunyai ketertarikan pada perusahaan kami, Nama saya Mirai dari tim rekrutmen. Terima kasih sudah meluangkan waktu untuk mengikuti sesi wawancara ini. Kami sangat senang bisa mengenal Anda lebih dekat hari ini. Semoga kita bisa melalui sesi ini dengan lancar dan nyaman. Jika ada hal yang ingin ditanyakan selama wawancara, jangan ragu untuk mengatakannya. Mari kita mulai dengan perkenalan diri anda secara kreatif"
            Jadi, tolong lanjutkan sesuai dengan konteks dan hasil dari jawaban kandidat sebagai "PERTANYAAN KEDUA"

            Ajukan 3 pertanyaan teknis terkait posisi ini. Berikut adalah contoh pertanyaan yang bisa Anda ajukan untuk beberapa posisi:
            - Software Engineer: Gimana cara anda melakukan caching, bagaimana cara anda untuk melakukan API versioning.
            - Data Engineer: Bagaimana Anda melakukan data modeling, strategi pipeline data.

            Ikuti panduan berikut:
            1. Berikan respons singkat terhadap jawaban kandidat.
            2. Ajukan pertanyaan yang relevan satu per satu sesuai dengan konteks dari jawaban sebelumnya.
            3. Setelah 3 pertanyaan, lakukan evaluasi kandidat berdasarkan jawaban mereka.

            Pertahankan nada profesional sepanjang wawancara.
            """

    def create_evaluation_prompt(self, conversation_history):
        if self.interview_type == "hr":
            return f"""
                Anda telah melakukan wawancara dengan kandidat untuk posisi {self.position}. Berdasarkan jawaban-jawaban kandidat berikut:

                {conversation_history}

                Berikan penilaian dalam bentuk angka 1-10 untuk masing-masing aspek berikut ini:
                1. Motivasi kandidat
                2. Technical skills yang relevan dengan posisi {self.position}
                3. Pengalaman proyek yang relevan dengan posisi {self.position}
                4. Kemampuan pemecahan masalah
                5. Kecocokan budaya kerja

                Jangan terlalu baik dalam memberikan skor jika memang dia belum kompeten/baru belajar, karena ini untuk pekerja professional. Selain memberikan skor, buatlah evaluasi singkat dalam bentuk teks untuk masing-masing aspek di atas. Evaluasi harus mencakup hal-hal positif serta area yang dapat ditingkatkan, dan berikan saran yang membantu kandidat dalam pengembangan lebih lanjut.

                Format output yang diinginkan:
                {{
                    "motivasi": nilai_1_sampai_10,
                    "technical_skills": nilai_1_sampai_10,
                    "pengalaman_proyek": nilai_1_sampai_10,
                    "pemecahan_masalah": nilai_1_sampai_10,
                    "kecocokan_budaya": nilai_1_sampai_10,
                    "evaluasi_teks": "Evaluasi & saran untuk kandidat ke depan."
                }}
                """
        elif self.interview_type == "tech":
            return f"""
                Anda telah melakukan wawancara teknis dengan kandidat untuk posisi {self.position}. Berdasarkan jawaban-jawaban kandidat berikut:

                {conversation_history}

                Berikan penilaian dalam bentuk angka 1-10 untuk masing-masing aspek berikut ini:
                1. Technical skills yang relevan dengan posisi {self.position}
                2. Pengalaman proyek yang relevan dengan posisi {self.position}
                3. Kemampuan pemecahan masalah

                Jangan terlalu baik dalam memberikan skor jika memang dia belum kompeten/baru belajar, karena ini untuk pekerja professional. Selain memberikan skor, buatlah evaluasi singkat dalam bentuk teks untuk masing-masing aspek di atas. Evaluasi harus mencakup hal-hal positif serta area yang dapat ditingkatkan, dan berikan saran yang membantu kandidat dalam pengembangan lebih lanjut.

                Format output yang diinginkan:
                {{
                    "technical_skills": nilai_1_sampai_10,
                    "pengalaman_proyek": nilai_1_sampai_10,
                    "pemecahan_masalah": nilai_1_sampai_10,
                    "evaluasi_teks": "Evaluasi & saran untuk kandidat ke depan."
                }}
                """

    def get_ai_response(self, user_input, position, interview_type="hr"):
        if self.position != position or self.interview_type != interview_type:
            self.position = position
            self.interview_type = interview_type
            self.conversation_history = []
            self.current_question_index = 0
            self.is_evaluation_done = False

        query_engine = self.index.as_query_engine(llm=Settings.llm)
        system_prompt = self.create_system_prompt()

        full_context = "\n".join(
            self.conversation_history + [f"Kandidat: {user_input}"]
        )

        # Limit untuk HR interview = 5, untuk Technical 3
        question_limit = 5 if self.interview_type == "hr" else 3

        if self.is_evaluation_done:
            return {
                "status": "Evaluasi selesai",
                "skor": self.evaluation_scores,
                "evaluasi_terperinci": self.evaluation_text,
            }

        if not self.conversation_history:
            # Ajukan pertanyaan pertama
            response = query_engine.query(
                f"{system_prompt}\n\nBerikan sambutan singkat dan ajukan pertanyaan pertama yang relevan untuk posisi {self.position}."
            )

        elif self.current_question_index < question_limit:
            # Ajukan pertanyaan berikutnya jika belum mencapai batas pertanyaan
            response = query_engine.query(
                f"{system_prompt}\n\nKonteks percakapan:\n{full_context}\n\nBerikan respons singkat dan ajukan pertanyaan berikutnya yang relevan untuk posisi {self.position}."
            )
        else:
            # Setelah jumlah pertanyaan yang ditentukan, buat prompt evaluasi
            evaluation_prompt = self.create_evaluation_prompt(full_context)
            evaluation_response = query_engine.query(evaluation_prompt)

            try:
                evaluation_data = json.loads(evaluation_response.response)
                if self.interview_type == "hr":
                    self.evaluation_scores = {
                        "motivasi": evaluation_data["motivasi"],
                        "technical_skills": evaluation_data["technical_skills"],
                        "pengalaman_proyek": evaluation_data["pengalaman_proyek"],
                        "pemecahan_masalah": evaluation_data["pemecahan_masalah"],
                        "kecocokan_budaya": evaluation_data["kecocokan_budaya"],
                    }
                else:
                    self.evaluation_scores = {
                        "technical_skills": evaluation_data["technical_skills"],
                        "pengalaman_proyek": evaluation_data["pengalaman_proyek"],
                        "pemecahan_masalah": evaluation_data["pemecahan_masalah"],
                    }
                self.evaluation_text = evaluation_data["evaluasi_teks"]
                self.is_evaluation_done = True

            except json.JSONDecodeError as e:
                print(f"Error parsing evaluation response: {e}")

            return {
                "status": "Evaluasi selesai",
                "skor": self.evaluation_scores,
                "evaluasi_terperinci": self.evaluation_text,
            }

        self.conversation_history.append(f"Kandidat: {user_input}")
        self.conversation_history.append(f"HR: {response.response}")

        self.current_question_index += 1

        return response.response

    def generate_quiz(self, position):
        quiz_prompt = f"""
        Anda adalah seorang profesional di bidang {position} yang sedang merancang 10 pertanyaan quiz teknikal untuk posisi {position}.
        Pertanyaan-pertanyaan ini harus relevan dengan keterampilan teknis yang dibutuhkan untuk posisi ini, mencakup berbagai aspek teknis terkait.

        Format hasil yang diinginkan adalah JSON dengan struktur berikut:

        ```json
        {{
          "quiz": [
            {{
              "question": "Pertanyaan 1",
              "options": ["Opsi A", "Opsi B", "Opsi C", "Opsi D"],
              "answer": "Jawaban yang benar"
            }},
            ...
          ]
        }}
        ```

        Harap buat 10 pertanyaan dengan format yang disebutkan di atas.
        """

        response = self.index.as_query_engine(llm=Settings.llm).query(quiz_prompt)

        try:
            start_index = response.response.find("{")
            end_index = response.response.rfind("}") + 1
            json_str = response.response[start_index:end_index]

            quiz_data = json.loads(json_str)

            return quiz_data

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from AI response: {e}")

        except Exception as e:
            raise ValueError(f"An error occurred while generating the quiz: {e}")


rag_service = RAGService()
