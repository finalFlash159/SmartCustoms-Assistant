# Các mẫu gợi ý cho kết quả tìm kiếm
# Sẽ được chọn ngẫu nhiên để hiển thị cho người dùng

# Danh sách các mẫu gợi ý về trường tìm kiếm
SUGGESTION_TEMPLATES = [
    "\n\nBạn có thể nhập thêm {fields} để có kết quả chính xác hơn 😉",
    "\n\nThử thêm {fields} để lọc kết quả tốt hơn nhé! 🔍",
    "\n\nĐể thu hẹp kết quả, bạn có thể bổ sung {fields} 👌",
    "\n\nMẹo tìm kiếm: Thêm {fields} sẽ giúp kết quả cụ thể hơn 💡",
    "\n\nHãy thử bổ sung {fields} để tìm kiếm hiệu quả hơn 🚀",
    "\n\nĐể tìm nhanh hơn, hãy thử kết hợp với {fields} 🎯",
    "\n\nGợi ý nhỏ: Bổ sung {fields} sẽ giúp lọc kết quả tốt hơn 💪",
    "\n\nTìm chưa chính xác? Thử thêm {fields} xem sao! ✨",
    "\n\nMuốn kết quả cụ thể hơn? Hãy bổ sung {fields} 📝",
    "\n\nThông tin còn thiếu? Bạn có thể thêm {fields} để hoàn thiện 🧩",
    "\n\nHãy làm phong phú tìm kiếm bằng cách thêm {fields} 🌈",
    "\n\nỨng dụng có thể tìm chính xác hơn nếu bạn nhập thêm {fields} 🔮",
    "\n\nCần tìm nhanh hơn? Thử thêm {fields} vào câu hỏi 🚀",
    "\n\nCụ thể hóa yêu cầu bằng cách thêm {fields} nhé 📊",
    "\n\nBí quyết tìm kiếm: Kết hợp tìm kiếm với {fields} 🔑",
    "\n\nNè bạn ơi, thử nhập thêm {fields} để tìm chính xác hơn nha! 🌟",
    "\n\nTrải nghiệm sẽ tốt hơn nếu bạn thêm {fields} đó! 🎁",
    "\n\nMình gợi ý bạn thử thêm {fields} xem sao! 😄",
    "\n\nBạn ơi, {fields} sẽ giúp tìm kiếm hiệu quả hơn đấy! 👍",
    "\n\nTìm kiếm sẽ chuẩn xác hơn nếu bạn thêm {fields} đó nha 💞",
    "\n\nBiết một bí kíp nhỏ không? Thêm {fields} vào tìm kiếm! 🤫",
    "\n\nMách nhỏ bạn nè: Thử nhập thêm {fields} nhé! 🌷",
    "\n\nCùng làm tìm kiếm hiệu quả hơn bằng cách thêm {fields} nhé bạn! 🥰",
    "\n\nBạn ơi, thêm {fields} sẽ giúp mình hỗ trợ bạn tốt hơn đó! 💯",
    "\n\nĐiều kỳ diệu sẽ xảy ra khi bạn thêm {fields} vào tìm kiếm! ✨"
]

# Danh sách các câu hỗ trợ thân thiện
SUPPORT_TEMPLATES = [
    "\nMình luôn sẵn sàng giúp bạn tìm thông tin chi tiết hơn! 💼✨",
    "\nCần tư vấn thêm về tìm kiếm, cứ hỏi mình nhé! 🤗",
    "\nMình ở đây để hỗ trợ bạn tìm chính xác thông tin cần thiết! 📊",
    "\nCần giúp đỡ gì thêm, đừng ngại nhắn mình nhé! 🌟",
    "\nMình sẽ giúp bạn tìm đúng thông tin cần thiết! 🔎✅",
    "\nHãy cho mình biết nếu bạn cần tìm thêm thông tin gì nhé! 💫",
    "\nMình rất vui được hỗ trợ bạn tìm kiếm thông tin! 😊",
    "\nBạn cứ thoải mái hỏi thêm nếu cần giúp đỡ nhé! 👋",
    "\nMình luôn ở đây để giúp bạn tìm kiếm hiệu quả hơn! 🌞",
    "\nNếu còn băn khoăn điều gì, cứ chia sẻ với mình nhé! 💭",
    "\nMình sẽ cố gắng hỗ trợ bạn tốt nhất có thể! 💯",
    "\nHãy cho mình biết nếu bạn muốn tìm hiểu thêm thông tin! 📚",
    "\nĐừng ngần ngại hỏi mình bất cứ lúc nào bạn cần nhé! 🤝",
    "\nMình rất hào hứng được hỗ trợ bạn tìm kiếm thông tin đầy đủ! 🎊",
    "\nCùng khám phá thêm thông tin nếu bạn quan tâm nhé! 🌠",
    "\nMình luôn bên cạnh bạn, cứ hỏi mình bất cứ điều gì nhé! 🌸",
    "\nBạn thân mến, mình sẵn sàng giúp bạn tìm hiểu thêm! 💕",
    "\nHey bạn ơi, có gì cần hỏi thêm cứ nhắn mình nha! 😘",
    "\nCứ thoải mái nhắn tin cho mình khi bạn cần giúp đỡ nhé! 🙌",
    "\nMình yêu thích được hỗ trợ bạn, đừng ngại hỏi nhé! 💖",
    "\nTrò chuyện với mình bất cứ lúc nào bạn cần tư vấn nhé! 🌹",
    "\nNhắn cho mình khi bạn muốn tìm hiểu thêm, mình luôn đây! 🏆",
    "\nMình sẽ là người bạn đồng hành cùng bạn trong hành trình tìm kiếm! 👯‍♀️",
    "\nBạn ơi, mình rất vui khi được giúp đỡ bạn thêm đó! 🥳",
    "\nCứ tâm sự với mình mọi thắc mắc của bạn nhé, mình lắng nghe! 👂"
]

# Danh sách các mẫu fallback khi không tìm thấy thông tin
FALLBACK_TEMPLATES = [
    "Rất tiếc, mình không tìm thấy thông tin bạn cần. Hãy thử từ khóa khác nhé! 🔄",
    "Mình chưa tìm được thông tin phù hợp với yêu cầu của bạn. Bạn có thể thử lại với từ khóa cụ thể hơn không? 🧐",
    "Hmm, dường như thông tin bạn tìm chưa có trong dữ liệu của mình. Bạn có thể diễn đạt lại không? 🤔",
    "Mình xin lỗi, hiện tại chưa tìm thấy kết quả nào phù hợp. Bạn có thể thử lại sau nhé! ⏱️",
    "Không tìm thấy kết quả nào cho yêu cầu này. Hãy thử cách diễn đạt khác hoặc từ khóa cụ thể hơn nhé! 🔍",
    "Rất tiếc, mình chưa tìm được thông tin bạn đang tìm kiếm. Có lẽ dữ liệu này chưa được cập nhật! 📊",
    "Mình không thấy thông tin này trong dữ liệu hiện có. Bạn có thể thử lại với cách diễn đạt khác không? 💬",
    "Ôi, mình tìm mãi mà không thấy thông tin này. Bạn thử dùng từ khóa khác xem sao nhé! 🌈",
    "Mình đã tìm hết cách nhưng chưa thấy thông tin này. Bạn có thể cung cấp thêm chi tiết được không? 🙏",
    "Thông tin này có vẻ chưa có trong hệ thống. Bạn có thể kiểm tra lại hoặc thử với từ khóa khác! 📝",
    "Thật đáng tiếc! Mình không tìm thấy thông tin về yêu cầu này. Hãy thử lại nhé bạn ơi! 😅",
    "Mình đã cố gắng tìm kiếm nhưng chưa có kết quả phù hợp. Có lẽ bạn nên thử cách khác! 🌟",
    "Hmm, mình chưa tìm được gì phù hợp với yêu cầu của bạn. Hay là thử lại với từ khóa cụ thể hơn? 🔎",
    "Thông tin này có vẻ nằm ngoài dữ liệu hiện có của mình. Bạn có muốn tìm thông tin khác không? 📚",
    "Dữ liệu của mình hiện chưa có thông tin này. Bạn có thể thử lại sau hoặc tìm kiếm với từ khóa khác! ⏳",
    "Bạn ơi, mình không tìm thấy kết quả nào. Thử kiểm tra lại chính tả hoặc đổi cách viết xem sao nhé! 🔤",
    "Mình chưa tìm thấy thông tin này. Bạn đã nhập đúng tên/mã/số liệu chưa? Kiểm tra lại nhé! 🧮",
    "Úi, không có kết quả nào cho tìm kiếm này. Bạn kiểm tra lại thứ tự các từ hoặc định dạng nhập vào nhé! 📋",
    "Mình không tìm thấy gì cả. Bạn hãy kiểm tra xem có gõ sai chính tả hoặc sai định dạng không nhé! ✏️",
    "Hmm, tìm không thấy gì. Bạn đã nhập đúng thông tin chưa? Thử viết lại theo cách khác xem sao! 🤗",
    "Bạn yêu ơi, mình không tìm được kết quả nào. Hãy kiểm tra lại cách viết các từ khóa nhé! ❤️",
    "Mình chưa tìm được thông tin này. Có thể bạn đã nhập sai định dạng hoặc gõ sai tên/mã số rồi đó! 📌",
    "Ôi không, mình tìm hoài mà không thấy. Bạn thử kiểm tra lại cách viết hoặc đổi từ khóa nhé! 🔍",
    "Xin lỗi bạn nhé, mình không tìm thấy kết quả. Bạn đã nhập đúng các thông tin như ngày tháng, tên, mã số chưa? 📅",
    "Chà, mình không tìm thấy gì cả. Bạn kiểm tra lại xem có gõ thiếu hoặc thừa ký tự nào không nhé! 🔢",
    "Mình rất muốn giúp bạn nhưng không tìm thấy kết quả nào. Thử kiểm tra lại cách viết hoa/viết thường hoặc dấu cách nhé! 🖋️",
    "Không tìm thấy kết quả nào rồi bạn ơi! Bạn có chắc là đã nhập đúng tên/mã/số liệu không? Kiểm tra lại nha! 📊",
    "Bạn ơi, mình không tìm thấy thông tin. Thử viết đầy đủ hơn hoặc kiểm tra lại định dạng nhập vào xem sao! 📝",
    "Hmm, tìm không ra rồi. Bạn kiểm tra lại thông tin đã nhập xem có chính xác không, hoặc thử cách viết khác nhé! 🧩",
    "Rất tiếc, mình không tìm được kết quả nào. Bạn kiểm tra lại xem có gõ sai tên hoặc nhầm năm/tháng không nhé! 📆"
]

def get_suggestion_templates():
    """
    Trả về danh sách các mẫu gợi ý
    """
    return SUGGESTION_TEMPLATES

def get_support_templates():
    """
    Trả về danh sách các câu hỗ trợ
    """
    return SUPPORT_TEMPLATES

def get_fallback_templates():
    """
    Trả về danh sách các mẫu fallback khi không tìm thấy thông tin
    """
    return FALLBACK_TEMPLATES