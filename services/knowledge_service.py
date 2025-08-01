import requests
import json
import requests
from config import Config
import logging
import time
from .obs_service import OBSService

logger = logging.getLogger(__name__)

class KnowledgeService:
    """知识库检索服务"""
    
    def __init__(self):
        self.base_url = Config.KNOWLEDGE_API_URL
        self.api_token = Config.KNOWLEDGE_API_TOKEN
        self.dataset_id = Config.KNOWLEDGE_DATASET_ID
        self.tenant_id = Config.KNOWLEDGE_TENANT_ID
        self.timeout = Config.REQUEST_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        self.retry_delay = Config.RETRY_DELAY
        self.obs_service = OBSService()
        
        # 构建数据集检索API的完整URL
        self.api_url = f"{self.base_url}/v1/datasets/{self.dataset_id}/retrieve"
    
    def search_similar_question(self, query_text, image_path=None):
        """在知识库中搜索相似题目
        
        Args:
            query_text: 查询文本
            image_path: 题目图片路径（可选）
            
        Returns:
            dict: 包含搜索结果的字典
        """
        try:
            logger.info(f"开始dify数据库检索，查询文本: {query_text[:100]}...")
            
            if not query_text or not query_text.strip():
                logger.warning("查询文本为空，跳过知识库检索")
                return {
                    'success': False,
                    'error': '查询文本为空',
                    'query': query_text
                }
            
            # 检查查询文本长度限制
            if len(query_text.strip()) > 250:
                logger.warning(f"查询文本超过250字符限制，当前长度: {len(query_text.strip())}")
                query_text = query_text.strip()[:250]
                logger.info(f"截取查询文本至250字符: {query_text}...")
            
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            # 构建dify数据库检索API请求载荷
            payload = {
                "query": query_text,
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
                            "vector_weight": 0.1,
                            "embedding_provider_name": "",
                            "embedding_model_name": ""
                        },
                        "keyword_setting": {
                            "keyword_weight": 0.9
                        }
                    },
                    "top_k": 5,
                    "score_threshold_enabled": True,
                    "score_threshold": 0.6
                }
            }
            
            # 如果有图片，暂时忽略图片检索功能
            if image_path:
                logger.warning("当前dify数据库检索API版本不支持图片检索，仅使用文本检索")
            
            logger.debug(f"知识库请求头: {headers}")
            logger.debug(f"知识库API URL: {self.api_url}")
            logger.debug(f"检索查询: {query_text}")
            logger.debug(f"知识库请求载荷: {json.dumps(payload, ensure_ascii=False)}")
            logger.info(f"使用数据集ID: {self.dataset_id} 进行检索")
            
            # 进行重试请求
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"调用知识库检索API，尝试次数: {attempt + 1}/{self.max_retries}")
                    start_time = time.time()
                    
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=(Config.KNOWLEDGE_CONNECT_TIMEOUT, Config.KNOWLEDGE_READ_TIMEOUT)
                    )
                    
                    end_time = time.time()
                    logger.info(f"知识库API响应时间: {end_time - start_time:.2f}秒")
                    
                    logger.info(f"知识库API响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            logger.debug(f"知识库API原始响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        except json.JSONDecodeError as e:
                            logger.error(f"知识库响应JSON解析失败: {str(e)}")
                            logger.error(f"响应内容: {response.text[:500]}...")
                            return {
                                'success': False,
                                'error': '知识库响应格式错误',
                                'query': query_text
                            }
                        
                        logger.info("知识库检索成功")
                        
                        # 解析搜索结果
                        logger.info(f"知识库检索完成原始数据，{result}")
                        parsed_result = self._parse_search_result(result, query_text)
                        logger.info(f"知识库检索完成，{parsed_result}")
                        logger.info(f"知识库检索完成，找到{len(parsed_result.get('all_results', []))}个结果")
                        logger.info(f"最佳匹配相似度: {parsed_result.get('similarity_score', 0.0)}")
                        
                        return {
                            'success': True,
                            'query': query_text,
                            'reference_answer': parsed_result.get('reference_answer', ''),
                            'question_image_url': parsed_result.get('question_image_url', ''),
                            'answer_image_url': parsed_result.get('answer_image_url', ''),
                            'question_text': parsed_result.get('question_text', ''),
                            'answer_text': parsed_result.get('answer_text', ''),
                            'similarity_score': parsed_result.get('similarity_score', 0.0),
                            'source_document': parsed_result.get('source_document', ''),
                            'all_results': parsed_result.get('all_results', []),
                            'raw_result': result
                        }
                    else:
                        logger.error(f"知识库API调用失败，状态码: {response.status_code}")
                        logger.error(f"响应内容: {response.text[:500]}...")
                        
                        if attempt < self.max_retries - 1:
                            logger.info(f"等待{self.retry_delay}秒后重试...")
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f'知识库API调用失败，状态码: {response.status_code}',
                                'query': query_text
                            }
                            
                except requests.exceptions.RequestException as e:
                    logger.error(f"知识库请求异常: {str(e)}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {
                            'success': False,
                            'error': f'知识库网络请求失败: {str(e)}',
                            'query': query_text
                        }
                        
        except Exception as e:
            logger.error(f"知识库检索处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query_text
            }
    
    def _parse_search_result(self, api_result, query_text):
        """解析知识库搜索结果
        
        Args:
            api_result: API返回的原始结果
            query_text: 原始查询文本
            
        Returns:
            dict: 解析后的结果
        """
        parsed_result = {
            'reference_answer': '',
            'similarity_score': 0.0,
            'source_document': '',
            'all_results': []
        }
        
        try:
            logger.info(f"开始解析dify数据库检索API返回结果...")
            logger.debug(f"API返回结构: {json.dumps(api_result, ensure_ascii=False, indent=2) if isinstance(api_result, dict) else str(api_result)}")
            
            # 解析Dify数据库检索API格式
            if isinstance(api_result, dict) and 'records' in api_result:
                records = api_result['records']
                
                # 检查是否为列表格式的检索结果
                if isinstance(records, list):
                    results = records
                    parsed_result['all_results'] = results
                    
                    if results and len(results) > 0:
                        best_result = results[0]
                        parsed_result['similarity_score'] = best_result.get('score', 0.0)
                        
                        # 提取segment中的详细信息
                        segment = best_result.get('segment', {})
                        content = segment.get('content', '')
                        
                        # 调试：打印原始content内容
                        logger.debug(f"原始segment content: {content[:500]}...")
                        
                        # 使用正则表达式解析题目信息
                        import re
                        
                        # 提取题目图片地址
                        question_image_match = re.search(r'"题目图片地址":"([^"]+)"', content)
                        raw_question_url = question_image_match.group(1) if question_image_match else ''
                        # 清理可能的markdown格式符号
                        parsed_result['question_image_url'] = raw_question_url.strip('`').strip()
                        
                        # 提取答案图片地址
                        answer_image_match = re.search(r'"答案图片地址":"([^"]+)"', content)
                        raw_answer_url = answer_image_match.group(1) if answer_image_match else ''
                        # 清理可能的markdown格式符号
                        parsed_result['answer_image_url'] = raw_answer_url.strip('`').strip()
                        
                        # 提取题目文本
                        question_text_match = re.search(r'"题目文本":"([^"]+(?:"[^"]*"[^"]*)*?)"(?=;")', content)
                        if question_text_match:
                            question_text = question_text_match.group(1).replace('\n', '\n').replace('\\n', '\n')
                            parsed_result['question_text'] = question_text
                        else:
                            parsed_result['question_text'] = ''
                        
                        # 提取答案文本
                        answer_text_match = re.search(r'"答案文本":"(.*?)"(?=;"|$)', content, re.DOTALL)
                        if answer_text_match:
                            answer_text = answer_text_match.group(1).replace('\n', '\n').replace('\\n', '\n')
                            parsed_result['answer_text'] = answer_text
                        else:
                            parsed_result['answer_text'] = ''
                        
                        # 保留原始内容用于兼容
                        parsed_result['reference_answer'] = content
                        parsed_result['source_document'] = best_result.get('source', '')
                        
                        logger.info(f"从dify数据库检索API解析，找到{len(results)}个结果")
                        logger.info(f"成功提取题目信息 - 题目文本长度: {len(parsed_result['question_text'])}, 答案文本长度: {len(parsed_result['answer_text'])}")
                        logger.info(f"题目图片URL: {parsed_result['question_image_url']}")
                        logger.info(f"答案图片URL: {parsed_result['answer_image_url']}")
                    else:
                        logger.warning("dify数据库检索API返回空结果")
                
                
                else:
                    logger.warning("API返回格式不符合预期")
            
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"搜索结果解析失败: {str(e)}")
            return parsed_result
    
    def batch_search(self, queries):
        """批量搜索题目
        
        Args:
            queries: 查询文本列表
            
        Returns:
            list: 搜索结果列表
        """
        logger.info(f"开始批量检索，共{len(queries)}个查询")
        results = []
        success_count = 0
        
        for i, query in enumerate(queries):
            logger.info(f"批量搜索第{i+1}/{len(queries)}个题目: {query[:50]}...")
            result = self.search_similar_question(query)
            results.append(result)
            
            if result.get('success'):
                success_count += 1
            
            # 避免请求过于频繁
            if i < len(queries) - 1:
                time.sleep(0.5)
        
        logger.info(f"批量检索完成，成功: {success_count}/{len(queries)}")
        return results
    
    def get_knowledge_base_info(self):
        """获取知识库基本信息（如果API支持）
        
        Returns:
            dict: 知识库信息
        """
        try:
            # 这里可以实现获取知识库信息的逻辑
            # 具体实现取决于Dify平台是否提供相关API
            return {
                'success': True,
                'info': '知识库信息查询功能待实现'
            }
            
        except Exception as e:
            logger.error(f"获取知识库信息失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_api_connection(self):
        """验证API连接是否正常
        
        Returns:
            bool: 连接是否正常
        """
        try:
            test_result = self.search_similar_question("测试查询")
            return test_result.get('success', False)
            
        except Exception as e:
            logger.error(f"API连接验证失败: {str(e)}")
            return False