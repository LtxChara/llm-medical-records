<template>
  <div class="medical-system">
    <AppHeader @new-record="handleNewRecord" />

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