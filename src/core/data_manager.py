"""
数据管理器
处理用户绑定数据的存储和查询
"""

import json
import os
import shutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from loguru import logger


class DataManager:
    """数据管理器"""
    
    def __init__(self, data_file: str, backup_enabled: bool = True, 
                 backup_interval: int = 86400, config_dir: Optional[str] = None):
        """
        初始化数据管理器
        
        Args:
            data_file: 数据文件路径
            backup_enabled: 是否启用自动备份
            backup_interval: 备份间隔（秒）
        """
        self.data_file = Path(data_file)
        self.backup_enabled = backup_enabled
        self.backup_interval = backup_interval
        self.last_backup_time = 0
        self.config_dir = Path(config_dir) if config_dir else None
        
        # 确保数据目录存在
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 确保配置目录存在
        if self.config_dir:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据结构
        self.data = self._load_data()
        
        logger.info(f"数据管理器初始化完成: {self.data_file}")
    
    def _load_data(self) -> Dict:
        """
        加载数据文件
        
        Returns:
            数据字典
        """
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"数据加载成功，共 {len(data.get('bindings', {}))} 条绑定记录")
                return data
            else:
                # 创建新的数据文件
                default_data = {
                    'bindings': {},  # QQ号到VRChat用户ID的映射
                    'vrc_to_qq': {},  # VRChat用户ID到QQ号的反向映射
                    'metadata': {
                        'version': '1.0',
                        'created_at': datetime.now().isoformat(),
                        'total_bindings': 0
                    }
                }
                self._save_data(default_data)
                logger.info("创建新的数据文件")
                return default_data
                
        except Exception as e:
            logger.exception(f"数据加载失败: {e}")
            # 创建备份并初始化新数据
            self._create_backup(is_error=True)
            return self._load_data()
    
    def _save_data(self, data: Optional[Dict] = None) -> bool:
        """
        保存数据到文件
        
        Args:
            data: 要保存的数据（默认使用self.data）
            
        Returns:
            bool: 保存成功返回True
        """
        try:
            if data is None:
                data = self.data
            
            # 更新元数据
            data['metadata']['last_updated'] = datetime.now().isoformat()
            data['metadata']['total_bindings'] = len(data.get('bindings', {}))
            
            # 写入临时文件后重命名，确保数据完整性
            temp_file = self.data_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 原子操作：重命名临时文件
            temp_file.replace(self.data_file)
            
            # 自动备份
            if self.backup_enabled:
                current_time = time.time()
                if current_time - self.last_backup_time > self.backup_interval:
                    self._create_backup()
                    self.last_backup_time = current_time
            
            return True
            
        except Exception as e:
            logger.exception(f"数据保存失败: {e}")
            return False
    
    def _create_backup(self, is_error: bool = False):
        """
        创建数据备份
        
        Args:
            is_error: 是否因为错误而创建备份
        """
        try:
            backup_dir = self.data_file.parent / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"backup_{timestamp}.json"
            
            if is_error:
                backup_file = backup_dir / f"error_backup_{timestamp}.json"
            
            shutil.copy2(self.data_file, backup_file)
            
            # 清理旧备份（保留最近30天的）
            self._cleanup_old_backups(backup_dir, days=30)
            
            logger.info(f"数据备份创建成功: {backup_file}")
            
        except Exception as e:
            logger.exception(f"创建备份失败: {e}")
    
    def _cleanup_old_backups(self, backup_dir: Path, days: int = 30):
        """
        清理旧备份文件
        
        Args:
            backup_dir: 备份目录
            days: 保留天数
        """
        try:
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            for backup_file in backup_dir.glob('backup_*.json'):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    logger.debug(f"删除旧备份: {backup_file}")
                    
        except Exception as e:
            logger.exception(f"清理旧备份失败: {e}")
    
    def bind_user(self, qq_id: int, vrc_user_id: str, 
                  vrc_username: str, operator_qq: Optional[int] = None) -> bool:
        """
        绑定QQ用户和VRChat用户
        
        Args:
            qq_id: QQ号
            vrc_user_id: VRChat用户ID
            vrc_username: VRChat用户名
            operator_qq: 操作者QQ号（可选）
            
        Returns:
            bool: 绑定成功返回True
        """
        try:
            qq_id_str = str(qq_id)
            vrc_user_id_lower = vrc_user_id.lower()
            
            # 检查是否已绑定
            if qq_id_str in self.data['bindings']:
                logger.warning(f"QQ用户 {qq_id} 已绑定到VRChat用户")
                return False
            
            # 检查VRChat用户是否已被绑定
            if vrc_user_id_lower in self.data['vrc_to_qq']:
                existing_qq = self.data['vrc_to_qq'][vrc_user_id_lower]
                logger.warning(f"VRChat用户 {vrc_user_id} 已绑定到QQ {existing_qq}")
                return False
            
            # 创建绑定记录
            binding_info = {
                'qq_id': qq_id,
                'vrc_user_id': vrc_user_id,
                'vrc_username': vrc_username,
                'created_at': datetime.now().isoformat(),
                'operator_qq': operator_qq
            }
            
            # 更新数据
            self.data['bindings'][qq_id_str] = binding_info
            self.data['vrc_to_qq'][vrc_user_id_lower] = qq_id
            
            # 保存数据
            if self._save_data():
                logger.success(f"用户绑定成功: QQ {qq_id} -> VRC {vrc_username} ({vrc_user_id})")
                return True
            else:
                return False
                
        except Exception as e:
            logger.exception(f"用户绑定失败: {e}")
            return False
    
    def unbind_user(self, qq_id: int, operator_qq: Optional[int] = None) -> bool:
        """
        解绑QQ用户
        
        Args:
            qq_id: QQ号
            operator_qq: 操作者QQ号（可选）
            
        Returns:
            bool: 解绑成功返回True
        """
        try:
            qq_id_str = str(qq_id)
            
            if qq_id_str not in self.data['bindings']:
                logger.warning(f"QQ用户 {qq_id} 未绑定")
                return False
            
            # 获取绑定信息
            binding_info = self.data['bindings'][qq_id_str]
            vrc_user_id = binding_info['vrc_user_id'].lower()
            
            # 删除绑定
            del self.data['bindings'][qq_id_str]
            
            # 删除反向映射
            if vrc_user_id in self.data['vrc_to_qq']:
                del self.data['vrc_to_qq'][vrc_user_id]
            
            # 保存数据
            if self._save_data():
                logger.success(f"用户解绑成功: QQ {qq_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.exception(f"用户解绑失败: {e}")
            return False
    
    def get_binding_by_qq(self, qq_id: int) -> Optional[Dict]:
        """
        通过QQ号获取绑定信息
        
        Args:
            qq_id: QQ号
            
        Returns:
            绑定信息字典或None
        """
        try:
            qq_id_str = str(qq_id)
            return self.data['bindings'].get(qq_id_str)
            
        except Exception as e:
            logger.exception(f"获取绑定信息失败: {e}")
            return None
    
    def get_binding_by_vrc(self, vrc_user_id: str) -> Optional[Dict]:
        """
        通过VRChat用户ID获取绑定信息
        
        Args:
            vrc_user_id: VRChat用户ID
            
        Returns:
            绑定信息字典或None
        """
        try:
            vrc_user_id_lower = vrc_user_id.lower()
            qq_id = self.data['vrc_to_qq'].get(vrc_user_id_lower)
            
            if qq_id:
                return self.get_binding_by_qq(qq_id)
            else:
                return None
                
        except Exception as e:
            logger.exception(f"获取绑定信息失败: {e}")
            return None
    
    def get_all_bindings(self) -> List[Dict]:
        """
        获取所有绑定信息
        
        Returns:
            绑定信息列表
        """
        try:
            return list(self.data['bindings'].values())
            
        except Exception as e:
            logger.exception(f"获取所有绑定信息失败: {e}")
            return []
    
    def search_bindings(self, keyword: str) -> List[Dict]:
        """
        搜索绑定信息
        
        Args:
            keyword: 搜索关键词（QQ号或VRChat用户名）
            
        Returns:
            匹配的绑定信息列表
        """
        try:
            results = []
            keyword_lower = keyword.lower()
            
            for binding in self.data['bindings'].values():
                # 搜索QQ号
                if keyword in str(binding['qq_id']):
                    results.append(binding)
                # 搜索VRChat用户名
                elif keyword_lower in binding['vrc_username'].lower():
                    results.append(binding)
            
            return results
            
        except Exception as e:
            logger.exception(f"搜索绑定信息失败: {e}")
            return []
    
    def is_admin(self, group_id: int, user_id: int, admin_list: List[int]) -> bool:
        """
        检查用户是否是管理员
        
        Args:
            group_id: 群号
            user_id: 用户QQ号
            admin_list: 管理员列表
            
        Returns:
            bool: 是管理员返回True
        """
        return user_id in admin_list
    
    def get_statistics(self) -> Dict:
        """
        获取统计数据
        
        Returns:
            统计数据字典
        """
        try:
            bindings = self.data['bindings']
            
            # 计算绑定时间分布
            time_distribution = {}
            for binding in bindings.values():
                created_at = datetime.fromisoformat(binding['created_at'])
                date_key = created_at.strftime('%Y-%m-%d')
                time_distribution[date_key] = time_distribution.get(date_key, 0) + 1
            
            return {
                'total_bindings': len(bindings),
                'time_distribution': time_distribution,
                'last_updated': self.data['metadata'].get('last_updated'),
                'created_at': self.data['metadata'].get('created_at')
            }
            
        except Exception as e:
            logger.exception(f"获取统计数据失败: {e}")
            return {}
    
    def export_data(self, format_type: str = 'json') -> str:
        """
        导出数据
        
        Args:
            format_type: 导出格式
            
        Returns:
            导出文件路径
        """
        try:
            export_dir = self.data_file.parent / 'exports'
            export_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_file = export_dir / f"export_{timestamp}.json"
            
            if format_type == 'json':
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据导出成功: {export_file}")
            return str(export_file)
            
        except Exception as e:
            logger.exception(f"数据导出失败: {e}")
            return ""
    
    def close(self):
        """关闭数据管理器"""
        # 创建最终备份
        if self.backup_enabled:
            self._create_backup()
        
        logger.info("数据管理器已关闭")