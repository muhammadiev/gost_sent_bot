import xml.etree.ElementTree as ET
import json
import logging

def convert_questions_to_json(xml_path, json_path):
    questions = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for q_elem in root.findall(".//QuestionBlock"):
            # Extract question text, base64, and picture
            question_text_elem = q_elem.find(".//Content/PlainText")
            question_base64_elem = q_elem.find(".//RichViewFormatBASE64")
            question_picture_elem = q_elem.find(".//Picture")

            # Determine question validity based on any of text, base64, or picture
            if not (question_text_elem is not None or question_base64_elem is not None or question_picture_elem is not None):
                continue  # Skip this question if all are missing

            question_text = question_text_elem.text.strip() if question_text_elem is not None and question_text_elem.text else None
            question_base64 = question_base64_elem.text.strip() if question_base64_elem is not None else None
            question_picture = question_picture_elem.text.strip() if question_picture_elem is not None else None

            # Skip if question text is empty and no base64/picture is present
            if not question_text and not question_base64 and not question_picture:
                continue

            answers = []
            correct_answer = None

            # Process answers
            for answer_elem in q_elem.findall(".//Answers/Answer"):
                answer_text_elem = answer_elem.find(".//Content/PlainText")
                answer_base64_elem = answer_elem.find(".//RichViewFormatBASE64")
                answer_picture_elem = answer_elem.find(".//Picture")

                # Determine answer validity based on any of text, base64, or picture
                if not (answer_text_elem is not None or answer_base64_elem is not None or answer_picture_elem is not None):
                    continue  # Skip this answer if all are missing

                answer_text = answer_text_elem.text.strip() if answer_text_elem is not None and answer_text_elem.text else None
                answer_base64 = answer_base64_elem.text.strip() if answer_base64_elem is not None else None
                answer_picture = answer_picture_elem.text.strip() if answer_picture_elem is not None else None

                # Skip if answer text, base64, and picture are all missing
                if not answer_text and not answer_base64 and not answer_picture:
                    continue

                is_correct = answer_elem.get("IsCorrect") == "Yes"
                if is_correct:
                    correct_answer = {
                        "text": answer_text,
                        "base64": answer_base64,
                        "picture": answer_picture
                    }

                answers.append({
                    "text": answer_text,
                    "base64": answer_base64,
                    "picture": answer_picture
                })

            if question_text or question_base64 or question_picture:
                questions.append({
                    "question": {
                        "text": question_text,
                        "base64": question_base64,
                        "picture": question_picture
                    },
                    "correct": correct_answer,
                    "options": answers
                })

        # Save to JSON
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(questions, json_file, ensure_ascii=False, indent=4)

        logging.info(f"{len(questions)} questions loaded and saved to {json_path}.")
        print(f"✅ Done! {len(questions)} questions saved to {json_path}")

    except Exception as e:
        logging.error(f"Error loading questions: {e}")
        print(f"❌ Error: {e}")

# Example usage
convert_questions_to_json('quiz.xml', 'quiz.json')
