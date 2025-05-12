# app.py
import os
import logging
import asyncio
from dotenv import load_dotenv
from llms.coordinator import Coordinator

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load biến môi trường
load_dotenv()

async def main_async():
    # Cấu hình tìm kiếm
    search_config = {
        "fuzzy_search": {
            "maxEdits": 2,
            "prefixLength": 3,
            "maxExpansions": 20,
            "score_threshold": 0.5,
            "pre_filter_threshold": 0.1
        },
        "result_limit": 10
    }
    
    # Khởi tạo agent
    coordinator = Coordinator(
        model_name="gpt-4-0613",
        temperature=0,
        mongodb_uri=os.environ.get("MONGODB_URI"),
        database_name=os.environ.get("MONGODB_DATABASE"),
        collection_name=os.environ.get("MONGODB_COLLECTION"),
        config=search_config
    )
    
    try:
        print("AI Assistant sẵn sàng! Gõ 'exit' để thoát.")
        while True:
            user_query = input("\nCâu hỏi của bạn: ")
            if user_query.lower() in ["exit", "quit", "thoát"]:
                break
                
            # Xử lý câu truy vấn bất đồng bộ
            response = await coordinator.decide_mongodb_usage(user_query)
            print("\nPhản hồi:")
            print(response)

            if response == "YES":
                response = await coordinator.search_mongodb(user_query)
                print("\nKết quả:")
                print(response)
            
    finally:
        # Đóng kết nối khi kết thúc
        coordinator.close()
        print("Đã đóng kết nối và thoát.")

def main():
    # Chạy hàm bất đồng bộ trong vòng lặp sự kiện
    asyncio.run(main_async())

if __name__ == "__main__":
    main()