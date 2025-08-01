# 作业批改系统

基于Flask框架的智能作业批改系统，集成图像识别、OCR文字提取、知识库查询和AI批改等功能，实现从图片上传到批改结果展示的全流程自动化处理。

## 系统功能

### 核心功能
- **图片上传**: 支持用户通过拍照或从本地相册上传作业图片
- **题目分割**: 自动识别图片中各题目的位置坐标，进行智能分割
- **OCR识别**: 提取题目的文字内容，支持字符级坐标定位
- **知识库检索**: 在知识库中搜索相似题目和参考答案
- **AI批改**: 使用VL模型进行智能批改，提供详细的批改意见和得分
- **结果展示**: 可视化展示批改结果，支持查看详细批改意见

### 技术特性
- 模块化设计，易于扩展和维护
- 完善的错误处理和重试机制
- 支持多种图片格式
- 字符级OCR坐标定位
- 流式AI批改支持
- 完整的日志记录

## 系统架构

```
作业批改系统/
├── app.py                 # Flask应用主文件
├── config.py              # 配置文件
├── requirements.txt       # 依赖包列表
├── services/              # 服务模块
│   ├── __init__.py
│   ├── image_processor.py    # 图像处理服务
│   ├── ocr_service.py       # OCR识别服务
│   ├── knowledge_service.py # 知识库检索服务
│   └── ai_grading_service.py # AI批改服务
├── uploads/               # 上传文件目录
├── processed/             # 处理后文件目录
└── logs/                  # 日志文件目录
```

## 安装指南

### 环境要求
- Python 3.8+
- Windows/Linux/macOS

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd pigai
```

2. **创建虚拟环境**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**

在项目根目录创建 `.env` 文件，配置以下参数：

```env
# 题目分割API配置
IMAGE_PROCESSING_API_URL=http://1265037983932887.cn-shanghai.pai-eas.aliyuncs.com/api/predict/yolox250701
IMAGE_PROCESSING_API_TOKEN=YjkwZTdlM2EzYTE5ZTgyOGQwMGRlOWI1NzE0ZDk2NjcwNGNlNzI5ZA==

# OCR识别API配置
OCR_API_URL=https://api.textin.com/ai/service/v1/pdf_to_markdown
OCR_APP_ID=2bae9d892b488e1d29f4ca0b650ad7a5
OCR_SECRET_CODE=46d25182d74cb02b9fb8a06734fb73a4

# 知识库检索API配置（Dify平台）
KNOWLEDGE_API_URL=http://agent.raysgo.com/v1/datasets/017f0684-e949-4e6f-a97a-50b7362680ae/retrieve
KNOWLEDGE_API_TOKEN=dataset-U15beb259AqwkwRRONwNaYtr

# AI批改API配置（Dify工作流）
AI_GRADING_API_URL=http://agent.raysgo.com/v1/workflows/run
AI_GRADING_API_TOKEN=your_ai_grading_token

# 应用配置
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
```

5. **创建必要目录**
```bash
mkdir uploads processed logs
```

6. **启动应用**
```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

## API 接口

### 1. 文件上传

**POST** `/api/upload`

上传作业图片文件。

**请求参数:**
- `file`: 图片文件（multipart/form-data）

**响应示例:**
```json
{
    "success": true,
    "message": "文件上传成功",
    "file_path": "/uploads/homework_20231201_123456.jpg"
}
```

### 2. 作业处理

**POST** `/api/process`

处理上传的作业图片，进行题目分割、OCR识别、知识库检索和AI批改。

**请求参数:**
```json
{
    "file_path": "/uploads/homework_20231201_123456.jpg"
}
```

**响应示例:**
```json
{
    "success": true,
    "message": "作业处理完成",
    "processing_time": 15.6,
    "results": [
        {
            "question_id": 1,
            "question_text": "题目OCR内容",
            "question_region": [100, 100, 300, 200],
            "reference_answer": "参考答案",
            "grading_result": {
                "score": 85,
                "max_score": 100,
                "feedback": "批改意见",
                "correct": true,
                "suggestions": ["改进建议1", "改进建议2"]
            }
        }
    ]
}
```

## 配置说明

### API服务配置

系统需要配置以下外部API服务：

1. **题目分割API**: 阿里云EAS服务，用于识别图片中题目位置
2. **OCR识别API**: Textin API，用于文字识别
3. **知识库检索API**: Dify平台，用于题目匹配
4. **AI批改API**: Dify工作流，用于智能批改

### 重要参数

- `MAX_CONTENT_LENGTH`: 最大上传文件大小（默认16MB）
- `REQUEST_TIMEOUT`: API请求超时时间（默认30秒）
- `MAX_RETRIES`: 最大重试次数（默认3次）
- `RETRIEVAL_CONFIG`: 知识库检索配置参数

## 开发部署

### 开发环境
```bash
# 开发模式启动
FLASK_ENV=development python app.py
```

### 生产环境
```bash
# 使用Gunicorn部署
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker部署

创建 `Dockerfile`：
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 注意事项

1. **API配置**: 确保所有外部API的URL和认证信息正确配置
2. **文件权限**: 确保上传和处理目录有适当的读写权限
3. **网络环境**: 某些API可能需要稳定的网络连接
4. **文件格式**: 支持常见图片格式（jpg, png, gif, bmp）
5. **安全考虑**: 生产环境中请更换默认的SECRET_KEY

## 错误排查

### 常见问题

1. **API调用失败**
   - 检查API URL和认证信息
   - 查看网络连接
   - 检查日志文件

2. **图片上传失败**
   - 检查文件大小限制
   - 验证文件格式
   - 确认目录权限

3. **OCR识别失败**
   - 确保图片清晰
   - 检查Textin API配额
   - 验证图片格式

### 日志查看

应用日志保存在 `logs/` 目录下，包含详细的错误信息和处理流程记录。

## 技术支持

如有技术问题，请查看日志文件或联系开发团队。

## 许可证

本项目采用 MIT 许可证。