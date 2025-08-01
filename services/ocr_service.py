import requests
import json
import os
import requests
import base64
from config import Config
import logging
import time

logger = logging.getLogger(__name__)

class OCRService:
    """OCR文字识别服务"""
    
    def __init__(self):
        self.api_url = Config.OCR_API_URL
        self.app_id = Config.OCR_APP_ID
        self.secret_code = Config.OCR_SECRET_CODE
        self.timeout = Config.REQUEST_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        self.retry_delay = Config.RETRY_DELAY
    
    def extract_text(self, image_path):
        """从图片中提取文字
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            dict: 包含OCR结果的字典
        """
        try:
            logger.info(f"开始OCR文字提取，图片路径: {image_path}")
            
            # 检查文件是否存在
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return {'success': False, 'error': '图片文件不存在'}
            
            headers = {
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Content-Type': 'application/octet-stream',
                'User-Agent': 'PostmanRuntime-ApipostRuntime/1.1.0',
                'x-ti-app-id': self.app_id,
                'x-ti-secret-code': self.secret_code
            }
            
            logger.debug(f"OCR请求头: {headers}")
            logger.debug(f"OCR API URL: {self.api_url}")
            
            # 读取图片文件
            with open(image_path, 'rb') as file:
                image_data = file.read()
            
            logger.info(f"图片文件大小: {len(image_data)} bytes")
            
            # 进行重试请求
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"调用OCR API，尝试次数: {attempt + 1}/{self.max_retries}")
                    start_time = time.time()
                    
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        data=image_data,
                        timeout=self.timeout
                    )
                    
                    end_time = time.time()
                    logger.info(f"OCR API响应时间: {end_time - start_time:.2f}秒")
                    
                    logger.info(f"OCR API响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            logger.info(f"OCR API原始响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        except json.JSONDecodeError as e:
                            logger.error(f"OCR响应JSON解析失败: {str(e)}")
                            logger.error(f"响应内容: {response.text[:500]}...")
                            return {'success': False, 'error': 'OCR响应格式错误'}
                        
                        if result.get('code') == 200:
                            text_content = self._extract_full_text(result)
                            logger.info(f"OCR识别成功，提取文本长度: {len(text_content)}")
                            logger.info(f"OCR完整返回数据: {result}")
                            logger.info(f"提取的文本内容: {text_content[:200]}...")
                            
                            return {
                                'success': True,
                                'result': result.get('result', {}),
                                'text_content': text_content,
                                'raw_result': result
                            }
                        else:
                            error_msg = result.get('message', '未知错误')
                            logger.error(f"OCR API返回错误码: {result.get('code')}, 错误信息: {error_msg}")
                            return {
                                'success': False,
                                'error': f'OCR API错误: {error_msg}'
                            }
                    else:
                        logger.error(f"OCR API调用失败，状态码: {response.status_code}")
                        logger.error(f"响应内容: {response.text[:500]}...")
                        
                        if attempt < self.max_retries - 1:
                            logger.info(f"等待{self.retry_delay}秒后重试...")
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f'OCR API调用失败，状态码: {response.status_code}'
                            }
                            
                except requests.exceptions.RequestException as e:
                    logger.error(f"OCR请求异常: {str(e)}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {
                            'success': False,
                            'error': f'OCR网络请求失败: {str(e)}'
                        }
                        
        except Exception as e:
            logger.error(f"OCR处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_full_text(self, ocr_result):
        """从OCR结果中提取完整文本
        
        Args:
            ocr_result: OCR API返回的结果
            
        Returns:
            str: 完整的文本内容
        """
        full_text = []
        
        try:
            # 提取markdown格式的文本
            if 'result' in ocr_result and 'markdown' in ocr_result['result']:
                return ocr_result['result']['markdown']
            
            # 如果没有markdown，从pages中提取文本
            if 'result' in ocr_result and 'pages' in ocr_result['result']:
                for page in ocr_result['result']['pages']:
                    if 'content' in page:
                        page_text = []
                        for item in page['content']:
                            if 'text' in item:
                                page_text.append(item['text'])
                        full_text.append(' '.join(page_text))
            
            return '\n'.join(full_text)
            
        except Exception as e:
            logger.error(f"文本提取失败: {str(e)}")
            return ""
    
    def get_text_with_coordinates(self, ocr_result):
        """获取带坐标信息的文本
        
        Args:
            ocr_result: OCR识别结果（包含raw_result字段的完整结果）
            
        Returns:
            list: 包含文本和坐标信息的列表
        """
        text_items = []
        
        try:
            # 获取原始OCR结果
            raw_result = ocr_result.get('raw_result', ocr_result)
            
            if 'result' in raw_result and 'pages' in raw_result['result']:
                logger.info(f"开始处理OCR结果中的坐标文本，页面数: {len(raw_result['result']['pages'])}")
                
                for page_idx, page in enumerate(raw_result['result']['pages']):
                    if 'content' in page:
                        logger.info(f"处理第{page_idx+1}页，文本项数量: {len(page['content'])}")
                        
                        for item in page['content']:
                            if 'text' in item and 'pos' in item:
                                text_item = {
                                    'text': item['text'],
                                    'coordinates': item['pos']
                                }
                                
                                # 如果存在char_pos字段，处理字符级坐标信息
                                if 'char_pos' in item:
                                    text_content = item['text']
                                    char_positions = item['char_pos']
                                    
                                    # 验证字符数和坐标数是否匹配
                                    if len(text_content) == len(char_positions):
                                        text_item['char_coordinates'] = char_positions
                                        logger.info(f"文本 '{text_content}' 字符级坐标匹配成功: {len(text_content)} 个字符对应 {len(char_positions)} 个坐标")
                                    else:
                                        logger.warning(f"文本 '{text_content}' 字符数({len(text_content)})与坐标数({len(char_positions)})不匹配")
                                        # 仍然保存坐标信息，但会在后续处理中进行调整
                                        text_item['char_coordinates'] = char_positions
                                        logger.warning(f"已保存坐标信息，将在字符映射时处理不匹配问题")
                                    
                                    # 记录详细的字符坐标信息
                                    logger.debug(f"文本内容: '{text_content}'")
                                    logger.debug(f"字符级坐标数组长度: {len(char_positions)}")
                                    
                                    # 显示前几个字符的坐标示例
                                    if len(char_positions) > 0:
                                        for i in range(min(3, len(text_content), len(char_positions))):
                                            char = text_content[i] if i < len(text_content) else 'N/A'
                                            coords = char_positions[i] if i < len(char_positions) else 'N/A'
                                            logger.debug(f"  字符[{i}]: '{char}' -> 坐标: {coords}")
                                else:
                                    logger.debug(f"文本 '{item['text'][:20]}...' 不包含字符级坐标信息(char_pos)")
                                
                                text_items.append(text_item)
            
            logger.info(f"提取到{len(text_items)}个文本块（包含字符级坐标信息）")
            return text_items
            
        except Exception as e:
            logger.error(f"坐标文本提取失败: {str(e)}，OCR结果结构: {type(ocr_result)}")
            return []
    
    def get_text_character_mapping(self, text, char_coordinates):
        """获取单个文本的字符级坐标映射
        
        Args:
            text (str): 文本内容
            char_coordinates (list): 字符级坐标数组列表
            
        Returns:
            list: 字符与坐标的映射列表
        """
        mappings = []
        
        try:
            if not text or not char_coordinates:
                logger.warning("文本或字符坐标为空")
                return []
            
            # 确保字符数和坐标数匹配
            if len(text) != len(char_coordinates):
                logger.warning(f"文本长度({len(text)})与坐标数组长度({len(char_coordinates)})不匹配")
                logger.warning(f"文本: '{text}'")
                actual_length = min(len(text), len(char_coordinates))
            else:
                actual_length = len(text)
                logger.debug(f"文本与坐标完全匹配，长度: {actual_length}")
            
            # 创建字符级映射
            for i in range(actual_length):
                mapping = {
                    'index': i,
                    'char': text[i],
                    'coordinates': char_coordinates[i],
                    'char_code': ord(text[i])  # 字符的Unicode编码
                }
                mappings.append(mapping)
                logger.debug(f"映射 {i}: '{text[i]}' -> {char_coordinates[i]}")
            
            logger.info(f"成功创建 {len(mappings)} 个字符级坐标映射")
            return mappings
            
        except Exception as e:
            logger.error(f"字符级坐标映射失败: {str(e)}")
            return []
    
    def filter_text_by_region(self, text_items, x1, y1, x2, y2):
        """根据区域过滤文本
        
        Args:
            text_items: 文本项列表
            x1, y1, x2, y2: 区域坐标
            
        Returns:
            list: 过滤后的文本项列表
        """
        filtered_items = []
        
        for item in text_items:
            if self._is_text_in_region(item['coordinates'], x1, y1, x2, y2):
                filtered_items.append(item)
        
        logger.debug(f"区域过滤：输入{len(text_items)}个文本项，过滤后得到{len(filtered_items)}个")
        return filtered_items
    
    def get_character_coordinates(self, text_items):
        """获取字符级坐标信息
        
        Args:
            text_items: 包含字符级坐标的文本项列表
            
        Returns:
            list: 字符级坐标详情列表，每个字符对应一个坐标数组
        """
        char_details = []
        
        try:
            for text_item in text_items:
                if 'char_coordinates' in text_item and text_item['char_coordinates']:
                    text = text_item['text']
                    char_coords = text_item['char_coordinates']
                    
                    logger.info(f"处理文本块: '{text}'")
                    logger.info(f"文本长度: {len(text)} 个字符")
                    logger.info(f"坐标数组长度: {len(char_coords)} 个坐标")
                    
                    # 验证字符数和坐标数是否完全匹配
                    if len(text) != len(char_coords):
                        logger.warning(f"字符数({len(text)})与坐标数({len(char_coords)})不匹配，文本: '{text}'")
                        # 使用较小的长度以避免索引错误
                        actual_length = min(len(text), len(char_coords))
                        logger.warning(f"将处理前 {actual_length} 个匹配的字符")
                    else:
                        actual_length = len(text)
                        logger.debug(f"字符数和坐标数完全匹配: {actual_length}")
                    
                    # 逐字符映射坐标
                    for i in range(actual_length):
                        char = text[i]
                        char_coordinate = char_coords[i]
                        
                        char_detail = {
                            'character': char,
                            'coordinates': char_coordinate,  # 单个字符对应的坐标数组
                            'index': i  # 在文本中的索引位置
                        }
                        char_details.append(char_detail)
                        
                        # 详细日志记录每个字符的映射
                        logger.debug(f"字符 '{char}' (索引{i}) 坐标: {char_coordinate}")
                    
                    logger.info(f"文本块 '{text}' 成功提取 {actual_length} 个字符级坐标")
                else:
                    logger.debug(f"文本项缺少字符级坐标信息: '{text_item.get('text', 'N/A')[:20]}...'")
            
            logger.info(f"总共提取到 {len(char_details)} 个字符级坐标详情")
            
            # 输出字符级坐标统计信息
            if char_details:
                sample_char = char_details[0]
                logger.info(f"字符级坐标示例 - 字符: '{sample_char['character']}', 坐标: {sample_char['coordinates']}")
            
            return char_details
            
        except Exception as e:
            logger.error(f"字符级坐标提取失败: {str(e)}")
            logger.error(f"输入参数类型: {type(text_items)}, 长度: {len(text_items) if hasattr(text_items, '__len__') else 'N/A'}")
            return []
    
    def filter_characters_by_region(self, char_details, x1, y1, x2, y2):
        """根据区域过滤字符级数据
        
        Args:
            char_details: 字符级坐标详情列表
            x1, y1, x2, y2: 区域坐标
            
        Returns:
            list: 过滤后的字符级详情列表
        """
        filtered_chars = []
        
        try:
            for char_detail in char_details:
                if self._is_text_in_region(char_detail['coordinates'], x1, y1, x2, y2):
                    filtered_chars.append(char_detail)
            
            logger.debug(f"字符级区域过滤：输入{len(char_details)}个字符，过滤后得到{len(filtered_chars)}个")
            return filtered_chars
            
        except Exception as e:
            logger.error(f"字符级区域过滤失败: {str(e)}")
            return []
    
    def _is_text_in_region(self, text_coords, x1, y1, x2, y2):
        """判断文字坐标是否在指定区域内
        
        Args:
            text_coords: 文字坐标数组 [x1, y1, x2, y1, x2, y2, x1, y2]
            x1, y1, x2, y2: 区域坐标
            
        Returns:
            bool: 是否在区域内
        """
        try:
            if len(text_coords) >= 8:
                text_x1, text_y1 = text_coords[0], text_coords[1]
                text_x2, text_y2 = text_coords[4], text_coords[5]
                
                # 检查文字区域是否与指定区域有重叠
                return not (text_x2 < x1 or text_x1 > x2 or text_y2 < y1 or text_y1 > y2)
            
            return False
            
        except Exception as e:
            logger.error(f"坐标判断失败: {str(e)}")
            return False