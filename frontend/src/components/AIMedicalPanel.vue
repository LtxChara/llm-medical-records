<template>
  <el-card class="ai-panel">

    <div class="ai-header">
      <h3><i class="el-icon-chat-line-round"></i> AI医生问诊系统</h3>
      <div class="header-actions">
        <el-tooltip content="重新开始" placement="bottom">
          <el-button
              class="restart-btn"
              @click="generateNewSessionId"
              circle
              size="small"
          >
            <svg class="refresh-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg">
              <path d="M841.8 313.2c-25.9-34.5-56.8-64.6-92-89.5-35.7-25.2-74.8-44.5-116.4-57.3-33.7-10.4-68.7-16.4-104.3-17.9V51.9L400.9 180.1l128.3 128.3v-95.9c29.1 1.4 57.7 6.4 85.4 15C761.4 272.7 860 406.4 860 560.1c0 191.9-156.1 348-348 348S164 752 164 560.1c0-37.7 6-74.8 17.8-110.1 5.6-16.8-3.5-34.9-20.2-40.5-16.8-5.6-34.9 3.5-40.5 20.2-14 41.9-21 85.7-21 130.3 0 55.6 10.9 109.6 32.4 160.4 20.8 49.1 50.5 93.1 88.3 130.9 37.8 37.8 81.9 67.5 130.9 88.3 50.8 21.5 104.8 32.4 160.4 32.4s109.6-10.9 160.4-32.4c49.1-20.8 93.1-50.5 130.9-88.3 37.8-37.8 67.5-81.9 88.3-130.9 21.5-50.8 32.4-104.8 32.4-160.4-0.1-89.7-28.5-175.1-82.3-246.8z"></path>
              <path d="M622.8 555.1c0-61.2-49.6-110.8-110.8-110.8S401.2 494 401.2 555.1 450.8 666 512 666s110.8-49.7 110.8-110.9z"></path>
            </svg>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <div class="model-select">
      <el-select
          v-model="selectedModel"
          placeholder="请选择模型"
          size="small"
          style="width: 220px"
          disabled
          title="当前仅支持后端配置的默认模型"
      >
        <el-option
            v-for="item in models"
            :key="item.value"
            :label="item.label"
            :value="item.value"
        />
      </el-select>
    </div>

    <div class="medical-buttons">
      <el-button
          v-for="btn in medicalButtons"
          :key="btn"
          class="medical-btn"
          :disabled="isGenerating"
          :type="medicalRecord.medicalContent[getEnglishKey(btn)] ? 'success' : 'info'"
          @click="reanalyzeField(btn)"
          plain
      >
        {{ btn }}
      </el-button>
    </div>

    <el-input
        v-model="inputText"
        type="textarea"
        :rows="10"
        placeholder="请在此输入患者自述或医患对话..."
        :disabled="isGenerating"
    />

    <div class="action-bar">
      <el-button
          :type="isGenerating ? 'danger' : 'success'"
          @click="toggleGeneration"
          :loading="isGenerating && !showStop"
          class="analyze-btn"
      >
        <template v-if="!isGenerating">
          <svg class="start-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
            <path d="M400.43759 732.273456a71.33239 71.33239 0 0 0 34.157473 8.810938 75.556813 75.556813 0 0 0 41.157944-12.069778l219.790665-144.837341a85.574729 85.574729 0 0 0 38.502593-72.418671 83.402169 83.402169 0 0 0-37.295615-70.608203l-221.842527-144.837341a72.41867 72.41867 0 0 0-74.591231-3.741631 84.488449 84.488449 0 0 0-41.761433 75.436115v289.674681a84.488449 84.488449 0 0 0 41.882131 74.591231z m42.002829-82.315889V374.163131l207.600188 135.664309v0.965582a13.156058 13.156058 0 0 1 0 2.293258z" fill="currentColor"></path>
            <path d="M149.989688 874.093352a509.948138 509.948138 0 1 0-109.714286-162.700613 513.206978 513.206978 0 0 0 109.714286 162.700613zM84.571489 512a428.11504 428.11504 0 1 1 427.511551 428.11504A428.597831 428.597831 0 0 1 84.571489 512z" fill="currentColor"></path>
          </svg>
          开始分析
        </template>
        <template v-else>
          <svg class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
            <path d="M924.8 337.6c-22.6-53.3-54.9-101.3-96-142.4-41.1-41.1-89.1-73.4-142.4-96C631.1 75.8 572.5 64 512 64S392.9 75.8 337.6 99.2c-53.3 22.6-101.3 54.9-142.4 96s-73.4 89.1-96 142.4C75.8 392.9 64 451.5 64 512s11.8 119.1 35.2 174.4c22.6 53.3 54.9 101.3 96 142.4 41.1 41.1 89.1 73.4 142.4 96C392.9 948.2 451.5 960 512 960s119.1-11.8 174.4-35.2c53.3-22.6 101.3-54.9 142.4-96 41.1-41.1 73.4-89.1 96-142.4C948.2 631.1 960 572.5 960 512s-11.8-119.1-35.2-174.4zM662 867.1c-47.5 20.1-98 30.3-150 30.3s-102.5-10.2-150-30.2c-45.8-19.3-87-47.1-122.5-82.6-35.5-35.5-63.3-76.7-82.6-122.5-20.1-47.5-30.3-98-30.3-150s10.2-102.5 30.2-150c19.3-45.8 47.1-87 82.6-122.5 35.5-35.5 76.7-63.3 122.5-82.6 47.5-20.1 98-30.3 150-30.3s102.5 10.2 150 30.2c45.8 19.3 87 47.1 122.5 82.6C819.9 275 847.7 316.2 867 362c20.1 47.5 30.3 98 30.3 150s-10.2 102.5 30.2 150c-19.3 45.8-47.1 87-82.6 122.5-35.5 35.4-76.7 63.2-122.5 82.6z" fill="currentColor"></path>
            <path d="M621.7 326.1H402.3c-42 0-76.2 34.2-76.2 76.2v219.3c0 42 34.2 76.2 76.2 76.2h219.3c42 0 76.2-34.2 76.2-76.2V402.3c0.1-42-34.1-76.2-76.1-76.2z m12.6 76.2v219.3c0 6.9-5.7 12.6-12.6 12.6H402.3c-6.9 0-12.6-5.7-12.6-12.6V402.3c0-6.9 5.7-12.6 12.6-12.6h219.3c7 0 12.7 5.7 12.7 12.6z" fill="currentColor"></path>
          </svg>
          停止
        </template>
      </el-button>

      <el-button
          type="primary"
          :disabled="isGenerating"
          @click="printMedicalRecord"
          :loading="isPrinting"
          class="print-btn"
      >
        <svg class="print-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
          <path d="M786.3 382.5m-40.9 0a40.9 40.9 0 1 0 81.8 0 40.9 40.9 0 1 0-81.8 0Z" fill="currentColor"></path>
          <path d="M125.4 689.9V649v16.2c0.8 13.8 12.2 24.7 26.2 24.7h-26.2zM266.4 888.9V848v16.2c0.8 13.8 12.2 24.7 26.2 24.7h-26.2zM886.4 689.7h-40.9 16.2c13.8-0.8 24.7-12.2 24.7-26.2v26.2zM745.8 888.4h-40.9 16.2c13.8-0.8 24.7-12.2 24.7-26.2v26.2zM745.5 139.8v40.9-16.2c-0.8-13.8-12.2-24.7-26.2-24.7h26.2zM745.5 619.9v40.9-16.2c-0.8-13.8-12.2-24.7-26.2-24.7h26.2zM265.9 139.8h40.9-16.2c-13.8 0.8-24.7 12.2-24.7 26.2v-26.2zM266 619.7h41-16.2c-13.8 0.9-24.8 12.3-24.8 26.2v-26.2zM125.4 289.1h40.9-16.2c-13.8 0.8-24.7 12.2-24.7 26.2v-26.2zM886.1 289.2v40.9-16.2c-0.8-13.8-12.2-24.7-26.2-24.7h26.2z" fill="currentColor"></path>
          <path d="M967.8 710.1V266c-4.7-33-33.1-58.5-67.4-58.5h-73.1v-89.6c-3.9-32.8-31.1-58.4-64.5-59.8H250.2c-34.8 1-63.1 28.2-65.8 62.6v86.8h-78.8c-33.2 3-59.5 29.7-61.8 63.1v438.7c2.4 31.7 26.4 57.3 57.4 62.1h83.2v133.1c1.2 34.8 28.5 62.9 62.8 65.5h519.2c32.6-3.3 58.4-29.7 60.9-62.6v-136h80.5c31.8-3.6 57-29.2 60-61.3zM266.3 140h479.1v67.5H266.3V140z m479.1 590.4V888H266.3V620h479.1v110.4z m140.5-40.9h-58.6v-92c-3.9-31.9-29.8-56.9-62.1-59.4H248.3c-34.4 2-61.9 29.6-63.9 64v87.4h-58.6V289.4H886v400.1z" fill="currentColor"></path>
        </svg>
        打印病历
      </el-button>
    </div>

  </el-card>
</template>

<script setup>
import { ref, reactive, createApp, h } from 'vue'
import { onMounted } from 'vue'
import { ElCard, ElSelect, ElOption, ElButton, ElInput, ElMessage, ElTag, ElMessageBox } from 'element-plus'
import PrintTemplate from './PrintTemplate.vue'
import { analyzeText, supplementText, generateDoc } from '../api/medical.js'

const selectedModel = ref('deepseek-r1-distill-qwen-7b')
const models = ref([
  { value: 'deepseek-r1-distill-qwen-7b', label: 'DeepSeek-R1-Distill-Qwen-7B' },
])
const inputText = ref('')
const isGenerating = ref(false)
const isPrinting = ref(false)
const showStop = ref(false)
const abortController = ref(null)

const medicalButtons = ref(['主诉', '现病史', '既往史', '过敏史', '诊断'])
const emit = defineEmits(['generate'])

const props = defineProps({
  patientInfoRef: {
    type: Object,
    default: null
  }
})

// 病历数据结构（仅保留 AI 生成的医疗内容，患者基本信息由 PatientInfo 管理）
const medicalRecord = reactive({
  medicalContent: {
    chiefComplaint: '',
    currentIllness: '',
    pastHistory: '',
    allergyHistory: '',
    diagnosis: '',
    prescription: '',
    advice: ''
  }
})

// 切换生成状态
const toggleGeneration = () => {
  if (isGenerating.value) {
    stopGenerating()
  } else {
    // 检查输入内容是否为空
    if (!inputText.value.trim()) {
      ElMessage.warning({
        message: '请输入患者自述或医患对话内容',
        duration: 2000,
        showClose: true
      })
      return
    }
    startGenerating()
  }
}

// 开始生成
const startGenerating = async () => {
  isGenerating.value = true
  showStop.value = true
  abortController.value = new AbortController()

  try {
    emit('generate', { type: 'all', status: 'generating' })

    // 检查输入是否为空
    if (!inputText.value.trim()) {
      throw new Error('请输入患者自述或医患对话内容')
    }

    console.log('发送请求数据:', { session_id: sessionId.value, text: inputText.value })

    // 调用分析API，传入 AbortSignal 支持取消
    const result = await analyzeText(sessionId.value, inputText.value, abortController.value.signal)
    console.log('响应数据:', result)

    // 处理响应
    if (result.status === 'success') {
      const medicalData = result.result || {}
      console.log('解析后的病历数据:', medicalData)

      // 更新病历内容并触发事件
      const sections = {
        '主诉': 'chiefComplaint',
        '现病史': 'currentIllness',
        '既往史': 'pastHistory',
        '过敏史': 'allergyHistory',
        '诊断': 'diagnosis'
      }

      for (const [chineseKey, englishKey] of Object.entries(sections)) {
        if (medicalData[chineseKey] !== undefined) {
          medicalRecord.medicalContent[englishKey] = medicalData[chineseKey]
          emit('generate', {
            type: 'all',
            section: chineseKey,
            content: medicalData[chineseKey],
            status: 'partial'
          })
        }
      }

      emit('generate', { type: 'all', status: 'completed' })
    } else if (result.status === 'incomplete') {
      // 调用补充循环处理多轮补充
      await handleSupplementLoop(result.field, result.message)
    } else if (result.status === 'error') {
      throw new Error(result.message || '分析过程中发生错误')
    } else {
      throw new Error('无效的响应格式')
    }

  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('生成失败:', error)
      emit('generate', { type: 'all', error: error.message, status: 'error' })
      ElMessage.error({
        message: `生成失败: ${error.message}`,
        duration: 3000,
        showClose: true
      })
    }
  } finally {
    isGenerating.value = false
    showStop.value = false
    abortController.value = null
  }
}

// 处理补充循环
const handleSupplementLoop = async (field, message) => {
  let userInput = ''
  try {
    const promptResult = await ElMessageBox.prompt(
      message || '请补充相关信息',
      `请补充【${field}】`,
      {
        confirmButtonText: '提交补充',
        cancelButtonText: '跳过',
        inputPlaceholder: '请输入补充信息...',
        type: 'info'
      }
    )
    userInput = promptResult.value
  } catch (e) {
    // 用户取消
    emit('generate', { type: 'all', status: 'stopped' })
    ElMessage.info('已取消补充')
    return
  }

  if (!userInput || !userInput.trim()) {
    ElMessage.warning('补充内容不能为空')
    return
  }

  // 显示补充中的状态
  emit('generate', { type: 'all', section: field, content: '等待补充...', status: 'partial' })

  try {
    const result = await supplementText(sessionId.value, field, userInput.trim(), abortController.value.signal)
    console.log('补充响应数据:', result)

    if (result.status === 'success') {
      const medicalData = result.result || {}
      console.log('补充后解析的病历数据:', medicalData)

      const sections = {
        '主诉': 'chiefComplaint',
        '现病史': 'currentIllness',
        '既往史': 'pastHistory',
        '过敏史': 'allergyHistory',
        '诊断': 'diagnosis'
      }

      for (const [chineseKey, englishKey] of Object.entries(sections)) {
        if (medicalData[chineseKey] !== undefined) {
          medicalRecord.medicalContent[englishKey] = medicalData[chineseKey]
          emit('generate', {
            type: 'all',
            section: chineseKey,
            content: medicalData[chineseKey],
            status: 'partial'
          })
        }
      }

      emit('generate', { type: 'all', status: 'completed' })
    } else if (result.status === 'incomplete') {
      // 递归处理多轮补充
      await handleSupplementLoop(result.field, result.message)
    } else if (result.status === 'error') {
      throw new Error(result.message || '补充处理过程中发生错误')
    } else {
      throw new Error('无效的响应格式')
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('补充失败:', error)
      emit('generate', { type: 'all', error: error.message, status: 'error' })
      ElMessage.error({
        message: `补充失败: ${error.message}`,
        duration: 3000,
        showClose: true
      })
    }
  }
}

// 停止生成
const stopGenerating = () => {
  if (abortController.value) {
    abortController.value.abort()
    emit('generate', { type: 'all', status: 'stopped' })
  }
  isGenerating.value = false
  showStop.value = false
}

// 打印病历：优先调用后端生成 Word，失败时 fallback 到前端 PDF
const printMedicalRecord = async () => {
  let currentData = null
  try {
    isPrinting.value = true

    // 从 PatientInfo 获取当前数据（允许空值，fallback 使用原始数据）
    try {
      currentData = props.patientInfoRef?.getCurrentData?.()
    } catch (validateErr) {
      ElMessage.warning('患者基本信息不完整，将使用默认值生成文档：' + validateErr.message)
      currentData = props.patientInfoRef?.getRawData?.()
    }
    if (!currentData) {
      throw new Error('无法获取当前病历数据')
    }

    // 优先调用后端生成 Word 文档，传入 AbortSignal 支持取消
    const docController = new AbortController()
    await generateDoc(currentData, docController.signal)
    ElMessage.success('Word 文档已开始下载')
  } catch (error) {
    if (error.name === 'AbortError') {
      ElMessage.info('文档生成已取消')
      return
    }
    console.error('后端文档生成失败，尝试前端 PDF:', error)
    ElMessage.warning('后端 Word 生成失败，正在尝试前端 PDF...')

    // Fallback: 前端 PDF 生成
    try {
      const now = new Date()
      const dateStr = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}`
      const patientName = currentData?.patient_info?.name || '未知患者'
      const printData = {
        patientInfo: {
          name: patientName,
          gender: currentData?.patient_info?.gender || '',
          age: String(currentData?.patient_info?.age || ''),
          department: currentData?.visit_info?.department || '康复科',
          recordNumber: currentData?.patient_info?.recordNumber || '',
          visitTime: currentData?.visit_info?.visit_date || `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`,
          phone: currentData?.patient_info?.phone || '',
          address: currentData?.patient_info?.address || ''
        },
        medicalData: [
          { title: '主诉', content: currentData?.medical_content?.['主诉'] },
          { title: '现病史', content: currentData?.medical_content?.['现病史'] },
          { title: '既往史', content: currentData?.medical_content?.['既往史'] },
          { title: '过敏史', content: currentData?.medical_content?.['过敏史'] },
          { title: '诊断', content: currentData?.medical_content?.['诊断'] }
        ].filter(item => item.content),
        signature: {
          name: currentData?.visit_info?.doctor || '',
          handwritten: currentData?.visit_info?.doctor || '',
          date: `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
        },
        pdfFilename: `${patientName}_康复科病历_${dateStr}.pdf`
      }

      const container = document.createElement('div')
      container.style.position = 'fixed'
      container.style.left = '-9999px'
      document.body.appendChild(container)

      const printApp = createApp(PrintTemplate, printData)
      const vm = printApp.mount(container)

      await new Promise(resolve => setTimeout(resolve, 200))

      if (typeof vm.generatePDF !== 'function') {
        throw new Error('打印组件初始化失败')
      }

      const success = await vm.generatePDF()
      if (success) {
        ElMessage.success('PDF 已开始下载')
      } else {
        throw new Error('PDF生成失败')
      }

      printApp.unmount()
      document.body.removeChild(container)
    } catch (pdfError) {
      console.error('PDF 生成也失败了:', pdfError)
      ElMessage.error('打印失败: ' + pdfError.message)
    }
  } finally {
    isPrinting.value = false
  }
}

// 生成随机ID函数
const generateId = () => {
  return 'id-' + Math.random().toString(36).substr(2, 9)
}

// 会话ID
const sessionId = ref('')

// 重置 AI 面板状态
const resetFormData = () => {
  sessionId.value = generateId()
  inputText.value = ''
  isGenerating.value = false
  showStop.value = false
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }

  Object.assign(medicalRecord.medicalContent, {
    chiefComplaint: '',
    currentIllness: '',
    pastHistory: '',
    allergyHistory: '',
    diagnosis: '',
    prescription: '',
    advice: ''
  })
}

// 修改后的生成新会话方法
const generateNewSessionId = async () => {
  try {
    // 检查是否有未保存的内容
    const hasUnsavedContent = inputText.value.trim() ||
      medicalRecord.medicalContent.diagnosis

    if (hasUnsavedContent) {
      const confirm = await ElMessageBox.confirm(
        '当前有未保存的内容，是否确认重新开始？',
        '提示',
        {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )

      if (confirm !== 'confirm') {
        return
      }
    }

    resetFormData()

    ElMessage.success({
      message: '已重置所有表单内容',
      duration: 2000,
      showClose: true
    })
  } catch (error) {
    console.error('重置错误:', error)
    ElMessage.error({
      message: `重置失败: ${error.message}`,
      duration: 3000,
      showClose: true
    })
  }
}

// 中文字段名到英文 key 的映射
const getEnglishKey = (chineseKey) => {
  const map = {
    '主诉': 'chiefComplaint',
    '现病史': 'currentIllness',
    '既往史': 'pastHistory',
    '过敏史': 'allergyHistory',
    '诊断': 'diagnosis'
  }
  return map[chineseKey] || ''
}

// 单字段重新提取：用户点击医疗字段按钮时触发
const reanalyzeField = async (field) => {
  if (isGenerating.value) {
    ElMessage.warning('当前正在生成中，请稍后再试')
    return
  }
  if (!inputText.value.trim()) {
    ElMessage.warning('请先在输入框中填写患者描述，然后点击开始分析')
    return
  }

  try {
    const result = await ElMessageBox.prompt(
      `请补充或修改【${field}】的相关信息，系统将重新提取该字段：`,
      `重新提取【${field}】`,
      {
        confirmButtonText: '提交并重新提取',
        cancelButtonText: '取消',
        inputPlaceholder: `请输入关于${field}的补充或修正信息...`,
        type: 'info'
      }
    )
    const supplement = result.value
    if (!supplement || !supplement.trim()) {
      ElMessage.warning('输入内容不能为空')
      return
    }

    isGenerating.value = true
    showStop.value = true
    abortController.value = new AbortController()

    emit('generate', { type: 'all', section: field, content: '重新提取中...', status: 'partial' })

    const res = await supplementText(sessionId.value, field, supplement.trim(), abortController.value.signal)

    if (res.status === 'success') {
      const medicalData = res.result || {}
      const englishKey = getEnglishKey(field)
      if (englishKey && medicalData[field] !== undefined) {
        medicalRecord.medicalContent[englishKey] = medicalData[field]
        emit('generate', {
          type: 'all',
          section: field,
          content: medicalData[field],
          status: 'partial'
        })
      }
      ElMessage.success(`【${field}】已更新`)
    } else if (res.status === 'incomplete') {
      // 重新提取后仍然需要补充，递归处理
      await handleSupplementLoop(res.field, res.message)
    } else if (res.status === 'error') {
      throw new Error(res.message || '重新提取过程中发生错误')
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      ElMessage.info('已取消重新提取')
    } else {
      console.error('重新提取失败:', error)
      ElMessage.error(`重新提取失败: ${error.message}`)
    }
  } finally {
    isGenerating.value = false
    showStop.value = false
    abortController.value = null
  }
}

// 页面加载时初始化
onMounted(() => {
  // 不再使用sessionStorage存储ID
  sessionId.value = generateId()
  inputText.value = '' // 刷新时清空输入框
})

defineExpose({
  generateNewSessionId,
  resetFormData,
  reanalyzeField,
  printMedicalRecord
})

</script>

<style lang="scss" scoped>
.ai-panel {
  height: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

  .ai-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #ebeef5;
    position: relative;

    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 500;
      color: #303133;
      display: flex;
      align-items: center;

      i {
        margin-right: 8px;
        color: #409EFF;
      }
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .restart-btn {
      width: 32px;
      height: 32px;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      border: none;
      background: #f5f7fa;
      transition: all 0.3s;

      &:hover {
        background: #e6e9ed;
        transform: rotate(90deg);
      }

      .refresh-icon {
        width: 16px;
        height: 16px;
        fill: #47444F;
      }
    }
  }

  .model-select {
    margin: 16px 0;
    padding: 0 20px;
  }

  .medical-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 16px 20px;

    .medical-btn {
      padding: 8px 15px;
      font-size: 14px;
      border-radius: 4px;
      transition: all 0.2s;

      &:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }
    }
  }

  .el-textarea {
    margin: 0 20px 16px;
    width: calc(100% - 40px);
  }

  .action-bar {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin: 0 20px 20px;

    .analyze-btn {
      min-width: 120px;
      height: 40px;
      font-size: 15px;
      font-weight: 500;

      &:not(.is-disabled):hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(64, 158, 255, 0.2);
      }
    }

    .print-btn {
      min-width: 120px;
      height: 40px;
      font-size: 15px;
      font-weight: 500;

      &:not(.is-disabled):hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(64, 158, 255, 0.2);
      }
    }
  }
}

/* 添加图标样式 */
.icon {
  margin-right: 8px;
  vertical-align: middle;
}

/* 打印图标样式 */
.print-icon {
  margin-right: 8px;
  vertical-align: middle;
  /* 微调新图标的位置 */
  position: relative;
  top: -1px;
}

.session-id {
  margin: 16px 0;
  display: flex;
  align-items: center;
  gap: 12px;

  .refresh-btn {
    margin-left: 10px;
  }
}
</style>