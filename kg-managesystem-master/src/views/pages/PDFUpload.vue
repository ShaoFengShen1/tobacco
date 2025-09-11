<template>
  <div class="pdf-management">
    <div class="header">
      <h1>PDF文件管理系统</h1>
      <div class="header-stats">
        <el-statistic title="文件总数" :value="totalFiles" />
      </div>
    </div>

    <div class="upload-section">
      <el-card shadow="hover" class="box-card">
        <template #header>
          <div class="card-header">
            <span><el-icon><Upload /></el-icon> 文件上传</span>
            <el-button type="primary" size="small" @click="toggleBatchMode" plain>
              {{ batchMode ? '切换单文件' : '切换批量' }}
            </el-button>
          </div>
        </template>

        <el-upload
          class="upload-area"
          drag
          :action="uploadUrl"
          :multiple="batchMode"
          :headers="{ 'Accept': 'application/json' }"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :show-file-list="false"
          accept=".pdf, .doc, .docx, .xls, .xlsx, .jpg, .jpeg, .png"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              {{ batchMode ? '支持批量上传文件' : '每次上传一个文件' }}，单个文件最大50MB
            </div>
          </template>
        </el-upload>

        <div v-if="uploadingFiles.length > 0" class="uploading-list">
          <h4>正在上传：</h4>
          <div v-for="file in uploadingFiles" :key="file.uid" class="uploading-item">
            <span>{{ file.name }}</span>
            <el-progress :percentage="file.percentage" />
          </div>
        </div>
      </el-card>
    </div>

    <div class="file-list-section">
        <el-card class="box-card">
            <template #header>
                <div class="card-header">
                    <span><el-icon><Document /></el-icon> 文件列表</span>
                    <div class="header-actions">
                    <el-input v-model="searchQuery" placeholder="搜索文件名、ES码" prefix-icon="Search" clearable style="width: 260px; margin-right: 10px" @clear="handleSearch" @keyup.enter="handleSearch" />
                    <el-button type="primary" @click="handleSearch" :icon="Search">搜索</el-button>
                    <el-button @click="refreshList">刷新</el-button>
                    <el-button v-if="selectedFiles.length > 0" type="danger" @click="handleBatchDelete" plain>批量删除 ({{ selectedFiles.length }})</el-button>
                    </div>
                </div>
            </template>
            <el-table v-loading="loading" :data="fileList" style="width: 100%" @selection-change="handleSelectionChange" stripe>
                <el-table-column type="selection" width="55" />
                <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip>
                    <template #default="scope">
                    <div class="file-name-cell">
                        <el-icon class="file-icon"><Document /></el-icon>
                        <span>{{ scope.row.file_name }}</span>
                    </div>
                    </template>
                </el-table-column>
                <el-table-column prop="file_size_mb" label="大小" width="100" align="center">
                    <template #default="scope">
                    <el-tag size="small">{{ scope.row.file_size_mb }} MB</el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="es_code" label="ES码" width="150">
                    <template #default="scope">
                    <el-input v-if="editingId === scope.row.id" v-model="editingData.es_code" size="small" @keyup.enter="saveEdit(scope.row)" />
                    <span v-else>{{ scope.row.es_code || '-' }}</span>
                    </template>
                </el-table-column>
                <el-table-column prop="upload_time" label="上传时间" width="180" sortable>
                    <template #default="scope">
                    {{ formatTime(scope.row.upload_time) }}
                    </template>
                </el-table-column>
                <el-table-column label="操作" width="300" fixed="right" align="center">
                    <template #default="scope">
                    <el-button-group>
                        <el-button type="primary" size="small" @click="handlePreview(scope.row)" text bg><el-icon><View /></el-icon> 预览</el-button>
                        <el-button type="success" size="small" @click="handleDownload(scope.row)" text bg><el-icon><Download /></el-icon> 下载</el-button>
                        <el-button v-if="editingId !== scope.row.id" type="warning" size="small" @click="startEdit(scope.row)" text bg><el-icon><Edit /></el-icon> 编辑</el-button>
                        <el-button v-else type="success" size="small" @click="saveEdit(scope.row)" text bg><el-icon><Check /></el-icon> 保存</el-button>
                        <el-button type="danger" size="small" @click="handleDelete(scope.row)" text bg><el-icon><Delete /></el-icon> 删除</el-button>
                    </el-button-group>
                    </template>
                </el-table-column>
            </el-table>
            <div class="pagination-wrapper">
                <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" :total="totalFiles" layout="total, sizes, prev, pager, next, jumper" @size-change="handleSizeChange" @current-change="handlePageChange" />
            </div>
        </el-card>
    </div>

    <el-dialog
      v-model="previewVisible"
      :title="`预览: ${previewFile?.file_name}`"
      width="90%"
      top="4vh"
      destroy-on-close
      :body-style="{ padding: '0', height: '188vh' }"
    >
      <iframe v-if="previewUrl" :src="previewUrl" width="100%" height="1000px" frameborder="0" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled, Document, View, Download, Edit, Delete, Check, Search } from '@element-plus/icons-vue'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8001'

const fileList = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalFiles = ref(0)
const searchQuery = ref('')
const selectedFiles = ref([])
const previewVisible = ref(false)
const previewFile = ref(null)
const previewUrl = ref('')
const batchMode = ref(false)
const uploadingFiles = ref([])
const editingId = ref(null)
const editingData = ref({})

const uploadUrl = computed(() => {
  return batchMode.value ? `${API_BASE_URL}/upload/batch` : `${API_BASE_URL}/upload`
})

onMounted(() => {
  fetchFiles()
})

const toggleBatchMode = () => {
  batchMode.value = !batchMode.value
  if (batchMode.value) {
    ElMessageBox.alert(
      '您已切换到批量上传模式。现在您可以一次性选择或拖拽多个PDF文件到上传区域。',
      '批量模式提示',
      { confirmButtonText: '我明白了' }
    )
  }
}

const fetchFiles = async () => {
  loading.value = true
  try {
    const response = await axios.get(`${API_BASE_URL}/files`, {
      params: { page: currentPage.value, per_page: pageSize.value, search: searchQuery.value || null }
    })
    if (response.data.status === 'success') {
      fileList.value = response.data.data.files
      totalFiles.value = response.data.data.pagination.total
    } else {
      ElMessage.error('获取文件列表时发生未知错误')
      fileList.value = []; totalFiles.value = 0
    }
  } catch (error) {
    ElMessage.error('获取文件列表失败，请检查后端服务是否开启。')
    console.error("获取文件列表时出错:", error)
    fileList.value = []; totalFiles.value = 0
  } finally {
    loading.value = false
  }
}

const handleSearch = () => { currentPage.value = 1; fetchFiles() }
const refreshList = () => { searchQuery.value = ''; currentPage.value = 1; fetchFiles() }

const beforeUpload = (file) => {
  const isPDF = file.type === 'application/pdf'
  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) { ElMessage.error('文件大小不能超过50MB!'); return false }
  return true
}

const handleUploadSuccess = (response, file) => {
  if (response.status === 'success') {
    ElMessage.success(response.message || '上传成功')
    fetchFiles()
  } else {
    ElMessage.error(response.message || `文件 ${file.name} 上传失败`)
  }
}

const handleUploadError = (error, file) => {
  ElMessage.error(`文件 ${file.name} 上传失败`)
  console.error(error)
}

const handlePreview = (file) => { previewFile.value = file; previewUrl.value = `${API_BASE_URL}/files/${file.id}/preview`; previewVisible.value = true }
const handleDownload = (file) => { window.open(`${API_BASE_URL}/files/${file.id}/download`, '_blank') }
const startEdit = (file) => { editingId.value = file.id; editingData.value = { es_code: file.es_code || '' } }
const saveEdit = async (file) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/files/${file.id}`, editingData.value)
    if (response.data.status === 'success') {
      ElMessage.success('更新成功'); editingId.value = null; fetchFiles()
    } else { ElMessage.error(response.data.message || '更新失败') }
  } catch (error) { ElMessage.error('更新请求失败'); console.error(error) }
}
const handleDelete = async (file) => {
  try {
    await ElMessageBox.confirm(`确定要删除文件 "${file.file_name}" 吗？`, '删除确认', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const response = await axios.delete(`${API_BASE_URL}/files/${file.id}`)
    if (response.data.status === 'success') {
      ElMessage.success('删除成功')
      if (fileList.value.length === 1 && currentPage.value > 1) { currentPage.value-- }
      fetchFiles()
    }
  } catch (error) { if (error !== 'cancel') { ElMessage.error('删除失败'); console.error(error) } }
}
const handleBatchDelete = async () => {
  if (selectedFiles.value.length === 0) { ElMessage.warning('请先选择要删除的文件'); return; }
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedFiles.value.length} 个文件吗？`, '批量删除确认', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const fileIds = selectedFiles.value.map(f => f.id)
    const response = await axios.post(`${API_BASE_URL}/files/batch-delete`, { file_ids: fileIds })
    if (response.data.status === 'success') {
      ElMessage.success(response.data.message); selectedFiles.value = []; fetchFiles()
    }
  } catch (error) { if (error !== 'cancel') { ElMessage.error('批量删除失败'); console.error(error) } }
}
const handleSelectionChange = (selection) => { selectedFiles.value = selection }
const handlePageChange = (page) => { currentPage.value = page; fetchFiles() }
const handleSizeChange = (size) => { pageSize.value = size; currentPage.value = 1; fetchFiles() }
const formatTime = (time) => { if (!time) return '-'; return new Date(time).toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-') }
</script>

<style scoped>
/* --- 全局与字体美化 --- */
.pdf-management {
  padding: 24px;
  background-color: #f0f2f5; /* 使用更柔和的背景色 */
  min-height: 100vh;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
}

/* --- 头部区域美化 --- */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 24px 32px;
  /* 新的淡蓝色渐变背景 */
  background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%);
  border-radius: 12px;
  color: white;
  box-shadow: 0 8px 16px rgba(102, 166, 255, 0.3);
}

.header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.15);
}

.header-stats {
  background: rgba(255, 255, 255, 0.25);
  padding: 10px 20px;
  border-radius: 8px;
  backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

:deep(.el-statistic__head) {
  color: rgba(255, 255, 255, 0.9) !important;
}

:deep(.el-statistic__content) {
  color: white !important;
  font-weight: 600;
}

/* --- 卡片样式美化 --- */
.box-card {
  border-radius: 12px;
  border: none;
  transition: all 0.3s ease;
}
.box-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.upload-section, .file-list-section {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.card-header span {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* --- 上传区域美化 --- */
:deep(.el-upload-dragger) {
  padding: 40px;
  border-radius: 10px;
  border: 2px dashed #dcdfe6;
  transition: all 0.3s ease;
}
:deep(.el-upload-dragger:hover) {
  border-color: #66a6ff;
  background-color: #f5f9ff;
}
.el-upload__text {
  color: #606266;
}
.el-upload__tip {
  color: #909399;
  font-size: 14px;
  margin-top: 10px;
}

/* --- 表格样式美化 --- */
:deep(.el-table) {
  border-radius: 8px;
}
:deep(.el-table th) {
  background-color: #fafafa !important;
  color: #606266;
  font-weight: 600;
}
:deep(.el-table tr:hover > td) {
  background-color: #ecf5ff !important;
}
.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.file-icon {
  color: #66a6ff;
}

/* --- 分页与控件美化 --- */
.pagination-wrapper {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}
.header-actions .el-button, .header-actions .el-input {
  transition: all 0.3s ease;
}
.header-actions .el-input:focus-within {
  box-shadow: 0 0 0 1px rgba(102, 166, 255, 0.5);
}
.el-button-group .el-button {
  margin: 0 2px !important;
}
</style>