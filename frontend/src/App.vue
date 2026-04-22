<template>
  <div class="medical-system">
    <AppHeader
      @new-record="handleNewRecord"
      @save-record="handleSaveRecord"
      @print-record="handlePrintRecord"
      @export-pdf="handleExportPdf"
      @focus-signature="handleFocusSignature"
    />

    <div class="main-container">
      <!-- 左侧患者信息区 -->
      <PatientInfo ref="patientInfoRef" />

      <!-- 右侧AI医疗区 -->
      <AIMedicalPanel ref="aiPanelRef" @generate="handleGenerate" :patient-info-ref="patientInfoRef" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppHeader from './components/AppHeader.vue'
import PatientInfo from './components/PatientInfo.vue'
import AIMedicalPanel from './components/AIMedicalPanel.vue'

const patientInfoRef = ref(null)
const aiPanelRef = ref(null)

const handleGenerate = (data) => {
  patientInfoRef.value?.handleGenerate(data)
}

const handleNewRecord = () => {
  patientInfoRef.value?.resetFormData()
  aiPanelRef.value?.resetFormData()
}

// 保存病历到 localStorage（使用原始数据，不强制校验必填项）
const handleSaveRecord = () => {
  try {
    const data = patientInfoRef.value?.getRawData?.() || patientInfoRef.value?.getCurrentData?.()
    if (!data) {
      throw new Error('无法获取当前病历数据')
    }
    const record = {
      timestamp: new Date().toISOString(),
      data
    }
    const saved = JSON.parse(localStorage.getItem('medical_records') || '[]')
    saved.push(record)
    // 最多保留20条历史记录
    if (saved.length > 20) {
      saved.shift()
    }
    localStorage.setItem('medical_records', JSON.stringify(saved))
    ElMessage.success('病历已保存到浏览器本地存储')
  } catch (error) {
    ElMessage.error('保存失败: ' + error.message)
    throw error
  }
}

// 打印病历（复用 AIMedicalPanel 的打印逻辑）
const handlePrintRecord = () => {
  aiPanelRef.value?.printMedicalRecord?.()
}

// 导出PDF（与打印使用相同的逻辑，最终生成PDF）
const handleExportPdf = () => {
  aiPanelRef.value?.printMedicalRecord?.()
}

// 聚焦到签名区域
const handleFocusSignature = () => {
  // 尝试找到签名输入框并聚焦
  const signatureInput = document.querySelector('.signature-section input')
  if (signatureInput) {
    signatureInput.focus()
    signatureInput.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}
</script>

<style lang="scss">
.medical-system {
  height: 100vh;
  background: #F0F9EB;

  .main-container {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 20px;
    padding: 20px;
    height: calc(100vh - 60px);
  }
}
</style>
