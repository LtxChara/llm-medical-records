<template>
  <div class="medical-record-container">
    <!-- 头部信息 -->
    <div class="medical-header">
      <h2>医院电子病历</h2>
      <div class="visit-type-selector">
        <el-radio-group v-model="visitType" class="medical-radio-group">
          <el-radio-button label="初诊" />
          <el-radio-button label="复诊" />
        </el-radio-group>
      </div>
    </div>

    <!-- 患者基本信息 -->
    <el-form :model="patientInfo" label-width="80px" class="patient-info-form">
      <div class="patient-info-grid">
        <el-form-item label="姓名">
          <el-input v-model="patientInfo.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="patientInfo.gender" placeholder="请选择" style="width: 100%">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="年龄">
          <el-input v-model="patientInfo.age" placeholder="请输入年龄" />
        </el-form-item>
        <el-form-item label="科室">
          <el-input v-model="patientInfo.department" disabled />
        </el-form-item>
        <el-form-item label="病历号">
          <el-input v-model="patientInfo.recordNumber" placeholder="请输入病历号" />
        </el-form-item>
        <el-form-item label="就诊时间">
          <el-input v-model="patientInfo.visitTime" disabled />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="patientInfo.phone" placeholder="请输入联系电话" />
        </el-form-item>
        <el-form-item label="家庭住址">
          <el-input v-model="patientInfo.address" placeholder="请输入家庭住址" />
        </el-form-item>
      </div>
    </el-form>

    <!-- 可滚动医疗内容区域 -->
    <div class="scroll-container">
      <!-- 医疗记录内容 -->
      <div class="medical-section" v-for="(item, index) in medicalData" :key="index">
        <h3 class="section-title">{{ item.title }}</h3>
        <el-input
            v-model="item.content"
            type="textarea"
            :rows="item.rows"
            :placeholder="isGenerating && !item.content ? '思考中...' : ''"
            resize="none"
            class="medical-input"
            :disabled="isGenerating"
            :class="{ 'generating': isGenerating && !item.content }"
        />
      </div>

      <!-- 医师签名 -->
      <div class="signature-section">
        <div class="signature-item" style="display: flex; align-items: center; gap: 10px;">
          <span>医师签字：</span>
          <el-input v-model="signature.name" style="width: 200px;" />
          <span>手签：</span>
          <el-input
              v-model="signature.handwritten"
              type="textarea"
              :rows="2"
              placeholder="请在此处手写签名"
              style="width: 300px;"
          />
        </div>
      </div>

      <!-- 分页信息 -->
      <div class="page-info">
        <span>第1页，共1页</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// 统一日期格式化：YYYY-MM-DD HH:mm
const formatDateTime = (date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const h = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${h}:${min}`
}

// 签名信息
const signature = ref({
  name: '',
  handwritten: ''
})

// 患者信息（默认值清空，避免隐私泄露与误导）
const patientInfo = ref({
  name: '',
  gender: '',
  age: '',
  department: '康复科',
  recordNumber: '',
  visitTime: formatDateTime(new Date()),
  phone: '',
  address: ''
})

// 生成状态控制
const isGenerating = ref(false)

// 医疗数据
const medicalData = ref([
  { title: '主诉', content: '', rows: 2 },
  { title: '现病史', content: '', rows: 4 },
  { title: '既往史', content: '', rows: 2 },
  { title: '过敏史', content: '', rows: 2 },
  { title: '诊断', content: '', rows: 2 }
])

// 响应式数据绑定
const visitType = ref('复诊') // 默认值设置

// 处理生成状态更新
const handleGenerate = (data) => {
  if (data.type === 'all') {
    if (data.status === 'generating') {
      // 开始生成
      isGenerating.value = true
    } else if (data.status === 'partial') {
      // 部分完成，更新对应部分内容
      const section = medicalData.value.find(item => item.title === data.section)
      if (section) {
        section.content = data.content
      }
    } else if (data.status === 'completed') {
      // 生成完成
      isGenerating.value = false
    } else if (data.status === 'stopped') {
      // 用户停止生成
      isGenerating.value = false
    } else if (data.status === 'error') {
      // 生成出错
      isGenerating.value = false
    }
  } else {
    // 单个部分的生成处理
    const section = medicalData.value.find(item => item.title === data.type)
    if (section) {
      if (data.status === 'generating') {
        section.content = ''
      } else if (data.status === 'completed') {
        section.content = data.content
      }
    }
  }
}

// 基础表单校验
const validateForm = () => {
  const errors = []
  if (!patientInfo.value.name || !patientInfo.value.name.trim()) {
    errors.push('患者姓名不能为空')
  }
  if (patientInfo.value.age !== '' && patientInfo.value.age !== null) {
    const ageNum = Number(patientInfo.value.age)
    if (isNaN(ageNum) || ageNum < 0 || ageNum > 150) {
      errors.push('患者年龄必须为 0-150 之间的有效数字')
    }
  }
  if (patientInfo.value.phone && patientInfo.value.phone.trim()) {
    const phoneRegex = /^1[3-9]\d{9}$/
    if (!phoneRegex.test(patientInfo.value.phone.trim())) {
      errors.push('联系电话格式不正确')
    }
  }
  return errors
}

// 获取当前完整数据，供后端文档生成使用（带校验）
const getCurrentData = () => {
  const validationErrors = validateForm()
  if (validationErrors.length > 0) {
    throw new Error(validationErrors.join('；'))
  }
  return _buildData()
}

// 获取原始数据，不做表单校验，用于本地保存和前端打印
const getRawData = () => {
  return _buildData()
}

// 内部数据组装逻辑
const _buildData = () => {
  const medicalContent = {}
  medicalData.value.forEach(item => {
    medicalContent[item.title] = item.content || ''
  })

  return {
    patient_info: {
      name: patientInfo.value.name || '',
      gender: patientInfo.value.gender || '',
      age: String(patientInfo.value.age || ''),
      id_card: '',
      phone: patientInfo.value.phone || '',
      address: patientInfo.value.address || ''
    },
    visit_info: {
      visit_date: patientInfo.value.visitTime
        ? new Date(patientInfo.value.visitTime).toISOString().split('T')[0]
        : new Date().toISOString().split('T')[0],
      department: patientInfo.value.department || '',
      doctor: signature.value.name || ''
    },
    medical_content: medicalContent
  }
}

// 重置方法
const resetFormData = () => {
  patientInfo.value = {
    name: '',
    gender: '',
    age: '',
    department: '康复科',
    recordNumber: '',
    visitTime: formatDateTime(new Date()),
    phone: '',
    address: ''
  }

  medicalData.value.forEach(item => item.content = '')
  signature.value = {
    name: '',
    handwritten: ''
  }
}

defineExpose({
  handleGenerate,
  resetFormData,
  getCurrentData,
  getRawData
})
</script>

<style lang="scss" scoped>
.medical-record-container {
  height: 100vh;
  background: white;
  padding: 20px;
  box-sizing: border-box;

  .medical-header {
    margin-bottom: 20px;
    h2 {
      color: #333;
      font-size: 24px;
      text-align: center;
      margin: 0 0 10px 0;
    }
    .visit-info {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 15px;
    }
  }

  .patient-info-form {
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f8f8;
    border-radius: 4px;

    .patient-info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 20px;
    }

    :deep(.el-form-item) {
      margin-bottom: 10px;
    }

    :deep(.el-form-item__label) {
      font-weight: bold;
      color: #606266;
    }
  }

  .scroll-container {
    height: calc(100vh - 280px);
    overflow-y: auto;
    padding-right: 10px;

    /* 自定义滚动条 */
    &::-webkit-scrollbar {
      width: 6px;
    }
    &::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    &::-webkit-scrollbar-thumb {
      background: #c0c0c0;
      border-radius: 3px;
    }
  }

  .medical-section {
    margin-bottom: 20px;
    .section-title {
      color: #67C23A;
      font-size: 16px;
      margin: 0 0 10px 0;
      padding-left: 8px;
      border-left: 3px solid #67C23A;
    }
  }

  .medical-input {
    :deep(.el-textarea__inner) {
      border: 1px solid #e0e0e0;
      border-radius: 4px;
      padding: 10px;
      font-size: 14px;
      line-height: 1.5;
      transition: all 0.3s ease;

      &.generating {
        color: #909399;
        background: #f5f7fa;
      }

      &.completed {
        color: #303133;
        background: #ffffff;
      }
    }
  }

  .signature-section {
    margin-top: 30px;
    padding-top: 20px;
    border-top: 1px dashed #e0e0e0;
    .signature-item {
      margin: 15px 0;
      .signature-name {
        font-weight: bold;
      }
      .signature-box {
        width: 150px;
        height: 40px;
        border: 1px solid #ccc;
        margin-top: 5px;
      }
    }
  }

  .page-info {
    text-align: center;
    color: #666;
    margin-top: 20px;
    padding: 10px;
    background: #f5f5f5;
    border-radius: 4px;
  }
}
</style>