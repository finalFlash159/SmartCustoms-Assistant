from pipelines.pdf_pipelines.pdf_processor import image_processor_pipeline

pdf_path = "/Users/vominhthinh/Downloads/08.2020.pdf"
model_path = "/Users/vominhthinh/Workspace/LogiTuning/project230225/backend/app/models/yolov11_tuned.pt"
save_dir = "/Users/vominhthinh/Workspace/LogiTuning/test_pdf"


images = image_processor_pipeline(
    pdf_path=pdf_path,
    model_path=model_path
)

# luu các ảnh đã xử lý vào thư mục save_dir
for i, image in enumerate(images):
    image.save(f"{save_dir}/image_{i}.jpg")
    print(f"Saved image_{i}.jpg")


