<template>
  <div class="print-template" ref="printRef">
    <div class="header">
      <h1>中山三院医院电子病历</h1>
    </div>

    <div class="patient-info">
      <div class="info-row">
        <span class="label">姓名：</span>
        <span class="value">{{ patientInfo.name }}</span>
        <span class="label">性别：</span>
        <span class="value">{{ patientInfo.gender }}</span>
        <span class="label">年龄：</span>
        <span class="value">{{ patientInfo.age }}</span>
      </div>
      <div class="info-row">
        <span class="label">科室：</span>
        <span class="value">{{ patientInfo.department }}</span>
        <span class="label">病历号：</span>
        <span class="value">{{ patientInfo.recordNumber }}</span>
      </div>
      <div class="info-row">
        <span class="label">就诊时间：</span>
        <span class="value">{{ patientInfo.visitTime }}</span>
      </div>
      <div class="info-row">
        <span class="label">联系电话：</span>
        <span class="value">{{ patientInfo.phone }}</span>
      </div>
      <div class="info-row">
        <span class="label">家庭住址：</span>
        <span class="value">{{ patientInfo.address }}</span>
      </div>
    </div>

    <div class="medical-content">
      <div v-for="(item, index) in medicalData" :key="index" class="section">
        <h3>{{ item.title }}</h3>
        <p>{{ item.content || '无' }}</p>
      </div>
    </div>

    <div class="footer">
      <div class="signature">
        <span>医师签名：</span>
        <span class="doctor-signature">{{ signature.name }}</span>
      </div>
      <div class="date">
        <span>日期：{{ signature.date }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineExpose } from 'vue'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

const props = defineProps({
  patientInfo: {
    type: Object,
    default: () => ({
      name: '',
      gender: '',
      age: '',
      department: '',
      recordNumber: '',
      visitTime: '',
      phone: '',
      address: ''
    })
  },
  medicalData: {
    type: Array,
    default: () => []
  },
  signature: {
    type: Object,
    default: () => ({
      name: '',
      handwritten: '',
      date: new Date().toLocaleDateString()
    })
  },
  pdfFilename: {
    type: String,
    default: ''
  }
})

const printRef = ref(null)

const generatePDF = async () => {
  try {
    if (!printRef.value) {
      console.error('打印模板元素未找到')
      return false
    }

    await new Promise(resolve => setTimeout(resolve, 200))

    const element = printRef.value
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
      allowTaint: true,
      backgroundColor: '#ffffff'
    })

    const imgData = canvas.toDataURL('image/jpeg', 1.0)
    const pdf = new jsPDF('p', 'mm', 'a4')
    const pdfWidth = pdf.internal.pageSize.getWidth()
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width

    pdf.addImage(imgData, 'JPEG', 0, 0, pdfWidth, pdfHeight)

    // 使用动态文件名，若未提供则使用默认命名
    const defaultName = `康复科病历_${new Date().toISOString().split('T')[0]}.pdf`
    const filename = props.pdfFilename || defaultName
    pdf.save(filename)

    return true
  } catch (error) {
    console.error('PDF生成错误:', error)
    return false
  }
}

defineExpose({
  generatePDF
})
</script>

<style scoped>
.print-template {
  width: 210mm;
  min-height: 297mm;
  padding: 20mm;
  background: white;
  box-sizing: border-box;
  font-family: SimSun, serif;
}

.header {
  text-align: center;
  margin-bottom: 20px;
}

.header h1 {
  font-size: 24px;
  font-weight: bold;
  margin: 0;
}

.patient-info {
  margin-bottom: 30px;
}

.info-row {
  margin-bottom: 10px;
  line-height: 1.5;
}

.label {
  font-weight: bold;
  margin-right: 10px;
}

.value {
  margin-right: 20px;
}

.medical-content {
  margin: 20px 0;
}

.section {
  margin-bottom: 15px;
}

.section h3 {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 8px;
  color: #333;
}

.section p {
  margin: 0;
  line-height: 1.6;
  text-align: justify;
  white-space: pre-wrap;
}

.footer {
  margin-top: 40px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.signature {
  margin-bottom: 10px;
}

.doctor-signature {
  display: inline-block;
  min-width: 100px;
  border-bottom: 1px solid #000;
  text-align: center;
  margin-left: 10px;
}

.date {
  margin-top: 10px;
}
</style>
