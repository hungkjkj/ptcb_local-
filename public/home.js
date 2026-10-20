document.addEventListener('DOMContentLoaded', async () => {
    const homeGrid = document.getElementById('home-grid');
    let targetSectors = ['Ngân hàng', 'Bán lẻ', 'Công nghệ thông tin', 'Xây dựng và Vật liệu'];

    try {
        const res = await fetch('/api/config/sectors');
        if (res.ok) {
            const data = await res.json();
            if (Object.keys(data).length > 0) {
                targetSectors = Object.keys(data);
            }
        }
    } catch (e) {
        console.error("Lỗi lấy danh sách ngành:", e);
    }

    // Initialize UI with skeletons
    targetSectors.forEach(sector => {
        // use base64 for safeId to avoid issues with special Vietnamese characters, removing padding
        const safeId = 's_' + btoa(unescape(encodeURIComponent(sector))).replace(/[^a-zA-Z0-9]/g, '');
        const cardHtml = `
            <div class="sector-card glass" id="card-${safeId}">
                <h2>${sector}</h2>
                <div class="table-container">
                    <table class="sector-table">
                        <thead>
                            <tr style="background: rgba(255,255,255,0.05);">
                                <th>#</th>
                                <th>Mã CP</th>
                                <th>Điểm</th>
                            </tr>
                        </thead>
                        <tbody id="tbody-${safeId}">
                            <tr><td colspan="3"><div class="skeleton-row"></div></td></tr>
                            <tr><td colspan="3"><div class="skeleton-row"></div></td></tr>
                            <tr><td colspan="3"><div class="skeleton-row"></div></td></tr>
                            <tr><td colspan="3"><div class="skeleton-row"></div></td></tr>
                            <tr><td colspan="3"><div class="skeleton-row"></div></td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        homeGrid.insertAdjacentHTML('beforeend', cardHtml);
    });

    // Fetch data sequentially to avoid API rate limits
    async function loadAllSectors() {
        for (const sector of targetSectors) {
            const safeId = 's_' + btoa(unescape(encodeURIComponent(sector))).replace(/[^a-zA-Z0-9]/g, '');
            await fetchDataForSector(sector, safeId);
            // Wait 1 second between sectors to reduce rate limits
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
    
    loadAllSectors();

    async function fetchDataForSector(sector, elementId) {
        try {
            // Using a cache buster but relying on backend caching for speed
            const response = await fetch(`/api/screener?sector=${encodeURIComponent(sector)}`);
            if (!response.ok) throw new Error('API server error');
            const data = await response.json();
            const rows = Array.isArray(data.data) ? data.data : [];

            const tbody = document.getElementById(`tbody-${elementId}`);
            tbody.innerHTML = '';

            const calculateMedian = (values) => {
                const sorted = values
                    .filter(value => typeof value === 'number' && Number.isFinite(value))
                    .sort((a, b) => a - b);
                if (sorted.length === 0) return null;
                const middle = Math.floor(sorted.length / 2);
                return sorted.length % 2
                    ? sorted[middle]
                    : (sorted[middle - 1] + sorted[middle]) / 2;
            };

            const medianFor = (field, cachedField, includeZero = false) => {
                const cachedValue = cachedField && data.medians?.[cachedField];
                if (typeof cachedValue === 'number' && Number.isFinite(cachedValue)) {
                    return cachedValue;
                }

                const values = rows
                    .map(row => row[field])
                    .filter(value => includeZero || value !== 0);
                return calculateMedian(values);
            };

            const scoreMedian = calculateMedian(rows.map(row => {
                const score = row['Total Score'] ?? row.Total_Score;
                return typeof score === 'number' ? score : null;
            }));
            const medianLabel = '<td colspan="2" class="median-label">TRUNG VỊ</td>';
            const medianScoreCell = `<td class="median-score">${scoreMedian === null ? '-' : scoreMedian.toFixed(1)}</td>`;
            
            if (rows.length > 0) {
                const isBank = sector.toLowerCase().includes('ngân hàng') || sector.toLowerCase().includes('bank');
                const isSecurities = sector.toLowerCase().includes('chứng khoán') || sector.toLowerCase().includes('securities') || sector.toLowerCase().includes('dịch vụ tài chính');
                
                // Add more headers if we have actual data
                const thead = document.querySelector(`#card-${elementId} thead`);
                let headers = '';
                if (isBank) {
                    headers = `
                        <tr style="background: rgba(255,255,255,0.05);">
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">#</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">MÃ CP</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ĐIỂM</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROA</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">NIM</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">VALUE</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">EQ</th>
                        </tr>
                    `;
                } else if (isSecurities) {
                    headers = `
                        <tr style="background: rgba(255,255,255,0.05);">
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">#</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">MÃ CP</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ĐIỂM</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">P/B</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">P/E</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROE TTM</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">VỐN CHỦ</th>
                        </tr>
                    `;
                } else {
                    headers = `
                        <tr style="background: rgba(255,255,255,0.05);">
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">#</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">MÃ CP</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ĐIỂM</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROIC</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">CFO</th>
                            <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">VALUE</th>
                        </tr>
                    `;
                }
                thead.innerHTML = headers;

                rows.forEach((r, idx) => {
                    const t = r.ticker || r.Ticker || r.TICKER;
                    const score = r['Total Score'] || r.Total_Score || 0;
                    
                    if (isBank) {
                        const roa = r.ROA ? (r.ROA * 100).toFixed(1) + '%' : '-';
                        const nim = r.NIM ? (r.NIM * 100).toFixed(1) + '%' : '-';
                        const value = r.Value_Ratio ? (r.Value_Ratio * 100).toFixed(1) : '-';
                        const eq = r.Equity_Ratio ? (r.Equity_Ratio * 100).toFixed(1) + '%' : '-';
                        
                        tbody.innerHTML += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td>${idx + 1}</td>
                                <td style="color: #38bdf8; font-weight: bold;"><a href="/compare?ticker=${t}" class="ticker-link" target="_blank">${t}</a></td>
                                <td style="color: #fbbf24; font-weight: bold;">${score.toFixed(1)}</td>
                                <td class="text-gray-300">${roa}</td>
                                <td class="text-gray-300">${nim}</td>
                                <td class="text-emerald-400">${value}</td>
                                <td class="text-gray-300">${eq}</td>
                            </tr>
                        `;
                    } else if (isSecurities) {
                        const pb = r.PB ? r.PB.toFixed(2) : '-';
                        const pe = r.PE ? r.PE.toFixed(1) : '-';
                        const roe_ttm = r.ROE_TTM ? (r.ROE_TTM * 100).toFixed(1) + '%' : '-';
                        const eq = r.Equity_Ratio ? (r.Equity_Ratio).toFixed(1) + 'x' : '-';
                        
                        tbody.innerHTML += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td>${idx + 1}</td>
                                <td style="color: #38bdf8; font-weight: bold;"><a href="/compare?ticker=${t}" class="ticker-link" target="_blank">${t}</a></td>
                                <td style="color: #fbbf24; font-weight: bold;">${score.toFixed(1)}</td>
                                <td style="color: #10b981;">${pb}</td>
                                <td class="text-gray-300">${pe}</td>
                                <td class="text-gray-300">${roe_ttm}</td>
                                <td class="text-emerald-400">${eq}</td>
                            </tr>
                        `;
                    } else {
                        const roic = r.ROIC_TTM ? (r.ROIC_TTM * 100).toFixed(1) + '%' : '-';
                        const cfo = r.CFO_Quality_TTM ? r.CFO_Quality_TTM.toFixed(2) : '-';
                        const val = r.Value_Ratio ? r.Value_Ratio.toFixed(1) : '-';
                        
                        tbody.innerHTML += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td>${idx + 1}</td>
                                <td style="color: #38bdf8; font-weight: bold;"><a href="/compare?ticker=${t}" class="ticker-link" target="_blank">${t}</a></td>
                                <td style="color: #fbbf24; font-weight: bold;">${score.toFixed(1)}</td>
                                <td>${roic}</td>
                                <td>${cfo}</td>
                                <td style="color: #10b981;">${val}</td>
                            </tr>
                        `;
                    }
                });

                if (isBank) {
                    const roa = medianFor('ROA', 'median_roa');
                    const nim = medianFor('NIM', 'median_nim');
                    const value = medianFor('Value_Ratio', 'median_value');
                    const eq = medianFor('Equity_Ratio', 'median_eq');
                    tbody.insertAdjacentHTML('afterbegin', `
                        <tr class="sector-median-row">
                            ${medianLabel}${medianScoreCell}
                            <td>${roa === null ? '-' : (roa * 100).toFixed(1) + '%'}</td>
                            <td>${nim === null ? '-' : (nim * 100).toFixed(1) + '%'}</td>
                            <td>${value === null ? '-' : (value * 100).toFixed(1)}</td>
                            <td>${eq === null ? '-' : (eq * 100).toFixed(1) + '%'}</td>
                        </tr>
                    `);
                } else if (isSecurities) {
                    const pb = medianFor('PB', 'median_pb');
                    const pe = medianFor('PE', 'median_pe');
                    const roeTtm = medianFor('ROE_TTM', 'median_roe_ttm');
                    const eq = medianFor('Equity_Ratio', 'median_eq');
                    tbody.insertAdjacentHTML('afterbegin', `
                        <tr class="sector-median-row">
                            ${medianLabel}${medianScoreCell}
                            <td>${pb === null ? '-' : pb.toFixed(2)}</td>
                            <td>${pe === null ? '-' : pe.toFixed(1)}</td>
                            <td>${roeTtm === null ? '-' : (roeTtm * 100).toFixed(1) + '%'}</td>
                            <td>${eq === null ? '-' : eq.toFixed(1) + 'x'}</td>
                        </tr>
                    `);
                } else {
                    const roic = medianFor('ROIC_TTM', 'median_roic_ttm');
                    const cfo = medianFor('CFO_Quality_TTM', 'median_cfo_ttm');
                    const value = medianFor('Value_Ratio', 'median_value');
                    tbody.insertAdjacentHTML('afterbegin', `
                        <tr class="sector-median-row">
                            ${medianLabel}${medianScoreCell}
                            <td>${roic === null ? '-' : (roic * 100).toFixed(1) + '%'}</td>
                            <td>${cfo === null ? '-' : cfo.toFixed(2)}</td>
                            <td>${value === null ? '-' : value.toFixed(1)}</td>
                        </tr>
                    `);
                }
            } else if (data.status === 'syncing' && rows.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="padding: 20px; text-align: center; color: #f59e0b;"><i class="fas fa-spinner fa-spin"></i> Đang tải dữ liệu...</td></tr>`;
            } else if (data.status !== 'syncing' && rows.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #94a3b8;">Không có dữ liệu hoặc lỗi.</td></tr>`;
            }

            if (data.status === 'syncing') {
                setTimeout(() => {
                    fetchDataForSector(sector, elementId);
                }, 3000);
            }
        } catch (error) {
            console.error(error);
            const tbody = document.getElementById(`tbody-${elementId}`);
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #ef4444;">Lỗi tải dữ liệu. Xin thử lại sau.</td></tr>`;
        }
    }
});
