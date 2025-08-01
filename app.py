from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.utils import secure_filename
from services.image_processor import ImageProcessor
from services.ocr_service import OCRService
from services.knowledge_service import KnowledgeService
from services.ai_grading_service import AIGradingService
from config import Config
import logging
from logging.handlers import RotatingFileHandler

# 创建logger对象
logger = logging.getLogger(__name__)
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler()
    ]
)



app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# 初始化服务
image_processor = ImageProcessor()
ocr_service = OCRService()
knowledge_service = KnowledgeService()
ai_grading_service = AIGradingService()

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# 前端页面路由
@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """图片上传接口"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            logger.info(f"文件上传成功: {filename}")
            return jsonify({
                'success': True,
                'filename': filename,
                'message': '文件上传成功'
            })
        else:
            return jsonify({'error': '不支持的文件格式'}), 400
            
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/api/process', methods=['POST'])
def process_homework():
    """处理作业批改"""
    import time
    start_time = time.time()
    
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        logger.info(f"开始处理作业批改请求，文件名: {filename}")
        
        if not filename:
            logger.error("缺少文件名参数")
            return jsonify({'error': '缺少文件名参数'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.info(f"文件完整路径: {filepath}")
        
        if not os.path.exists(filepath):
            logger.error(f"文件不存在: {filepath}")
            return jsonify({'error': '文件不存在'}), 404
        
        file_size = os.path.getsize(filepath)
        logger.info(f"文件大小: {file_size} 字节")
        
        # 步骤1: 题目分割
        step1_start = time.time()
        logger.info("=== 步骤1: 开始题目分割 ===")
        segmentation_result = image_processor.segment_questions(filepath)
        step1_time = time.time() - step1_start
        
        if not segmentation_result['success']:
            logger.error(f"题目分割失败: {segmentation_result['error']}")
            return jsonify({'error': f'题目分割失败: {segmentation_result["error"]}'}), 500
        
        logger.info(f"题目分割完成，用时: {step1_time:.2f}秒，检测到{len(segmentation_result.get('coordinates', []))}个题目")
        
        # 步骤2: OCR识别
        step2_start = time.time()
        logger.info("=== 步骤2: 开始OCR识别 ===")
        ocr_result = ocr_service.extract_text(filepath)
        step2_time = time.time() - step2_start
        
        if not ocr_result['success']:
            logger.error(f"OCR识别失败: {ocr_result['error']}")
            return jsonify({'error': f'OCR识别失败: {ocr_result["error"]}'}), 500
        
        text_length = len(ocr_result.get('text_content', ''))
        logger.info(f"OCR识别完成，用时: {step2_time:.2f}秒，识别文本长度: {text_length}")
        
        # 获取字符级坐标信息用于批改
        text_items = ocr_service.get_text_with_coordinates(ocr_result)
        char_details = ocr_service.get_character_coordinates(text_items)
        logger.info(f"提取字符级坐标信息: {len(text_items)}个文本块，{len(char_details)}个字符")
        
        # 步骤3: 题目分割与处理
        step3_start = time.time()
        logger.info("=== 步骤3: 开始题目分割与处理 ===")
        questions = image_processor.split_questions(filepath, segmentation_result['coordinates'], ocr_result, char_details)
        step3_time = time.time() - step3_start
        
        logger.info(f"题目分割处理完成，用时: {step3_time:.2f}秒，处理了{len(questions)}个题目")
        
        # 步骤4: 原题检索和批改
        step4_start = time.time()
        logger.info("=== 步骤4: 开始原题检索和AI批改（并发模式）===")
        results = [None] * len(questions)  # 预分配结果数组
        successful_grading = 0
        
        def process_question(i, question):
            """处理单个题目的函数"""
            question_start = time.time()
            logger.info(f"--- 并发处理第{i+1}题，文本: {question['text'][:50]}... ---")
            
            # 知识库检索（传递图片路径）
            search_start = time.time()
            search_result = knowledge_service.search_similar_question(
                question['text'], 
                question['image_path']
            )
            search_time = time.time() - search_start
            
            logger.info(f"第{i+1}题知识库检索完成，用时: {search_time:.2f}秒，相似度: {search_result.get('similarity_score', 0)}")
            
            # AI批改
            grading_start = time.time()
            grading_result = ai_grading_service.grade_question(
                question['image_path'],
                question['text'],
                search_result,  # 传递整个知识库检索结果
                question.get('char_details', [])  # 传递字符级坐标信息
            )
            grading_time = time.time() - grading_start
            
            success = grading_result.get('success', False)
            if success:
                logger.info(f"第{i+1}题AI批改完成，用时: {grading_time:.2f}秒，得分: {grading_result.get('score', '未知')}")
            else:
                logger.error(f"第{i+1}题AI批改失败: {grading_result.get('error', '未知错误')}")
            
            question_time = time.time() - question_start
            logger.info(f"第{i+1}题总处理时间: {question_time:.2f}秒")
            
            return i, {
                'question_id': i + 1,
                'coordinates': question['coordinates'],
                'text': question['text'],
                'reference_answer': search_result.get('reference_answer', ''),
                'similarity_score': search_result.get('similarity_score', 0),
                'grading_result': grading_result,
                'image_path': question['image_path']
            }, success
        
        # 检查是否有题目需要处理
        if not questions:
            logger.warning("没有检测到任何题目，跳过批改步骤")
            return []
        
        # 使用线程池并发处理所有题目
        max_workers = min(len(questions), 20)  # 最多20个并发线程，适应一页最多20道题目的处理需求
        logger.info(f"启动{max_workers}个并发线程处理{len(questions)}道题目")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_question = {executor.submit(process_question, i, question): i 
                                for i, question in enumerate(questions)}
            
            # 收集结果
            for future in as_completed(future_to_question):
                try:
                    i, result, success = future.result()
                    results[i] = result  # 按原序号放置结果
                    if success:
                        successful_grading += 1
                except Exception as exc:
                    question_idx = future_to_question[future]
                    logger.error(f'第{question_idx+1}题处理时发生异常: {exc}')
                    # 创建错误结果
                    results[question_idx] = {
                        'question_id': question_idx + 1,
                        'coordinates': questions[question_idx]['coordinates'],
                        'text': questions[question_idx]['text'],
                        'reference_answer': '',
                        'similarity_score': 0,
                        'grading_result': {'success': False, 'error': str(exc)},
                        'image_path': questions[question_idx]['image_path']
                    }
        
        step4_time = time.time() - step4_start
        total_time = time.time() - start_time
        
        logger.info(f"原题检索和批改完成，用时: {step4_time:.2f}秒，成功批改: {successful_grading}/{len(questions)}题")
        logger.info(f"=== 作业处理完成，总用时: {total_time:.2f}秒 ===")
        logger.info(f"处理统计: 题目分割({step1_time:.2f}s) + OCR识别({step2_time:.2f}s) + 题目处理({step3_time:.2f}s) + 检索批改({step4_time:.2f}s)")
        
        return jsonify({
            'success': True,
            'results': results,
            'total_questions': len(results),
            'processing_time': total_time,
            'successful_grading': successful_grading
        })
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"作业处理失败: {str(e)}, 用时: {total_time:.2f}秒")
        logger.error(f"异常类型: {type(e).__name__}")
        import traceback
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

@app.route('/api/results/<filename>')
def get_results(filename):
    """获取处理结果"""
    # 这里可以实现结果缓存和查询逻辑
    pass

@app.route('/api/knowledge/search', methods=['POST'])
def knowledge_search_detail():
    """知识库检索详细信息接口，用于调试和查看检索内容"""
    try:
        data = request.get_json()
        query_text = data.get('query_text', '')
        image_path = data.get('image_path', '')
        
        if not query_text:
            return jsonify({'error': '缺少查询文本'}), 400
        
        logger.info(f"=== 知识库检索详细信息 ===")
        logger.info(f"查询文本: {query_text}")
        logger.info(f"图片路径: {image_path}")
        
        # 执行知识库检索
        search_result = knowledge_service.search_similar_question(query_text, image_path)
        
        # 打印详细的知识库检索结果
        logger.info(f"\n=== 知识库检索返回内容 ===")
        logger.info(f"检索成功: {search_result.get('success', False)}")
        logger.info(f"相似度分数: {search_result.get('similarity_score', 0.0)}")
        logger.info(f"参考答案长度: {len(search_result.get('reference_answer', ''))}")
        logger.info(f"参考答案内容:\n{search_result.get('reference_answer', '')}")
        logger.info(f"源文档信息: {search_result.get('source_document', '')}")
        
        # 打印原始API响应
        raw_result = search_result.get('raw_result', {})
        logger.info(f"\n=== API原始响应结构 ===")
        logger.info(f"原始响应: {json.dumps(raw_result, ensure_ascii=False, indent=2)}")
        
        # 解析和提取图片信息
        extracted_images = []
        extracted_answers = []
        
        def extract_content_from_result(result_data, path=""):
            """递归提取结果中的图片URL和答案内容"""
            if isinstance(result_data, dict):
                for key, value in result_data.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # 检查是否是图片URL
                    if isinstance(value, str) and any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']):
                        extracted_images.append({
                            'path': current_path,
                            'url': value,
                            'type': 'image_url'
                        })
                        logger.info(f"发现图片URL [{current_path}]: {value}")
                    
                    # 检查是否是答案内容（包含常见的答案关键词）
                    elif isinstance(value, str) and len(value) > 10 and any(keyword in value for keyword in ['答案', '解答', '答', '解', '结果', '选择']):
                        extracted_answers.append({
                            'path': current_path,
                            'content': value,
                            'length': len(value)
                        })
                        logger.info(f"发现答案内容 [{current_path}] (长度: {len(value)}): {value[:100]}...")
                    
                    # 递归处理嵌套结构
                    elif isinstance(value, (dict, list)):
                        extract_content_from_result(value, current_path)
            
            elif isinstance(result_data, list):
                for i, item in enumerate(result_data):
                    current_path = f"{path}[{i}]" if path else f"[{i}]"
                    extract_content_from_result(item, current_path)
        
        # 提取内容
        extract_content_from_result(raw_result)
        
        logger.info(f"\n=== 提取结果汇总 ===")
        logger.info(f"提取到的图片数量: {len(extracted_images)}")
        logger.info(f"提取到的答案数量: {len(extracted_answers)}")
        
        # 构建返回结果
        detailed_result = {
            'success': search_result.get('success', False),
            'query_text': query_text,
            'image_path': image_path,
            'similarity_score': search_result.get('similarity_score', 0.0),
            'reference_answer': search_result.get('reference_answer', ''),
            'source_document': search_result.get('source_document', ''),
            'extracted_images': extracted_images,
            'extracted_answers': extracted_answers,
            'raw_api_response': raw_result,
            'all_results': search_result.get('all_results', [])
        }
        
        return jsonify(detailed_result)
        
    except Exception as e:
        logger.error(f"知识库检索详细信息获取失败: {str(e)}")
        import traceback
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        return jsonify({'error': f'检索失败: {str(e)}'}), 500

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3020)