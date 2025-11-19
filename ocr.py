from validate_data import get_single_question_data
import openai
import cv2
from PIL import Image
import easyocr
import os
import requests
from config import BOT_TOKEN, GROUP_CHAT_ID
import datetime
import telebot

class OCRHandler:
    def __init__(self, bot, group_chat_id):
        self.bot = bot
        self.group_chat_id = group_chat_id

        self.reader = easyocr.Reader(['en' ,'hi'])  # Supports English and Hindi languages

    def preprocess_image(self,image_path):
        """
        Enhances image contrast and sharpness to improve OCR accuracy.
        """
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)  # Convert to grayscale
        img = cv2.resize(img, (1080, 1080))  # Resize to standard 1080p resolution
        img = cv2.GaussianBlur(img, (5, 5), 0)  # Reduce noise
        _, img = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # Binarization
        processed_path = "processed_" + image_path
        cv2.imwrite(processed_path, img)  # Save preprocessed image
        return processed_path  # Return new image path

    def extract_text_from_image(self, file_id):
        """
        Downloads an image from Telegram and extracts text using OpenAI's Vision API.
        """
        local_file_path = None
        try:
            # ✅ Step 1: Get the file from Telegram
            file_info = self.bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
            local_file_path = f"temp_image_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"

            # ✅ Step 2: Download the image
            response = requests.get(file_url, stream=True)
            response.raise_for_status()
            with open(local_file_path, "wb") as f:
                f.write(response.content)

            # ✅ Step 3: Send Image to OpenAI Vision API
            processed_image_path = self.preprocess_image(local_file_path)

        # ✅ Step 4: Send Processed Image to OpenAI Vision API
            extracted_text = self.get_text_from_openai(processed_image_path)
            

            if extracted_text:
                print("Extracted Text:", extracted_text)
                return extracted_text
            else:
                raise ValueError("No text detected in the image.")

        except requests.exceptions.RequestException as e:
            error_message = f"Failed to download file: {e}"
            print(error_message)
            self.bot.send_message(self.group_chat_id, error_message)
            return ""

        except Exception as e:
            error_message = f"Error during OCR processing: {str(e)}"
            print(error_message)
            self.bot.send_message(self.group_chat_id, error_message)
            return ""

        finally:
            # ✅ Step 4: Cleanup Temporary File
            if local_file_path and os.path.exists(local_file_path):
                os.remove(local_file_path)

    def get_text_from_openai(self, image_path):
        """
        Uses OpenAI's Vision API (GPT-4 Turbo) to extract text from an image.
        """
        try:
            # ✅ Open the image as binary
            with open(image_path, "rb") as image_file:
                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an AI that extracts text from images accurately."},
                        {"role": "user", "content": [
                            {"type": "text", "text": (
                            "Extract the text **exactly as written and do not guess unnecessaryily** in the image while maintaining formatting, language, and structure."
                            "Extract all the proper questions from the given image."
                            "Exclude explanations, answers, or any incomplete or meaningless data."
                            "Maintain the order and structure as it appears in the image."
                            "If a question is present in both Hindi and English, prioritize Hindi and ignore the English version."
                            "If a question is only in English, extract and return it as it is."
                           "Extract the COMPLETE question with ALL its components:"
                            "\n1. MAIN STRUCTURE:"
                            "\n   - Main question title/heading"
                            "\n   - ALL numbered points that follow (1., 2., 3., etc.)"
                            "\n   - The final query line (इनमें से कौन सा/से कथन सही है/हैं?)"
                            "\n   - All options with their markers"
                            "\n2. INTEGRITY RULES:"
                            "\n   - Never separate the main question from its numbered points"
                            "\n   - Keep all numbered points as part of the main question"
                            "\n   - Treat numbered points as essential part of question context"
                            "\n   - Include ALL text between question and options"
                            "\n3. FORMATTING:"
                            "\n   - Keep all line breaks exactly as shown"
                            "\n   - Preserve indentation and spacing"
                            "\n   - Maintain any English text in brackets"
                            "\n4. OUTPUT FORMAT:"
                            '   {"Question": "<main_question>\\n\\n1. <point1>\\n2. <point2>\\n3. <point3>\\n\\n<query_line>",'
                            '    "Options": ['
                            '      "(a) <option_a>",'
                            '      "(b) <option_b>",'
                            '      "(c) <option_c>",'
                            '      "(d) <option_d>"'
                            '    ]}'
                            "\n5. CRITICAL:"
                            "\n   - MUST extract numbered points (1., 2., 3.) as part of question"
                            "\n   - MUST include context between question and options"
                            "\n   - MUST preserve all line breaks"
                        "\n\n### **Extraction Rules**:"
                        "\n **Maintain the original language (including Hindi text).**"
                        "\n **Preserve MCQ structure:**"
                        "\n   - Extract **each question separately**."
                        "\n   - Ensure **all four answer choices are present**."
                        "\n   - If an answer choice is missing, leave it as an empty string (`\"\"`)."
                        "\n **Do not extract answers or explanations. Only extract questions and options.**"
                        "\n\n### **Expected Output Format (JSON):**"
                        "\n```json"
                        "\n["
                        "\n  {"
                        "\n    \"Question\": \"Original question text exactly as seen in the image.\","
                        "\n    \"Options\": ["
                        "\n      \"a) Option 1 text exactly as in the image.\","
                        "\n      \"b) Option 2 text exactly as in the image.\","
                        "\n      \"c) Option 3 text exactly as in the image.\","
                        "\n      \"d) Option 4 text exactly as in the image.\""
                        "\n    ],"
                        "\n  }"
                        "\n]"
                        "\n```"
                    )},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.encode_image(image_path)}"}}
                        ]}
                    ],
                    max_tokens=2000
                )

            # ✅ Extract text from the response
            extracted_text = response["choices"][0]["message"]["content"]
            return extracted_text

        except Exception as e:
            print(f"OpenAI Vision API Error: {e}")
            return None

    def encode_image(self, image_path):
        """
        Encodes an image file as a Base64 string.
        """
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
   
    def process_text_with_openai(self, extracted_text):
        """
        Processes extracted text with OpenAI to structure it as questions, options, answers, and explanations.
        """
        return get_single_question_data(extracted_text)
            
    def accumulate_questions(self, extracted_text,question_data):
        """
        Accumulates structured questions into the main question_data dictionary.
        """
        try:
            questions_data = self.process_text_with_openai(extracted_text)
            question_data["Question"].extend(questions_data["Question"])
            question_data["Options"].extend(questions_data["Options"])
        except Exception as e:
              print(f"Error in accumulating questions: {e}")
              self.bot.send_message(self.group_chat_id, f"Error processing extracted data: {e}")