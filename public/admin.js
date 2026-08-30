document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('groupsContainer');
    const btnAddGroup = document.getElementById('btnAddGroup');
    const btnSave = document.getElementById('btnSave');
    const btnSync = document.getElementById('btnSync');
    const statusMsg = document.getElementById('statusMessage');

    function showStatus(msg, type) {
        statusMsg.textContent = msg;
        statusMsg.className = `status-msg ${type}`;
        setTimeout(() => {
            statusMsg.style.display = 'none';
        }, 5000);
    }

    function createGroupElement(groupName = '', tickers = []) {
        const div = document.createElement('div');
        div.className = 'group-card';
        div.innerHTML = `
            <div class="group-header">
                <input type="text" class="group-title-input" value="${groupName}" placeholder="Tên nhóm (VD: Công nghệ)">
                <button class="btn-remove-group">Xóa Nhóm</button>
            </div>
            <textarea class="tickers-input" placeholder="Nhập mã cổ phiếu cách nhau bằng dấu phẩy hoặc khoảng trắng. VD: FPT CMG VCB">${tickers.join(', ')}</textarea>
            <div class="input-hint">Tối đa 20 mã cổ phiếu. Dùng dấu phẩy, khoảng trắng hay xuống dòng đều được.</div>
        `;
        
        div.querySelector('.btn-remove-group').addEventListener('click', () => {
            div.remove();
        });
        
        return div;
    }

    // Load initial data
    try {
        const res = await fetch('/api/config/sectors');
        if (res.ok) {
            const data = await res.json();
            for (const [group, tickers] of Object.entries(data)) {
                container.appendChild(createGroupElement(group, tickers));
            }
        }
    } catch (e) {
        showStatus('Lỗi tải cấu hình ban đầu.', 'error');
    }

    btnAddGroup.addEventListener('click', () => {
        container.appendChild(createGroupElement());
    });

    btnSave.addEventListener('click', async () => {
        const payload = {};
        let hasError = false;

        container.querySelectorAll('.group-card').forEach(card => {
            const name = card.querySelector('.group-title-input').value.trim();
            const tickersStr = card.querySelector('.tickers-input').value;
            
            if (!name) return;
            
            // Tự động phân tách bằng dấu phẩy, khoảng trắng hoặc xuống dòng
            const tickers = tickersStr.split(/[\s,]+/)
                .map(t => t.trim().toUpperCase())
                .filter(t => t.length > 0);
                
            if (tickers.length > 20) {
                showStatus(`Nhóm "${name}" vượt quá 20 mã!`, 'error');
                hasError = true;
            }
            
            payload[name] = tickers;
        });

        if (hasError) return;

        try {
            const res = await fetch('/api/config/sectors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: payload })
            });
            const data = await res.json();
            
            if (res.ok) {
                showStatus('Đã lưu cấu hình thành công! Hãy bấm Đồng bộ để tải dữ liệu.', 'success');
            } else {
                showStatus(data.detail || 'Lỗi khi lưu.', 'error');
            }
        } catch (e) {
            showStatus('Lỗi kết nối máy chủ.', 'error');
        }
    });

    btnSync.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/config/sync', { method: 'POST' });
            if (res.ok) {
                showStatus('Đã ra lệnh đồng bộ nền thành công! Vui lòng chờ vài phút rồi tải lại trang chủ.', 'success');
            } else {
                showStatus('Lỗi khi gọi lệnh đồng bộ.', 'error');
            }
        } catch (e) {
            showStatus('Lỗi kết nối máy chủ.', 'error');
        }
    });
});
