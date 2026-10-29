<script setup>
/** 输血记录单打印页：合并发血记录、配血结果和申请单信息。 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Printer, ArrowLeft } from '@element-plus/icons-vue'
import { issueApi, requestApi } from '@/api'
import { formatDate, formatDateTime, todayString } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const issue = ref(null)
const request = ref(null)
const printedAt = ref('')

/** 生成本地时区的打印时间文本。 */
function localNowText() {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

/** 将每袋血与对应的配血结果合并为打印行。 */
const bagRows = computed(() => {
  const matches = issue.value?.cross_matches || []
  return (issue.value?.bags || []).map((bag) => {
    const match = matches.find((item) => item.bag_id === bag.id)
    return { ...bag, match }
  })
})

/** 加载发血记录和申请单详情，供 A4 记录单展示。 */
async function loadData() {
  loading.value = true
  printedAt.value = localNowText()
  try {
    issue.value = await issueApi.detail(route.params.id)
    request.value = await requestApi.detail(issue.value.request_id)
  } catch (err) {
    error.value = err.message || '输血记录加载失败'
  } finally {
    loading.value = false
  }
}

/** 调用浏览器打印记录单。 */
function printPage() {
  window.print()
}

/** 返回上一页；无历史记录时回到发血工作台。 */
function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/issue')
}

onMounted(loadData)
</script>

<template>
  <div class="print-shell">
    <div class="toolbar no-print">
      <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
      <span>输血记录单预览 · A4</span>
      <el-button type="primary" :icon="Printer" @click="printPage">打印记录单</el-button>
    </div>

    <div v-loading="loading" class="print-paper">
      <template v-if="issue && request">
        <header class="record-header">
          <div class="hospital-mark">
            <span class="cross">✚</span>
            <div>
              <h1>仁和医院</h1>
              <p>临床输血记录单</p>
            </div>
          </div>
          <div class="record-meta">
            <span>记录单号</span>
            <strong>{{ issue.record_no }}</strong>
            <span>打印日期</span>
            <strong>{{ todayString() }}</strong>
          </div>
        </header>

        <section class="record-section">
          <h2>一、患者与申请信息</h2>
          <div class="info-grid">
            <div><span>患者姓名</span><strong>{{ request.patient_name }}</strong></div>
            <div><span>住院号</span><strong>{{ request.admission_no }}</strong></div>
            <div><span>科室</span><strong>{{ request.department }}</strong></div>
            <div><span>床号</span><strong>{{ request.bed_no || '-' }}</strong></div>
            <div><span>患者血型</span><strong>{{ request.blood_type }} / {{ request.rh }}</strong></div>
            <div><span>申请单号</span><strong>{{ request.request_no }}</strong></div>
            <div class="full"><span>临床诊断</span><strong>{{ request.diagnosis }}</strong></div>
            <div><span>申请品种</span><strong>{{ request.product_name }}</strong></div>
            <div><span>申请量</span><strong>{{ request.quantity }}{{ request.quantity_unit }}</strong></div>
          </div>
        </section>

        <section class="record-section">
          <h2>二、血液发放明细</h2>
          <table class="record-table">
            <thead>
              <tr>
                <th style="width: 8%">序号</th>
                <th style="width: 18%">储血号</th>
                <th style="width: 13%">品种</th>
                <th style="width: 12%">血型/Rh</th>
                <th style="width: 10%">规格</th>
                <th style="width: 9%">数量</th>
                <th style="width: 14%">有效期</th>
                <th style="width: 16%">配血结果</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(bag, index) in bagRows" :key="bag.id">
                <td>{{ index + 1 }}</td>
                <td>{{ bag.bag_no }}</td>
                <td>{{ bag.product_name }}</td>
                <td>{{ bag.blood_type }} / {{ bag.rh }}</td>
                <td>{{ bag.specification }}</td>
                <td>{{ bag.quantity }}{{ request.quantity_unit }}</td>
                <td>{{ formatDate(bag.expiry_date) }}</td>
                <td>{{ bag.match?.compatibility || '相容' }}{{ bag.match?.method ? `（${bag.match.method}）` : '' }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="record-section">
          <h2>三、发血核对</h2>
          <div class="check-list">
            <label v-for="item in issue.check_items" :key="item"><span>☑</span>{{ item }}</label>
          </div>
          <div class="info-grid compact">
            <div><span>发血人</span><strong>{{ issue.issued_by }}</strong></div>
            <div><span>发血时间</span><strong>{{ formatDateTime(issue.issued_at) }}</strong></div>
            <div><span>领血护士</span><strong>{{ issue.pickup_nurse }}</strong></div>
            <div><span>执行状态</span><strong>{{ issue.execution_status }}</strong></div>
            <div><span>执行护士</span><strong>{{ issue.executed_by || '-' }}</strong></div>
            <div><span>执行时间</span><strong>{{ formatDateTime(issue.executed_at) }}</strong></div>
          </div>
        </section>

        <section v-if="issue.adverse_reactions?.length" class="record-section">
          <h2>四、输血不良反应记录</h2>
          <table class="record-table">
            <thead><tr><th>时间</th><th>储血号</th><th>类型</th><th>程度</th><th>处理措施</th><th>上报血站</th></tr></thead>
            <tbody>
              <tr v-for="item in issue.adverse_reactions" :key="item.id">
                <td>{{ formatDateTime(item.occurred_at) }}</td>
                <td>{{ item.bag_no }}</td>
                <td>{{ item.reaction_type }}</td>
                <td>{{ item.severity }}</td>
                <td>{{ item.treatment }}</td>
                <td>{{ item.reported_to_station ? '是' : '否' }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="record-section signature-section">
          <div><span>发血者签名</span><i /></div>
          <div><span>领血护士签名</span><i /></div>
          <div><span>执行护士签名</span><i /></div>
          <div><span>核对者签名</span><i /></div>
        </section>

        <footer class="record-footer">
          <span>本记录由输血管理分系统生成</span>
          <span>打印时间：{{ printedAt }}</span>
        </footer>
      </template>
      <div v-else-if="error" class="load-error">{{ error }}</div>
    </div>
  </div>
</template>

<style>
.print-shell {
  min-height: 100vh;
  padding: 22px;
  overflow: auto;
  background: #e9eef5;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 210mm;
  margin: 0 auto 14px;
  color: #475569;
  font-size: 12px;
}

.print-paper {
  width: 210mm;
  min-height: 297mm;
  padding: 14mm 16mm;
  margin: 0 auto;
  color: #111827;
  background: #fff;
  box-shadow: 0 10px 32px rgba(15, 23, 42, 0.16);
}

.record-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 2px solid #111827;
}

.hospital-mark {
  display: flex;
  gap: 10px;
  align-items: center;
}

.cross {
  color: #b91c1c;
  font-size: 34px;
  font-weight: 700;
  line-height: 1;
}

.hospital-mark h1 {
  margin: 0;
  font-size: 24px;
  letter-spacing: 4px;
}

.hospital-mark p {
  margin: 4px 0 0;
  font-size: 13px;
  letter-spacing: 5px;
}

.record-meta {
  display: grid;
  grid-template-columns: auto auto;
  gap: 4px 10px;
  font-size: 10px;
  text-align: right;
}

.record-meta span {
  color: #64748b;
}

.record-meta strong {
  font-variant-numeric: tabular-nums;
}

.record-section {
  margin-top: 14px;
}

.record-section h2 {
  padding: 5px 8px;
  margin: 0 0 8px;
  font-size: 12px;
  background: #f1f5f9;
  border-left: 3px solid #1d4ed8;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 1px solid #cbd5e1;
  border-left: 1px solid #cbd5e1;
}

.info-grid > div {
  display: flex;
  min-height: 29px;
  border-right: 1px solid #cbd5e1;
  border-bottom: 1px solid #cbd5e1;
}

.info-grid span {
  flex: 0 0 78px;
  padding: 7px 8px;
  color: #475569;
  font-size: 10px;
  background: #f8fafc;
  border-right: 1px solid #cbd5e1;
}

.info-grid strong {
  flex: 1;
  padding: 7px 8px;
  font-size: 10px;
  font-weight: 500;
  word-break: break-all;
}

.info-grid .full {
  grid-column: 1 / -1;
}

.info-grid.compact {
  margin-top: 8px;
}

.record-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.record-table th,
.record-table td {
  padding: 6px 5px;
  font-size: 9px;
  line-height: 1.45;
  text-align: center;
  word-break: break-all;
  border: 1px solid #cbd5e1;
}

.record-table th {
  color: #334155;
  font-weight: 600;
  background: #f1f5f9;
}

.check-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 5px 14px;
  padding: 8px 10px;
  font-size: 10px;
  border: 1px solid #cbd5e1;
}

.check-list label {
  display: flex;
  gap: 5px;
  align-items: center;
}

.check-list span {
  color: #15803d;
  font-weight: 700;
}

.signature-section {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px 40px;
  padding-top: 22px;
}

.signature-section > div {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  font-size: 10px;
}

.signature-section span {
  flex: 0 0 auto;
}

.signature-section i {
  flex: 1;
  height: 1px;
  border-bottom: 1px solid #64748b;
}

.record-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
  margin-top: 24px;
  color: #64748b;
  font-size: 9px;
  border-top: 1px solid #cbd5e1;
}

.load-error {
  padding: 80px 0;
  color: #b91c1c;
  text-align: center;
}

@page {
  size: A4;
  margin: 10mm;
}

@media print {
  .print-shell {
    padding: 0;
    background: #fff;
  }

  .print-paper {
    width: auto;
    min-height: auto;
    padding: 0;
    margin: 0;
    box-shadow: none;
  }
}
</style>
