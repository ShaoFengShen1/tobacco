from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import uuid
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS配置 - 允许前端跨域访问
CORS(app, origins=["http://localhost:5173", "http://localhost:3000"])

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root123@localhost/file_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

# 上传配置
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

db = SQLAlchemy(app)


# 定义files表模型 (根据你的数据库结构)
class Files(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.String(255), nullable=False, comment='文件名')
    file_path = db.Column(db.String(500), nullable=False, comment='文件路径')
    upload_time = db.Column(db.DateTime, default=datetime.utcnow, comment='上传时间')
    es_code = db.Column(db.String(255), nullable=True, comment='ES代码')

    def to_dict(self):
        return {
            'id': self.id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'es_code': self.es_code
        }


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file):
    """保存单个文件"""
    try:
        if not file or file.filename == '':
            return None, 'No file selected'

        if not allowed_file(file.filename):
            return None, 'Only PDF files are allowed'

        # 生成唯一文件名
        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        # 保存文件
        file.save(file_path)

        # 保存到数据库
        pdf_file = Files(
            file_name=original_filename,
            file_path=file_path
        )
        db.session.add(pdf_file)
        db.session.flush()  # 获取生成的ID

        logger.info(f"文件保存成功: {original_filename}")
        return pdf_file, None

    except Exception as e:
        logger.error(f"保存文件失败: {str(e)}")
        return None, f'Failed to save file: {str(e)}'


# 创建数据库表
def create_tables():
    """创建数据库表"""
    try:
        db.create_all()
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")


# 单个文件上传路由
@app.route('/upload', methods=['POST'])
def upload_pdf():
    """单个PDF文件上传"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file part in request'
            }), 400

        file = request.files['file']

        # 保存文件
        saved_file, error = save_file(file)
        if error:
            return jsonify({
                'status': 'error',
                'message': error
            }), 400

        # 提交数据库事务
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': f'File {saved_file.file_name} uploaded successfully',
            'data': saved_file.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"文件上传失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500


# 批量文件上传路由
@app.route('/upload/batch', methods=['POST'])
def upload_batch_pdfs():
    """批量PDF文件上传"""
    try:
        files = request.files.getlist('files')

        if not files or len(files) == 0:
            return jsonify({
                'status': 'error',
                'message': 'No files provided'
            }), 400

        uploaded_files = []
        failed_files = []

        for file in files:
            saved_file, error = save_file(file)
            if error:
                failed_files.append({
                    'filename': file.filename if file else 'Unknown',
                    'error': error
                })
            else:
                uploaded_files.append(saved_file.to_dict())

        # 如果有成功上传的文件，提交事务
        if uploaded_files:
            db.session.commit()
            logger.info(f"批量上传成功: {len(uploaded_files)} 个文件")
        else:
            db.session.rollback()

        response_data = {
            'status': 'success' if uploaded_files else 'error',
            'message': f'Uploaded {len(uploaded_files)} files successfully',
            'data': {
                'uploaded': uploaded_files,
                'failed': failed_files,
                'total': len(files),
                'success_count': len(uploaded_files),
                'failed_count': len(failed_files)
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"批量上传失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Batch upload failed: {str(e)}'
        }), 500


# 获取文件列表
@app.route('/files', methods=['GET'])
def get_files():
    """获取所有文件列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        files = Files.query.order_by(Files.upload_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'status': 'success',
            'data': {
                'files': [file.to_dict() for file in files.items],
                'pagination': {
                    'page': files.page,
                    'pages': files.pages,
                    'per_page': files.per_page,
                    'total': files.total,
                    'has_next': files.has_next,
                    'has_prev': files.has_prev
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get files: {str(e)}'
        }), 500


# 删除文件
@app.route('/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """删除指定文件"""
    try:
        file = Files.query.get(file_id)
        if not file:
            return jsonify({
                'status': 'error',
                'message': 'File not found'
            }), 404

        # 删除物理文件
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
            logger.info(f"物理文件删除成功: {file.file_path}")

        # 从数据库删除记录
        db.session.delete(file)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'File deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"删除文件失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete file: {str(e)}'
        }), 500


# 更新文件信息
@app.route('/files/<file_id>', methods=['PUT'])
def update_file(file_id):
    """更新文件信息"""
    try:
        file = Files.query.get(file_id)
        if not file:
            return jsonify({
                'status': 'error',
                'message': 'File not found'
            }), 404

        data = request.get_json()
        if data.get('es_code'):
            file.es_code = data['es_code']

        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'File updated successfully',
            'data': file.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"更新文件失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to update file: {str(e)}'
        }), 500


# 健康检查
@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        # 测试数据库连接
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# 错误处理
@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'status': 'error',
        'message': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024):.1f}MB'
    }), 413


@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500


if __name__ == '__main__':
    # 确保上传目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # 在应用上下文中创建数据库表
    with app.app_context():
        create_tables()

    logger.info("Flask PDF Upload Service 启动中...")
    logger.info(f"上传目录: {os.path.abspath(UPLOAD_FOLDER)}")
    logger.info(f"最大文件大小: {MAX_FILE_SIZE / (1024 * 1024):.1f}MB")

    app.run(host='0.0.0.0', port=8080, debug=True)