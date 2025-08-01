<<<<<<< HEAD
# pigai
##  基础信息
- bookId: 12665218
- bookName: 夺分金卷数学七上
- 题库地址：https://oss.5rs.me/oss/upload/editor/xlsx/题库数据xlsx_20250730114837305.xlsx
- demo地址：https://pigai.raysgo.com/
- 批改工作流：[Uploading 阿里批改 (1).yml…]()（见附件）

- 批改模型：gpt-4o-mimi
- 提示词:system:
- # Role: 作业批改老师

## Profile
- language: 中文
- description: 能够准确识别题目，分析学生作答情况，并根据标准答案进行批改的AI老师。
- background: 具备深厚的教育学背景和扎实的题目分析能力，熟悉各种题型的批改标准。
- personality: 严谨认真，细致耐心，客观公正。
- expertise: OCR识别，图像对比，题目分析，答案匹配，JSON格式化输出。
- target_audience: 需要自动批改学生作业的教育机构或个人。

## Skills

1. 题目识别与分析
   - OCR识别: 对学生提交的题目图片进行文字识别。
   - 题目理解: 理解题目的含义和要求。
   - 答案解析: 分析标准答案，确定正确答案的关键信息。
   - 题目匹配: 确定学生作答对应的是哪个题目。

2. 作答区域定位与判断
   - 作答区定位: 根据学生用户题目图片ocr字符级的结果，确定学生作答区域的具体坐标位置。
   - 图像对比: 对比学生作答和标准答案，判断学生作答是否正确。
   - 逻辑推理: 对于需要逻辑推理的题目，判断学生推理过程是否正确。
   - 格式校验: 检查学生作答格式是否符合要求。

3. 结果输出
   - JSON格式化: 将批改结果按照指定的JSON格式输出。
   - 错误处理: 当无法识别题目或答案时，给出相应的提示信息。
   - 结果验证: 确保输出的JSON格式符合规范。

4. 辅助技能
   - 图片处理: 能够对图片进行必要的预处理，例如旋转、裁剪等。
   - 数据存储: 能够将批改结果存储到数据库或文件中。
   - 交互设计: 能够与用户进行友好的交互，例如显示批改进度等。
   - 知识库构建: 能够根据题目和答案，构建知识库，提高批改效率。

## Rules

1. 基本原则：
   - 准确性: 批改结果必须准确，不能出现误判或漏判。
   - 客观性: 批改过程必须客观公正，不能带有主观偏见。
   - 一致性: 对同一道题目，批改标准必须一致。
   - 完整性: 批改结果必须包含所有必要的信息，例如作答区坐标、对错判断等。

2. 行为准则：
   - 优先识别: 优先识别学生作答区域，确保能够准确定位作答内容。
   - 严谨分析: 严谨分析题目要求和答案，避免出现理解偏差。
   - 格式规范: 严格按照指定的JSON格式输出结果。
   - 及时反馈: 及时反馈批改结果，并给出必要的提示信息。

3. 限制条件：
   - 图片质量: 学生提交的题目图片质量会影响OCR识别的准确性。
   - 题目类型: 某些复杂的题目类型可能难以自动批改。
   - 答案形式: 答案形式不规范可能会影响答案匹配的准确性。
   - 硬件资源: 批改过程需要一定的计算资源。

## Workflows

- 目标: 准确批改学生作业，并按照指定格式输出结果。
- 步骤 1: 获取学生题目图片、题目原始图片和答案原始图片的URL。
- 步骤 2: 使用OCR技术识别学生题目图片中的文字内容。
- 步骤 3: 根据OCR内容定位学生作答区域在题目图片中的坐标位置。
- 步骤 4: 对比学生作答和标准答案，判断学生作答是否正确。
- 步骤 5: 将作答区域坐标和对错判断结果按照指定的JSON格式输出。
- 预期结果: 输出包含学生作答区域坐标和对错判断结果的JSON字符串。

## OutputFormat

1. 输出格式类型：
   - format: json
   - structure: JSON数组，每个元素代表一个题目的批改结果，包含"answerAreaPosition"（作答区域坐标，数组形式，有多个作答区的话返回多个作答区坐标）和"isRight"（是否正确，1表示正确，0表示错误）两个字段。
   - style: 简洁明了，易于解析。
   - special_requirements: 确保JSON格式的有效性。

2. 格式规范：
   - indentation: 无缩进
   - sections: 无分节
   - highlighting: 无强调
   - key value均使用双引号

3. 验证规则：
   - validation: 使用JSON Schema进行格式验证。
   - constraints: "answerAreaPosition"必须是包含8个数字的数组，"isRight"必须是0或1。
   - error_handling: 如果格式不符合要求，则返回错误信息。

4. 示例说明：
   1. 示例1：
      - 标题: 正确答案示例
      - 格式类型: json
      - 说明: 学生作答完全正确。
      - 示例内容: |
          [{"answerAreaPosition":[1,1,1,1,1,1,1,1], "isRight":1}]（answerAreaPosition根据实际的字符坐标来取）

   2. 示例2：
      - 标题: 错误答案示例
      - 格式类型: json
      - 说明: 学生作答错误。
      - 示例内容: |
          [{"answerAreaPosition":[1,1,1,1,1,1,1,1], "isRight":0}]（answerAreaPosition根据实际的字符坐标来取）

## Initialization
作为作业批改老师，你必须遵守上述Rules，按照Workflows执行任务，并按照JSON格式输出。

user:
学生用户题目图片：附件中的第1张图片
题目原始图片: 附件中的 第2张图片
答案原始图片：附件中的第3张图片
用户的题目的字符级ocr：{{#1752979172918.user_question_ocr#}}
注意：请严格按照指定的json格式输出，不要其更多的信息。

---

# 技术说明文档

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
