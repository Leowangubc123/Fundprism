# 基金对比功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按任务逐步实施。任务使用 `- [ ]` 复选框语法以便跟踪。

**Goal:** 实现基金多选对比功能：总览页可选中多只基金，跳转至对比页查看并排指标与同图净值走势。

**Architecture:** 前端通过 URL query `ids` 传递选中基金，后端提供批量查询接口 `GET /api/funds/compare` 返回基金详情及历史净值；前端复用已有的 `vue-chartjs` 渲染多线折线图。

**Tech Stack:** FastAPI + SQLAlchemy + PostgreSQL（后端），Vue 3 + Pinia + Vue Router + Tailwind CSS + Chart.js（前端），pytest（测试）。

---

## 文件结构

- 修改：
  - `backend/app/schemas.py` — 添加对比相关 Pydantic 模型。
  - `backend/app/routers/funds.py` — 添加 `GET /api/funds/compare` 端点。
  - `frontend/src/views/OverviewView.vue` — 添加复选框、选中状态、对比按钮。
  - `frontend/src/views/CompareView.vue` — 重写为完整对比页。
- 新增：
  - `backend/tests/conftest.py` — 测试数据库与 FastAPI TestClient  fixtures。
  - `backend/tests/test_compare.py` — 对比接口测试。
  - `frontend/src/components/CompareMetrics.vue` — 并排指标组件。
  - `frontend/src/components/CompareChart.vue` — 多线净值图表组件。

---

### Task 1: 添加对比接口数据模型

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: 在文件末尾追加模型**

```python
class FundCompareItem(FundDetail):
    manager: Optional[str]
    nav_history: List[NavHistoryItem]

    class Config:
        from_attributes = True


class FundCompareResponse(BaseModel):
    funds: List[FundCompareItem]
```

- [ ] **Step 2: 保存文件**

---

### Task 2: 实现后端对比接口

**Files:**
- Modify: `backend/app/routers/funds.py`

- [ ] **Step 1: 在文件顶部导入新模型与 List/UUID 校验工具**

修改后顶部导入区应为：

```python
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.schemas import FundCompareItem, FundCompareResponse, FundDetail, FundListItem, NavHistoryItem
from app.security import get_current_user
```

- [ ] **Step 2: 在 `get_nav_history` 函数之后添加 `/compare` 端点**

```python
@router.get("/compare", response_model=FundCompareResponse)
def compare_funds(
    ids: List[UUID] = Query(default_factory=list),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not ids:
        raise HTTPException(status_code=400, detail="至少需要选择一只基金")
    if len(ids) > 5:
        raise HTTPException(status_code=400, detail="最多只能选择 5 只基金进行对比")

    latest = _latest_performance_subquery(db)
    rows = (
        db.query(Fund, FundCode, FundPerformance)
        .join(FundCode, FundCode.fund_id == Fund.id)
        .filter(FundCode.is_primary.is_(True))
        .filter(Fund.id.in_(ids))
        .outerjoin(
            latest,
            latest.c.fund_code_id == FundCode.id,
        )
        .outerjoin(
            FundPerformance,
            (FundPerformance.fund_code_id == FundCode.id)
            & (FundPerformance.date == latest.c.max_date),
        )
        .all()
    )

    result = []
    for fund, code, perf in rows:
        history_rows = (
            db.query(FundPerformance)
            .filter(FundPerformance.fund_code_id == code.id)
            .order_by(FundPerformance.date)
            .limit(90)
            .all()
        )
        nav_history = [
            NavHistoryItem(date=r.date, nav=float(r.nav))
            for r in history_rows
            if r.nav is not None
        ]
        result.append(
            FundCompareItem(
                id=fund.id,
                name=fund.name,
                code=code.code,
                category=fund.category,
                nav=float(perf.nav) if perf and perf.nav is not None else None,
                daily_return=float(perf.daily_return) if perf and perf.daily_return is not None else None,
                manager=fund.manager,
                nav_history=nav_history,
            )
        )

    return {"funds": result}
```

- [ ] **Step 3: 运行后端并访问 Swagger 验证接口存在**

Run: `cd backend && uvicorn app.main:app --reload --port 8000`
Open: `http://localhost:8000/docs`
Expected: `GET /api/funds/compare` 可见。

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/funds.py
git commit -m "feat(backend): add fund compare endpoint"
```

---

### Task 3: 编写后端对比接口测试

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_compare.py`

- [ ] **Step 1: 创建测试 fixtures**

`backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.user import User
from app.security import create_access_token, get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_user(db):
    user = User(username="tester", hashed_password=get_password_hash("pass"), role="sales")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(auth_user):
    token = create_access_token({"sub": str(auth_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def sample_funds(db):
    fund_a = Fund(name="基金 A", category="混合型", risk_level="中", manager="张三")
    fund_b = Fund(name="基金 B", category="股票型", risk_level="高", manager="李四")
    db.add_all([fund_a, fund_b])
    db.commit()
    db.refresh(fund_a)
    db.refresh(fund_b)

    code_a = FundCode(fund_id=fund_a.id, code="000001", is_primary=True)
    code_b = FundCode(fund_id=fund_b.id, code="000002", is_primary=True)
    db.add_all([code_a, code_b])
    db.commit()
    db.refresh(code_a)
    db.refresh(code_b)

    performances = [
        FundPerformance(fund_code_id=code_a.id, date="2026-08-01", nav=1.1000, daily_return=0.0100),
        FundPerformance(fund_code_id=code_a.id, date="2026-08-02", nav=1.1100, daily_return=0.0091),
        FundPerformance(fund_code_id=code_b.id, date="2026-08-01", nav=2.2000, daily_return=-0.0050),
        FundPerformance(fund_code_id=code_b.id, date="2026-08-02", nav=2.1900, daily_return=-0.0045),
    ]
    db.add_all(performances)
    db.commit()

    return {"fund_a": fund_a, "fund_b": fund_b, "code_a": code_a, "code_b": code_b}
```

- [ ] **Step 2: 创建对比接口测试**

`backend/tests/test_compare.py`:

```python
from uuid import uuid4


def test_compare_requires_login(client):
    response = client.get("/api/funds/compare")
    assert response.status_code == 401


def test_compare_empty_ids(client, auth_headers):
    response = client.get("/api/funds/compare", headers=auth_headers)
    assert response.status_code == 400


def test_compare_too_many_ids(client, auth_headers):
    ids = ",".join([str(uuid4()) for _ in range(6)])
    response = client.get(f"/api/funds/compare?ids={ids}", headers=auth_headers)
    assert response.status_code == 400


def test_compare_returns_funds(client, auth_headers, sample_funds):
    ids = f"{sample_funds['fund_a'].id},{sample_funds['fund_b'].id}"
    response = client.get(f"/api/funds/compare?ids={ids}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["funds"]) == 2
    names = {f["name"] for f in data["funds"]}
    assert names == {"基金 A", "基金 B"}
    fund_a = next(f for f in data["funds"] if f["name"] == "基金 A")
    assert fund_a["nav"] == 1.11
    assert len(fund_a["nav_history"]) == 2
```

- [ ] **Step 3: 安装测试依赖并运行测试**

Run: `cd backend && pip install pytest httpx`
Run: `cd backend && pytest tests/test_compare.py -v`
Expected: 4 tests PASS。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/
git commit -m "test(backend): add compare endpoint tests"
```

---

### Task 4: 总览页添加多选与对比按钮

**Files:**
- Modify: `frontend/src/views/OverviewView.vue`

- [ ] **Step 1: 添加 `selectedIds` 与相关计算属性**

在 `<script setup>` 顶部添加：

```js
import { ref, onMounted, computed } from 'vue'
```

在 `loading` 声明下方添加：

```js
const selectedIds = ref([])
const canCompare = computed(() => selectedIds.value.length >= 2)
const tooManySelected = computed(() => selectedIds.value.length > 5)
```

- [ ] **Step 2: 添加复选框切换逻辑**

```js
function toggleFund(id) {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  } else if (selectedIds.value.length < 5) {
    selectedIds.value.push(id)
  }
}

function goCompare() {
  if (!canCompare.value) return
  router.push(`/compare?ids=${selectedIds.value.join(',')}`)
}
```

- [ ] **Step 3: 在卡片上添加复选框，并在顶部工具栏添加对比按钮**

工具栏区域改为：

```vue
<div class="flex items-center justify-between mb-6">
  <input v-model="keyword" type="text" class="search-pill w-72" placeholder="搜索基金名称/代码" @keyup.enter="fetchFunds" />
  <div class="flex items-center gap-3">
    <span v-if="selectedIds.length" class="text-sm text-body">
      已选 {{ selectedIds.length }} 只基金
    </span>
    <button class="btn-secondary" @click="fetchFunds">搜索</button>
    <button
      class="btn-primary"
      :disabled="!canCompare || tooManySelected"
      :class="{ 'opacity-50 cursor-not-allowed': !canCompare || tooManySelected }"
      @click="goCompare"
    >
      对比
    </button>
  </div>
</div>
```

卡片内 `v-for` 容器改为：

```vue
<div
  v-for="fund in funds"
  :key="fund.id"
  class="card p-5 cursor-pointer hover:shadow-md transition-shadow relative"
  @click="router.push(`/detail/${fund.id}`)"
>
  <input
    type="checkbox"
    class="absolute top-4 right-4 w-4 h-4 accent-brand"
    :checked="selectedIds.includes(fund.id)"
    @click.stop="toggleFund(fund.id)"
  />
  ...
</div>
```

- [ ] **Step 4: 运行前端 dev 验证总览页正常**

Run: `cd frontend && npm run dev`
Expected: 总览页每张卡片有复选框，选中 2 只后“对比”按钮可点击。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/OverviewView.vue
git commit -m "feat(frontend): add fund selection and compare button on overview"
```

---

### Task 5: 创建对比指标组件

**Files:**
- Create: `frontend/src/components/CompareMetrics.vue`

- [ ] **Step 1: 写入组件代码**

```vue
<script setup>
defineProps({
  funds: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm text-left">
      <thead class="text-muted border-b border-hairline">
        <tr>
          <th class="py-3 pr-4 font-medium">指标</th>
          <th v-for="fund in funds" :key="fund.id" class="py-3 px-4 font-medium min-w-[140px]">
            {{ fund.name }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr class="border-b border-hairline-soft">
          <td class="py-3 pr-4 text-muted">基金代码</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">{{ fund.code }}</td>
        </tr>
        <tr class="border-b border-hairline-soft">
          <td class="py-3 pr-4 text-muted">类别</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">{{ fund.category }}</td>
        </tr>
        <tr class="border-b border-hairline-soft">
          <td class="py-3 pr-4 text-muted">最新净值</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4 font-semibold">{{ fund.nav?.toFixed(4) ?? '-' }}</td>
        </tr>
        <tr class="border-b border-hairline-soft">
          <td class="py-3 pr-4 text-muted">日涨幅</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">
            <span v-if="fund.daily_return != null" :class="fund.daily_return >= 0 ? 'text-up' : 'text-down'">
              {{ fund.daily_return >= 0 ? '+' : '' }}{{ fund.daily_return.toFixed(2) }}%
            </span>
            <span v-else class="text-muted">-</span>
          </td>
        </tr>
        <tr>
          <td class="py-3 pr-4 text-muted">基金经理</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">{{ fund.manager ?? '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CompareMetrics.vue
git commit -m "feat(frontend): add CompareMetrics component"
```

---

### Task 6: 创建对比图表组件

**Files:**
- Create: `frontend/src/components/CompareChart.vue`

- [ ] **Step 1: 写入组件代码**

```vue
<script setup>
import { computed } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

const props = defineProps({
  funds: { type: Array, default: () => [] },
})

const colors = ['#0052ff', '#cf202f', '#05b169', '#f4b000', '#7c3aed']

const chartData = computed(() => {
  if (!props.funds.length) return { labels: [], datasets: [] }

  const dateSet = new Set()
  props.funds.forEach((fund) => {
    fund.nav_history?.forEach((item) => dateSet.add(item.date))
  })
  const labels = Array.from(dateSet).sort()

  const datasets = props.funds.map((fund, index) => {
    const navMap = new Map(fund.nav_history?.map((item) => [item.date, item.nav]))
    return {
      label: fund.name,
      data: labels.map((date) => navMap.get(date) ?? null),
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length],
      tension: 0.3,
      pointRadius: 2,
    }
  })

  return { labels, datasets }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'bottom' } },
  scales: {
    y: { grid: { color: '#eef0f3' }, ticks: { color: '#7c828a' } },
    x: { grid: { display: false }, ticks: { color: '#7c828a' } },
  },
}
</script>

<template>
  <div class="h-90">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CompareChart.vue
git commit -m "feat(frontend): add CompareChart component"
```

---

### Task 7: 重写对比页面

**Files:**
- Modify: `frontend/src/views/CompareView.vue`

- [ ] **Step 1: 替换为完整实现**

```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import CompareMetrics from '../components/CompareMetrics.vue'
import CompareChart from '../components/CompareChart.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const funds = ref([])
const loading = ref(false)
const error = ref('')

const selectedIds = computed(() => {
  const raw = route.query.ids || ''
  return raw.split(',').filter(Boolean)
})

async function fetchCompareData() {
  if (!selectedIds.value.length) {
    error.value = '请先选择要对比的基金'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/funds/compare?ids=${selectedIds.value.join(',')}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (!res.ok) throw new Error('加载失败')
    const data = await res.json()
    funds.value = data.funds
  } catch (e) {
    error.value = '加载对比数据失败'
  } finally {
    loading.value = false
  }
}

function removeFund(id) {
  const ids = selectedIds.value.filter((x) => x !== id)
  router.replace({ path: '/compare', query: { ids: ids.join(',') } })
}

onMounted(fetchCompareData)
</script>

<template>
  <div class="min-h-screen bg-surface-soft">
    <header class="bg-canvas border-b border-hairline px-6 h-16 flex items-center justify-between sticky top-0 z-10">
      <div class="flex items-center gap-4">
        <button class="text-sm text-body hover:text-ink" @click="router.push('/overview')">← 返回总览</button>
        <h1 class="font-bold text-lg">基金对比</h1>
      </div>
      <button class="btn-secondary" @click="router.push('/overview')">重新选择</button>
    </header>

    <main class="max-w-6xl mx-auto p-6 space-y-6">
      <div v-if="loading" class="text-center py-20 text-muted">加载中...</div>
      <div v-else-if="error" class="text-center py-20 text-up">{{ error }}</div>
      <template v-else-if="funds.length">
        <div class="card p-6">
          <div class="flex items-center gap-3 mb-4 flex-wrap">
            <span class="text-sm text-muted">已选基金：</span>
            <span
              v-for="fund in funds"
              :key="fund.id"
              class="inline-flex items-center gap-1 text-sm px-3 py-1 rounded-full bg-surface-strong"
            >
              {{ fund.name }}
              <button class="text-muted hover:text-up" @click="removeFund(fund.id)">×</button>
            </span>
          </div>
          <CompareMetrics :funds="funds" />
        </div>

        <div class="card p-6">
          <h3 class="font-semibold mb-4">净值走势对比</h3>
          <CompareChart :funds="funds" />
        </div>
      </template>
    </main>
  </div>
</template>
```

- [ ] **Step 2: 验证对比页可正常访问**

Run: `cd frontend && npm run dev`
Open: `http://localhost:5173/overview`
选择两只基金，点击“对比”，跳转到 `/compare?ids=...` 后应展示指标表格和图表。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/CompareView.vue
git commit -m "feat(frontend): implement compare page with metrics and chart"
```

---

### Task 8: 全量构建验证与最终提交

- [ ] **Step 1: 前端生产构建**

Run: `cd frontend && npm run build`
Expected: `built in ...ms`，无错误。

- [ ] **Step 2: 后端导入检查**

Run: `cd backend && python3 -c "from app.main import app; print('ok')"`
Expected: `ok`。

- [ ] **Step 3: Commit 任何未提交改动**

```bash
git status
# 如有未提交文件：
git add -A
git commit -m "feat: complete fund compare feature"
```

---

## 自审清单

1. **Spec coverage:**
   - 总览多选 → Task 4
   - 对比页指标表格 → Task 5 + Task 7
   - 同图净值走势 → Task 6 + Task 7
   - 后端批量接口 → Task 2
   - 错误处理（空 ids、超过 5 只）→ Task 2 + Task 3
2. **Placeholder scan:** 无 TODO/TBD。
3. **类型一致性：** `FundCompareItem` 继承 `FundDetail` 并扩展 `nav_history`；前端 `funds` 数组贯穿 `CompareMetrics` 与 `CompareChart`。

---

## 执行方式

计划已保存到 `docs/superpowers/plans/2026-08-07-fund-compare.md`。

两种执行方式：

1. **Subagent-Driven（推荐）** — 每个任务派独立子代理执行，任务间我进行复核，迭代快。
2. **Inline Execution** — 在当前会话中使用 `executing-plans` 批量执行，适合一次性推进。

你选哪种？
