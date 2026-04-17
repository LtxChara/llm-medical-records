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
    <el-descriptions :column="2" border class="patient-info">
      <el-descriptions-item label="姓名">
        {{ patientInfo.name }}
      </el-descriptions-item>
      <el-descriptions-item label="性别">
        {{ patientInfo.gender }}
      </el-descriptions-item>
      <el-descriptions-item label="年龄">
        {{ patientInfo.age }}
      </el-descriptions-item>
      <el-descriptions-item label="科室">
        {{ patientInfo.department }}
      </el-descriptions-item>
      <el-descriptions-item label="病历号">
        {{ patientInfo.recordNumber }}
      </el-descriptions-item>
      <el-descriptions-item label="就诊时间">
        {{ patientInfo.visitTime }}
      </el-descriptions-item>
      <el-descriptions-item label="联系电话">
        {{ patientInfo.phone }}
      </el-descriptions-item>
      <el-descriptions-item label="家庭住址">
        {{ patientInfo.address }}
      </el-descriptions-item>
    </el-descriptions>

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

// 签名信息
const signature = ref({
  name: '贾连荣',
  handwritten: ''
})

// 患者信息
const patientInfo = ref({
  name: '蔡志军',
  gender: '男',
  age: 45,
  department: '中医内科',
  recordNumber: 'MZ07882405098',
  visitTime: new Date().toLocaleString(),
  phone: '13920631008',
  address: '上海市宝山区上大路99号'
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

// 获取当前完整数据，供后端文档生成使用
const getCurrentData = () => {
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
    recordNumber: 'MZ07882405098',
    visitTime: new Date().toLocaleString(),
    phone: '',
    address: ''
  }

  medicalData.value.forEach(item => item.content = '')
  signature.value = {
    name: '贾连荣',
    handwritten: ''
  }
}

defineExpose({
  handleGenerate,
  resetFormData,
  getCurrentData
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

  .patient-info {
    margin-bottom: 20px;
    :deep(.el-descriptions__body) {
      background: #f8f8f8;
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