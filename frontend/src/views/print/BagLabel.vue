<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Printer } from '@element-plus/icons-vue'
import QRCode from 'qrcode'
import { bagApi } from '@/api'
import { formatDate } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const bag = ref(null)
const qrCode = ref('')

const retestEntries = computed(() => {
  const labels = {
    blood_type: '定血型',
    rh: 'Rh',
    alt: 'ALT',
    hiv: 'HIV',
    syphilis: '梅毒',
    hbv: '乙肝',
    hcv: '丙肝',
  }
  return Object.entries(bag.value?.retest_result || {}).map(([key, value]) => ({ label: labels[key] || key, value }))
})

const quantityUnit = computed(() => (bag.value?.product_name === '血浆' ? 'ml' : 'U'))

async function loadBag() {
  loading.value = true
  try {
    bag.value = await bagApi.detail(route.params.id)
    const payload = JSON.stringify({
      bag_no: bag.value.bag_no,
      product_name: bag.value.product_name,
      blood_type: bag.value.blood_type,
      rh: bag.value.rh,
      expiry_date: bag.value.expiry_date,
    })
    qrCode.value = await QRCode.toDataURL(payload, { width: 220, margin: 1, errorCorrectionLevel: 'M' })
  } catch (err) {
    error.value = err.message || '血袋标签加载失败'
  } finally {
    loading.value = false
  }
}

function printPage() {
  window.print()
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/stock')
}

onMounted(loadBag)
</script>

<template>
  <div class="label-shell">
    <div class="label-toolbar no-print">
      <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
      <span>血袋标签预览 · 100mm × 70mm</span>
      <el-button type="primary" :icon="Printer" @click="printPage">打印袋签</el-button>
    </div>

    <div v-loading="loading" class="label-paper">
      <div v-if="bag" class="blood-label">
        <header class="label-header">
          <div class="label-brand">
            <span class="cross">✚</span>
            <div><strong>仁和医院输血科</strong><small>BLOOD COMPONENT LABEL</small></div>
          </div>
          <span class="label-title">血液制品标签</span>
        </header>

        <div class="label-body">
          <div class="qr-block">
            <img v-if="qrCode" :src="qrCode" alt="血袋二维码" />
            <span>{{ bag.bag_no }}</span>
          </div>
          <div class="label-main">
            <div class="blood-type">
              <strong>{{ bag.blood_type }}</strong>
              <span>{{ bag.rh === 'D阴性' ? 'RhD 阴性' : 'RhD 阳性' }}</span>
            </div>
            <div class="product-name">{{ bag.product_name }}</div>
            <div class="label-grid">
              <div><span>规格</span><strong>{{ bag.specification }}</strong></div>
              <div><span>数量</span><strong>{{ bag.quantity }}{{ quantityUnit }}</strong></div>
              <div><span>采血日期</span><strong>{{ formatDate(bag.collection_date) }}</strong></div>
              <div><span>有效期至</span><strong class="expiry">{{ formatDate(bag.expiry_date) }}</strong></div>
              <div><span>献血者编号</span><strong>{{ bag.donor_no }}</strong></div>
              <div><span>血站</span><strong>{{ bag.collection_unit }}</strong></div>
              <div><span>储存位置</span><strong>{{ bag.fridge_code || bag.storage_location || '-' }}</strong></div>
              <div><span>状态</span><strong>{{ bag.status }}</strong></div>
            </div>
          </div>
        </div>

        <div class="retest-strip">
          <span>复检：</span>
          <i v-for="item in retestEntries" :key="item.label" :class="item.value === '合格' ? 'ok' : 'warn'">{{ item.label }} {{ item.value }}</i>
          <i v-if="!retestEntries.length" class="warn">复检结果未录入</i>
        </div>

        <footer class="label-footer">
          <strong>输血前请双人核对患者与血袋信息</strong>
          <span>严禁将血液加热或加入药物 · 发现异常立即停止输注</span>
        </footer>
      </div>
      <div v-else-if="error" class="label-error">{{ error }}</div>
    </div>
  </div>
</template>

<style>
.label-shell {
  min-height: 100vh;
  padding: 22px;
  overflow: auto;
  background: #e9eef5;
}

.label-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 210mm;
  margin: 0 auto 14px;
  color: #475569;
  font-size: 12px;
}

.label-paper {
  width: 210mm;
  min-height: 297mm;
  padding: 12mm;
  margin: 0 auto;
  background: #fff;
  box-shadow: 0 10px 32px rgba(15, 23, 42, 0.16);
}

.blood-label {
  width: 100mm;
  height: 70mm;
  overflow: hidden;
  color: #111827;
  background: #fff;
  border: 1.5px solid #111827;
}

.label-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2.5mm 3mm;
  color: #fff;
  background: #991b1b;
}

.label-brand {
  display: flex;
  gap: 2mm;
  align-items: center;
}

.label-brand .cross {
  font-size: 18px;
  font-weight: 700;
}

.label-brand strong,
.label-brand small {
  display: block;
}

.label-brand strong {
  font-size: 9px;
  letter-spacing: 0.5px;
}

.label-brand small {
  margin-top: 0.5mm;
  font-size: 5px;
  letter-spacing: 0.6px;
  opacity: 0.76;
}

.label-title {
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 1px;
}

.label-body {
  display: grid;
  grid-template-columns: 27mm minmax(0, 1fr);
  gap: 2.5mm;
  padding: 2.5mm 3mm 1.5mm;
}

.qr-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
}

.qr-block img {
  width: 24mm;
  height: 24mm;
}

.qr-block span {
  margin-top: 1mm;
  font-size: 6px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.blood-type {
  display: flex;
  gap: 2mm;
  align-items: baseline;
}

.blood-type strong {
  color: #b91c1c;
  font-size: 24px;
  line-height: 1;
}

.blood-type span {
  color: #334155;
  font-size: 7px;
  font-weight: 700;
}

.product-name {
  padding: 1mm 0 1.2mm;
  font-size: 12px;
  font-weight: 700;
  border-bottom: 1px solid #cbd5e1;
}

.label-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5mm 2mm;
  padding-top: 1mm;
}

.label-grid > div {
  display: flex;
  gap: 1mm;
  min-width: 0;
  font-size: 5.5px;
  line-height: 1.35;
}

.label-grid span {
  flex: 0 0 9mm;
  color: #64748b;
}

.label-grid strong {
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.label-grid .expiry {
  color: #b91c1c;
}

.retest-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8mm 2mm;
  padding: 1.5mm 3mm;
  margin: 0 3mm;
  font-size: 5px;
  border-top: 1px dashed #cbd5e1;
  border-bottom: 1px dashed #cbd5e1;
}

.retest-strip span {
  color: #64748b;
}

.retest-strip i {
  font-style: normal;
}

.retest-strip i.ok {
  color: #15803d;
}

.retest-strip i.warn {
  color: #b45309;
}

.label-footer {
  padding: 1.2mm 3mm;
  text-align: center;
}

.label-footer strong,
.label-footer span {
  display: block;
}

.label-footer strong {
  color: #b91c1c;
  font-size: 6px;
  letter-spacing: 0.4px;
}

.label-footer span {
  margin-top: 0.5mm;
  color: #64748b;
  font-size: 4.5px;
}

.label-error {
  padding: 80px 0;
  color: #b91c1c;
  text-align: center;
}

@page {
  size: A4;
  margin: 10mm;
}

@media print {
  .label-shell {
    padding: 0;
    background: #fff;
  }

  .label-paper {
    width: auto;
    min-height: auto;
    padding: 0;
    margin: 0;
    box-shadow: none;
  }
}
</style>
