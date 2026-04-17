const BASE_URL = 'http://localhost:5000'

/**
 * 调用后端 /process 接口，启动病历分析
 * @param {string} session_id
 * @param {string} text
 * @returns {Promise<object>} 后端返回的 JSON 对象
 */
export async function analyzeText(session_id, text) {
  const response = await fetch(`${BASE_URL}/process`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({ session_id, text })
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`HTTP错误: ${response.status} - ${errorText}`)
  }

  return await response.json()
}

/**
 * 调用后端 /supplement 接口，补充缺失的医疗字段信息
 * @param {string} session_id
 * @param {string} field
 * @param {string} text
 * @returns {Promise<object>} 后端返回的 JSON 对象
 */
export async function supplementText(session_id, field, text) {
  const response = await fetch(`${BASE_URL}/supplement`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({ session_id, field, text })
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`HTTP错误: ${response.status} - ${errorText}`)
  }

  return await response.json()
}

/**
 * 调用后端 /generate_doc 接口，生成并下载 Word 文档
 * @param {object} input - 符合 GenerateDocRequestInput 格式的对象
 * @returns {Promise<void>}
 */
export async function generateDoc(input) {
  const response = await fetch(`${BASE_URL}/generate_doc`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/octet-stream'
    },
    body: JSON.stringify({ input })
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`HTTP错误: ${response.status} - ${errorText}`)
  }

  // 从 Content-Disposition 提取文件名
  const disposition = response.headers.get('Content-Disposition')
  let filename = '康复医疗报告.docx'
  if (disposition) {
    const filenameStarMatch = disposition.match(/filename\*=UTF-8''(.+)/)
    if (filenameStarMatch && filenameStarMatch[1]) {
      filename = decodeURIComponent(filenameStarMatch[1])
    } else {
      const filenameMatch = disposition.match(/filename="(.+)"/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1]
      }
    }
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
