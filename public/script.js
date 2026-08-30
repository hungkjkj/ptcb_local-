document.addEventListener('DOMContentLoaded', () => {
    const tickerInput = document.getElementById('ticker-input');
    const runBtn = document.getElementById('run-btn');
    const statusMessage = document.getElementById('status-message');
    const reportContainer = document.getElementById('report-container');
    const summaryCards = document.getElementById('summary-cards');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.querySelector('.spinner');
    const rankingContainer = document.getElementById('ranking-container');
    const rankingBody = document.getElementById('ranking-body');
    const rankingHeader = document.getElementById('ranking-header');

    let currentReportData = null; // Store data for JSON export
    let charts = {}; // Store chart instances to destroy them later

    // Color palette for different companies
    const chartColors = [
        { border: '#38bdf8', bg: 'rgba(56, 189, 248, 0.1)' }, // Main (Blue)
        { border: '#fbbf24', bg: 'rgba(251, 191, 36, 0.1)' }, // Yellow
        { border: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' }, // Green
        { border: '#f43f5e', bg: 'rgba(244, 63, 94, 0.1)' }, // Pink
        { border: '#a855f7', bg: 'rgba(168, 85, 247, 0.1)' }  // Purple
    ];

    runBtn.addEventListener('click', () => {
        const ticker = tickerInput.value.trim().toUpperCase();
        const peerInputs = document.querySelectorAll('.peer-input');
        const taxRateInput = document.getElementById('tax-rate-input');
        
        const peersArr = [];
        peerInputs.forEach(input => {
            const val = input.value.trim().toUpperCase();
            if (val) peersArr.push(val);
        });
        const peers = peersArr.join(' ');
        
        const taxRate = taxRateInput.value ? parseFloat(taxRateInput.value) : 0.2;
        
        if (!ticker) {
            showError('Vui lòng nhập mã cổ phiếu chính.');
            return;
        }
        runReport(ticker, peers, taxRate);
    });
    
    tickerInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') runBtn.click();
    });

    async function runReport(ticker, peers, taxRate = 0.2) {
        // UI Loading state
        runBtn.disabled = true;
        tickerInput.disabled = true;
        document.querySelectorAll('.peer-input').forEach(el => el.disabled = true);
        btnText.textContent = 'Đang phân tích...';
        spinner.style.display = 'block';
        reportContainer.style.display = 'none';
        statusMessage.textContent = `Hệ thống đang tải dữ liệu cho mã "${ticker}"${peers ? ` và các mã so sánh` : ''}. Vui lòng đợi...`;
        statusMessage.style.color = '#38bdf8';

        try {
            const queryParams = new URLSearchParams({ ticker: ticker, peers: peers });
            queryParams.append('taxRate', taxRate);
            
            // Thêm cache-buster để tránh Cloudflare hoặc trình duyệt cache lại kết quả cũ
            queryParams.append('t', Date.now());

            const response = await fetch(`/api/report?${queryParams.toString()}`);
            if (!response.ok) throw new Error('API server error');
            const data = await response.json();

            if (data.status === 'success' && data.data) {
                const parsedPeers = peers ? peers.split(' ').filter(p => p.trim() !== '') : [];
                const totalRequested = parsedPeers.length + 1;
                if (data.data.ranking && data.data.ranking.length > 0 && data.data.ranking.length < totalRequested) {
                    showStatus(`Đã phân tích xong dữ liệu! (Lưu ý: Một số mã đối thủ không hợp lệ hoặc không có dữ liệu)`, false);
                } else {
                    showStatus('Đã phân tích xong dữ liệu!', false);
                }
                currentReportData = data.data;
                renderReport(data.data);
                reportContainer.style.display = 'block';
            } else {
                showError(data.detail || 'Có lỗi xảy ra trong quá trình lấy dữ liệu.');
            }
        } catch (error) {
            showError('Lỗi kết nối hoặc mã cổ phiếu không tồn tại.');
            console.error(error);
        } finally {
            // Restore UI
            runBtn.disabled = false;
            tickerInput.disabled = false;
            document.querySelectorAll('.peer-input').forEach(el => el.disabled = false);
            btnText.textContent = 'Phân tích';
            spinner.style.display = 'none';
        }
    }

    function renderReport(data) {
        const { main_ticker, reports, ranking } = data;
        
        const mainReport = reports[main_ticker];
        if (!mainReport) {
            showError('Không lấy được dữ liệu cho mã chính.');
            return;
        }

        const { company_name, sector, summary, history } = mainReport;
        
        // Render Company Info
        const companyInfo = document.getElementById('company-info');
        if (companyInfo) {
            companyInfo.innerHTML = `
                <h2 style="color: var(--text-color); font-size: 1.8rem; margin-bottom: 0.5rem; font-weight: 700;">${company_name || main_ticker}</h2>
                <p style="color: #94a3b8; font-size: 1.1rem; letter-spacing: 0.05em; text-transform: uppercase;">Lĩnh vực: <span style="color: var(--primary-color);">${sector || 'Chưa phân loại'}</span></p>
            `;
        }
        
        const isBank = (sector && (sector.toLowerCase() === 'ngân hàng' || sector.toLowerCase() === 'banks'));
        const isSecurities = (sector && (sector.toLowerCase().includes('chứng khoán') || sector.toLowerCase().includes('dịch vụ tài chính') || sector.toLowerCase().includes('financial services') || sector.toLowerCase().includes('securities')));

        // Render Ranking Table
        if (ranking && ranking.length > 0) {
            rankingContainer.style.display = 'block';
            
            if (isBank) {
                rankingHeader.innerHTML = `
                    <tr style="background: rgba(255,255,255,0.05); color: #94a3b8;">
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Xếp hạng</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Mã CP</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Tổng điểm</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROA (%)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROE (%)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">NIM (%)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">P/B</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Value Ratio</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">EQ (%)</th>
                    </tr>
                `;
            } else if (isSecurities) {
                rankingHeader.innerHTML = `
                    <tr style="background: rgba(255,255,255,0.05); color: #94a3b8;">
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Xếp hạng</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Mã CP</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Tổng điểm</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">P/B (Cur)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">P/E (Cur)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROE (TTM)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROE (5Y)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">EQ (Cur)</th>
                    </tr>
                `;
            } else {
                rankingHeader.innerHTML = `
                    <tr style="background: rgba(255,255,255,0.05); color: #94a3b8;">
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Xếp hạng</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Mã CP</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">Tổng điểm</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROIC (5Y)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">ROIC (TTM)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">B/P (5Y)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">CFO/NI (TTM)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">D/E (Cur)</th>
                        <th style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">P/B (Cur)</th>
                    </tr>
                `;
            }

            const formatPBWithPrice = (pb, price) => {
                if (pb === undefined || pb === null || isNaN(pb)) return '-';
                let pbStr = pb.toFixed(2);
                if (price && price > 0) {
                    pbStr += ` <span style="font-size: 0.85em; color: #94a3b8;">(${price.toLocaleString('vi-VN')} vnd)</span>`;
                }
                return pbStr;
            };

            let html = '';
            ranking.forEach((r, idx) => {
                const isMain = r.ticker === main_ticker;
                const rowStyle = isMain ? 'background: rgba(56, 189, 248, 0.15); font-weight: bold; color: #fff;' : '';
                
                let pbStyle = '';
                if (isBank) {
                    // Highlight P/B in 1.0 - 1.2
                    const pbVal = r.PB_Current;
                    if (pbVal >= 1.0 && pbVal <= 1.2) {
                        pbStyle = 'color: #10b981; font-weight: bold; text-shadow: 0 0 5px rgba(16,185,129,0.5);';
                    }
                }

                if (isBank) {
                    html += `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); ${rowStyle}">
                            <td style="padding: 12px;">${idx + 1}</td>
                            <td style="padding: 12px; color: ${isMain ? '#38bdf8' : 'inherit'}">${r.ticker}</td>
                            <td style="padding: 12px; color: #fbbf24;">${r.Total_Score.toFixed(1)}</td>
                            <td style="padding: 12px;">${(r.ROA_Current * 100).toFixed(2)}%</td>
                            <td style="padding: 12px;">${(r.ROE_Current * 100).toFixed(1)}%</td>
                            <td style="padding: 12px;">${(r.NIM_Current * 100).toFixed(1)}%</td>
                            <td style="padding: 12px; ${pbStyle}">${formatPBWithPrice(r.PB_Current, r.Current_Price)}</td>
                            <td style="padding: 12px; color: #10b981; font-weight: bold;">${(r.Value_Ratio_Current * 100).toFixed(1)}</td>
                            <td style="padding: 12px;">${(r.Equity_Ratio_Current * 100).toFixed(1)}%</td>
                        </tr>
                    `;
                } else if (isSecurities) {
                    html += `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); ${rowStyle}">
                            <td style="padding: 12px;">${idx + 1}</td>
                            <td style="padding: 12px; color: ${isMain ? '#38bdf8' : 'inherit'}">${r.ticker}</td>
                            <td style="padding: 12px; color: #fbbf24;">${r.Total_Score ? r.Total_Score.toFixed(1) : '-'}</td>
                            <td style="padding: 12px;">${formatPBWithPrice(r.PB_Current, r.Current_Price)}</td>
                            <td style="padding: 12px;">${r.PE_Current ? r.PE_Current.toFixed(1) : '-'}</td>
                            <td style="padding: 12px;">${r.ROE_TTM ? (r.ROE_TTM * 100).toFixed(1) + '%' : '-'}</td>
                            <td style="padding: 12px;">${r.ROE_5Y ? (r.ROE_5Y * 100).toFixed(1) + '%' : '-'}</td>
                            <td style="padding: 12px;">${r.Equity_Ratio_Current ? (r.Equity_Ratio_Current * 100).toFixed(1) + '%' : '-'}</td>
                        </tr>
                    `;
                } else {
                    html += `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); ${rowStyle}">
                            <td style="padding: 12px;">${idx + 1}</td>
                            <td style="padding: 12px; color: ${isMain ? '#38bdf8' : 'inherit'}">${r.ticker}</td>
                            <td style="padding: 12px; color: #fbbf24;">${r.Total_Score.toFixed(1)}</td>
                            <td style="padding: 12px;">${(r.ROIC_5Y * 100).toFixed(1)}%</td>
                            <td style="padding: 12px;">${(r.ROIC_TTM * 100).toFixed(1)}%</td>
                            <td style="padding: 12px;">${r.BP_5Y ? r.BP_5Y.toFixed(2) : '-'}</td>
                            <td style="padding: 12px;">${r.CFO_Quality_TTM ? r.CFO_Quality_TTM.toFixed(2) : '-'}</td>
                            <td style="padding: 12px;">${r.DE_Current ? r.DE_Current.toFixed(2) : '-'}</td>
                            <td style="padding: 12px;">${formatPBWithPrice(r.PB_Current, r.Current_Price)}</td>
                        </tr>
                    `;
                }
            });
            rankingBody.innerHTML = html;
        } else {
            rankingContainer.style.display = 'none';
        }

        // Render Summary (Always for main ticker)
        const formatPct = (val) => (val * 100).toFixed(2) + '%';
        const formatNum = (val) => val.toFixed(2);
        const formatPBWithPriceSummary = (pb, price) => {
            if (pb === undefined || pb === null || isNaN(pb)) return '-';
            let pbStr = pb.toFixed(2);
            if (price && price > 0) {
                pbStr += ` <span style="font-size: 0.85em; color: #94a3b8;">(${price.toLocaleString('vi-VN')} vnd)</span>`;
            }
            return pbStr;
        };
        
        const tQ = summary.Latest_Quarter ? ` <span style="font-size:0.85rem; color:#94a3b8">(${summary.Latest_Quarter})</span>` : '';
        const tY = summary.Latest_Year ? ` <span style="font-size:0.85rem; color:#94a3b8">(${summary.Latest_Year})</span>` : '';

        if (isBank) {
            summaryCards.innerHTML = `
                <div class="card" title="Sinh lời trên Tổng Tài Sản (ROA): Hiệu quả sử dụng tài sản, bao hàm cả chất lượng tài sản (nợ xấu).">
                    <h3>ROA ⓘ</h3>
                    <p>${formatPct(summary.ROA_Current)}${tQ}</p>
                </div>
                <div class="card" title="Sinh lời trên Vốn Chủ Sở Hữu (ROE): Lợi nhuận sinh ra từ vốn của cổ đông.">
                    <h3>ROE ⓘ</h3>
                    <p>${formatPct(summary.ROE_Current)}${tQ}</p>
                </div>
                <div class="card" title="Biên lãi thuần (Net Interest Margin): Khả năng sinh lời cốt lõi từ tín dụng.">
                    <h3>NIM ⓘ</h3>
                    <p>${formatPct(summary.NIM_Current)}${tQ}</p>
                </div>
                <div class="card" title="Chỉ số Giá trên Sổ sách (Price to Book).">
                    <h3>P/B (Current) ⓘ</h3>
                    <p>${formatPBWithPriceSummary(summary.PB_Current, summary.Current_Price)}${tQ}</p>
                </div>
                <div class="card" title="Tỷ số Giá trị = ROE / P/B. Càng cao càng hấp dẫn.">
                    <h3>Value Ratio ℹ️</h3>
                    <p style="color: #10b981; font-weight: bold;">${formatNum(summary.Value_Ratio_Current * 100)}</p>
                </div>
                <div class="card" title="Độ an toàn vốn (Equity Ratio) = ROA / ROE. Mức đòn bẩy tài chính.">
                    <h3>EQ (%) ℹ️</h3>
                    <p>${formatPct(summary.Equity_Ratio_Current)}${tQ}</p>
                </div>
            `;
        } else if (isSecurities) {
            summaryCards.innerHTML = `
                <div class="card" title="Chỉ số Giá trên Sổ sách (Price to Book).">
                    <h3>P/B (Current) ⓘ</h3>
                    <p style="color: #10b981; font-weight: bold;">${formatPBWithPriceSummary(summary.PB_Current, summary.Current_Price)}${tQ}</p>
                </div>
                <div class="card" title="Chỉ số P/E.">
                    <h3>P/E (Current) ⓘ</h3>
                    <p>${formatNum(summary.PE_Current)}${tQ}</p>
                </div>
                <div class="card" title="Sinh lời trên Vốn Chủ Sở Hữu (ROE).">
                    <h3>ROE (TTM) ⓘ</h3>
                    <p>${formatPct(summary.ROE_TTM)}${tQ}</p>
                </div>
                <div class="card" title="ROE trung bình 5 năm.">
                    <h3>ROE (5Y) ⓘ</h3>
                    <p>${formatPct(summary.ROE_5Y)}${tY}</p>
                </div>
                <div class="card" title="Tỷ lệ vốn chủ sở hữu (Equity Ratio).">
                    <h3>Equity Ratio ⓘ</h3>
                    <p>${formatPct(summary.Equity_Ratio_Current)}${tQ}</p>
                </div>
            `;
        } else {
            summaryCards.innerHTML = `
                <div class="card" title="Tỷ suất sinh lời trên vốn đầu tư (Return on Invested Capital). Công thức: EBIT * (1 - Thuế) / (Vốn chủ sở hữu + Nợ vay - Tiền mặt).">
                    <h3>ROIC (TTM / 5Y) ⓘ</h3>
                    <p>${formatPct(summary.ROIC_TTM)}${tQ} / <span style="font-size:0.9rem; color:#94a3b8">${formatPct(summary.ROIC_5Y)}${tY}</span></p>
                </div>
                <div class="card" title="Công thức: Lợi suất E/P (Trung bình 5 năm) / ROIC (Trung bình 5 năm). Đo lường mức định giá rẻ (E/P) trên mỗi đơn vị hiệu quả sinh lời (ROIC).">
                    <h3>Value Ratio ⓘ</h3>
                    <p>${formatNum(summary.Value_Ratio)}${tY}</p>
                    <div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">Avg E/P ÷ Avg ROIC (5Y)</div>
                </div>
                <div class="card" title="Chất lượng dòng tiền (CFO Quality). Công thức: Dòng tiền hoạt động kinh doanh (CFO) / Lợi nhuận sau thuế (Net Income). Đo lường mức độ lợi nhuận được hậu thuẫn bởi tiền mặt thực tế.">
                    <h3>CFO Quality (TTM) ⓘ</h3>
                    <p>${formatNum(summary.CFO_Quality_TTM)}${tQ}</p>
                </div>
                <div class="card" title="Tỷ lệ Nợ vay trên Vốn chủ sở hữu (Debt to Equity). Công thức: Tổng nợ vay / Vốn chủ sở hữu. Đo lường đòn bẩy tài chính.">
                    <h3>D/E (Current) ⓘ</h3>
                    <p>${formatNum(summary.DE_Current)}${tQ}</p>
                </div>
                <div class="card" title="Hệ số thanh toán lãi vay (Interest Coverage Ratio). Công thức: Lợi nhuận trước lãi vay và thuế (EBIT) / Chi phí lãi vay. Đo lường khả năng trả lãi của doanh nghiệp.">
                    <h3>ICR (Current) ⓘ</h3>
                    <p>${formatNum(summary.ICR_Current)}${tQ}</p>
                </div>
                <div class="card" title="Chỉ số Giá trên Sổ sách (Price to Book).">
                    <h3>P/B (Current) ⓘ</h3>
                    <p>${formatPBWithPriceSummary(summary.PB_Current, summary.Current_Price)}${tQ}</p>
                </div>
            `;
        }
        
        // Destroy old charts if exist
        Object.values(charts).forEach(chart => chart.destroy());
        charts = {};
        
        // Prepare datasets for charts
        const labels = history.map(h => h.year);
        
        let datasetsRoic = [];
        let datasetsDe = [];
        let datasetsCfo = [];
        let datasetsBp = [];
        let datasetsIcr = [];
        let datasetsEp = [];

        let colorIndex = 0;
        
        // We want main ticker to be first
        const tickersToPlot = [main_ticker, ...Object.keys(reports).filter(t => t !== main_ticker)];

        for (const t of tickersToPlot) {
            const rep = reports[t];
            if (!rep || !rep.history) continue;
            
            const hist = rep.history;
            const c = chartColors[colorIndex % chartColors.length];
            const isMain = t === main_ticker;
            const borderWidth = isMain ? 3 : 2;

            if (isBank) {
                datasetsRoic.push({
                    label: `${t} ROA (%)`,
                    data: hist.map(h => (h.roa * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsDe.push({
                    label: `${t} ROE (%)`,
                    data: hist.map(h => (h.roe * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsCfo.push({
                    label: `${t} NIM (%)`,
                    data: hist.map(h => (h.nim * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsBp.push({
                    label: `${t} P/B`,
                    data: hist.map(h => h.pb.toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsIcr.push({
                    label: `${t} Value Ratio`,
                    data: hist.map(h => (h.value_ratio * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsEp.push({
                    label: `${t} E/P (%)`,
                    data: hist.map(h => (h.ep * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
            } else if (isSecurities) {
                datasetsRoic.push({
                    label: `${t} ROE (%)`,
                    data: hist.map(h => (h.roe * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsDe.push({
                    label: `${t} Equity Ratio (%)`,
                    data: hist.map(h => (h.equity_ratio * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsCfo.push({
                    label: `${t} ROA (%)`,
                    data: hist.map(h => (h.roa * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsBp.push({
                    label: `${t} P/B`,
                    data: hist.map(h => h.pb.toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsIcr.push({
                    label: `${t} P/E`,
                    data: hist.map(h => h.pe.toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsEp.push({
                    label: `${t} E/P (%)`,
                    data: hist.map(h => (h.pe > 0 ? (1/h.pe)*100 : 0).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
            } else {
                datasetsRoic.push({
                    label: `${t} ROIC (%)`,
                    data: hist.map(h => (h.roic * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });

                datasetsDe.push({
                    label: `${t} D/E`,
                    data: hist.map(h => h.de.toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                
                // CFO Quality = CFO / NI
                datasetsCfo.push({
                    label: `${t} CFO/NI`,
                    data: hist.map(h => (h.ni !== 0 ? (h.cfo / h.ni) : 0).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });

                datasetsBp.push({
                    label: `${t} P/B`,
                    data: hist.map(h => (h.bp > 0 ? 1 / h.bp : 0).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });

                datasetsIcr.push({
                    label: `${t} ICR`,
                    data: hist.map(h => h.icr.toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
                datasetsEp.push({
                    label: `${t} E/P (%)`,
                    data: hist.map(h => (h.ep * 100).toFixed(2)),
                    borderColor: c.border,
                    backgroundColor: c.bg,
                    borderWidth: borderWidth,
                    tension: 0.4
                });
            }

            colorIndex++;
        }

        // Setup Charts
        Chart.defaults.color = 'rgba(255, 255, 255, 0.7)';
        Chart.defaults.font.family = 'Inter';
        
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: { mode: 'index', intersect: false }
            },
            interaction: { mode: 'nearest', axis: 'x', intersect: false },
            scales: {
                y: { grid: { color: 'rgba(255, 255, 255, 0.1)' } },
                x: { 
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    offset: true
                }
            }
        };

        const createLineChart = (ctxId, datasets) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'line',
                data: { labels: labels, datasets: datasets },
                options: commonOptions
            });
        };

        charts.roic = createLineChart('roicChart', datasetsRoic);
        charts.de = createLineChart('deChart', datasetsDe);
        charts.cf = createLineChart('cfChart', datasetsCfo);
        charts.bp = createLineChart('bpChart', datasetsBp);
        charts.icr = createLineChart('icrChart', datasetsIcr);
        charts.ep = createLineChart('epChart', datasetsEp);

        // Update titles if necessary (CFO vs NI is now CFO/NI)
        const cfChartH3 = document.querySelector('#cfChart').parentElement.querySelector('h3');
        if (cfChartH3) {
            cfChartH3.textContent = isBank ? 'LLR (%)' : 'CFO / Net Income (CFO Quality)';
        }
        
        const bpChartH3 = document.querySelector('#bpChart').parentElement.querySelector('h3');
        if (bpChartH3) {
            bpChartH3.textContent = 'P/B';
        }

        const epChartH3 = document.querySelector('#epChart').parentElement.querySelector('h3');
        if (epChartH3) {
            epChartH3.textContent = 'E/P (%)';
        }

        reportContainer.style.display = 'block';
    }

    function showStatus(msg, isError = false) {
        statusMessage.textContent = msg;
        statusMessage.style.color = isError ? 'var(--danger-color)' : '#10b981';
    }

    function showError(msg) {
        statusMessage.textContent = msg;
        statusMessage.style.color = 'var(--danger-color)';
        tickerInput.disabled = false;
        document.querySelectorAll('.peer-input').forEach(el => el.disabled = false);
        runBtn.disabled = false;
    }

    const copyReportBtn = document.getElementById('copy-report-btn');
    if (copyReportBtn) {
        copyReportBtn.addEventListener('click', () => {
            if (!currentReportData) return;
            
            const mainTicker = currentReportData.main_ticker;
            const mainReport = currentReportData.reports[mainTicker];
            
            const aiData = {
                ticker: mainTicker,
                company_name: mainReport.company_name,
                sector: mainReport.sector,
                summary_indicators: mainReport.summary,
                historical_data: mainReport.history,
            };
            
            const peers = Object.keys(currentReportData.reports).filter(t => t !== mainTicker);
            if (peers.length > 0) {
                aiData.peers = peers.map(p => ({
                    ticker: p,
                    company_name: currentReportData.reports[p].company_name,
                    summary_indicators: currentReportData.reports[p].summary,
                    historical_data: currentReportData.reports[p].history
                }));
            }
            
            if (currentReportData.ranking && currentReportData.ranking.length > 0) {
                aiData.ranking = currentReportData.ranking;
            }

            const jsonString = JSON.stringify(aiData, null, 2);

            // Sao chép vào clipboard để người dùng dễ dán
            navigator.clipboard.writeText(jsonString).catch(err => console.error("Clipboard error:", err));

            // Tải file JSON xuống
            const blob = new Blob([jsonString], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${mainTicker}_AI_Analysis_Data.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            const originalText = copyReportBtn.innerHTML;
            copyReportBtn.innerHTML = '<i class="fas fa-check"></i> Đã xuất file JSON';
            setTimeout(() => {
                copyReportBtn.innerHTML = originalText;
            }, 2000);
        });
    }
});
