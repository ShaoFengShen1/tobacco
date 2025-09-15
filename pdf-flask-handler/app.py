import os
import uuid
import logging
import shutil  # 新增：用于移动物理文件
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS
from datetime import datetime, timedelta  # 需确保导入 timedelta（用于时间偏移）
# --- Elasticsearch 配置（新增）---
from elasticsearch import Elasticsearch, exceptions as es_exceptions
import hashlib
import logging

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- CORS 配置 ---
CORS(app,
     origins=["http://localhost:5173", "http://localhost:3000"],
     expose_headers=["Content-Disposition", "Content-Type"],
     supports_credentials=True)

# 初始化带账号密码的 ES 客户端
try:
    es_client = Elasticsearch(
        hosts=["https://localhost:9200"],  # ES 服务地址+端口
        basic_auth=("elastic", "D_stvik=9QpSGSOpd2v0"),  # 替换为实际的用户名和密码
        verify_certs=False,  # 禁用证书验证（开发环境用，生产环境需配置证书）
        ssl_show_warn=False,  # 关闭SSL警告
    )

    # 验证连接（通过 ping 测试）
    if es_client.ping():
        logger.info("Elasticsearch 带账号密码连接成功！")
    else:
        logger.error("Elasticsearch ping 失败，服务可能未启动或认证失败")
except Exception as e:
    logger.error(f"Elasticsearch 连接异常: {str(e)}", exc_info=True)

# --- 数据库配置 ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root2333@localhost/file_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

# --- 上传配置 ---
UPLOAD_FOLDER = os.path.abspath('uploads')  # 使用绝对路径更可靠
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx','png', 'jpg', 'jpeg'}  # 匹配前端支持的文件类型

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

db = SQLAlchemy(app)


# --- 数据库模型 ---

class BaseFile(db.Model):
    __abstract__ = True
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.String(255), nullable=False, comment='文件名（含后缀）')
    file_path = db.Column(db.String(500), nullable=False, comment='文件物理路径')
    file_size = db.Column(db.Integer, nullable=True, comment='文件大小 (bytes)')  # 解决前端file_size字段报错问题
    upload_time = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8),
                            comment='上传时间（北京时间）')
    es_code = db.Column(db.String(255), nullable=True, comment='量化索引码')

    def to_dict(self):
        return {
            'id': self.id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'es_code': self.es_code
        }


class MaintenanceFile(BaseFile):
    __tablename__ = 'maintenance_files'


class ExperienceFile(BaseFile):
    __tablename__ = 'experience_files'


class OperationFile(BaseFile):
    __tablename__ = 'operation_files'


# --- 辅助函数 ---

LIBRARY_MODELS = {
    'maintenance': MaintenanceFile,
    'experience': ExperienceFile,
    'operation': OperationFile
}



# --- 新增：生成唯一索引码的工具函数 ---
def generate_es_code(file_content: bytes, file_id: str) -> str:
    import hashlib
    try:
        # 1. 计算文件内容+文件ID的MD5哈希（确保唯一性）
        combined_data = file_content + file_id.encode("utf-8")
        md5_hash = hashlib.md5(combined_data).hexdigest()  # 32位哈希值
        
        # 2. 在 ES 中创建索引（若不存在）
        es_index = "file_es_codes"  # ES 索引名（可自定义）
        if not es_client.indices.exists(index=es_index):
            es_client.indices.create(
                index=es_index,
                body={
                    "mappings": {
                        "properties": {
                            "es_code": {"type": "keyword"},  # 索引码（精确匹配）
                            "file_id": {"type": "keyword"},  # 文件ID
                            "create_time": {"type": "date", "format": "iso8601"}  # 创建时间
                        }
                    }
                }
            )
            logger.info(f"ES 索引 {es_index} 创建成功")
        
        # 3. 将索引码写入 ES（绑定文件ID，确保后续可追溯）
        es_client.index(
            index=es_index,
            id=md5_hash,  # 用索引码作为ES文档ID，避免重复
            body={
                "es_code": md5_hash,
                "file_id": file_id,
                "create_time": datetime.utcnow().isoformat() + "Z"  # ES 标准时间格式
            }
        )
        logger.info(f"文件 {file_id} 索引码生成成功: {md5_hash}")
        return md5_hash
    
    except es_exceptions.ElasticsearchException as e:
        logger.error(f"ES 操作失败（索引码生成终止）: {str(e)}", exc_info=True)
        raise  # 抛出异常，让上层判定为上传失败
    except Exception as e:
        logger.error(f"索引码生成异常: {str(e)}", exc_info=True)
        raise

def get_model_by_library_type(library_type):
    """根据库类型获取对应的数据库模型"""
    return LIBRARY_MODELS.get(library_type)


def allowed_file(filename):
    """验证文件后缀是否在允许列表内"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file, library_type):
    """保存文件到本地和数据库（新增索引码生成，失败则整体回滚）"""
    try:
        if not file or file.filename == '':
            return None, 'No file selected'
        if not allowed_file(file.filename):
            allowed_ext_str = ', '.join(ALLOWED_EXTENSIONS)
            return None, f'Only {allowed_ext_str} files are allowed'

        model = get_model_by_library_type(library_type)
        if not model:
            return None, f'Invalid library_type: {library_type}'

        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1]  # 保留原始后缀（如.pdf）
        unique_physical_name = f"{uuid.uuid4()}{file_extension}"  # 物理文件名（防重名）

        # 1. 准备存储路径
        library_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], library_type)
        os.makedirs(library_upload_folder, exist_ok=True)
        file_path = os.path.join(library_upload_folder, unique_physical_name)

        # 2. 生成文件唯一ID（先创建ID，用于索引码生成）
        file_id = str(uuid.uuid4())
        file_content = file.read()  # 读取为 bytes 类型
        file.seek(0)  # 重置指针，确保后续 file.save() 能正常保存完整文件

        # -------------------------- 核心修改：生成索引码（失败则终止）--------------------------
        es_code = generate_es_code(file_content, file_id)  # 调用新增的索引码生成函数
        # 若索引码生成失败，会直接抛出异常，不执行后续保存逻辑

        # 3. 获取文件大小
        file_size = len(file_content)  # 优化：直接使用已读取的内容长度

        # 4. 保存物理文件到本地
        file.save(file_path)

        # 5. 写入数据库（带es_code字段）
        db_file = model(
            id=file_id,  # 使用预先生成的ID（与索引码绑定）
            file_name=original_filename,  # 存储原始文件名（给用户看）
            file_path=file_path,  # 存储物理路径（服务器用）
            file_size=file_size,
            es_code=es_code  # 写入生成的索引码
        )
        db.session.add(db_file)
        db.session.flush()  # 暂不提交，批量上传统一处理

        logger.info(f"文件保存成功: {original_filename} -> {library_type}库, 索引码: {es_code}")
        return db_file, None

    # 捕获索引码生成失败/文件保存失败的异常
    except Exception as e:
        # 若已生成物理文件，删除残留
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
            logger.warning(f"删除残留文件: {file_path}")
        db.session.rollback()
        error_msg = f'Failed to save file: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return None, error_msg


# --- 路由 ---

@app.route('/upload/batch', methods=['POST'])
def upload_batch_pdfs():
    """批量上传文件接口（修改：索引码失败即判定为上传失败）"""
    try:
        files = request.files.getlist('files')
        library_type = request.form.get('library_type')

        # 参数校验
        if not library_type or library_type not in LIBRARY_MODELS:
            return jsonify({'status': 'error', 'message': 'Missing or invalid library_type.'}), 400
        if not files:
            return jsonify({'status': 'error', 'message': 'No files provided'}), 400

        success_count = 0
        failed_details = []
        success_files = []  # 存储成功的文件记录（用于后续返回）

        # 开启事务：批量上传要么部分成功，要么失败文件回滚（不影响成功文件）
        db.session.begin_nested()
        for file in files:
            saved_file, error = save_file(file, library_type)
            if error:
                # 索引码生成失败/文件保存失败，记录失败详情
                failed_details.append({
                    'filename': file.filename,
                    'error': error,
                    'reason': '索引码生成失败或文件保存异常'
                })
            else:
                success_count += 1
                success_files.append(saved_file.to_dict())  # 记录成功文件信息

        # 提交事务（仅成功的文件会保存到数据库）
        db.session.commit()

        # 返回结果（明确区分“索引码成功”的文件）
        return jsonify({
            'status': 'success',
            'message': 'Batch upload finished.',
            'data': {
                'success_count': success_count,
                'failed_count': len(failed_details),
                'failed_details': failed_details,
                'success_files': success_files  # 返回成功文件的完整信息（含es_code）
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"批量上传失败: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Batch upload failed: {str(e)}'}), 500

@app.route('/files', methods=['GET'])
def get_files():
    """获取文件列表（支持搜索、库类型过滤）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search_query = request.args.get('search')
        library_type = request.args.get('library_type')  # 按库类型过滤

        # 确定要查询的模型（全部库或指定库）
        target_models = LIBRARY_MODELS
        if library_type and library_type in LIBRARY_MODELS:
            target_models = {library_type: LIBRARY_MODELS[library_type]}

        # 构建各库的查询语句（统一字段名，方便union）
        queries = []
        for lib_name, model in target_models.items():
            query = db.session.query(
                model.id,
                model.file_name,
                model.file_size,  # 返回file_size（解决前端报错）
                model.upload_time.label('upload_time'),
                model.es_code,
                db.literal(lib_name).label('repository')  # 标记文件所属库
            )

            # 搜索过滤（文件名或量化索引码）
            if search_query:
                search_term = f"%{search_query}%"
                query = query.filter(db.or_(
                    model.file_name.ilike(search_term),  # 文件名模糊搜索（不区分大小写）
                    model.es_code.ilike(search_term)  # 量化索引码模糊搜索
                ))
            queries.append(query)

        # 合并查询结果（union_all 保留所有结果，不去重）
        if not queries:
            return jsonify({
                'status': 'success',
                'data': {
                    'files': [],
                    'pagination': {'page': page, 'pages': 0, 'per_page': per_page, 'total': 0}
                }
            }), 200

        # 合并查询并排序（按上传时间倒序）
        union_query = queries[0].union_all(*queries[1:]) if len(queries) > 1 else queries[0]
        ordered_query = union_query.order_by(db.desc(text('upload_time')))

        # 分页处理
        pagination = ordered_query.paginate(page=page, per_page=per_page, error_out=False)
        results = pagination.items

        # 格式化返回数据
        files_list = [
            {
                'id': r.id,
                'file_name': r.file_name,
                'file_size': r.file_size,
                'upload_time': r.upload_time.isoformat() if r.upload_time else None,
                'es_code': r.es_code,
                'repository': r.repository
            } for r in results
        ]

        return jsonify({
            'status': 'success',
            'data': {
                'files': files_list,
                'pagination': {
                    'page': page,
                    'pages': pagination.pages,
                    'per_page': per_page,
                    'total': pagination.total
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Failed to get files: {str(e)}'}), 500


@app.route('/files/<library_type>/<file_id>/preview', methods=['GET'])
def preview_file(library_type, file_id):
    """文件预览接口（返回文件流）"""
    model = get_model_by_library_type(library_type)
    if not model:
        return jsonify({'status': 'error', 'message': 'Invalid library type'}), 400

    # 查询文件记录
    file_record = model.query.get(file_id)
    if not file_record:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404

    try:
        # 验证文件是否存在
        if not os.path.exists(file_record.file_path):
            return jsonify({'status': 'error', 'message': 'File does not exist on server'}), 404

        # 提取目录和文件名（用于send_from_directory）
        directory = os.path.dirname(file_record.file_path)
        filename = os.path.basename(file_record.file_path)

        # 返回文件流（前端通过iframe预览）
        return send_from_directory(
            directory,
            filename,
            mimetype=None  # 自动识别MIME类型（适配多种文件格式）
        )

    except Exception as e:
        logger.error(f"预览文件失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Could not access file'}), 500


@app.route('/files/<library_type>/<file_id>/download', methods=['GET'])
def download_file(library_type, file_id):
    """文件下载接口（带中文文件名支持）"""
    model = get_model_by_library_type(library_type)
    if not model:
        return jsonify({'status': 'error', 'message': 'Invalid library type'}), 400

    file_record = model.query.get(file_id)
    if not file_record:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404

    try:
        # 验证文件存在性
        if not os.path.exists(file_record.file_path):
            return jsonify({'status': 'error', 'message': 'File does not exist on server'}), 404

        # 提取目录和物理文件名
        directory = os.path.dirname(file_record.file_path)
        physical_filename = os.path.basename(file_record.file_path)

        # 处理中文文件名（RFC 5987编码，避免乱码）
        from urllib.parse import quote
        safe_filename = quote(file_record.file_name)  # 对原始文件名编码

        # 构造下载响应
        response = send_from_directory(
            directory,
            physical_filename,
            as_attachment=True,  # 强制下载（而非预览）
            download_name=file_record.file_name,  # 显示给用户的文件名
            mimetype=None  # 自动识别文件类型
        )

        # 修复中文文件名下载问题
        response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{safe_filename}"
        # 跨域相关头
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Type'

        logger.info(f"文件下载成功: {file_record.file_name}")
        return response

    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Could not download file',
            'error': str(e)
        }), 500


@app.route('/files/<library_type>/<file_id>', methods=['PUT'])
def update_file(library_type, file_id):
    """更新文件信息（修改：禁止修改es_code，确保索引码绑定不变）"""
    db.session.begin_nested()
    try:
        # 1. 基础校验（原有逻辑保留）
        old_model = get_model_by_library_type(library_type)
        if not old_model:
            return jsonify({'status': 'error', 'message': f'Invalid old library_type: {library_type}'}), 400
        old_file = old_model.query.get(file_id)
        if not old_file:
            return jsonify({'status': 'error', 'message': 'File not found in old library'}), 404
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No update data provided'}), 400

        # -------------------------- 新增：禁止修改es_code --------------------------
        if 'es_code' in data and data['es_code'] != old_file.es_code:
            raise ValueError("量化索引码（es_code）一旦生成不可修改，禁止提交es_code字段")

        # 2. 所属库迁移/文件名修改（原有逻辑保留，不改动）
        new_library_type = data.get('repository')
        file_moved = False
        new_file = None

        if new_library_type and new_library_type != library_type:
            new_model = get_model_by_library_type(new_library_type)
            if not new_model:
                raise ValueError(f'Invalid new library_type: {new_library_type}')
            # 物理文件迁移（原有逻辑）
            old_file_path = old_file.file_path
            new_library_dir = os.path.join(app.config['UPLOAD_FOLDER'], new_library_type)
            os.makedirs(new_library_dir, exist_ok=True)
            new_file_name = os.path.basename(old_file_path)
            new_file_path = os.path.join(new_library_dir, new_file_name)
            if os.path.exists(new_file_path):
                os.remove(new_file_path)
            shutil.move(old_file_path, new_file_path)
            file_moved = True
            # 数据库记录迁移（原有逻辑，保留es_code）
            new_file = new_model(
                file_name=old_file.file_name,
                file_path=new_file_path,
                file_size=old_file.file_size,
                upload_time=old_file.upload_time,
                es_code=old_file.es_code  # 迁移时保留原索引码
            )
            db.session.add(new_file)
            db.session.delete(old_file)

        # 3. 文件名修改（原有逻辑保留）
        if 'file_name' in data:
            new_filename = data['file_name'].strip()
            if not new_filename:
                raise ValueError('File name cannot be empty')
            if any(char in new_filename for char in ['\\', '/', ':', '*', '?', '"', '<', '>']):
                raise ValueError('File name contains invalid characters (\\ / : * ? " < >)')
            target_file = new_file if new_file else old_file
            target_file.file_name = new_filename

        # 4. 提交事务
        db.session.commit()
        result_file = new_file if new_file else old_file
        response_data = result_file.to_dict()
        response_data['repository'] = new_library_type if new_library_type else library_type

        return jsonify({
            'status': 'success',
            'message': 'File updated successfully (es_code is immutable)',
            'data': response_data
        }), 200

    except ValueError as ve:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        if file_moved and 'new_file_path' in locals() and os.path.exists(new_file_path):
            os.remove(new_file_path)
            logger.warning(f"回滚：删除残留迁移文件: {new_file_path}")
        logger.error(f"文件更新失败: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Failed to update file: {str(e)}'}), 500

@app.route('/files/<library_type>/<file_id>', methods=['DELETE'])
def delete_file(library_type, file_id):
    """删除文件（同时删除数据库记录和本地物理文件）"""
    try:
        model = get_model_by_library_type(library_type)
        if not model:
            return jsonify({'status': 'error', 'message': f'Invalid library_type: {library_type}'}), 400

        file_record = model.query.get(file_id)
        if not file_record:
            return jsonify({'status': 'error', 'message': 'File not found'}), 404

        # 1. 先删除本地物理文件（避免数据库记录删除后文件残留）
        physical_file_path = file_record.file_path
        if os.path.exists(physical_file_path):
            os.remove(physical_file_path)
            logger.info(f"本地物理文件删除成功: {physical_file_path}")
        else:
            logger.warning(f"本地物理文件不存在，跳过删除: {physical_file_path}")

        # 2. 再删除数据库记录
        db.session.delete(file_record)
        db.session.commit()
        logger.info(f"数据库文件记录删除成功: {file_id}（{file_record.file_name}）")

        return jsonify({'status': 'success', 'message': 'File deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"删除文件失败: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Failed to delete file: {str(e)}'}), 500


# --- 应用启动入口（确保最后执行）---
if __name__ == '__main__':
    # 1. 确保上传目录及各库子目录存在（避免首次上传时报错）
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    for lib_type in LIBRARY_MODELS.keys():
        lib_upload_dir = os.path.join(UPLOAD_FOLDER, lib_type)
        os.makedirs(lib_upload_dir, exist_ok=True)
        logger.info(f"初始化上传目录: {lib_upload_dir}")

    # 2. 同步数据库模型（创建新增字段或表，需确保数据库连接正常）
    with app.app_context():
        # 注意：如果是首次运行或模型有变更，会自动创建/更新表结构
        # 生产环境建议使用迁移工具（如Flask-Migrate），避免直接drop_all()
        db.create_all()
        logger.info("数据库模型同步完成（新增字段已创建）")

    # 3. 启动服务（0.0.0.0 允许局域网访问，端口8001与前端配置一致）
    logger.info("=" * 50)
    logger.info("Flask File Management Service 启动成功")
    logger.info(f"服务地址: http://0.0.0.0:8001")
    logger.info(f"允许上传文件类型: {', '.join(ALLOWED_EXTENSIONS)}")
    logger.info(f"最大文件大小: {MAX_FILE_SIZE // (1024*1024)} MB")
    logger.info("=" * 50)
    app.run(host='0.0.0.0', port=8001, debug=True)  # 生产环境需关闭debug