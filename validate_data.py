import re
import openai
import json
from config import GROUP_CHAT_ID,openai
import re
def clean_json_response(formatted_data):
    """
    Cleans and extracts valid JSON array content from the response.
    """
    formatted_data = formatted_data.strip("`").strip()

    # Use regex to extract JSON content
    json_match = re.search(r'(\[\s*\{[\s\S]*?\}\s*\])', formatted_data, re.UNICODE)

    if json_match:
        json_content = json_match.group(1).strip()
        try:
            return json.loads(json_content)  # ✅ Properly parse JSON into Python object
        except json.JSONDecodeError as e:
            print(f"JSON Parsing Error: {e}")
            return None
    else:
        print("No valid JSON detected in response.")
        return None
    
def get_single_question_data(extracted_text, max_retries=3, max_tokens=500):
    """
    Queries OpenAI to retrieve structured questions, options, answers, and explanations from extracted text.

    Args:
        extracted_text (str): The text extracted from an image.
        max_retries (int): Maximum number of retries for API calls.
        max_tokens (int): Maximum number of tokens to be returned in the API response.

    Returns:
        dict: Structured data with keys "Question", "Options".
    """
    all_data = {
        "Question": [],
        "Options": [],

    }
    offset = 0

    while offset < len(extracted_text):
        prompt = (
            "Extract all text **exactly as it appears** in the image. Do NOT modify, summarize, or create new text. Maintain original line breaks and formatting." 

            "If the text contains multiple-choice questions (MCQs), structure them in **this exact JSON format**:"
            "Extract all the proper questions from the following OCR text, starting from the specified offset position. "
            "Return only the extracted questions and their details in a JSON array. Strictly adhere to the exact format specified below, "
            "and do not include any additional text, notes, interpretations, or unrelated content. Only output structured JSON in this format:\n\n"
            "Structure the following Hindi questions into JSON format while maintaining exact formatting:"
        "\n\nRULES:"
        "\n1. HANDLE BOTH QUESTION TYPES:"
        "\n   Simple Questions Example:"
        '   {"Question": "SRY जीन कहाँ पाया जा सकता है?","Options": ["(a) केवल पुरुषों में।","(b) केवल महिलाओं में।"]}'
        "\n   Complex Questions Example:"
        '   {"Question": "पेरिस में भारत द्वारा सह-अध्यक्षता किए गए एआई एक्शन समिट 2025 का उद्देश्य है:\\n1. केवल एआई सुरक्षा पर ध्यान केंद्रित करना।\\n2. एआई शासन..."}'
        "\n2. FORMATTING RULES:"
        "\n   - Remove initial question numbers (12., 13., etc.)"
        "\n   - Keep all line breaks using \\n"
        "\n   - Preserve both Hindi and English scientific terms"
        "\n   - Maintain exact option formatting with bullets/dots"
        "\n   - Keep all brackets and parentheses"
        "\n3. STRICT JSON STRUCTURE:"
        "["
        "  {"
        '    "Question": "Question text here",'
        '    "Options": ['
        '      "(a) Option text",'
        '      "(b) Option text",'
        '      "(c) Option text",'
        '      "(d) Option text"'
        "    ]"
        "  }"
        "]"
        "\n\nPROCESS THIS TEXT:"
            "[\n"
            "  {\n"
            "    \"Question\": \"Complete question text here as it appears in the OCR content.\",\n"
            "    \"Options\": [\"Option A text\", \"Option B text\", \"Option C text\", \"Option D text\"],\n"
            "  },\n"
            "  {\n"
            "    \"Question\": \"Next complete question text here as it appears in the OCR content.\",\n"
            "    \"Options\": [\" text\", \" text\", \" text\", \" text\"],\n"
            "  }\n"
            "]\n\n"
            "Make sure each question includes:\n"
            "- The full question text under the \"Question\" key.\n"
            "- Exactly four options under the \"Options\" key, listed in order as they appear, each option enclosed in quotation marks and separated by commas.\n"
            f"Here is the text starting from position {offset}:\n\n{extracted_text[offset:]}"
        )

        attempts = 0
        while attempts < max_retries:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that strictly returns JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens
                )

                formatted_data = response.choices[0].message['content']
                print(formatted_data)
                cleaned_data = clean_json_response(formatted_data)
                if not cleaned_data:
                    print("No valid JSON detected in response.")
                    continue

                if isinstance(cleaned_data, str):
                    single_question_data = json.loads(cleaned_data)
                else:
                    single_question_data = cleaned_data  # Already parsed

                #single_question_data = json.loads(cleaned_data)

                # Append question data to all_data
                for question_data in single_question_data:
                    all_data["Question"].append(question_data["Question"])
                    all_data["Options"].append(question_data["Options"])


                # Update offset based on processed text length
                offset += len(formatted_data)
                break

            except (json.JSONDecodeError, Exception) as e:
                print(f"Error at offset {offset}, attempt {attempts + 1}: {e}")
                attempts += 1

        if attempts == max_retries:
            print(f"Failed after {max_retries} attempts at offset {offset}. Exiting.")
            break

    return all_data