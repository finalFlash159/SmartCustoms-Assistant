import re

digit_to_word = {
    "0": "KHÔNG", "1": "MỘT", "2": "HAI", "3": "BA", "4": "BỐN",
    "5": "NĂM", "6": "SÁU", "7": "BẢY", "8": "TÁM", "9": "CHÍN"
}

def number_to_words(number_str: str) -> str:
    return " ".join(digit_to_word.get(ch, ch) for ch in number_str if ch.isdigit())

def process_query(text: str) -> str:
    # Tìm các cụm số (có thể chứa dấu chấm), ví dụ: 4802.55.69, 10010099, 1234
    pattern = r'\b(?:\d+\.)*\d+\b'
    matches = re.findall(pattern, text)

    # Loại trùng lặp và giữ nguyên thứ tự
    seen = set()
    unique_matches = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            unique_matches.append(m)

    # Tạo phần diễn giải
    explanations = []
    for m in unique_matches:
        word_form = number_to_words(m)
        explanations.append(f" [{word_form}]")

    if explanations:
        return text.strip() + ",".join(explanations)
    else:
        return text
