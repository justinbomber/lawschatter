from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
from dotenv import load_dotenv

from ..modules.config import Config
from ..modules.database import DatabaseConnection
from ..modules.queue_manager import get_global_queue

load_dotenv()

app = FastAPI(title="Judgment RAR Upload API")

config = Config.from_env()
config.validate()
logger = config.setup_logging()


@app.post("/upload-rar")
async def upload_rar(file: UploadFile = File(...)):
    if not file.filename.endswith('.rar'):
        raise HTTPException(status_code=400, detail="Only RAR files are allowed")

    # 儲存上傳的檔案到臨時位置
    with tempfile.NamedTemporaryFile(delete=False, suffix='.rar') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    logger.info(f"RAR file uploaded: {file.filename}, saved to: {temp_file_path}")

    # 使用新的排隊系統處理檔案
    queue_manager = get_global_queue()
    success = queue_manager.add_file_to_queue(temp_file_path, "rar")
    
    if success:
        logger.info(f"RAR file added to processing queue: {temp_file_path}")
        
        # 立即回應前端
        return JSONResponse(
            status_code=200,
            content={
                "message": "RAR file uploaded successfully, added to processing queue",
                "filename": file.filename,
                "status": "queued"
            }
        )
    else:
        # 如果加入佇列失敗，刪除臨時檔案
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        raise HTTPException(
            status_code=500, 
            detail="Failed to add file to processing queue"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/queue-status")
async def get_queue_status():
    """獲取處理佇列狀態"""
    queue_manager = get_global_queue()
    status = queue_manager.get_queue_status()
    
    return JSONResponse(
        status_code=200,
        content={
            "queue_size": status["queue_size"],
            "is_processing": status["is_processing"],
            "worker_alive": status["worker_alive"],
            "message": "Queue status retrieved successfully"
        }
    )


@app.post("/process-extracted")
async def process_extracted_directories():
    """手動觸發處理現有的extracted目錄"""
    try:
        queue_manager = get_global_queue()
        queue_manager.process_existing_extracted_dirs()
        
        logger.info("Manual trigger: processing existing extracted directories")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Started processing existing extracted directories",
                "status": "triggered"
            }
        )
    except Exception as e:
        logger.error(f"Failed to trigger extracted directory processing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger processing: {str(e)}"
        )