<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FirstAidKit, Lock, User } from '@element-plus/icons-vue'
import { useAppStore } from '@/store/app'
import { useAuthStore } from '@/store/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const appStore = useAppStore()
const formRef = ref(null)
const loading = ref(false)
const shaking = ref(false)
const form = reactive({ username: 'admin', password: '123456' })

const accounts = [
  { username: 'admin', label: '血库管理员' },
  { username: 'tech', label: '输血科技师' },
  { username: 'doctor', label: '临床医生' },
  { username: 'nurse', label: '护士' },
  { username: 'director', label: '科室主任' },
]

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function shake() {
  shaking.value = false
  requestAnimationFrame(() => {
    shaking.value = true
    window.setTimeout(() => {
      shaking.value = false
    }, 320)
  })
}

async function submit() {
  try {
    await formRef.value.validate()
  } catch {
    shake()
    return
  }
  loading.value = true
  try {
    await auth.login(form)
    await appStore.fetchAlertSummary()
    ElMessage.success(`欢迎回来，${auth.user.real_name}`)
    router.replace(route.query.redirect || '/dashboard')
  } catch {
    shake()
  } finally {
    loading.value = false
  }
}

function useAccount(username) {
  form.username = username
  form.password = '123456'
}
</script>

<template>
  <div class="login-page">
    <div class="orb orb-one" />
    <div class="orb orb-two" />
    <div class="ecg-line" aria-hidden="true">
      <svg viewBox="0 0 900 120" preserveAspectRatio="none">
        <path d="M0 68h210l20-20 24 40 30-68 28 82 26-34h190l18-16 20 32 22-46 22 62 24-32h246" />
      </svg>
    </div>

    <section class="login-brand">
      <div class="brand-line">
        <span class="brand-mark" aria-hidden="true">
          <el-icon :size="24"><FirstAidKit /></el-icon>
        </span>
        <span>BLOOD BANK</span>
      </div>
      <h1>输血管理分系统</h1>
      <p>血液入库、储存、配血、发血、执行与追溯的临床用血闭环</p>
      <div class="brand-points">
        <span>ABO/Rh 相容性校验</span>
        <span>有效期自动预警</span>
        <span>全周期输血追溯</span>
      </div>
      <div class="floating-drops" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
    </section>

    <section class="login-panel">
      <div class="panel-head">
        <span class="eyebrow">临床输血技术规范</span>
        <h2>登录工作台</h2>
        <p>请选择演示账号或输入凭证</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :class="{ shake: shaking }" @submit.prevent="submit">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" size="large" placeholder="请输入用户名" autocomplete="username">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" size="large" type="password" show-password placeholder="演示密码 123456" autocomplete="current-password" @keyup.enter="submit">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button class="login-button" type="primary" size="large" :loading="loading" native-type="submit">
          进入输血管理分系统
        </el-button>
      </el-form>

      <div class="account-grid">
        <button v-for="item in accounts" :key="item.username" type="button" :class="{ active: form.username === item.username }" @click="useAccount(item.username)">
          <strong>{{ item.label }}</strong>
          <span>{{ item.username }}</span>
        </button>
      </div>
      <p class="demo-tip">演示账号密码统一为 <code>123456</code>，仅用于课程演示环境。</p>
    </section>

    <footer class="login-foot">输血管理分系统 · 单机演示版 · 推荐分辨率 1440 × 900</footer>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  display: flex;
  gap: 72px;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 40px 7%;
  overflow: hidden;
  color: #fff;
  background:
    radial-gradient(circle at 15% 15%, rgba(255, 255, 255, 0.15), transparent 34%),
    linear-gradient(135deg, #0f2d66 0%, #173f8f 48%, #2563eb 100%);
}

.login-page::before {
  position: absolute;
  inset: 0;
  pointer-events: none;
  content: "";
  background-image: linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.8), transparent 82%);
}

.orb {
  position: absolute;
  width: 360px;
  height: 360px;
  pointer-events: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  filter: blur(2px);
}

.orb-one {
  top: -170px;
  right: 10%;
}

.orb-two {
  bottom: -240px;
  left: -70px;
  width: 480px;
  height: 480px;
  background: rgba(8, 25, 61, 0.26);
}

.ecg-line {
  position: absolute;
  right: 0;
  bottom: 14%;
  left: 0;
  height: 120px;
  pointer-events: none;
  opacity: 0.16;
}

.ecg-line svg {
  width: 100%;
  height: 100%;
}

.ecg-line path {
  fill: none;
  stroke: #fff;
  stroke-width: 2;
  stroke-dasharray: 1300;
  stroke-dashoffset: 1300;
  animation: draw-ecg 4s linear infinite;
}

@keyframes draw-ecg {
  to {
    stroke-dashoffset: 0;
  }
}

.login-brand {
  position: relative;
  z-index: 1;
  width: 510px;
}

.brand-line {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  color: #1d4ed8;
  background: linear-gradient(145deg, #ffffff, #dbeafe);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 13px;
  box-shadow: 0 8px 24px rgba(5, 20, 55, 0.24), inset 0 1px 0 #fff;
}

.brand-line span {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 4px;
  opacity: 0.78;
}

.login-brand h1 {
  margin: 0;
  font-size: 54px;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: 2px;
  text-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
}

.login-brand > p {
  max-width: 470px;
  margin: 18px 0 26px;
  font-size: 15px;
  line-height: 1.8;
  opacity: 0.78;
}

.brand-points {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.brand-points span {
  padding: 7px 12px;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
}

.floating-drops i {
  position: absolute;
  width: 12px;
  height: 12px;
  background: rgba(255, 255, 255, 0.28);
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  animation: float-drop 5s ease-in-out infinite;
}

.floating-drops i:nth-child(1) {
  top: 38%;
  right: 10%;
}

.floating-drops i:nth-child(2) {
  top: 58%;
  right: 24%;
  width: 8px;
  height: 8px;
  animation-delay: -1.8s;
}

.floating-drops i:nth-child(3) {
  top: 76%;
  right: 5%;
  width: 16px;
  height: 16px;
  animation-delay: -3s;
}

@keyframes float-drop {
  0%,
  100% {
    transform: translateY(0) rotate(-45deg);
  }
  50% {
    transform: translateY(-18px) rotate(-45deg);
  }
}

.login-panel {
  position: relative;
  z-index: 2;
  width: 430px;
  padding: 32px;
  color: #1f2937;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.65);
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(5, 18, 47, 0.28);
  backdrop-filter: blur(18px);
}

.panel-head {
  margin-bottom: 22px;
}

.eyebrow {
  color: #2563eb;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 2px;
}

.panel-head h2 {
  margin: 8px 0 6px;
  color: #0f172a;
  font-size: 28px;
}

.panel-head p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
}

.login-button {
  width: 100%;
  margin-top: 4px;
  font-weight: 700;
  letter-spacing: 1px;
}

.account-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  margin-top: 22px;
}

.account-grid button {
  padding: 9px 2px;
  color: #64748b;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  cursor: pointer;
}

.account-grid button:hover,
.account-grid button.active {
  color: #2563eb;
  background: #eff6ff;
  border-color: #93c5fd;
}

.account-grid strong,
.account-grid span {
  display: block;
  font-size: 10px;
  line-height: 1.5;
}

.account-grid span {
  color: #94a3b8;
  font-size: 9px;
}

.demo-tip {
  margin: 16px 0 0;
  color: #94a3b8;
  font-size: 10px;
  text-align: center;
}

.demo-tip code {
  color: #2563eb;
}

.login-foot {
  position: absolute;
  bottom: 22px;
  left: 0;
  width: 100%;
  color: rgba(255, 255, 255, 0.48);
  font-size: 10px;
  text-align: center;
}
</style>
