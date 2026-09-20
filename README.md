# 医院信息系统 —— 就诊记录模块

## 一、项目说明

- 仓库地址：https://github.com/yunyucn/YiYuanXinXi
- 技术栈：原生 HTML + CSS + JavaScript，单文件页面，无构建依赖
- 页面清单：
  - `index.html`：系统首页，提供各业务模块入口
  - `visit-records.html`：就诊记录页面（本次开发成果）
- 运行方式：直接用浏览器打开 `index.html` 即可，无需启动任何服务

## 二、分支模型

| 分支 | 用途 | 是否推送 |
| --- | --- | --- |
| `main` | 主干分支，始终保持可用状态 | 是 |
| `feature/visit-records` | 个人开发分支，就诊记录页面开发 | 是 |
| `demo/rollback` | 本地回滚演练分支，仅用于演示回滚操作 | 否 |

## 三、个人分支开发并合并回主分支的过程

### 1. 从主干拉出个人分支

```bash
git checkout main
git checkout -b feature/visit-records
```

### 2. 在个人分支上按功能拆分提交（共 3 次规范提交）

| 序号 | 提交哈希 | 提交信息 | 主要内容 |
| --- | --- | --- | --- |
| 1 | `41ee2ef` | `feat(就诊记录): 新增就诊记录页面结构与静态列表数据` | 顶栏、侧边导航、面包屑、患者信息卡片、统计概览、筛选表单、记录表格、分页条、详情弹窗容器 |
| 2 | `304779c` | `style(就诊记录): 完善页面布局与视觉样式` | 页面完整样式、类型与状态标签、按钮与分页样式、弹窗样式、窄屏适配 |
| 3 | `08baf31` | `feat(就诊记录): 实现筛选查询、分页与就诊详情弹窗交互` | 12 条就诊数据、组合筛选、前端分页、详情弹窗（主诉/现病史/体格检查/医嘱/处方明细） |

提交信息统一采用 `<type>(<scope>): <subject>` 的规范格式，`type` 取 `feat` / `style` / `fix` / `chore` 等。

### 3. 合并回主分支

```bash
git checkout main
git merge --no-ff feature/visit-records -m "merge: 合并 feature/visit-records 分支到 main"
```

使用 `--no-ff` 参数保留分支历史，合并后提交图为：

```text
*   e47484f (HEAD -> main) merge: 合并 feature/visit-records 分支到 main
|\
| * 08baf31 (feature/visit-records) feat(就诊记录): 实现筛选查询、分页与就诊详情弹窗交互
| * 304779c style(就诊记录): 完善页面布局与视觉样式
| * 41ee2ef feat(就诊记录): 新增就诊记录页面结构与静态列表数据
|/
* 4f891e3 chore: 初始化医院信息系统项目骨架
```

### 4. 推送分支

```bash
git push -u origin main
git push -u origin feature/visit-records
```

## 四、回滚演练记录

### 场景一：撤销工作区中尚未提交的改动

误改了 `index.html` 中顶栏文字，尚未提交，使用 `git checkout` 丢弃改动。

```bash
# 回滚前
git status --short
#  M index.html
git diff -- index.html
# -  <div class="topbar">医院信息系统</div>
# +  <div class="topbar">医院信息系统（测试改动）</div>

# 执行回滚
git checkout -- index.html

# 回滚后
git status --short        # 无输出，工作区已干净
```

对比结论：文件内容恢复到最近一次提交的版本，未产生任何新提交。

### 场景二：撤销已经提交的错误改动

提交了一次错误改动（把首页链接地址由 `visit-records.html` 误写为 `visit-record.html`），使用 `git revert` 生成反向提交来撤销。

```bash
# 错误提交
git log --oneline -2
# aaa7bc6 fix(首页): 调整就诊记录入口链接地址
# e47484f merge: 合并 feature/visit-records 分支到 main

# 执行回滚
git revert --no-edit HEAD

# 回滚后
git log --oneline -3
# 09d3393 Revert "fix(首页): 调整就诊记录入口链接地址"
# aaa7bc6 fix(首页): 调整就诊记录入口链接地址
# e47484f merge: 合并 feature/visit-records 分支到 main
```

对比结论：`git revert` 不删除原有提交，而是新增一条反向提交，历史记录完整可追溯，适合已推送到远程的提交回滚；`git reset` 会改写历史，只适合尚未推送的本地提交。

## 五、就诊记录页面功能说明

- 患者基本信息：姓名、性别、年龄、病历号、医保类型、联系电话及过敏史提示
- 就诊统计概览：就诊总次数、门诊/急诊/住院次数、最近就诊时间
- 组合筛选：就诊类型、就诊科室、起止日期、关键字（就诊号/医生/诊断）四项条件可叠加，查询结果与记录条数联动更新
- 分页浏览：每页 6 条，支持上一页/下一页与页码跳转，筛选后自动回到第一页
- 就诊详情：点击“查看详情”弹出详情窗口，展示主诉、现病史、体格检查、医嘱与处方明细，支持遮罩点击、关闭按钮与 `Esc` 键关闭
- 列表标签：就诊类型（门诊/急诊/住院）与就诊状态（已完成/进行中）使用不同颜色区分

## 六、验证方式

1. 用浏览器打开 `index.html`，点击“就诊记录”进入页面
2. 在筛选区选择就诊类型为“门诊”，点击“查询”，列表仅显示门诊记录
3. 在关键字输入框输入“李静”后查询，列表仅显示该医生的接诊记录
4. 点击“重置”恢复全部 12 条记录，点击“下一页”验证分页
5. 点击任意一行的“查看详情”，检查详情弹窗内容并尝试用 `Esc` 关闭
