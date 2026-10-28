# 输血管理分系统技术方案与数据库设计

## 1. 建设目标与边界

系统面向医院输血科与临床用血场景，围绕「入库 → 库存与效期 → 输血申请 → 配血 → 发血 → 护士执行 → 不良反应 → 全周期追溯 → 报废 → 统计」构建闭环。采用单机部署，前端仅适配 PC 桌面端，不引入微服务、容器、缓存中间件或外部云服务，确保课堂演示环境可离线复现。

## 2. 总体架构

| 层次 | 技术选型 | 职责 |
| --- | --- | --- |
| 表现层 | Vue 3 + Vite + Element Plus + ECharts | 业务页面、状态反馈、图表与打印视图 |
| 状态与路由 | Pinia + Vue Router | 登录态、主题与侧边栏状态、按角色守卫 |
| 接口层 | Axios + Flask Blueprint | 统一响应、错误提示、模块化 API |
| 领域层 | Python 业务函数 | 相容性校验、预警扫描、四项发血核对 |
| 数据层 | SQLAlchemy + SQLite | 事务持久化、种子数据、测试内存库 |

后端采用应用工厂 `create_app()`，注册 JWT、CORS、蓝图与 APScheduler。前端路由按业务模块懒加载，主布局使用 `Suspense` 与路由加载骨架，避免首次进入业务页时整页白屏。

## 3. 数据模型

核心表与关键字段如下：

- `blood_bag`：储血号、品种、ABO/Rh、规格、数量、采血与有效期、复检七项、状态、冰箱、献血者、入库人。
- `fridge`：冰箱编号、名称、位置、容量、状态。
- `transfusion_request`：申请单号、患者信息、血型与 Rh、诊断、品种与数量、紧急程度、状态、申请医生。
- `cross_match`：申请单、血袋、配血方法、主侧与次侧、相容性、技师、时间、备注。
- `issue_record`：申请单、发血血袋 JSON、发血人、领血护士、核对项、执行状态、执行确认时间。
- `adverse_reaction`：发血记录、血袋、住院号、反应类型、程度、处理措施、上报状态、记录护士。
- `scrap_record`：血袋、原因、经手人、审批人、审批状态与日期。
- `alert` 与 `scan_log`：预警类型与级别、关联对象、处理状态、扫描时间与扫描结果。
- `user`、`role`、`department`、`blood_product_dict`、`operation_log`：账号权限、科室字典、品种保质期与安全库存、审计日志。

## 4. 关键状态机

### 4.1 血袋

`在库 → 备血锁定 → 已发血`；`在库/已过期 → 已报废`；扫描到期时 `在库 → 已过期`。备血锁定、已发血、已报废血袋不可再次申请报废。

### 4.2 申请单

`待配血 → 配血中 → 已备血 → 已发血 → 已完成`；待配血或配血中可取消。取消配血会将血袋解锁回在库，申请单回到待配血。

### 4.3 发血记录

发血成功后执行状态为 `待执行`，护士确认后变为 `已完成`。已完成记录才允许上报输血不良反应。

## 5. 核心规则

### 5.1 ABO/Rh 相容性

`check_compatibility(recipient, donor, product_type)` 返回 `compatible / level / reason`：

- 红细胞类：受者 A 接受 A/O，B 接受 B/O，AB 接受 A/B/AB/O，O 仅接受 O。
- 血浆与冷沉淀：方向相反，受者 A 接受 A/AB，B 接受 B/AB，AB 仅接受 AB，O 接受全部。
- 血小板：同型优先，不同型返回提示级警告。
- Rh 阴性受者仅接受 Rh 阴性；Rh 阳性受者接受 Rh 阴性血返回提示。
- 前端按 level 渲染绿、黄、红横幅；后端提交时二次校验，fail 直接返回 400。

### 5.2 发血四项核对

后端逐项验证申请单状态、血袋锁定归属、效期与报废状态、相容配血记录，任一失败即拦截，避免仅依赖前端校验。

### 5.3 预警扫描

APScheduler 启动即扫描，之后每 10 分钟执行。扫描覆盖临期、过期、低库存、待配血超时、复检未完成五类预警；同对象同类型未处理预警去重。铃铛红点仅统计未处理的警告与严重预警。

## 6. API 设计

接口统一以 `/api` 为前缀，返回 `{ code, msg, data }`，分页数据包含 `items / total / page / page_size`。

- `POST /auth/login`、`GET /auth/me`
- `GET/POST /bags`、`GET /bags/<id>`、`POST /bags/batch`
- `GET/POST /requests`、`POST /requests/<id>/cancel`
- `GET /cross-match/pending`、`POST /cross-match`、`POST /cross-match/<id>/cancel`
- `GET /issue/pending`、`POST /issue`、`POST /issue/<id>/execute`
- `GET/POST /adverse`、`GET /trace/<admission_no>`
- `GET/POST /scrap`、`POST /scrap/<id>/approve|reject`
- `GET /alerts`、`GET /alerts/summary`、`POST /alerts/refresh`、`POST /alerts/<id>/handle`
- `GET /reports/overview`、`GET /reports/export`
- `GET/POST/PUT /system/*`

所有写接口按角色增加 RBAC 装饰器，并写入操作日志。

## 7. 权限矩阵

| 角色 | 入库 | 配血/发血 | 申请 | 执行 | 不良反应 | 报废审批 | 报表 | 系统管理 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admin | 是 | 是 | 是 | 是 | 是 | 是 | 是 | 是 |
| tech | 是 | 是 | 查看 | - | 查看 | 申请 | - | - |
| doctor | - | - | 是 | - | - | - | - | - |
| nurse | - | 领血核对 | - | 是 | 是 | - | - | - |
| director | 查看 | 查看 | 查看 | - | 查看 | 是 | 是 | - |

## 8. 前端视觉与交互规范

- 业务页采用医疗蓝主色、1px 描边、6px 圆角与克制的顶部渐变光，不使用大面积玻璃拟态。
- 页面标题、统计卡叠加低透明度内联 SVG 纹理，包含心电、血细胞与医疗十字图案，颜色随业务语义在蓝、青、琥珀、玫红之间渐变。
- 关键操作按钮采用渐变背景、Element Plus SVG 图标与悬停扫光，普通按钮悬停时使用浅色渐变和轻微上浮。
- 图标统一使用 Element Plus 组件并固定尺寸，避免自绘图标比例漂移。
- 表格操作列统一由 `TableActions` 组件渲染，最多三个操作保持单行，超出自动折叠到「更多」，解决不同分辨率下按钮换行。
- 路由懒加载配合 `RouteLoading` 骨架与 `Suspense`，并增加路由级错误兜底，阻止异常导致整页白屏。
- 交互遵循 `prefers-reduced-motion`，暗色模式提供独立渐变与边框变量。

## 9. 测试与验收

- 后端使用 `pytest` 运行现有 `unittest` 风格用例，覆盖登录鉴权、系统管理越权、相容性、入库复检、配血发血执行、不良反应、追溯、预警去重与报表权限。
- `backend/tests/e2e_api.py` 通过真实 HTTP 请求跑通主流程，并反查发血审计日志和验证普通角色访问系统管理接口返回 403。
- 前端执行 `npm run build` 验证按需组件、路由与样式编译。
- 课堂验收使用 1440×900，兼顾 1280×720 操作列与表格滚动表现。
