import os
import tempfile
import requests
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class OBSService:
    """对象存储服务，用于处理图片上传"""
    
    def __init__(self):
        # OBS上传API配置
        self.upload_url = "https://adviser.raysgo.com/raysserve/v1.0/readArticle/obsUpload"
        self.upload_token = "y2BWwpIZtc9YFUvdUqOheKp4CR8w9l1d"
        self.timeout = 30
        
    def is_remote_url(self, path):
        """判断是否为远程URL
        
        Args:
            path: 文件路径或URL
            
        Returns:
            bool: 是否为远程URL
        """
        try:
            result = urlparse(path)
            return bool(result.netloc) and result.scheme in ['http', 'https']
        except Exception:
            return False
    
    def is_local_file(self, path):
        """判断是否为本地文件
        
        Args:
            path: 文件路径
            
        Returns:
            bool: 是否为本地文件且存在
        """
        try:
            return os.path.isfile(path)
        except Exception:
            return False
    
    def upload_file(self, file_path):
        """将文件上传到对象存储
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            dict: 包含上传结果的字典
        """
        return self.upload_file_to_obs(file_path)
    
    def upload_file_to_obs(self, file_path):
        """将文件上传到对象存储
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            dict: 包含上传结果的字典
        """
        try:
            logger.info(f"开始上传文件到OBS: {file_path}")
            
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'文件不存在: {file_path}'
                }
            
            with open(file_path, 'rb') as file:
                files = {'file': file}
                headers = {
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'User-Agent': 'PostmanRuntime-ApipostRuntime/1.1.0',
                    'token': self.upload_token
                }
                
                response = requests.post(
                    self.upload_url,
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.info(f"OBS上传响应状态码: {response.status_code}")
                logger.info(f"OBS上传响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        logger.info(f"文件上传成功: {result}")
                        # 根据实际API返回格式调整
                        obs_url = result.get('data', {}).get('url') or result.get('url', '')
                        return {
                            'success': True,
                            'url': obs_url,
                            'message': result.get('message', 'Upload successful')
                        }
                    except ValueError as e:
                        logger.error(f"解析上传响应JSON失败: {e}")
                        # 如果返回的不是JSON，可能直接是URL
                        return {
                            'success': True,
                            'url': response.text.strip(),
                            'message': 'Upload successful'
                        }
                else:
                    logger.error(f"文件上传失败，状态码: {response.status_code}, 响应: {response.text}")
                    return {
                        'success': False,
                        'error': f'HTTP {response.status_code}: {response.text}'
                    }
                    
        except Exception as e:
            logger.error(f"文件上传异常: {str(e)}")
            return {
                'success': False,
                'error': f'Upload exception: {str(e)}'
            }
    
    def process_image_path(self, image_path):
        """处理图片路径，如果是URL则上传到OBS，本地文件保持不变
        
        Args:
            image_path: 图片路径或URL
            
        Returns:
            dict: 处理结果包含最终可用的URL或路径
        """
        try:
            if not image_path:
                return {
                    'success': False,
                    'error': '图片路径为空'
                }
            
            logger.info(f"处理图片路径: {image_path}")
            
            # 如果是远程URL，需要先下载然后上传到OBS
            if self.is_remote_url(image_path):
                logger.info(f"检测到远程URL，需要重新上传到OBS: {image_path}")
                
                # 下载远程图片
                download_result = self.download_remote_image(image_path)
                if not download_result['success']:
                    return {
                        'success': False,
                        'error': f'下载远程图片失败: {download_result.get("error", "未知错误")}'
                    }
                
                # 上传到OBS
                upload_result = self.upload_file_to_obs(download_result['local_path'])
                
                # 清理临时文件
                try:
                    os.unlink(download_result['local_path'])
                    logger.debug(f"已清理临时文件: {download_result['local_path']}")
                except Exception as cleanup_error:
                    logger.warning(f"清理临时文件失败: {cleanup_error}")
                
                if upload_result['success']:
                    return {
                        'success': True,
                        'url': upload_result['url'],
                        'is_local': False,
                        'original_path': image_path
                    }
                else:
                    return {
                        'success': False,
                        'error': f'上传到OBS失败: {upload_result.get("error", "未知错误")}'
                    }
            
            else:
                # 本地文件，需要上传到OBS
                logger.info(f"检测到本地文件，需要上传到OBS: {image_path}")
                if not os.path.exists(image_path):
                    return {
                        'success': False,
                        'error': f'本地文件不存在: {image_path}'
                    }
                
                # 上传本地文件到OBS
                upload_result = self.upload_file_to_obs(image_path)
                if upload_result['success']:
                    return {
                        'success': True,
                        'url': upload_result['url'],
                        'is_local': False,
                        'original_path': image_path
                    }
                else:
                    return {
                        'success': False,
                        'error': f'上传本地文件到OBS失败: {upload_result.get("error", "未知错误")}'
                    }
                
        except Exception as e:
            error_msg = f"处理图片路径异常: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def download_remote_image(self, url):
        """下载远程图片到本地临时文件
        
        Args:
            url: 图片URL
            
        Returns:
            dict: 包含本地文件路径的字典
        """
        try:
            logger.info(f"开始下载远程图片: {url}")
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_path = temp_file.name
            temp_file.close()
            
            # 下载文件
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"远程图片下载成功: {temp_path}")
                
                return {
                    'success': True,
                    'local_path': temp_path
                }
            else:
                logger.error(f"下载失败，状态码: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                }
            
        except Exception as e:
            logger.error(f"远程图片下载失败: {str(e)}")
            return {
                'success': False,
                'error': f'Download failed: {str(e)}'
            }