import os
import uuid
from fpdf import FPDF
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
# Load environment variables

class PDF(FPDF):
    def header(self):
        self.set_font("DejaVu", style="B", size=14)
        self.cell(0, 10, "SCIENCE", ln=True, align="C")
        self.cell(0, 10, "CLASS IX (THEORY)", ln=True, align="C")
        self.cell(0, 10, "SAMPLE QUESTION PAPER - II", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", size=8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
import re
def text_to_mcq_pdf(text, filename):
    pdf = PDF()

    # Register fonts
    try:
        pdf.add_font("DejaVu", style="", fname="DejaVuSans.ttf", uni=True)  # Regular
        pdf.add_font("DejaVu", style="B", fname="DejaVuSans-Bold.ttf", uni=True)  # Bold
        pdf.add_font("DejaVu", style="I", fname="DejaVuSans-Oblique.ttf", uni=True)  # Italic
        pdf.add_font("DejaVu", style="BI", fname="DejaVuSans-BoldOblique.ttf", uni=True)  # Bold-Italic
    except Exception as font_error:
        print(f"Font registration error: {font_error}")
        raise

    # Helper function to set a header
    def set_header(title):
        pdf.add_page()
        pdf.set_font("DejaVu", style="B", size=14)
        pdf.cell(0, 10, title, ln=True, align="C")
        pdf.ln(10)
    blocks = re.split(r"(Question\s+\d+)", text)  # Retain the "Question X" marker
    blocks = [blocks[i] + blocks[i + 1] for i in range(1, len(blocks), 2)]  # Combine marker with content
    # Split the input into individual questions
    #questions = text.split("\n\n")  # Split by double newline for each question block
    questions_section = []
    answers_section = []
    explanations_section = []
    for block in blocks:
        # Extract question and options
        question_part = re.split(r"(Answer:|Explanation:)",block)[0].strip()
        questions_section.append(question_part)

        # Extract answer
        answer_match = re.search(r"Answer:\s*(.*)", block)
        if answer_match:
            answers_section.append(answer_match.group(1).strip())

        # Extract explanation
        explanation_match = re.search(r"Explanation:\s*(.*)", block, re.DOTALL)
        if explanation_match:
            explanations_section.append(explanation_match.group(1).strip())

    # Add Questions Section
    set_header("Questions")
    pdf.set_font("DejaVu", size=12)
    for q in questions_section:
        pdf.multi_cell(0, 10, q)
        pdf.ln(5)

    # Add Answers Section
    set_header("Answers")
    pdf.set_font("DejaVu", size=12)
    for ans in answers_section:
        pdf.multi_cell(0, 10, ans)
        pdf.ln(5)

    # Add Explanations Section
    set_header("Explanations")
    pdf.set_font("DejaVu", size=12)
    for exp in explanations_section:
        pdf.multi_cell(0, 10, exp)
        pdf.ln(5)

    # Save the PDF
    pdf.output(filename)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me the text of your MCQ question paper, and I'll format it into a styled PDF for you!"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id

    # Generate a unique filename for the PDF
    pdf_filename = f"{uuid.uuid4().hex}_mcq_question_paper.pdf"

    try:
        # Generate the formatted MCQ PDF
        print("Anshhhhh")
        text_to_mcq_pdf(user_text, pdf_filename)
        print("Ansh wadhwa")
        # Send the PDF to the user
        with open(pdf_filename, "rb") as pdf_file:
            await context.bot.send_document(chat_id=chat_id, document=pdf_file)
            print("Pdf send successfully")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")
    finally:
        # Remove the PDF after sending or in case of error
        if os.path.exists(pdf_filename):
            os.remove(pdf_filename)

def main():
    print("Bot is running...")
    # Fetch the bot token from environment variables
    bot_token = "6772673902:AAGg4zzRXMslhqn9CA0O2uFzePJiekuQXww"
    if not bot_token:
        raise ValueError("Bot token not found in environment variables.")

    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == "__main__":
    main()