const API = '/api';

const STATUS_LABELS = {
  pending: 'قيد الانتظار',
  preparing: 'قيد التحضير',
  delivering: 'قيد التوصيل',
  success: 'مكتمل',
  cancelled: 'ملغى',
};

const STATUS_NEXT = {
  pending: 'preparing',
  preparing: 'delivering',
  delivering: 'success',
};

let token = localStorage.getItem('token') || '';
let userId = parseInt(localStorage.getItem('userId') || '0', 10);
let username = localStorage.getItem('username') || '';

// ── Helpers ──────────────────────────────────────────

function formatUSD(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function showToast(msg, ok = true) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${ok ? 'ok' : 'err'}`;
  setTimeout(() => el.classList.add('hidden'), 3500);
}

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

function decodeUserId(jwt) {
  try {
    const payload = JSON.parse(atob(jwt.split('.')[1]));
    return payload.user_id;
  } catch {
    return null;
  }
}

async function api(method, path, body = null, auth = false) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (auth) opts.headers = authHeaders();
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API}${path}`, opts);
  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  return { ok: res.ok, status: res.status, data };
}

function setAuth(t, user, name) {
  token = t;
  userId = user;
  username = name;
  localStorage.setItem('token', t);
  localStorage.setItem('userId', user);
  localStorage.setItem('username', name);
}

function clearAuth() {
  token = '';
  userId = 0;
  username = '';
  localStorage.removeItem('token');
  localStorage.removeItem('userId');
  localStorage.removeItem('username');
}

function showApp(loggedIn) {
  document.getElementById('auth-section').classList.toggle('hidden', loggedIn);
  document.getElementById('app-section').classList.toggle('hidden', !loggedIn);
  document.getElementById('user-bar').classList.toggle('hidden', !loggedIn);
  if (loggedIn) {
    document.getElementById('user-label').textContent = `مرحباً، ${username}`;
    loadBank();
    loadProducts();
    loadCart();
  }
}

// ── Auth ─────────────────────────────────────────────

document.querySelectorAll('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
    document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
  });
});

document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const u = document.getElementById('login-username').value.trim();
  const p = document.getElementById('login-password').value;

  const { ok, data } = await api('POST', '/user/login', { username: u, password: p });
  if (!ok) {
    showToast(data?.detail || 'فشل تسجيل الدخول', false);
    return;
  }

  const uid = decodeUserId(data.access);
  setAuth(data.access, uid, u);
  showApp(true);
  showToast('تم تسجيل الدخول بنجاح');
});

document.getElementById('register-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = {
    username: document.getElementById('reg-username').value.trim(),
    email: document.getElementById('reg-email').value.trim(),
    password: document.getElementById('reg-password').value,
  };

  const { ok, data } = await api('POST', '/user/create', body);
  if (!ok) {
    const msg = data?.username?.[0] || data?.email?.[0] || 'فشل إنشاء الحساب';
    showToast(msg, false);
    return;
  }

  showToast('تم إنشاء الحساب — سجّل دخولك الآن');
  document.querySelector('.tab[data-tab="login"]').click();
  document.getElementById('login-username').value = body.username;
});

document.getElementById('btn-logout').addEventListener('click', () => {
  clearAuth();
  showApp(false);
  showToast('تم تسجيل الخروج');
});

// ── Navigation ───────────────────────────────────────

document.querySelectorAll('.nav-tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    const page = btn.dataset.page;
    document.querySelectorAll('.page').forEach((p) => p.classList.add('hidden'));
    document.getElementById(`page-${page}`).classList.remove('hidden');
    if (page === 'cart') loadCart();
    if (page === 'orders') loadOrders();
  });
});

// ── Bank ─────────────────────────────────────────────

async function loadBank() {
  const { ok, data } = await api('GET', `/bank/show/${userId}`, null, true);
  if (ok) {
    document.getElementById('balance-label').textContent =
      `Balance: ${formatUSD(data.balance)}`;
  }
}

// ── Products ─────────────────────────────────────────

async function loadProducts() {
  const grid = document.getElementById('products-grid');
  grid.innerHTML = '<p class="empty-msg">جاري التحميل...</p>';

  const { ok, data } = await api('GET', '/product/all');
  if (!ok || !data.length) {
    grid.innerHTML = '<p class="empty-msg">لا توجد منتجات</p>';
    return;
  }

  grid.innerHTML = data.map((p) => `
    <div class="product-card">
      <h3>${esc(p.name)}</h3>
      <div class="product-price">${formatUSD(p.price)}</div>
      <div class="product-stock">المخزون: ${p.quantity}</div>
      <div class="qty-row">
        <input type="number" min="1" max="${p.quantity}" value="1" id="qty-${p.id}">
        <button class="btn btn-primary btn-sm" onclick="addToCart(${p.id})">أضف للسلة</button>
      </div>
    </div>
  `).join('');
}

document.getElementById('btn-refresh-products').addEventListener('click', loadProducts);

async function addToCart(productId) {
  const qty = parseInt(document.getElementById(`qty-${productId}`).value, 10) || 1;
  const { ok, data } = await api('POST', '/cart-product/create', {
    user_id: userId,
    product_id: productId,
    quantity: qty,
  }, true);

  if (!ok) {
    showToast(data?.message || 'فشل الإضافة', false);
    return;
  }
  showToast('تمت الإضافة للسلة');
  loadCart();
}

// ── Cart ─────────────────────────────────────────────

async function loadCart() {
  const el = document.getElementById('cart-content');
  const totalEl = document.getElementById('cart-total');
  const badge = document.getElementById('cart-badge');

  const { ok, data } = await api('GET', `/cart/show/${userId}`, null, true);
  if (!ok || !data.products?.length) {
    el.innerHTML = '<p class="empty-msg">السلة فارغة</p>';
    totalEl.textContent = '';
    badge.classList.add('hidden');
    return;
  }

  badge.textContent = data.products.length;
  badge.classList.remove('hidden');

  el.innerHTML = `
    <table class="cart-table">
      <thead>
        <tr><th>المنتج</th><th>السعر</th><th>الكمية</th><th>المجموع</th><th></th></tr>
      </thead>
      <tbody>
        ${data.products.map((item) => `
          <tr>
            <td>${esc(item.product_name)}</td>
            <td>${formatUSD(item.price)}</td>
            <td>
              <input type="number" min="1" value="${item.quantity}" style="width:60px"
                onchange="updateCartItem(${item.cart_product_id}, this.value)">
            </td>
            <td>${formatUSD(item.total)}</td>
            <td><button class="btn btn-danger btn-sm" onclick="deleteCartItem(${item.cart_product_id})">حذف</button></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  totalEl.textContent = `Total: ${formatUSD(data.total_price)}`;
}

async function updateCartItem(id, qty) {
  const { ok, data } = await api('POST', `/cart-product/update/${id}`, { quantity: parseInt(qty, 10) }, true);
  showToast(ok ? 'تم التحديث' : (data?.message || 'فشل التحديث'), ok);
  loadCart();
}

async function deleteCartItem(id) {
  const { ok } = await api('POST', `/cart-product/delete/${id}`, null, true);
  if (ok) { showToast('تم الحذف'); loadCart(); }
}

document.getElementById('btn-empty-cart').addEventListener('click', async () => {
  const { ok } = await api('GET', `/cart/empty/${userId}`, null, true);
  if (ok) { showToast('تم إفراغ السلة'); loadCart(); }
});

document.getElementById('btn-checkout').addEventListener('click', async () => {
  const btn = document.getElementById('btn-checkout');
  btn.disabled = true;
  btn.textContent = 'جاري الدفع...';

  const { ok, data } = await api('POST', `/cart/confirm/${userId}`, null, true);

  btn.disabled = false;
  btn.textContent = 'إتمام الدفع';

  if (!ok) {
    showToast(data?.message || 'فشل الدفع', false);
    return;
  }
  showToast(`تم الدفع! رقم الطلب: ${data.order_id}`);
  loadBank();
  loadCart();
  loadProducts();
});

// ── Orders ───────────────────────────────────────────

async function loadOrders() {
  const el = document.getElementById('orders-list');
  el.innerHTML = '<p class="empty-msg">جاري التحميل...</p>';

  const { ok, data } = await api('GET', `/order/show/${userId}`, null, true);
  if (!ok || !data.length) {
    el.innerHTML = '<p class="empty-msg">لا توجد طلبات</p>';
    return;
  }

  el.innerHTML = [...data].reverse().map((order) => {
    const items = order.products.map((p) =>
      `${p.product_name || 'منتج #' + p.product} × ${p.quantity}`
    ).join('، ');

    const next = STATUS_NEXT[order.status];
    let actions = '';

    if (order.status === 'pending') {
      actions += `<button class="btn btn-danger btn-sm" onclick="cancelOrder(${order.order_id})">إلغاء</button>`;
    }
    if (next) {
      actions += `<button class="btn btn-success btn-sm" onclick="advanceOrder(${order.order_id}, '${next}')">
        → ${STATUS_LABELS[next]}</button>`;
    }

    return `
      <div class="order-card">
        <div class="order-header">
          <strong>طلب #${order.order_id}</strong>
          <span class="status status-${order.status}">${STATUS_LABELS[order.status] || order.status}</span>
        </div>
        <div>Amount: <strong>${formatUSD(order.total_amount)}</strong></div>
        <div class="order-items">${esc(items)}</div>
        <div class="order-actions">${actions}</div>
      </div>
    `;
  }).join('');
}

document.getElementById('btn-refresh-orders').addEventListener('click', loadOrders);

async function advanceOrder(id, status) {
  const { ok, data } = await api('POST', `/order/change-status/${id}`, { status }, true);
  showToast(ok ? 'تم تحديث الحالة' : (data?.message || 'فشل'), ok);
  loadOrders();
}

async function cancelOrder(id) {
  if (!confirm('هل تريد إلغاء هذا الطلب؟')) return;
  const { ok, data } = await api('POST', `/order/cancel/${id}`, null, true);
  showToast(ok ? 'تم الإلغاء' : (data?.message || 'فشل الإلغاء'), ok);
  if (ok) { loadBank(); loadOrders(); loadProducts(); }
}

// ── System ───────────────────────────────────────────

document.getElementById('btn-load-balance').addEventListener('click', async () => {
  const { ok, data } = await api('GET', '/load-balance');
  document.getElementById('load-balance-result').textContent =
    ok ? JSON.stringify(data, null, 2) : 'فشل الاتصال';
});

// ── Utils ────────────────────────────────────────────

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

// expose for inline onclick
window.addToCart = addToCart;
window.updateCartItem = updateCartItem;
window.deleteCartItem = deleteCartItem;
window.advanceOrder = advanceOrder;
window.cancelOrder = cancelOrder;

// ── Init ─────────────────────────────────────────────

if (token && userId) {
  showApp(true);
} else {
  showApp(false);
}
