const API_BASE = window.location.origin;

// Session and History management disabled
let sessionId = Math.random().toString(36).substring(7);
let messageHistory = [];

// Configure marked
marked.setOptions({
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true
});

let currentTents = [];
let pendingEdits = {}; // { id: { field: newValue } }
let sortConfig = { key: 'id', direction: 'asc' }; // default sort

// Configuration for numeric fields
const numericFields = ['id', 'price', 'capacity', 'weight_kg', 'size_w', 'size_d', 'size_h', 'pack_w', 'pack_d', 'pack_h'];

async function fetchTents() {
    const res = await fetch(`${API_BASE}/tents`);
    const data = await res.json();
    currentTents = data;
    applySort(); // Initial sort
}

async function fetchStats() {
    const res = await fetch(`${API_BASE}/tents/stats`);
    const data = await res.json();
    const statsHeader = document.getElementById('stats-header');
    if (statsHeader) {
        statsHeader.innerHTML = `
            <span style="margin: 0 10px;">Total: <strong>${data.total_count}</strong></span>
            <span>Avg Price: <strong>${data.avg_price}</strong></span>
        `;
    }
}

function handleSort(key) {
    if (sortConfig.key === key) {
        sortConfig.direction = sortConfig.direction === 'asc' ? 'desc' : 'asc';
    } else {
        sortConfig.key = key;
        sortConfig.direction = 'asc';
    }
    applySort();
}
window.handleSort = handleSort;

function applySort() {
    // Merge currentTents and new items from pendingEdits for sorting/rendering
    const allIds = new Set([
        ...currentTents.map(t => t.id),
        ...Object.keys(pendingEdits).map(k => parseInt(k))
    ]);

    const displayList = [...allIds].map(id => {
        const original = currentTents.find(t => t.id === id) || {};
        const edits = pendingEdits[id] || {};
        return { ...original, ...edits, id: id };
    });

    const sorted = displayList.sort((a, b) => {
        let valA = a[sortConfig.key];
        let valB = b[sortConfig.key];

        if (numericFields.includes(sortConfig.key)) {
            valA = parseFloat(valA) || 0;
            valB = parseFloat(valB) || 0;
            return sortConfig.direction === 'asc' ? valA - valB : valB - valA;
        }

        valA = String(valA || '');
        valB = String(valB || '');
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
    });
    renderTable(sorted);
}

function renderTable(displayList) {
    const headers = {
        'id': 'col-id', 'name': 'col-name', 'brand': 'col-brand',
        'price': 'col-price', 'capacity': 'col-capacity',
        'weight_kg': 'col-weight_kg', 'size_w': 'col-size_w',
        'size_d': 'col-size_d', 'size_h': 'col-size_h',
        'pack_w': 'col-pack_w', 'pack_d': 'col-pack_d',
        'pack_h': 'col-pack_h', 'material': 'col-material',
        'purchase_date': 'col-purchase_date'
    };

    Object.keys(headers).forEach(key => {
        const th = document.getElementById(headers[key]);
        if (!th) return;
        const baseName = th.getAttribute('data-base-name') || th.innerText.replace(/[▲▼]/g, '').trim();
        th.setAttribute('data-base-name', baseName);
        if (sortConfig.key === key) {
            th.innerHTML = `${baseName} ${sortConfig.direction === 'asc' ? '▲' : '▼'}`;
            th.style.color = 'var(--primary-color)';
        } else {
            th.innerHTML = baseName;
            th.style.color = 'inherit';
        }
    });

    const tbody = document.querySelector('#data-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    displayList.forEach(item => {
        const id = item.id;
        const isNew = item._isNew || id < 0;
        const isDeleted = pendingEdits[id] && pendingEdits[id]._deleted;

        const tr = document.createElement('tr');
        if (isDeleted) tr.classList.add('pending-delete');
        if (isNew) tr.classList.add('pending-add');

        const tent = currentTents.find(t => t.id === id) || {};

        // Check if field is actually modified from original
        const isMod = (field) => (pendingEdits[id] && pendingEdits[id].hasOwnProperty(field)) ? 'modified' : '';
        const getVal = (field) => (pendingEdits[id] && pendingEdits[id].hasOwnProperty(field)) ? pendingEdits[id][field] : tent[field];

        tr.innerHTML = `
            <td>${isNew ? 'NEW' : id}</td>
            <td contenteditable="true" class="editable ${isMod('name')}" onblur="updateField(${id}, 'name', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('name') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('brand')}" onblur="updateField(${id}, 'brand', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('brand') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('price')}" onblur="updateField(${id}, 'price', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${(getVal('price') || 0).toLocaleString()}</td>
            <td contenteditable="true" class="editable ${isMod('capacity')}" onblur="updateField(${id}, 'capacity', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${(parseFloat(getVal('capacity')) || 0).toFixed(1)}</td>
            <td contenteditable="true" class="editable ${isMod('weight_kg')}" onblur="updateField(${id}, 'weight_kg', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('weight_kg') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('size_w')}" onblur="updateField(${id}, 'size_w', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('size_w') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('size_d')}" onblur="updateField(${id}, 'size_d', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('size_d') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('size_h')}" onblur="updateField(${id}, 'size_h', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('size_h') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('pack_w')}" onblur="updateField(${id}, 'pack_w', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('pack_w') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('pack_d')}" onblur="updateField(${id}, 'pack_d', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('pack_d') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('pack_h')}" onblur="updateField(${id}, 'pack_h', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('pack_h') || ''}</td>
            <td contenteditable="true" class="editable ${isMod('material')}" onblur="updateField(${id}, 'material', this.innerText, this)" onkeydown="if(event.key==='Enter'){event.preventDefault();this.blur();}">${getVal('material') || ''}</td>
            <td class="${isMod('purchase_date')}">${getVal('purchase_date') || '-'}</td>
        `;
        tbody.appendChild(tr);
    });
}



function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerText = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function customConfirm(message) {
    return new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal-content">
                <p style="margin-bottom:1rem; line-height:1.6;">${message}</p>
                <div class="modal-btns">
                    <button id="modal-cancel" style="background:#475569;">キャンセル</button>
                    <button id="modal-ok">OK</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const cleanup = (val) => {
            overlay.classList.add('fade-out');
            setTimeout(() => overlay.remove(), 200);
            resolve(val);
        };

        overlay.querySelector('#modal-ok').onclick = () => cleanup(true);
        overlay.querySelector('#modal-cancel').onclick = () => cleanup(false);
    });
}

function updateField(id, field, value, element) {
    const tent = currentTents.find(t => t.id === id);
    if (!tent) return;

    let finalValue = value.trim();
    let originalValue = tent[field];

    // If both are empty/null/undefined, they are effectively the same
    const isEmpty = (v) => v === null || v === undefined || v === "";
    if (isEmpty(finalValue) && isEmpty(originalValue)) {
        if (pendingEdits[id]) {
            delete pendingEdits[id][field];
            if (Object.keys(pendingEdits[id]).length === 0) delete pendingEdits[id];
        }
        if (element) element.classList.remove('modified');
        updateStatus();
        return;
    }

    if (numericFields.includes(field)) {
        const numericStr = finalValue.replace(/,/g, '');
        const numValue = parseFloat(numericStr);
        if (numericStr.trim() !== '' && !isNaN(numValue)) {
            finalValue = numValue;
            const originalNum = parseFloat(originalValue) || 0;
            if (finalValue === originalNum) finalValue = originalValue;
        }
    }

    if (finalValue == originalValue) {
        if (pendingEdits[id]) {
            delete pendingEdits[id][field];
            if (Object.keys(pendingEdits[id]).length === 0) delete pendingEdits[id];
        }
        if (element) element.classList.remove('modified');
    } else {
        if (!pendingEdits[id]) pendingEdits[id] = {};
        pendingEdits[id][field] = finalValue;
        if (element) element.classList.add('modified');
    }
    updateStatus();
    console.log(`[DEBUG] Updated pendingEdits:`, pendingEdits);
}
window.updateField = updateField;

function updateStatus() {
    const status = document.getElementById('edit-status');
    if (!status) return;
    let count = 0;
    for (let id in pendingEdits) count += Object.keys(pendingEdits[id]).length;
    status.innerText = count > 0 ? `${count} 箇所変更あり (未保存)` : '未編集';
    status.style.color = count > 0 ? '#ffb946' : '#94a3b8';
}

async function validateEdits() {
    console.log('[DEBUG] validateEdits start', pendingEdits);
    const status = document.getElementById('edit-status');

    let errors = [];
    let count = 0;
    for (const [id, fields] of Object.entries(pendingEdits)) {
        for (const [field, value] of Object.entries(fields)) {
            count++;
            // 型および数値チェック
            if (numericFields.includes(field)) {
                if (value !== "" && value !== null && value !== undefined) {
                    const num = parseFloat(value);
                    if (isNaN(num)) {
                        errors.push(`ID ${id}: ${field} は数値である必要があります。`);
                    }
                }
            }

            // 必須チェック
            if (field === 'name' && (!value || !String(value).trim())) {
                errors.push(`ID ${id}: 名前を空にできません。`);
            }
        }
    }

    if (count === 0) {
        if (status) {
            status.innerText = '検証する変更がありません。';
            status.style.color = '#94a3b8';
        }
        return false;
    }

    if (errors.length > 0) {
        if (status) {
            status.innerText = `検証エラー: ${errors[0]}`;
            status.style.color = '#ef4444';
        }
        return false;
    } else {
        if (status) {
            status.innerText = '(検証OK): 書き込み可能です。';
            status.style.color = '#10b981';
        }
        return true;
    }
}
window.validateEdits = validateEdits;

async function commitEdits() {
    console.log('[DEBUG] commitEdits start', pendingEdits);

    if (!(await validateEdits())) return;
    if (!(await customConfirm('変更をデータベースに永久保存しますか？'))) return;

    try {
        const res = await fetch(`${API_BASE}/tents/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pendingEdits)
        });

        if (res.ok) {
            const result = await res.json();
            pendingEdits = {};
            await fetchTents();
            await fetchStats();
            updateStatus();
            showToast(`保存完了: ${result.updated_count}件を更新しました。`, 'success');
        } else {
            const errData = await res.json().catch(() => null);
            const errMsg = errData && errData.detail ? JSON.stringify(errData.detail) : await res.text();
            showToast('書き込み失敗: ' + errMsg, 'error');
        }

    } catch (e) {
        showToast('ネットワークエラーが発生しました。', 'error');
    }
}
window.commitEdits = commitEdits;

async function resetEdits() {
    console.log('[DEBUG] resetEdits start');
    if (Object.keys(pendingEdits).length > 0) {
        if (!(await customConfirm('編集を破棄して最新データを読み込みますか？'))) return;
    }

    pendingEdits = {};
    const tbody = document.querySelector('#data-table tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="14" style="text-align:center; padding: 2rem;">Loading...</td></tr>';

    await fetchTents();
    await fetchStats();
    updateStatus();
    showToast('DBから最新データを読み込みました。', 'info');
}
window.resetEdits = resetEdits;

// AI Proposal Handling
function parseUIProposals(text) {
    const proposalRegex = /\[UI_PROPOSAL:\s*({[\s\S]*?})\]/g;
    const bulkProposalRegex = /\[UI_BULK_PROPOSAL:\s*({[\s\S]*?})\]/g;
    const addProposalRegex = /\[UI_ADD_PROPOSAL:\s*({[\s\S]*?})\]/g;
    const deleteProposalRegex = /\[UI_DELETE_PROPOSAL:\s*({[\s\S]*?})\]/g;

    let match;
    let hasChanges = false;

    // Handle single proposals (Update)
    while ((match = proposalRegex.exec(text)) !== null) {
        try {
            const data = JSON.parse(match[1]);
            const id = parseInt(data.id);
            if (!isNaN(id)) {
                if (!pendingEdits[id]) pendingEdits[id] = {};
                Object.assign(pendingEdits[id], data.updates);
                hasChanges = true;
            }
        } catch (e) { console.error('Failed to parse proposal:', e); }
    }

    // Handle bulk proposals (Update)
    while ((match = bulkProposalRegex.exec(text)) !== null) {
        try {
            const data = JSON.parse(match[1]);
            const ids = Array.isArray(data.ids) ? data.ids.map(id => parseInt(id)) : [];
            ids.forEach(id => {
                if (!isNaN(id)) {
                    if (!pendingEdits[id]) pendingEdits[id] = {};
                    Object.assign(pendingEdits[id], data.updates);
                    hasChanges = true;
                }
            });
        } catch (e) { console.error('Failed to parse bulk proposal:', e); }
    }

    // Handle Add proposals
    while ((match = addProposalRegex.exec(text)) !== null) {
        try {
            const data = JSON.parse(match[1]);
            // Generate a unique negative ID for the new row
            const newId = (Math.min(0, ...Object.keys(pendingEdits).map(k => parseInt(k))) - 1);
            pendingEdits[newId] = { ...data, _isNew: true };
            if (pendingEdits[newId].id) delete pendingEdits[newId].id; // Use newId as key
            hasChanges = true;
        } catch (e) { console.error('Failed to parse add proposal:', e); }
    }

    // Handle Delete proposals
    while ((match = deleteProposalRegex.exec(text)) !== null) {
        try {
            const data = JSON.parse(match[1]);
            const id = parseInt(data.id);
            if (!isNaN(id)) {
                if (!pendingEdits[id]) pendingEdits[id] = {};
                pendingEdits[id]._deleted = true;
                hasChanges = true;
            }
        } catch (e) { console.error('Failed to parse delete proposal:', e); }
    }

    if (hasChanges) {
        applySort();
        updateStatus();
    }
}


async function sendMessage() {
    const input = document.getElementById('chat-input');
    const btn = document.getElementById('send-btn');
    if (!input || !btn) return;
    const msg = input.value.trim();
    if (!msg) return;

    appendMessage('user', msg);
    input.value = '';

    btn.disabled = true;
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing';
    typingDiv.style.display = 'block';
    typingDiv.innerText = 'AIが考え中...';
    document.getElementById('chat-messages').appendChild(typingDiv);
    document.getElementById('chat-messages').scrollTop = document.getElementById('chat-messages').scrollHeight;

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, session_id: sessionId })
        });
        if (!res.ok) {
            const errData = await res.json();
            appendMessage('ai', `サーバーエラーが発生しました: ${errData.detail || '不明なエラー'}`);
        } else {
            const data = await res.json();
            // Process UI proposals from AI response
            parseUIProposals(data.response);

            // Clean up response text (remove tags from display)
            const cleanResponse = data.response.replace(/\[UI_PROPOSAL:[\s\S]*?\]/g, '').replace(/\[UI_BULK_PROPOSAL:[\s\S]*?\]/g, '').trim();
            appendMessage('ai', cleanResponse || 'ご提案を反映しました。');
        }
    } catch (e) {
        typingDiv.remove();
        console.error('Chat Error:', e);
        appendMessage('ai', `通信エラーが発生しました: ${e.message}`);
    } finally {

        btn.disabled = false;
    }
}

function appendMessage(sender, text) {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-message`;

    if (sender === 'ai') {
        const chartRegex = /```chart\s+([\s\S]*?)```/g;
        let processedText = text;
        const chartsToRender = [];

        processedText = text.replace(chartRegex, (match, jsonStr) => {
            const chartId = `chart-${Math.random().toString(36).substring(7)}`;
            chartsToRender.push({ id: chartId, json: jsonStr.trim() });
            return `<div class="chart-wrapper"><canvas id="${chartId}"></canvas></div>`;
        });

        msgDiv.innerHTML = marked.parse(processedText);
        container.appendChild(msgDiv);

        chartsToRender.forEach(chartObj => {
            try {
                const config = JSON.parse(chartObj.json);
                const ctx = document.getElementById(chartObj.id).getContext('2d');
                new Chart(ctx, config);
            } catch (e) {
                console.error('Failed to render chart:', e);
            }
        });
    } else {
        msgDiv.innerText = text;
        container.appendChild(msgDiv);
    }
    container.scrollTop = container.scrollHeight;
    messageHistory.push({ sender, text });
}

function loadHistory() {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    if (messageHistory.length > 0) {
        container.innerHTML = '';
        messageHistory.forEach(msg => {
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${msg.sender}-message`;
            if (msg.sender === 'ai') msgDiv.innerHTML = marked.parse(msg.text);
            else msgDiv.innerText = msg.text;
            container.appendChild(msgDiv);
        });
        container.scrollTop = container.scrollHeight;
    }
}

document.getElementById('send-btn').addEventListener('click', sendMessage);
document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

fetchTents();
fetchStats();
// loadHistory(); 履歴機能は削除されました
