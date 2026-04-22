<template>
  <el-menu
      mode="horizontal"
      class="medical-header"
      background-color="#67C23A"
      text-color="#fff"
      active-text-color="#ffd04b"
      @select="handleSelect"
  >
    <el-sub-menu index="1">
      <template #title>病历管理</template>
      <el-menu-item index="1-1">新建病历</el-menu-item>
      <el-menu-item index="1-2">保存病历</el-menu-item>
      <el-menu-item index="1-3">导出PDF</el-menu-item>
    </el-sub-menu>

    <el-sub-menu index="2">
      <template #title>模板</template>
      <el-menu-item index="2-1">常用模板</el-menu-item>
      <el-menu-item index="2-2">自定义模板</el-menu-item>
    </el-sub-menu>

    <el-menu-item index="3">打印</el-menu-item>
    <el-menu-item index="4">签名</el-menu-item>
  </el-menu>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'

const emit = defineEmits(['newRecord', 'saveRecord', 'printRecord', 'exportPdf', 'focusSignature'])

const handleSelect = async (key) => {
  switch(key) {
    case '1-1':
      // 新建病历
      try {
        const confirm = await ElMessageBox.confirm(
          '是否确认新建病历？当前未保存的内容将会丢失。',
          '提示',
          {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        if (confirm === 'confirm') {
          emit('newRecord')
          ElMessage.success('已新建病历')
        }
      } catch (error) {
        // 用户取消操作
      }
      break

    case '1-2':
      // 保存病历
      try {
        emit('saveRecord')
        ElMessage.success('病历已保存到本地')
      } catch (error) {
        ElMessage.error('保存失败：' + error.message)
      }
      break

    case '1-3':
      // 导出PDF
      try {
        emit('exportPdf')
      } catch (error) {
        ElMessage.error('导出失败：' + error.message)
      }
      break

    case '2-1':
      // 常用模板
      ElMessage.info('常用模板功能开发中')
      break

    case '2-2':
      // 自定义模板
      ElMessage.info('自定义模板功能开发中')
      break

    case '3':
      // 打印
      try {
        const confirm = await ElMessageBox.confirm(
          '是否确认打印当前病历？',
          '打印确认',
          {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            type: 'info'
          }
        )
        if (confirm === 'confirm') {
          emit('printRecord')
        }
      } catch (error) {
        // 用户取消操作
      }
      break

    case '4':
      // 签名
      emit('focusSignature')
      ElMessage.info('已聚焦到医师签字区域')
      break
  }
}
</script>

<style scoped>
.medical-header {
  height: 60px;
  padding: 0 20px;
}

.medical-header :deep(.el-menu-item) {
  font-size: 16px;
  padding: 0 25px;
}

.medical-header :deep(.el-sub-menu__title) {
  font-size: 16px;
  padding: 0 25px;
}
</style>
