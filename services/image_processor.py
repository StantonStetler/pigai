import requests
import json
import os
import requests
import base64
from PIL import Image
from config import Config
import logging
import time

logger = logging.getLogger(__name__)

class ImageProcessor:
    """图像处理服务"""
    
    def __init__(self):
        self.api_url = Config.SEGMENTATION_API_URL
        self.api_token = Config.SEGMENTATION_API_TOKEN
        self.timeout = Config.REQUEST_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        self.retry_delay = Config.RETRY_DELAY
    
    def segment_questions(self, image_path):
        """调用API进行题目分割
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            dict: 包含分割结果的字典
        """
        logger.info(f"开始调用题目分割API，图片路径: {image_path}")
        logger.info(f"API配置 - URL: {self.api_url}")
        logger.info(f"API配置 - Token: {self.api_token[:20]}...")  # 只记录token前20位
        
        try:
            # 准备请求头，按照实际API要求设置
            headers = {
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Authorization': self.api_token,
                'Connection': 'keep-alive',
                'User-Agent': 'PostmanRuntime-ApipostRuntime/1.1.0',
                'Content-Type': 'application/octet-stream'
            }
            
            logger.info(f"请求头配置: {json.dumps(headers, ensure_ascii=False, indent=2)}")
            
            # 读取图片文件并转换为字节数据
            with open(image_path, 'rb') as file:
                image_data = file.read()
                logger.info(f"成功读取图片文件，大小: {len(image_data)} 字节")
                
                # 进行重试请求
                for attempt in range(self.max_retries):
                    try:
                        logger.info(f"调用题目分割API，尝试次数: {attempt + 1}/{self.max_retries}")
                        logger.info(f"请求URL: {self.api_url}")
                        
                        # 发送POST请求，直接传递图片二进制数据
                        response = requests.post(
                            self.api_url,
                            headers=headers,
                            data=image_data,
                            timeout=self.timeout
                        )
                        
                        logger.info(f"API响应状态码: {response.status_code}")
                        logger.info(f"API响应头: {dict(response.headers)}")
                        
                        if response.status_code == 200:
                            result = response.json()
                            logger.info(f"API调用成功，响应数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
                            
                            coordinates = self._parse_coordinates(result)
                            logger.info(f"成功解析出 {len(coordinates)} 个题目区域")
                            
                            return {
                                'success': True,
                                'coordinates': coordinates,
                                'raw_result': result
                            }
                        else:
                            error_text = response.text
                            logger.error(f"API调用失败，状态码: {response.status_code}，响应内容: {error_text}")
                            if attempt < self.max_retries - 1:
                                logger.info(f"等待 {self.retry_delay} 秒后重试...")
                                time.sleep(self.retry_delay)
                                continue
                            else:
                                return {
                                    'success': False,
                                    'error': f'API调用失败，状态码: {response.status_code}，响应: {error_text}'
                                }
                                
                    except requests.exceptions.RequestException as e:
                        logger.error(f"网络请求异常: {str(e)}")
                        if attempt < self.max_retries - 1:
                            logger.info(f"等待 {self.retry_delay} 秒后重试...")
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f'网络请求失败: {str(e)}'
                            }
                        
        except FileNotFoundError:
            error_msg = f"图片文件不存在: {image_path}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"题目分割处理失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _parse_coordinates(self, api_result):
        """解析API返回的坐标信息
        
        Args:
            api_result: API返回的原始结果
            
        Returns:
            list: 解析后的坐标列表
        """
        logger.info("开始解析API返回的坐标信息")
        coordinates = []
        try:
            # 根据用户提供的API返回格式解析坐标
            if not api_result.get('success', False):
                logger.error(f"API调用失败，详情: {api_result}")
                return coordinates
                
            detection_boxes = api_result.get('detection_boxes', [])
            detection_scores = api_result.get('detection_scores', [])
            detection_classes = api_result.get('detection_classes', [])
            detection_class_names = api_result.get('detection_class_names', [])
            ori_img_shape = api_result.get('ori_img_shape', [])
            
            logger.info(f"检测到 {len(detection_boxes)} 个边界框")
            logger.info(f"原图尺寸: {ori_img_shape}")
            
            # 固定缩放因子为1.0，不使用API返回的缩放因子
            scale_factor = [1.0, 1.0, 1.0, 1.0]
            logger.info(f"使用固定缩放因子: {scale_factor}")
            
            for i, bbox in enumerate(detection_boxes):
                if i < len(detection_scores) and i < len(detection_class_names):
                    # 坐标格式: [x1, y1, x2, y2]
                    # 需要将坐标从模型输出尺寸转换回原图尺寸
                    x1 = bbox[0] / scale_factor[0]
                    y1 = bbox[1] / scale_factor[1] 
                    x2 = bbox[2] / scale_factor[2]
                    y2 = bbox[3] / scale_factor[3]
                    
                    score = detection_scores[i]
                    class_name = detection_class_names[i]
                    
                    coord_info = {
                        'x1': int(x1),
                        'y1': int(y1),
                        'x2': int(x2),
                        'y2': int(y2),
                        'confidence': float(score),
                        'class_name': class_name,
                        'question_id': i + 1
                    }
                    
                    coordinates.append(coord_info)
                    logger.info(f"题目 {i+1}: 坐标({int(x1)},{int(y1)},{int(x2)},{int(y2)}) 置信度:{score:.3f} 类别:{class_name}")
            
            # 按y坐标排序，从上到下排列题目
            coordinates.sort(key=lambda x: x['y1'])
            logger.info(f"成功解析 {len(coordinates)} 个题目区域，已按位置排序")
            
            return coordinates
            
        except Exception as e:
            error_msg = f"坐标解析失败: {str(e)}"
            logger.error(error_msg)
            return []
    
    def split_questions(self, image_path, coordinates, ocr_result, char_details=None):
        """根据坐标信息分割题目
        
        Args:
            image_path: 原始图片路径
            coordinates: 题目坐标列表
            ocr_result: OCR识别结果
            char_details: 字符级坐标信息（用于批改接口）
            
        Returns:
            list: 分割后的题目信息列表
        """
        questions = []
        
        try:
            # 打开原始图片
            image = Image.open(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            
            for i, coord in enumerate(coordinates):
                # 裁剪题目区域
                question_image = image.crop((
                    coord['x1'], coord['y1'], coord['x2'], coord['y2']
                ))
                
                # 保存裁剪后的图片
                question_image_path = os.path.join(
                    Config.PROCESSED_FOLDER, 
                    f"{base_name}_question_{i+1}.jpg"
                )
                
                # 如果图片是RGBA模式，转换为RGB模式以支持JPEG格式
                if question_image.mode == 'RGBA':
                    # 创建白色背景
                    rgb_image = Image.new('RGB', question_image.size, (255, 255, 255))
                    rgb_image.paste(question_image, mask=question_image.split()[-1])  # 使用alpha通道作为mask
                    question_image = rgb_image
                
                question_image.save(question_image_path, 'JPEG')
                
                # 提取该区域的OCR文字
                question_text = self._extract_region_text(
                    ocr_result, coord['x1'], coord['y1'], coord['x2'], coord['y2']
                )
                
                # 提取该区域的字符级坐标信息
                question_char_details = []
                if char_details:
                    for char_detail in char_details:
                        # coordinates是8个值的数组: [x1, y1, x2, y2, x3, y3, x4, y4]
                        char_coords = char_detail.get('coordinates', [])
                        if len(char_coords) >= 4:
                            # 使用字符坐标的左上角点进行区域判断
                            char_x = char_coords[0]
                            char_y = char_coords[1]
                            # 判断字符是否在题目区域内
                            if (coord['x1'] <= char_x <= coord['x2'] and 
                                coord['y1'] <= char_y <= coord['y2']):
                                question_char_details.append(char_detail)
                
                questions.append({
                    'question_id': i + 1,
                    'coordinates': coord,
                    'image_path': question_image_path,
                    'text': question_text,
                    'char_details': question_char_details
                })
            
            logger.info(f"成功分割{len(questions)}道题目")
            return questions
            
        except Exception as e:
            logger.error(f"题目分割失败: {str(e)}")
            return []
    
    def _extract_region_text(self, ocr_result, x1, y1, x2, y2):
        """从OCR结果中提取指定区域的文字
        
        Args:
            ocr_result: OCR识别结果
            x1, y1, x2, y2: 区域坐标
            
        Returns:
            str: 该区域的文字内容
        """
        region_text = []
        
        try:
            logger.debug(f"提取区域文本，坐标: ({x1}, {y1}) 到 ({x2}, {y2})")
            logger.info(f"OCR结果结构: {list(ocr_result.keys()) if isinstance(ocr_result, dict) else 'not dict'}")
            
            # 检查OCR结果结构，优先从pages的content中获取字符级坐标信息
            if 'result' in ocr_result:
                # 优先使用pages格式，因为它包含字符级坐标信息
                if 'pages' in ocr_result['result']:
                    logger.info(f"使用Pages格式处理OCR结果（包含字符级坐标）")
                    for page_idx, page in enumerate(ocr_result['result']['pages']):
                        if 'content' in page:
                            logger.debug(f"处理第{page_idx+1}页，包含{len(page['content'])}个文本项")
                            
                            for item in page['content']:
                                if 'char_pos' in item and 'text' in item:
                                    # 检查文字是否在指定区域内 - 使用char_pos计算整体文本边界
                                    if not item['char_pos']:
                                        continue
                                    
                                    # 计算所有字符的边界框
                                    all_x = []
                                    all_y = []
                                    for char_coords in item['char_pos']:
                                        if len(char_coords) >= 8:
                                            all_x.extend([char_coords[i] for i in [0, 2, 4, 6]])
                                            all_y.extend([char_coords[i] for i in [1, 3, 5, 7]])
                                    
                                    if all_x and all_y:
                                        # 构造边界框坐标格式 [x1, y1, x2, y1, x2, y2, x1, y2]
                                        min_x, max_x = min(all_x), max(all_x)
                                        min_y, max_y = min(all_y), max(all_y)
                                        text_coords = [min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y]
                                        
                                        if self._is_text_in_region(text_coords, x1, y1, x2, y2):
                                            # 如果有字符级坐标，可以进行更精确的文本提取
                                            if 'char_pos' in item and item['char_pos']:
                                                char_text = self._extract_precise_text_with_char_coords(
                                                    item, x1, y1, x2, y2
                                                )
                                                if char_text:
                                                    region_text.append(char_text)
                                                    logger.info(f"✓ 字符级提取文本: '{char_text}'")
                                            else:
                                                region_text.append(item['text'])
                                                logger.info(f"✓ 直接提取文本: '{item['text']}'")
                
                # 如果没有pages格式，才使用detail格式（但这种格式缺少字符级坐标）
                elif 'detail' in ocr_result['result']:
                    logger.info(f"使用Detail格式处理OCR结果（缺少字符级坐标），detail数组长度: {len(ocr_result['result']['detail'])}")
                    logger.warning("注意：Detail格式不包含字符级坐标，可能影响精确度")
                    
                    found_texts = []
                    for idx, item in enumerate(ocr_result['result']['detail']):
                        if 'text' in item and 'position' in item:
                            # 检查文字是否在指定区域内
                            text_coords = item['position']
                            logger.debug(f"检查文本第{idx}项: '{item['text']}', 坐标: {text_coords}")
                            
                            if self._is_text_in_region_new_format(text_coords, x1, y1, x2, y2):
                                logger.info(f"✓ 找到区域内文本第{idx}项: '{item['text']}'")
                                region_text.append(item['text'])
                                found_texts.append(item['text'])
                            else:
                                logger.debug(f"✗ 文本第{idx}项不在区域内: '{item['text']}'")
                    
                    logger.info(f"区域内找到的所有文本: {found_texts}")
                else:
                    logger.warning(f"OCR结果中既没有pages也没有detail格式")
            else:
                logger.warning(f"OCR结果格式不认识: {list(ocr_result.keys()) if isinstance(ocr_result, dict) else 'not dict'}")
                return ""
            
            result_text = ' '.join(region_text)
            logger.debug(f"区域文本提取完成，总长度: {len(result_text)}")
            return result_text
            
        except Exception as e:
            logger.error(f"区域文字提取失败: {str(e)}")
            return ""
    
    def _extract_precise_text_with_char_coords(self, text_item, x1, y1, x2, y2):
        """使用字符级坐标进行精确文本提取
        
        Args:
            text_item: 包含字符级坐标的文本项
            x1, y1, x2, y2: 区域坐标
            
        Returns:
            str: 精确提取的文本
        """
        try:
            text = text_item['text']
            char_coords = text_item['char_pos']
            
            # 确保字符数和坐标数匹配
            min_length = min(len(text), len(char_coords))
            extracted_chars = []
            
            logger.debug(f"开始字符级精确提取: 文本='{text}', 区域=[{x1},{y1},{x2},{y2}]")
            
            for i in range(min_length):
                char_coord = char_coords[i]
                # 检查字符坐标是否在题目区域内
                if self._is_char_in_region(char_coord, x1, y1, x2, y2):
                    extracted_chars.append(text[i])
                    logger.debug(f"字符'{text[i]}'在区域内: {char_coord}")
            
            result = ''.join(extracted_chars)
            if result != text:
                logger.debug(f"字符级精确提取：原文本'{text}' -> 区域文本'{result}'")
            
            return result
            
        except Exception as e:
            logger.error(f"字符级文本提取失败: {str(e)}")
            return text_item.get('text', '')
    
    def _is_text_in_region(self, text_coords, x1, y1, x2, y2):
        """判断文字坐标是否在指定区域内
        
        Args:
            text_coords: 文字坐标数组
            x1, y1, x2, y2: 区域坐标
            
        Returns:
            bool: 是否在区域内
        """
        try:
            # text_coords格式: [x1, y1, x2, y1, x2, y2, x1, y2]
            if len(text_coords) >= 8:
                text_x1, text_y1 = text_coords[0], text_coords[1]
                text_x2, text_y2 = text_coords[4], text_coords[5]
                
                # 检查文字区域是否与题目区域有重叠
                return not (text_x2 < x1 or text_x1 > x2 or text_y2 < y1 or text_y1 > y2)
            
            return False
        except Exception as e:
            logger.error(f"判断文字坐标是否在区域内时出错: {str(e)}")
            return False
    
    def _is_char_in_region(self, char_coords, x1, y1, x2, y2):
        """判断单个字符坐标是否在指定区域内
        
        Args:
            char_coords: 单个字符的坐标数组 [x1, y1, x2, y1, x2, y2, x1, y2]
            x1, y1, x2, y2: 区域坐标
            
        Returns:
            bool: 是否在区域内
        """
        try:
            # char_coords格式: [x1, y1, x2, y1, x2, y2, x1, y2]
            if len(char_coords) >= 8:
                # 获取字符的边界坐标
                char_x1 = min(char_coords[0], char_coords[6])  # 左边界
                char_y1 = min(char_coords[1], char_coords[3])  # 上边界  
                char_x2 = max(char_coords[2], char_coords[4])  # 右边界
                char_y2 = max(char_coords[5], char_coords[7])  # 下边界
                
                # 判断字符中心点是否在题目区域内
                char_center_x = (char_x1 + char_x2) / 2
                char_center_y = (char_y1 + char_y2) / 2
                
                is_in_region = (x1 <= char_center_x <= x2 and y1 <= char_center_y <= y2)
                
                logger.debug(f"字符坐标检查: 字符边界[{char_x1:.1f},{char_y1:.1f},{char_x2:.1f},{char_y2:.1f}], 中心点({char_center_x:.1f},{char_center_y:.1f}), 区域[{x1},{y1},{x2},{y2}], 结果={is_in_region}")
                
                return is_in_region
            
            return False
            
        except Exception as e:
            logger.error(f"字符坐标检查失败: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"坐标判断失败: {str(e)}")
            return False
    
    def _is_text_in_region_new_format(self, position_coords, x1, y1, x2, y2):
        """判断新格式OCR文字坐标是否在指定区域内
        
        Args:
            position_coords: 新格式position坐标数组 [左上x, 左上y, 右上x, 右上y, 右下x, 右下y, 左下x, 左下y]
            x1, y1, x2, y2: 区域坐标(左上角和右下角)
            
        Returns:
            bool: 是否在区域内
        """
        try:
            # position格式: [左上x, 左上y, 右上x, 右上y, 右下x, 右下y, 左下x, 左下y]
            if len(position_coords) >= 8:
                text_x1 = position_coords[0]  # 左上角x
                text_y1 = position_coords[1]  # 左上角y
                text_x2 = position_coords[4]  # 右下角x
                text_y2 = position_coords[5]  # 右下角y
                
                logger.debug(f"坐标匹配检查:")
                logger.debug(f"  文本坐标: ({text_x1}, {text_y1}) 到 ({text_x2}, {text_y2})")
                logger.debug(f"  区域坐标: ({x1}, {y1}) 到 ({x2}, {y2})")
                logger.debug(f"  原始position: {position_coords}")
                
                # 检查文字区域是否与题目区域有重叠
                # 条件检查：text_x2 < x1(文本在区域左侧) or text_x1 > x2(文本在区域右侧) or text_y2 < y1(文本在区域上方) or text_y1 > y2(文本在区域下方)
                cond1 = text_x2 < x1  # 文本在区域左侧
                cond2 = text_x1 > x2  # 文本在区域右侧  
                cond3 = text_y2 < y1  # 文本在区域上方
                cond4 = text_y1 > y2  # 文本在区域下方
                
                overlap = not (cond1 or cond2 or cond3 or cond4)
                
                logger.debug(f"  重叠检查: 左侧={cond1}, 右侧={cond2}, 上方={cond3}, 下方={cond4}")
                logger.debug(f"  结果: {'重叠' if overlap else '不重叠'}")
                
                return overlap
            
            return False
            
        except Exception as e:
             logger.error(f"新格式坐标判断失败: {str(e)}")
             return False