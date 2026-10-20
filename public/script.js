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
    const riskFreeRateInput = document.getElementById('risk-free-rate-input');
    const marketRiskPremiumInput = document.getElementById('market-risk-premium-input');
    const forecastGrowthInput = document.getElementById('forecast-growth-input');
    const terminalGrowthInput = document.getElementById('terminal-growth-input');

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
            const riskFreePercent = riskFreeRateInput?.value.trim();
            const marketRiskPremiumPercent = marketRiskPremiumInput?.value.trim();
            const forecastGrowthPercent = forecastGrowthInput?.value.trim();
            const terminalGrowthPercent = terminalGrowthInput?.value.trim();
            if (riskFreePercent !== '' && Number.isFinite(Number(riskFreePercent))) {
                queryParams.append('riskFreeRate', Number(riskFreePercent) / 100);
            }
            if (marketRiskPremiumPercent !== '' && Number.isFinite(Number(marketRiskPremiumPercent))) {
                queryParams.append('marketRiskPremium', Number(marketRiskPremiumPercent) / 100);
            }
            if (forecastGrowthPercent !== '' && Number.isFinite(Number(forecastGrowthPercent))) {
                queryParams.append('forecastGrowthRate', Number(forecastGrowthPercent) / 100);
            }
            if (terminalGrowthPercent !== '' && Number.isFinite(Number(terminalGrowthPercent))) {
                queryParams.append('terminalGrowthRate', Number(terminalGrowthPercent) / 100);
            }
            
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

        renderValuationInputs(mainReport.valuation_inputs, mainReport.summary?.Current_Price);
        
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

    function calculateDcfFromInputs(valuation, currentMarketPrice) {
        const capital = valuation.capital_structure || {};
        const history = Array.isArray(valuation.history) ? valuation.history : [];
        const toNumber = (value) => typeof value === 'number' && Number.isFinite(value) ? value : null;
        const inputRate = (input) => {
            const raw = input?.value.trim();
            return raw !== '' && Number.isFinite(Number(raw)) ? Number(raw) / 100 : null;
        };
        const historicalRows = [...history].sort((a, b) => Number(a.year) - Number(b.year));
        const positiveFcffPoints = historicalRows
            .map((row) => ({ year: Number(row.year), fcff: toNumber(row.fcff) }))
            .filter((point) => Number.isInteger(point.year) && point.fcff !== null && point.fcff > 0);
        let historicalGrowthRate = null;
        let historicalGrowthSource = 'unavailable';
        if (positiveFcffPoints.length === 1) {
            historicalGrowthRate = 0;
            historicalGrowthSource = 'flat_fcff_fallback';
        } else if (positiveFcffPoints.length >= 2) {
            const first = positiveFcffPoints[0];
            const last = positiveFcffPoints[positiveFcffPoints.length - 1];
            if (last.year > first.year) {
                historicalGrowthRate = (last.fcff / first.fcff) ** (1 / (last.year - first.year)) - 1;
                if (Number.isFinite(historicalGrowthRate)) historicalGrowthSource = 'historical_fcff_cagr';
                else historicalGrowthRate = null;
            }
        }
        const manualForecastGrowth = inputRate(forecastGrowthInput);
        const manualTerminalGrowth = inputRate(terminalGrowthInput);
        let forecastGrowth = manualForecastGrowth ?? historicalGrowthRate;
        let terminalGrowth = manualTerminalGrowth ?? historicalGrowthRate;
        let forecastGrowthSource = manualForecastGrowth !== null ? 'user_input' : historicalGrowthSource;
        let terminalGrowthSource = manualTerminalGrowth !== null ? 'user_input' : historicalGrowthSource;
        const rate = toNumber(valuation.wacc?.value);
        if (terminalGrowthSource === 'historical_fcff_cagr' && terminalGrowth !== null
            && rate !== null && rate > 0 && terminalGrowth >= rate) {
            terminalGrowth = 0;
            terminalGrowthSource = 'flat_terminal_fallback';
        }
        if (forecastGrowthSource === 'historical_fcff_cagr' && forecastGrowth !== null && forecastGrowth > 1) {
            forecastGrowth = 0;
            forecastGrowthSource = 'flat_fcff_fallback';
        }
        let baseRow = [...history].reverse().find((row) => {
            const fcff = toNumber(row.fcff);
            return fcff !== null && fcff > 0;
        });
        const latestHistoryRow = historicalRows[historicalRows.length - 1] || {};
        const fcffFieldLabels = {
            ebit: 'EBIT / lợi nhuận hoạt động',
            nopat: 'NOPAT (cần EBIT và thuế suất)',
            da: 'D&A / khấu hao và phân bổ',
            capex: 'CapEx / chi đầu tư tài sản cố định',
            delta_nwc: 'ΔNWC (cần NWC năm hiện tại và năm trước)'
        };
        const missingFcffKeys = new Set(latestHistoryRow.fcff_missing_inputs || []);
        if (missingFcffKeys.has('ebit')) missingFcffKeys.delete('nopat');
        const missingFcffParts = ['ebit', 'nopat', 'da', 'capex', 'delta_nwc']
            .filter((key) => missingFcffKeys.has(key)).map((key) => fcffFieldLabels[key]);
        let baseFcffAssumptions = [];
        if (!baseRow) {
            for (const row of [...history].reverse()) {
                const missing = new Set(row.fcff_missing_inputs || []);
                if (missing.has('ebit') || missing.has('nopat') || missing.has('capex')) continue;
                let nopat = toNumber(row.nopat);
                if (nopat === null) {
                    const ebit = toNumber(row.ebit);
                    const taxRate = toNumber(row.tax_rate_used_for_fcff);
                    if (ebit === null || taxRate === null) continue;
                    nopat = ebit * (1 - taxRate);
                }
                const capex = toNumber(row.capex);
                if (capex === null) continue;
                let da = toNumber(row.da);
                let deltaNwc = toNumber(row.delta_nwc);
                const assumptions = [];
                if (missing.has('da') || da === null) {
                    da = 0;
                    assumptions.push('D&A = 0 do thiếu dữ liệu');
                }
                if (missing.has('delta_nwc') || deltaNwc === null) {
                    deltaNwc = 0;
                    assumptions.push('ΔNWC = 0 do thiếu dữ liệu');
                }
                const scenarioFcff = nopat + da - capex - deltaNwc;
                if (scenarioFcff > 0 && assumptions.length) {
                    baseRow = { ...row, fcff: scenarioFcff };
                    baseFcffAssumptions = assumptions;
                    break;
                }
            }
        }
        if (baseFcffAssumptions.length && historicalGrowthRate === null) {
            if (manualForecastGrowth === null) {
                forecastGrowth = 0;
                forecastGrowthSource = 'flat_fcff_fallback';
            }
            if (manualTerminalGrowth === null) {
                terminalGrowth = 0;
                terminalGrowthSource = 'flat_fcff_fallback';
            }
        }
        const dcf = {
            status: 'not_calculated',
            forecast_years: 5,
            forecast_growth_rate: forecastGrowth,
            forecast_growth_rate_source: forecastGrowthSource,
            terminal_growth_rate: terminalGrowth,
            terminal_growth_rate_source: terminalGrowthSource,
            historical_growth_start_year: positiveFcffPoints.length ? positiveFcffPoints[0].year : null,
            historical_growth_end_year: positiveFcffPoints.length ? positiveFcffPoints[positiveFcffPoints.length - 1].year : null,
            historical_growth_points: positiveFcffPoints.length,
            growth_method_version: 2,
            base_fcff: baseRow ? baseRow.fcff : null,
            base_fcff_year: baseRow ? baseRow.year : null,
            base_fcff_source: baseFcffAssumptions.length ? 'zero_missing_inputs_scenario' : (baseRow ? 'historical_fcff' : null),
            base_fcff_assumptions: baseFcffAssumptions,
            fcff_missing_components: missingFcffParts,
            enterprise_value: null,
            equity_value: null,
            intrinsic_value_per_share: null,
            current_share_price: toNumber(capital.current_share_price) ?? toNumber(currentMarketPrice),
            upside: null
        };
        const reasons = [];
        if (forecastGrowth === null) reasons.push('Chưa có năm nào có FCFF dương và đủ đầu vào làm cơ sở; hãy bổ sung dữ liệu FCFF hoặc nhập g 5 năm.');
        else if (forecastGrowth <= -1 || forecastGrowth > 1) reasons.push('Tốc độ tăng trưởng 5 năm phải lớn hơn -100% và không quá 100%.');
        if (terminalGrowth === null) reasons.push('Chưa có FCFF dương hợp lệ để tự tính g dài hạn; hãy bổ sung dữ liệu hoặc nhập g dài hạn.');
        else if (terminalGrowth <= -1 || terminalGrowth > 1) reasons.push('Tốc độ tăng trưởng dài hạn phải lớn hơn -100% và không quá 100%.');
        if (!baseRow) {
            reasons.push(missingFcffParts.length
                ? `FCFF gần nhất chưa tính được; thiếu: ${missingFcffParts.join(', ')}.`
                : 'Không có FCFF lịch sử đầy đủ để làm cơ sở dự phóng; kiểm tra EBIT, D&A, CapEx và ΔNWC.');
        }
        if (rate === null) reasons.push('WACC chưa tính được đầy đủ.');
        else if (rate <= -1) reasons.push('WACC phải lớn hơn -100%.');
        if (terminalGrowth !== null && rate !== null && terminalGrowth >= rate) reasons.push('Tăng trưởng dài hạn phải thấp hơn WACC.');
        if (reasons.length) {
            dcf.message = 'Chưa thể tính giá trị nội tại: ' + reasons.join(' ');
            return dcf;
        }

        const forecastFcff = Array.from({ length: 5 }, (_, index) => baseRow.fcff * (1 + forecastGrowth) ** (index + 1));
        const pvForecast = forecastFcff.reduce((sum, cashFlow, index) => sum + cashFlow / (1 + rate) ** (index + 1), 0);
        const terminalValue = forecastFcff[4] * (1 + terminalGrowth) / (rate - terminalGrowth);
        dcf.enterprise_value = pvForecast + terminalValue / (1 + rate) ** 5;

        const debt = toNumber(capital.interest_bearing_debt);
        const cash = toNumber(capital.cash_and_equivalents);
        const shares = toNumber(capital.shares_outstanding_estimate);
        if (debt !== null && cash !== null) {
            dcf.equity_value = dcf.enterprise_value + cash - debt;
            if (shares !== null && shares > 0) {
                dcf.intrinsic_value_per_share = dcf.equity_value / shares;
                if (dcf.current_share_price !== null && dcf.current_share_price > 0) {
                    dcf.upside = dcf.intrinsic_value_per_share / dcf.current_share_price - 1;
                }
            }
        }
        dcf.status = dcf.intrinsic_value_per_share !== null ? 'ready' : 'partial';
        const notes = [];
        if (baseFcffAssumptions.length) {
            notes.push(`FCFF cơ sở là kịch bản tham khảo từ năm ${baseRow.year}: ${baseFcffAssumptions.join('; ')}. Không ghi các giả định này thành dữ liệu lịch sử.`);
        }
        if ((positiveFcffPoints.length === 1 || baseFcffAssumptions.length) && (forecastGrowthSource === 'flat_fcff_fallback' || terminalGrowthSource === 'flat_fcff_fallback')) {
            notes.push('Chưa có đủ chuỗi FCFF lịch sử nên g mặc định dùng kịch bản FCFF đi ngang 0%; bạn có thể nhập g để ghi đè.');
        } else if (forecastGrowthSource === 'flat_fcff_fallback') {
            notes.push('CAGR FCFF lịch sử vượt phạm vi hợp lý nên g 5 năm tự động dùng kịch bản đi ngang 0%; bạn có thể nhập g để ghi đè.');
        }
        if (terminalGrowthSource === 'flat_terminal_fallback') {
            notes.push('CAGR FCFF lịch sử không thấp hơn WACC nên g dài hạn tự động dùng kịch bản 0%; bạn có thể nhập g để ghi đè.');
        }
        if (baseRow && history.length && Number(baseRow.year) !== Number(history[history.length - 1].year) && !baseFcffAssumptions.length) {
            notes.push(`FCFF cơ sở lấy từ năm ${baseRow.year} gần nhất có FCFF dương và đủ đầu vào; các năm sau thiếu hoặc không có FCFF dương được bỏ qua.`);
        }
        if (dcf.status === 'partial') notes.push('Đã tính EV; thiếu dữ liệu để quy đổi đầy đủ sang giá trị mỗi cổ phiếu.');
        dcf.message = notes.join(' ') || 'Ước tính DCF từ FCFF dương gần nhất; các năm thiếu dữ liệu được bỏ qua.';
        return dcf;
    }

    function renderBankValuationInputs(container, valuation) {
        const capital = valuation.capital_structure || {};
        const cost = valuation.cost_of_equity || {};
        const bankValue = valuation.bank_valuation || {};
        const history = Array.isArray(valuation.history) ? valuation.history : [];
        const valid = (value) => typeof value === 'number' && Number.isFinite(value);
        const money = (value) => valid(value) ? `${(value / 1e9).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} tỷ` : '—';
        const pct = (value) => valid(value) ? `${(value * 100).toFixed(2)}%` : '—';
        const num = (value, digits = 2) => valid(value) ? value.toLocaleString('vi-VN', { maximumFractionDigits: digits }) : '—';
        const sharePrice = (value) => valid(value) ? `${value.toLocaleString('vi-VN', { maximumFractionDigits: 0 })} đ/cp` : '—';
        const signedPct = (value) => valid(value) ? `${value > 0 ? '+' : ''}${(value * 100).toFixed(1)}%` : '—';
        const card = (label, value, detail = '') => `
            <div class="valuation-metric-card">
                <span>${label}</span><strong>${value}</strong>${detail ? `<small>${detail}</small>` : ''}
            </div>`;
        const growthSourceLabel = (source) => ({
            user_input: 'nhập tay',
            historical_book_equity_cagr: 'CAGR vốn chủ lịch sử',
            flat_book_growth_fallback: 'giả định vốn chủ đi ngang',
            stable_growth_fallback: 'giả định ổn định'
        }[source] || 'chưa có');
        const sourceLabels = {
            'HNX 10Y yield entered manually': 'HNX 10 năm nhập thủ công',
            'User-provided HNX 10Y override': 'Rf nhập từ HNX 10 năm',
            'Vnstock Macro, Vietnam Government Bond 10Y': 'Vnstock Macro · TPCP Việt Nam 10 năm',
            'Damodaran current country-premium workbook (rating-based total ERP)': 'Damodaran · ERP tổng Việt Nam',
            'User-provided ERP override': 'ERP nhập thủ công',
            unavailable: 'chưa có dữ liệu'
        };
        const historyRows = history.map((row) => `
            <tr>
                <td>${row.year ?? '—'}</td>
                <td>${money(row.book_equity)}</td>
                <td>${pct(row.roe)}</td>
                <td>${pct(row.roa)}</td>
                <td>${pct(row.nim)}</td>
                <td>${pct(row.npl_ratio)}</td>
                <td>${pct(row.capital_adequacy_ratio)}</td>
                <td>${num(row.pb)}</td>
                <td>${num(row.pe)}</td>
            </tr>`).join('');
        const riskFreeSource = sourceLabels[cost.risk_free_rate_source] || cost.risk_free_rate_source || 'HNX 10 năm';
        const erpSource = sourceLabels[cost.equity_risk_premium_source] || cost.equity_risk_premium_source || 'Damodaran ERP';
        const rateDetails = `Rf ${pct(cost.risk_free_rate)} · ERP ${pct(cost.equity_risk_premium)} · Beta ${num(cost.beta)} · ${riskFreeSource} · ${erpSource}`;
        const growthDetails = `g vốn chủ 5 năm ${pct(bankValue.forecast_book_growth)} · ${growthSourceLabel(bankValue.forecast_book_growth_source)}; g dài hạn ${pct(bankValue.terminal_growth_rate)} · ${growthSourceLabel(bankValue.terminal_growth_source)}`;

        const forecastLabel = document.querySelector('label[for="forecast-growth-input"]');
        const terminalLabel = document.querySelector('label[for="terminal-growth-input"]');
        if (forecastLabel) forecastLabel.textContent = 'g vốn chủ 5 năm (%)';
        if (terminalLabel) terminalLabel.textContent = 'g vốn chủ dài hạn (%)';
        if (forecastGrowthInput) {
            forecastGrowthInput.setAttribute('aria-label', 'Tăng trưởng vốn chủ ngân hàng trong 5 năm; để trống để ước tính từ lịch sử');
            forecastGrowthInput.title = 'Để trống để lấy CAGR vốn chủ sổ sách lịch sử; nhập số để ghi đè.';
        }
        if (terminalGrowthInput) {
            terminalGrowthInput.setAttribute('aria-label', 'Tăng trưởng vốn chủ ngân hàng dài hạn; phải thấp hơn chi phí vốn chủ');
            terminalGrowthInput.title = 'Để trống để tự ước tính; tăng trưởng dài hạn phải thấp hơn chi phí vốn chủ.';
        }

        container.innerHTML = `
            <div class="valuation-panel-heading">
                <div>
                    <h3><i class="fas fa-building-columns"></i> Định giá ngân hàng · Lợi nhuận thặng dư</h3>
                    <p>Giá trị vốn chủ = vốn chủ sổ sách + giá trị hiện tại của lợi nhuận vượt chi phí vốn chủ; không dùng FCFF/WACC doanh nghiệp.</p>
                </div>
                <span class="valuation-status ${bankValue.status === 'ready' ? 'is-ready' : 'is-partial'}">${bankValue.status === 'ready' ? 'Đã tính giá trị nội tại' : 'Định giá còn thiếu dữ liệu'}</span>
            </div>
            <div class="valuation-metrics-grid bank-valuation-grid">
                ${card('Vốn chủ sổ sách', money(bankValue.book_equity), bankValue.book_equity_as_of ? `Kỳ ${bankValue.book_equity_as_of}` : '')}
                ${card('Chi phí vốn chủ (Ke)', pct(bankValue.cost_of_equity), rateDetails)}
                ${card('ROE hiện tại', pct(bankValue.forecast_roe_start))}
                ${card('ROE ổn định', pct(bankValue.stable_roe), 'Trung vị ROE lịch sử khả dụng')}
                ${card('Giá trị vốn chủ nội tại', money(bankValue.equity_value))}
                ${card('Giá trị nội tại / cổ phiếu', sharePrice(bankValue.intrinsic_value_per_share))}
                ${card('Giá thị trường / cổ phiếu', sharePrice(bankValue.current_share_price))}
                ${card('Chênh lệch so với thị trường', signedPct(bankValue.upside))}
                ${card('P/B thị trường', num(bankValue.market_pb))}
                ${card('P/B hợp lý · lợi nhuận thặng dư', num(bankValue.fair_pb_residual_income))}
                ${card('P/B ổn định · đối chiếu ROE', num(bankValue.fair_pb_stable_state), valid(bankValue.stable_value_per_share) ? `Giá đối chiếu ${sharePrice(bankValue.stable_value_per_share)}` : '')}
                ${card('Giá trị sổ sách / cổ phiếu', sharePrice(bankValue.book_value_per_share))}
            </div>
            <div class="valuation-result-heading"><p>${growthDetails}</p></div>
            <p class="valuation-dcf-note ${bankValue.status === 'ready' ? 'is-ready' : ''}">${bankValue.message || 'Chưa đủ dữ liệu để tính giá trị ngân hàng.'}</p>
            <p class="valuation-source-note">ROE dự phóng giảm dần từ ROE hiện tại về trung vị lịch sử trong 5 năm. P/B ổn định đối chiếu theo (ROE ổn định − g dài hạn) / (Ke − g dài hạn). Giá mỗi cổ phiếu dùng số cổ phiếu ước tính từ vốn hóa / giá hiện tại. CAR hiển thị để tham khảo, chưa được dự phóng riêng trong mô hình.</p>
            <div class="valuation-source-note">
                Nguồn báo cáo: ${valuation.financial_statement_source || 'Vnstock VCI / KBS'}.
                Rf theo <a href="https://qtcb.hnx.vn/vi-vn/trai-phieu/duong-cong-loi-suat.html" target="_blank" rel="noopener">HNX 10Y</a>; ERP từ <a href="https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html" target="_blank" rel="noopener">Damodaran</a> hoặc giá trị bạn nhập.
            </div>
            <div class="table-responsive valuation-history-wrap">
                <table class="valuation-history-table">
                    <thead><tr><th>Năm</th><th>Vốn chủ</th><th>ROE</th><th>ROA</th><th>NIM</th><th>Nợ xấu</th><th>CAR</th><th>P/B</th><th>P/E</th></tr></thead>
                    <tbody>${historyRows || '<tr><td colspan="9">Chưa có dữ liệu lịch sử phù hợp.</td></tr>'}</tbody>
                </table>
            </div>
        `;
    }

    function renderValuationInputs(valuation, currentSharePrice = null) {
        const container = document.getElementById('valuation-inputs-container');
        if (!container) return;
        if (!valuation) {
            container.style.display = 'none';
            container.innerHTML = '';
            return;
        }
        container.style.display = 'block';

        if (valuation.model === 'bank_residual_income') {
            renderBankValuationInputs(container, valuation);
            return;
        }

        const forecastLabel = document.querySelector('label[for="forecast-growth-input"]');
        const terminalLabel = document.querySelector('label[for="terminal-growth-input"]');
        if (forecastLabel) forecastLabel.textContent = 'g 5 năm (%)';
        if (terminalLabel) terminalLabel.textContent = 'g dài hạn (%)';
        if (forecastGrowthInput) {
            forecastGrowthInput.setAttribute('aria-label', 'Tăng trưởng FCFF trong 5 năm; để trống để tự tính');
            forecastGrowthInput.title = 'Để trống để tự tính từ các năm FCFF dương hợp lệ; năm thiếu được bỏ qua.';
        }
        if (terminalGrowthInput) {
            terminalGrowthInput.setAttribute('aria-label', 'Tăng trưởng FCFF dài hạn; để trống để tự tính');
            terminalGrowthInput.title = 'Để trống để dùng CAGR FCFF lịch sử; g dài hạn cần thấp hơn WACC.';
        }

        if (valuation.model === 'sector_specific') {
            container.innerHTML = `
                <h3><i class="fas fa-scale-balanced"></i> Bộ dữ liệu định giá theo ngành</h3>
                <div class="valuation-sector-note">${valuation.message || 'Ngành tài chính cần mô hình và chỉ tiêu định giá riêng.'}</div>
                <p class="valuation-source-note">Chỉ tiêu đang có: ${(valuation.sector_metrics || []).join(', ') || 'xem bảng lịch sử ngành ở phía trên'}.</p>
            `;
            return;
        }

        const capital = valuation.capital_structure || {};
        const wacc = valuation.wacc || {};
        const serverDcf = valuation.dcf;
        const dcf = serverDcf && serverDcf.growth_method_version >= 2
            ? serverDcf
            : calculateDcfFromInputs(valuation, currentSharePrice);
        const dcfCalculated = dcf.status === 'ready' || dcf.status === 'partial';
        const history = Array.isArray(valuation.history) ? valuation.history : [];
        const valid = (value) => typeof value === 'number' && Number.isFinite(value);
        const money = (value) => valid(value) ? `${(value / 1e9).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} tỷ` : '—';
        const pct = (value) => valid(value) ? `${(value * 100).toFixed(2)}%` : '—';
        const num = (value) => valid(value) ? value.toFixed(2) : '—';
        const sharePrice = (value) => valid(value) ? `${value.toLocaleString('vi-VN', { maximumFractionDigits: 0 })} đ/cp` : '—';
        const signedPct = (value) => valid(value) ? `${value > 0 ? '+' : ''}${(value * 100).toFixed(1)}%` : '—';
        const cellMoney = (value) => valid(value) ? (value / 1e9).toLocaleString('vi-VN', { maximumFractionDigits: 1 }) : '—';
        const card = (label, value, detail = '') => `
            <div class="valuation-metric-card">
                <span>${label}</span><strong>${value}</strong>${detail ? `<small>${detail}</small>` : ''}
            </div>`;
        const rows = history.map((row) => {
            const missing = new Set(row.fcff_missing_inputs || []);
            return `
            <tr>
                <td>${row.year}</td>
                <td>${missing.has('ebit') ? '—' : cellMoney(row.ebit)}</td>
                <td>${cellMoney(row.net_income)}</td>
                <td>${missing.has('nopat') || missing.has('ebit') ? '—' : pct(row.tax_rate_used_for_fcff)}</td>
                <td>${missing.has('da') ? '—' : cellMoney(row.da)}</td>
                <td>${missing.has('capex') ? '—' : cellMoney(row.capex)}</td>
                <td>${missing.has('delta_nwc') ? '—' : cellMoney(row.delta_nwc)}</td>
                <td class="fcff-value">${missing.size ? '—' : cellMoney(row.fcff)}</td>
            </tr>`;
        }).join('');
        const missingWacc = (wacc.missing_inputs || []).length > 0;
        const sourceLabels = {
            'HNX 10Y yield entered manually': 'Lợi suất HNX 10 năm nhập thủ công',
            'User-provided HNX 10Y override': 'Rf nhập từ HNX 10 năm',
            'Vnstock Macro, Vietnam Government Bond 10Y': 'Vnstock Macro · TPCP Việt Nam 10 năm',
            'Damodaran current country-premium workbook (rating-based total ERP)': 'Damodaran · ERP tổng theo xếp hạng quốc gia',
            'User-provided ERP override': 'ERP nhập thủ công'
        };
        const riskFreeSource = sourceLabels[wacc.risk_free_rate_source] || wacc.risk_free_rate_source || 'Nguồn HNX 10 năm';
        const erpSource = sourceLabels[wacc.equity_risk_premium_source] || wacc.equity_risk_premium_source || 'Nguồn Damodaran ERP';
        const riskFreeDate = wacc.risk_free_rate_as_of ? ` · ${wacc.risk_free_rate_as_of}` : '';
        const erpDate = wacc.equity_risk_premium_as_of ? ` · ${wacc.equity_risk_premium_as_of}` : '';
        const growthLabel = (source) => ({
            user_input: 'nhập tay',
            historical_fcff_cagr: 'CAGR FCFF lịch sử',
            flat_fcff_fallback: 'kịch bản FCFF đi ngang 0%',
            flat_terminal_fallback: 'kịch bản dài hạn 0% (CAGR ≥ WACC)'
        }[source] || 'chưa có');
        const historyYears = valid(dcf.historical_growth_start_year) && valid(dcf.historical_growth_end_year)
            ? ` ${dcf.historical_growth_start_year}–${dcf.historical_growth_end_year}` : '';
        const growthYears = (source) => ['historical_fcff_cagr', 'flat_fcff_fallback', 'flat_terminal_fallback'].includes(source) ? historyYears : '';
        const growthDetails = [
            valid(dcf.forecast_growth_rate) ? `g 5 năm ${pct(dcf.forecast_growth_rate)} · ${growthLabel(dcf.forecast_growth_rate_source)}${growthYears(dcf.forecast_growth_rate_source)}` : null,
            valid(dcf.terminal_growth_rate) ? `g dài hạn ${pct(dcf.terminal_growth_rate)} · ${growthLabel(dcf.terminal_growth_rate_source)}${growthYears(dcf.terminal_growth_rate_source)}` : null,
            valid(dcf.base_fcff_year) ? `FCFF cơ sở ${dcf.base_fcff_year}` : null
        ].filter(Boolean).join(' · ');
        const missingFields = [];
        if (!valid(wacc.beta)) missingFields.push('beta (thiếu chuỗi giá đủ dài hoặc nguồn giá lỗi)');
        if (!valid(wacc.risk_free_rate)) missingFields.push('Rf');
        if (!valid(wacc.equity_risk_premium)) missingFields.push('ERP');
        if (!valid(capital.market_equity_value)) missingFields.push('vốn hóa');
        if (!valid(capital.interest_bearing_debt)) missingFields.push('nợ vay chịu lãi');
        if (!valid(wacc.cost_of_equity)) missingFields.push('chi phí vốn chủ');
        if (!valid(wacc.tax_rate)) missingFields.push('thuế suất WACC');
        if (valid(capital.interest_bearing_debt) && capital.interest_bearing_debt > 0 && !valid(capital.cost_of_debt)) missingFields.push('chi phí nợ');

        container.innerHTML = `
            <div class="valuation-panel-heading">
                <div>
                    <h3><i class="fas fa-coins"></i> Dữ liệu FCFF và WACC</h3>
                    <p>FCFF lịch sử = NOPAT + D&amp;A − CapEx − ΔNWC. Vốn hóa là giá trị thị trường hiện tại, chưa phải giá trị nội tại.</p>
                </div>
                <span class="valuation-status ${valid(wacc.value) ? 'is-ready' : 'is-partial'}">${valid(wacc.value) ? 'Đã đủ đầu vào WACC' : 'Dữ liệu WACC chưa đầy đủ'}</span>
            </div>
            <div class="valuation-metrics-grid">
                ${card('Vốn hóa thị trường (E)', money(capital.market_equity_value))}
                ${card('Nợ vay chịu lãi (D)', money(capital.interest_bearing_debt), capital.debt_as_of_period ? `Kỳ báo cáo ${capital.debt_as_of_period}` : '')}
                ${card('Tiền và tương đương tiền', money(capital.cash_and_equivalents))}
                ${card('Nợ ròng', money(capital.net_debt))}
                ${card('Chi phí nợ (Rd)', pct(capital.cost_of_debt), valid(capital.cost_of_debt) ? 'Lãi vay / nợ vay chịu lãi bình quân' : '')}
                ${card('Beta (3 năm, ngày)', num(wacc.beta), 'Hồi quy lợi suất cổ phiếu so với VNINDEX')}
                ${card('Lãi suất phi rủi ro (Rf)', pct(wacc.risk_free_rate), `${riskFreeSource}${riskFreeDate}`)}
                ${card('Phần bù rủi ro (ERP)', pct(wacc.equity_risk_premium), `${erpSource}${erpDate}`)}
                ${card('Chi phí vốn chủ (Re)', pct(wacc.cost_of_equity), 'Rf + Beta × ERP')}
                ${card('Thuế suất dùng cho WACC', pct(wacc.tax_rate), 'Lấy từ ô Thuế suất phía trên')}
                ${card('Trọng số vốn chủ (E/V)', pct(wacc.equity_weight))}
                ${card('Trọng số nợ (D/V)', pct(wacc.debt_weight))}
                ${card('WACC', pct(wacc.value))}
            </div>
            ${missingWacc ? `<p class="valuation-missing-note">Còn thiếu: ${[...new Set(missingFields)].join(', ')}. Nhập Rf từ HNX ở phía trên; ERP được tự lấy từ Damodaran khi có kết nối, ô ERP cho phép ghi đè.</p>` : ''}
            <div class="valuation-result-heading">
                <h4>Giá trị nội tại ước tính theo DCF</h4>
                <p>Để trống g để tự tính từ các năm FCFF dương có đủ đầu vào; năm thiếu được bỏ qua. Nếu chỉ có một năm, hệ thống dùng kịch bản FCFF đi ngang 0%. Số bạn nhập sẽ ghi đè; g dài hạn phải thấp hơn WACC.</p>
            </div>
            <div class="valuation-metrics-grid valuation-results-grid">
                ${card('Giá trị doanh nghiệp (EV)', money(dcfCalculated ? dcf.enterprise_value : null), growthDetails)}
                ${card('Giá trị vốn chủ sở hữu', money(dcfCalculated ? dcf.equity_value : null), 'EV + tiền mặt − nợ vay')}
                ${card('Giá trị nội tại ước tính / cổ phiếu', sharePrice(dcfCalculated ? dcf.intrinsic_value_per_share : null), 'Giá trị vốn chủ ÷ số cổ phiếu ước tính')}
                ${card('Giá thị trường hiện tại / cổ phiếu', sharePrice(dcf.current_share_price), 'Giá tham chiếu để so sánh')}
                ${card('Chênh lệch so với thị trường', signedPct(dcfCalculated ? dcf.upside : null), 'Dương: cao hơn giá thị trường · âm: thấp hơn')}
            </div>
            <p class="valuation-dcf-note ${dcf.status === 'ready' ? 'is-ready' : ''}">${dcf.message || 'Chưa đủ dữ liệu để tính DCF.'}</p>
            <p class="valuation-source-note">EV là giá trị hoạt động của toàn doanh nghiệp; giá trị vốn chủ đã cộng tiền mặt và trừ nợ vay. “Giá trị nội tại / cổ phiếu” là ước tính theo DCF, không phải giá giao dịch thực tế. Đơn vị EV/vốn chủ: tỷ VND; đơn vị giá cổ phiếu: VND/cổ phiếu.</p>
            <div class="valuation-source-note">
                Nguồn báo cáo: ${valuation.financial_statement_source || 'Vnstock'}.
                Nhập Rf theo <a href="https://qtcb.hnx.vn/vi-vn/trai-phieu/duong-cong-loi-suat.html" target="_blank" rel="noopener">HNX 10Y</a>; ERP tự lấy từ bảng <a href="https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html" target="_blank" rel="noopener">Damodaran</a> hoặc có thể ghi đè.
                ERP ở đây là phần bù tổng; không cộng country risk premium lần hai.
            </div>
            <div class="table-responsive valuation-history-wrap">
                <table class="valuation-history-table">
                    <thead><tr><th>Năm</th><th>EBIT</th><th>LNST</th><th>Thuế suất</th><th>D&amp;A</th><th>CapEx</th><th>ΔNWC</th><th>FCFF</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="8">Chưa có dữ liệu báo cáo năm.</td></tr>'}</tbody>
                </table>
            </div>
            <p class="valuation-source-note">Dấu “—” nghĩa là dữ liệu báo cáo chưa có; FCFF lịch sử không tính nếu thiếu đầu vào. Khi thiếu D&amp;A hoặc ΔNWC nhưng EBIT/NOPAT và CapEx đủ, DCF có thể hiện kịch bản tham khảo với giả định giá trị thiếu bằng 0 và ghi rõ giả định. D&amp;A và CapEx được chuẩn hóa thành dòng tiền chi/giá trị dương.</p>
        `;
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
                valuation_inputs: mainReport.valuation_inputs || null,
            };
            
            const peers = Object.keys(currentReportData.reports).filter(t => t !== mainTicker);
            if (peers.length > 0) {
                aiData.peers = peers.map(p => ({
                    ticker: p,
                    company_name: currentReportData.reports[p].company_name,
                    summary_indicators: currentReportData.reports[p].summary,
                    historical_data: currentReportData.reports[p].history,
                    valuation_inputs: currentReportData.reports[p].valuation_inputs || null
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
