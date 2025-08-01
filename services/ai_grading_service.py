import requests
import json
import base64
import requests
from config import Config
import logging
import time
import os
import re
from .obs_service import OBSService

logger = logging.getLogger(__name__)

class AIGradingService:
    """AI批改服务"""
    
    def __init__(self):
        self.api_url = Config.AI_GRADING_API_URL
        self.api_token = Config.AI_GRADING_API_TOKEN
        self.timeout = Config.REQUEST_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        self.retry_delay = Config.RETRY_DELAY
        self.obs_service = OBSService()
    
    def grade_question(self, question_image_path, question_text, knowledge_result=None, char_details=None):
        """批改单个题目
        
        Args:
            question_image_path: 题目图片路径
            question_text: 题目OCR文字
            knowledge_result: 知识库检索结果（可选）
            char_details: 字符级坐标信息（用于获取作答区坐标）
        
        Returns:
            dict: 批改结果
        """
        try:
            logger.info(f"开始AI批改，题目文本: {question_text[:100]}...")
            logger.info(f"题目图片路径: {question_image_path}")
            
            # 从knowledge_result中提取信息
            if isinstance(knowledge_result, dict):
                reference_answer = knowledge_result.get('reference_answer', '')
                answer_image_url = knowledge_result.get('answer_image_url', '')
                question_image_url = knowledge_result.get('question_image_url', '')
            else:
                # 向后兼容：如果传入的是字符串
                reference_answer = str(knowledge_result) if knowledge_result else ''
                answer_image_url = ''
                question_image_url = ''
            
            logger.info(f"参考答案长度: {len(reference_answer)}")
            logger.info(f"答案图片URL: {answer_image_url}")
            logger.info(f"题目图片URL: {question_image_url}")
            
            # 检查文件是否存在
            if not os.path.exists(question_image_path):
                logger.error(f"题目图片文件不存在: {question_image_path}")
                return {
                    'success': False,
                    'error': '题目图片文件不存在',
                    'question_text': question_text
                }
            
            headers = {
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Authorization': f'Bearer {self.api_token}',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'User-Agent': 'PostmanRuntime-ApipostRuntime/1.1.0'
            }
            
            # 获取图片URL
            image_result = self.obs_service.process_image_path(question_image_path)
            if not image_result['success']:
                logger.error(f"图片处理失败: {image_result.get('error', '未知错误')}")
                return {
                    'success': False,
                    'error': '图片处理失败',
                    'question_text': question_text
                }
            
            image_url = image_result['url']
            
            # 构建请求数据
            # 将char_details直接转换为JSON字符串
            user_question_ocr = ""
            if char_details and len(char_details) > 0:
                import json
                # 将字符级坐标信息转换为JSON字符串
                user_question_ocr = json.dumps(char_details, ensure_ascii=False)
                logger.info(f"使用字符级OCR信息JSON格式，包含{len(char_details)}个字符")
                logger.debug(f"JSON字符串长度: {len(user_question_ocr)}")
            else:
                logger.warning("没有字符级坐标信息可用")
            
            payload = {
                "inputs": {
                    "user_question_ocr": user_question_ocr
                },
                "user": "abc-123",
                "response_mode": "blocking",
                "files": [
                    {
                        "type": "image",
                        "transfer_method": "remote_url",
                        "url": image_url
                    }
                ]
            }
            
            # 添加知识库中的题目图片
            if question_image_url and question_image_url.strip():
                payload["files"].append({
                    "type": "image",
                    "transfer_method": "remote_url",
                    "url": question_image_url
                })
            
            # 只有当answer_image_url不为空时才添加答案图片
            if answer_image_url and answer_image_url.strip():
                payload["files"].append({
                    "type": "image",
                    "transfer_method": "remote_url",
                    "url": answer_image_url
                })
            
            # 打印完整的请求参数用于调试
            logger.info(f"=== AI批改API调用参数 ===")
            logger.info(f"API URL: {self.api_url}")
            logger.info(f"请求头: {headers}")
            logger.info(f"完整请求体: {payload}")
            logger.info(f"图片URL: {image_url}")
            logger.info(f"题目文本: {question_text}")
            logger.info(f"参考答案: {reference_answer}")
            logger.info(f"============================")
            
            # 进行重试请求
            for attempt in range(self.max_retries):
                try:
                    start_time = time.time()
                    logger.info(f"调用AI批改API，尝试次数: {attempt + 1}/{self.max_retries}")
                    logger.debug(f"请求超时设置: {self.timeout}秒")
                    
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout
                    )
                    
                    response_time = time.time() - start_time
                    logger.info(f"AI批改API响应时间: {response_time:.2f}秒")
                    logger.info(f"AI批改API响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            logger.info("AI批改API调用成功")
                            logger.debug(f"AI批改API原始响应: {result}")
                            
                            # 解析批改结果
                            parsed_result = self._parse_grading_result(result)
                            logger.info(f"批改结果解析完成，得分: {parsed_result.get('score', '未知')}")
                        except json.JSONDecodeError as e:
                            logger.error(f"AI批改API响应JSON解析失败: {e}")
                            logger.error(f"响应内容: {response.text[:500]}")
                            if attempt < self.max_retries - 1:
                                logger.info(f"等待{self.retry_delay}秒后重试...")
                                time.sleep(self.retry_delay)
                                continue
                            else:
                                return {
                                    'success': False,
                                    'error': f'AI批改API响应格式错误: {str(e)}',
                                    'question_text': question_text
                                }
                        
                        return {
                            'success': True,
                            'question_text': question_text,
                            'reference_answer': reference_answer,
                            'grading_result': parsed_result,
                            'raw_result': result
                        }
                    else:
                        logger.error(f"AI批改API调用失败，状态码: {response.status_code}")
                        logger.error(f"错误响应内容: {response.text[:500]}")
                        if attempt < self.max_retries - 1:
                            logger.info(f"等待{self.retry_delay}秒后重试...")
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f'AI批改API调用失败，状态码: {response.status_code}',
                                'question_text': question_text
                            }
                            
                except requests.exceptions.RequestException as e:
                    logger.error(f"AI批改请求异常: {str(e)}")
                    logger.error(f"异常类型: {type(e).__name__}")
                    if attempt < self.max_retries - 1:
                        logger.info(f"等待{self.retry_delay}秒后重试...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {
                            'success': False,
                            'error': f'AI批改网络请求失败: {str(e)}',
                            'question_text': question_text
                        }
                        
        except Exception as e:
            logger.error(f"AI批改处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'question_text': question_text
            }
    
    def grade_question_streaming(self, question_image_path, question_text, reference_answer, char_details=None):
        """流式批改题目（适用于长时间处理）
        
        Args:
            question_image_path: 题目图片路径
            question_text: 题目OCR文本
            reference_answer: 参考答案
            
        Returns:
            dict: 包含批改结果的字典
        """
        try:
            logger.info(f"开始流式AI批改，题目文本: {question_text[:100]}...")
            logger.info(f"题目图片路径: {question_image_path}")
            
            # 检查文件是否存在
            if not os.path.exists(question_image_path):
                logger.error(f"题目图片文件不存在: {question_image_path}")
                return {
                    'success': False,
                    'error': '题目图片文件不存在',
                    'question_text': question_text
                }
            
            headers = {
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Authorization': f'Bearer {self.api_token}',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'User-Agent': 'PostmanRuntime-ApipostRuntime/1.1.0'
            }
            
            # 获取图片URL
            image_result = self.obs_service.process_image_path(question_image_path)
            if not image_result['success']:
                logger.error(f"图片处理失败: {image_result.get('error', '未知错误')}")
                return {
                    'success': False,
                    'error': '图片处理失败',
                    'question_text': question_text
                }
            
            image_url = image_result['url']
            
            # 构建请求数据
            # 优先使用字符级坐标信息，如果没有则使用普通OCR文本
            user_question_ocr = question_text if question_text else ""
            if char_details and len(char_details) > 0:
                # 将字符级坐标信息转换为批改API需要的格式
                user_question_ocr = {
                    "text": question_text,
                    "char_details": char_details
                }
                logger.info(f"流式批改使用字符级OCR信息，包含{len(char_details)}个字符")
            else:
                logger.info("流式批改使用普通OCR文本信息")
            
            payload = {
                "inputs": {
                    "user_question_ocr": user_question_ocr
                },
                "user": "abc-123",
                "response_mode": "streaming",
                "files": [
                    {
                        "type": "image",
                        "transfer_method": "remote_url",
                        "url": image_url
                    }
                ]
            }
            
            # 打印完整的流式请求参数用于调试
            logger.info(f"=== 流式AI批改API调用参数 ===")
            logger.info(f"API URL: {self.api_url}")
            logger.info(f"请求头: {headers}")
            logger.info(f"完整请求体: {payload}")
            logger.info(f"图片URL: {image_url}")
            logger.info(f"题目文本: {question_text}")
            logger.info(f"参考答案: {reference_answer}")
            logger.info(f"============================")
            
            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            
            response_time = time.time() - start_time
            logger.info(f"流式API响应时间: {response_time:.2f}秒")
            logger.info(f"流式API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 处理流式响应
                full_result = self._handle_streaming_response(response)
                
                return {
                    'success': True,
                    'question_text': question_text,
                    'reference_answer': reference_answer,
                    'grading_result': full_result,
                    'streaming': True
                }
            else:
                return {
                    'success': False,
                    'error': f'流式批改失败，状态码: {response.status_code}',
                    'question_text': question_text
                }
                
        except Exception as e:
            logger.error(f"流式批改处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'question_text': question_text
            }
    
    def _image_to_base64(self, image_path):
        """将图片转换为base64编码
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            str: base64编码的图片数据
        """
        try:
            logger.debug(f"开始处理图片: {image_path}")
            
            # 使用OBS服务处理图片路径
            image_result = self.obs_service.process_image_path(image_path)
            
            if not image_result['success']:
                logger.error(f"图片处理失败: {image_result.get('error', '未知错误')}")
                return ""
            
            final_image_path = image_result['url']
            
            # 统一处理OBS URL，不支持本地文件路径
            if image_result.get('is_local', False):
                logger.error(f"AI批改不支持本地文件路径: {final_image_path}，必须使用OBS URL")
                return ""
            
            # 从OBS URL下载图片并转换为base64
            import requests
            try:
                response = requests.get(final_image_path, timeout=30)
                if response.status_code == 200:
                    image_data = response.content
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    
                    logger.debug(f"从OBS下载图片大小: {len(image_data)} 字节")
                    logger.debug(f"base64编码长度: {len(base64_data)}")
                    logger.info(f"OBS图片下载并转换base64成功: {final_image_path}")
                    
                    return f"data:image/jpeg;base64,{base64_data}"
                else:
                    logger.error(f"从OBS下载图片失败，状态码: {response.status_code}")
                    return ""
            except Exception as e:
                logger.error(f"从OBS下载图片失败: {str(e)}")
                return ""
                
        except Exception as e:
            logger.error(f"图片处理失败: {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            return ""
    
    def _parse_grading_result(self, api_result):
        """解析批改结果
        
        Args:
            api_result: API返回的原始结果
            
        Returns:
            dict: 解析后的批改结果
        """
        logger.debug(f"开始解析AI批改结果: {api_result}")
        
        grading_result = {
            'score': 0,
            'max_score': 100,
            'feedback': '',
            'correct': False,
            'suggestions': [],
            'analysis': ''
        }
        
        try:
            # 根据Dify工作流的实际返回格式进行解析
            if 'data' in api_result:
                data = api_result['data']
                logger.debug(f"从API结果中提取data字段: {data}")
                
                if 'outputs' in data:
                    outputs = data['outputs']
                    logger.debug(f"从data中提取outputs字段: {outputs}")
                    
                    # 处理result字段中的JSON字符串
                    if 'result' in outputs:
                        try:
                            import json
                            result_str = outputs['result']
                            logger.debug(f"提取result字符串: {result_str}")
                            
                            # 解析JSON字符串
                            result_data = json.loads(result_str)
                            logger.debug(f"解析JSON结果: {result_data}")
                            
                            # 处理结果数组（通常是第一个元素）
                            if isinstance(result_data, list) and len(result_data) > 0:
                                first_result = result_data[0]
                                logger.debug(f"提取第一个结果: {first_result}")
                                
                                # 解析isRight字段
                                if 'isRight' in first_result:
                                    is_right = first_result['isRight']
                                    grading_result['correct'] = bool(is_right)
                                    grading_result['score'] = 100 if is_right else 0
                                    logger.debug(f"解析正确性: {grading_result['correct']}, 分数: {grading_result['score']}")
                                
                                # 解析answerAreaPosition字段（区域坐标）
                                if 'answerAreaPosition' in first_result:
                                    area_position = first_result['answerAreaPosition']
                                    grading_result['answer_area_position'] = area_position
                                    logger.debug(f"解析答题区域位置: {area_position}")
                                    
                        except json.JSONDecodeError as e:
                            logger.error(f"解析result JSON失败: {e}")
                        except Exception as e:
                            logger.error(f"处理result字段失败: {e}")
                    
                    # 提取文本输出（保留原有逻辑以防万一）
                    if 'text' in outputs:
                        feedback_text = outputs['text']
                        grading_result['feedback'] = feedback_text
                        logger.debug(f"提取反馈文本，长度: {len(feedback_text)}")
                        
                    # 如果工作流返回其他结构化数据（保留原有逻辑）
                    if 'score' in outputs:
                        grading_result['score'] = outputs['score']
                        logger.debug(f"从API结果中直接获取分数: {outputs['score']}")
                    
                    if 'correct' in outputs:
                        grading_result['correct'] = outputs['correct']
                        logger.debug(f"从API结果中直接获取正确性: {outputs['correct']}")
            else:
                logger.warning("API结果中未找到data字段")
            
            logger.info(f"批改结果解析完成，得分: {grading_result['score']}，正确性: {grading_result['correct']}")
            logger.debug(f"完整解析结果: {grading_result}")
            return grading_result
            
        except Exception as e:
            logger.error(f"批改结果解析失败: {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"原始结果: {api_result}")
            return grading_result
    
    def _extract_structured_feedback(self, feedback_text):
        """从反馈文本中提取结构化信息
        
        Args:
            feedback_text: 反馈文本
            
        Returns:
            dict: 提取出的结构化信息
        """
        structured_info = {}
        
        try:
            # 尝试提取分数
            import re
            
            # 匹配分数模式，如 "得分: 85/100" 或 "分数：90"等
            score_patterns = [
                r'得分[:：]\s*(\d+)(?:/\d+)?',
                r'分数[:：]\s*(\d+)(?:/\d+)?',
                r'评分[:：]\s*(\d+)(?:/\d+)?',
                r'(\d+)\s*分'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, feedback_text)
                if match:
                    structured_info['score'] = int(match.group(1))
                    break
            
            # 判断是否正确
            if '正确' in feedback_text or '对' in feedback_text:
                structured_info['correct'] = True
            elif '错误' in feedback_text or '不对' in feedback_text or '错' in feedback_text:
                structured_info['correct'] = False
            
            # 提取建议（简单的关键词匹配）
            suggestion_keywords = ['建议', '推荐', '应该', '可以', '需要']
            suggestions = []
            
            for line in feedback_text.split('\n'):
                for keyword in suggestion_keywords:
                    if keyword in line:
                        suggestions.append(line.strip())
                        break
            
            if suggestions:
                structured_info['suggestions'] = suggestions
            
            return structured_info
            
        except Exception as e:
            logger.error(f"结构化信息提取失败: {str(e)}")
            return {}
    
    def _handle_streaming_response(self, response):
        """处理流式响应
        
        Args:
            response: requests响应对象
            
        Returns:
            dict: 完整的批改结果
        """
        full_result = {
            'feedback': '',
            'score': 0,
            'correct': False
        }
        
        try:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data_str = decoded_line[6:]
                        if data_str.strip() == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if 'text' in data:
                                full_result['feedback'] += data['text']
                        except json.JSONDecodeError:
                            continue
            
            # 从完整反馈中提取结构化信息
            structured_info = self._extract_structured_feedback(full_result['feedback'])
            full_result.update(structured_info)
            
            return full_result
            
        except Exception as e:
            logger.error(f"流式响应处理失败: {str(e)}")
            return full_result