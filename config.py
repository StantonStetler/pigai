import os
from datetime import timedelta

class Config:
    """应用配置类"""
    
    # 基本配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    DEBUG = True
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    PROCESSED_FOLDER = 'processed'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    
    # API配置
    
    # 接口2: 题目分割API
    SEGMENTATION_API_URL = 'http://1265037983932887.cn-shanghai.pai-eas.aliyuncs.com/api/predict/yolox250701'
    SEGMENTATION_API_TOKEN = 'YjkwZTdlM2EzYTE5ZTgyOGQwMGRlOWI1NzE0ZDk2NjcwNGNlNzI5ZA=='
    
    # 接口3: OCR识别API（注意，试用账号，仅100页额度 https://www.textin.com/console/dashboard/overview）
    OCR_API_URL = 'https://api.textin.com/ai/service/v1/pdf_to_markdown?char_details=1'
    OCR_APP_ID = 'd046af581266d8ba707a63ceb5cf9ed1'
    OCR_SECRET_CODE = 'bc7546609fda4688a48666a2f52e38a0'
    
    # 接口4: 知识库检索API (新搜题接口)
    KNOWLEDGE_API_URL = 'https://agent-aireader.5rs.me/'
    KNOWLEDGE_API_TOKEN = 'dataset-lfzoNPQOMoKh7BUIlVX2y178'
    KNOWLEDGE_DATASET_ID = '3c60b039-3846-44b2-9c27-dbbdcdbc0182'
    KNOWLEDGE_TENANT_ID = '3dbb368a-a30c-49bd-b61e-d272f693e33e'
    
    # 接口5: AI批改API (Dify工作流)
    AI_GRADING_API_URL = 'https://agent.raysgo.com/v1/workflows/run'
    AI_GRADING_API_TOKEN = 'app-NhPGPuygSp7B8eK2WoL8c5Kc'
    
    # 知识库检索配置
    RETRIEVAL_CONFIG = {
        "retrieval_model": {
            "search_method": "hybrid_search",
            "reranking_enable": True,
            "reranking_mode": "reranking_model",
            "reranking_model": {
                "reranking_provider_name": "tongyi",
                "reranking_model_name": "gte-rerank"
            },
            "weights": {
                "weight_type": "customized",
                "vector_setting": {
                    "vector_weight": 0.5,
                    "embedding_provider_name": "",
                    "embedding_model_name": ""
                },
                "keyword_setting": {
                    "keyword_weight": 0.5
                }
            },
            "top_k": 10,
            "score_threshold_enabled": False,
            "score_threshold": 0.1
        }
    }
    
    # 请求超时设置
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 60))
    KNOWLEDGE_TIMEOUT = int(os.getenv('KNOWLEDGE_TIMEOUT', 60))
    KNOWLEDGE_READ_TIMEOUT = int(os.getenv('KNOWLEDGE_READ_TIMEOUT', 45))
    KNOWLEDGE_CONNECT_TIMEOUT = int(os.getenv('KNOWLEDGE_CONNECT_TIMEOUT', 15))

    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # 秒
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'