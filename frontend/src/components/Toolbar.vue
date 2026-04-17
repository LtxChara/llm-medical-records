<template>
  <footer class="toolbar">
    <div class="left-section">
      <el-select v-model="selectedModel" placeholder="AI模型选择">
        <el-option label="医疗BERT" value="bert" />
        <el-option label="临床GPT" value="gpt" />
      </el-select>
    </div>

    <div class="right-section">
      <el-button type="primary">提交</el-button>
      <el-button>打印</el-button>
      <el-button>导出</el-button>
    </div>
  </footer>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  padding: 12px 24px;
  background: white;
  border-top: 1px solid #eee;
}
</style>