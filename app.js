const API_BASE = '/api';

// State
let allSectors = [];
let currentStocks = [];
let currentTicker = null;
let currentTickerName = null;
let currentMarket = 'KR'; // 'KR' or 'US'

// Charts References
let mainChart, mainSeries, volumeSeries;
let ma5Series, ma20Series, ma60Series, ma120Series;
let bbuSeries, bblSeries;
let ichTenkanSeries, ichKijunSeries, ichSpanASeries, ichSpanBSeries;
let rsiChart, rsiSeries;
let macdChart, macdLineSeries, macdSignalSeries, macdHistSeries;

document.addEventListener('DOMContentLoaded', () => {

    try {
        initCharts();
    } catch (e) {
        document.getElementById('currentStockTitle').textContent = "차트 초기화 오류: " + e.message;
        console.error(e);
    }
    try {
        loadSectors();
    } catch(e) {
        document.getElementById('currentStockTitle').textContent = "섹터 로딩 오류: " + e.message;
    }
    
    // Market Toggle
    document.querySelectorAll('input[name="market"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentMarket = e.target.value;
            const isKR = currentMarket === 'KR';
            // Show/hide sector section
            document.getElementById('sectorSection').style.display = isKR ? '' : 'none';
            // Update search placeholder
            document.getElementById('searchInput').placeholder = isKR
                ? '회사명 검색 (예: 삼성)...'
                : 'Search US stocks (e.g. Apple)...';
            // Clear previous results
            document.getElementById('stockList').innerHTML = '';
            document.getElementById('searchInput').value = '';
            currentTicker = null;
            currentTickerName = null;
        });
    });

    document.getElementById('sectorSelect').addEventListener('change', (e) => {
        document.getElementById('searchInput').value = "";
        loadStocks(e.target.value);
    });
    
    document.getElementById('searchInput').addEventListener('input', (e) => {
        const query = e.target.value.trim();
        if(query.length > 0) {
            if (currentMarket === 'KR') {
                document.getElementById('sectorSelect').value = "";
            }
            searchStocksByQuery(query, currentMarket);
        } else {
            document.getElementById('stockList').innerHTML = '';
        }
    });
    
    document.getElementById('capitalInput').addEventListener('change', () => {
        if (currentTicker && document.querySelector('#mainChart').innerHTML !== '') analyzeStock(currentTicker, currentTickerName);
    });
    
    document.getElementById('analyzeBtn').addEventListener('click', () => {
        if (!currentTicker) {
            alert('먼저 종목을 선택해주세요.');
            return;
        }
        analyzeStock(currentTicker, currentTickerName, currentMarket);
    });

    // News Modal Logic
    document.getElementById('newsBtn').addEventListener('click', () => {
        if (!currentTicker) {
            alert('먼저 종목을 선택해주세요.');
            return;
        }
        document.getElementById('newsModal').classList.remove('hidden');
    });

    document.getElementById('closeNewsModal').addEventListener('click', () => {
        document.getElementById('newsModal').classList.add('hidden');
    });

    document.getElementById('fetchNewsBtn').addEventListener('click', async () => {
        if (!currentTicker) return;
        const prompt = document.getElementById('newsPrompt').value.trim();
        const aiLevel = document.getElementById('aiLevelSelect').value;
        const btn = document.getElementById('fetchNewsBtn');
        const contentDiv = document.getElementById('newsContent');
        
        btn.disabled = true;
        btn.textContent = '검색 중...';
        contentDiv.innerHTML = '<div style="text-align:center; padding: 20px;"><span style="color:#58a6ff;">데이터 수집 및 요약 중...</span></div>';
        
        try {
            const res = await fetch(`${API_BASE}/news?ticker=${encodeURIComponent(currentTickerName || currentTicker)}&ai_level=${encodeURIComponent(aiLevel)}&prompt=${encodeURIComponent(prompt)}`);
            if (!res.ok) throw new Error('Failed to fetch news');
            const data = await res.json();
            
            if (typeof marked !== 'undefined') {
                contentDiv.innerHTML = marked.parse(data.news);
            } else {
                contentDiv.innerText = data.news;
            }
        } catch (e) {
            contentDiv.innerHTML = `<div style="color: #f85149;">오류: ${e.message}</div>`;
        } finally {
            btn.disabled = false;
            btn.textContent = '검색 실행';
        }
    });
    
    document.getElementById('exportPdfBtn').addEventListener('click', () => {
        if (!currentTicker) {
            alert('먼저 분석할 종목을 선택해주세요.');
            return;
        }
        const element = document.querySelector('.main-content');
        
        // Hide PDF button locally while generating PDF so it doesn't show in the PDF
        const pdfBtn = document.getElementById('exportPdfBtn');
        pdfBtn.style.display = 'none';
        
        const opt = {
            margin:       0.3,
            filename:     `${document.getElementById('currentStockTitle').textContent.replace(/[^a-zA-Z0-9가-힣()]/g, '_')}_종목분석리포트.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#0d1117' },
            jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' }
        };
        
        // Use html2pdf to generate and download the PDF
        html2pdf().set(opt).from(element).save().then(() => {
            pdfBtn.style.display = 'block'; // Restore button
        });
    });
});


function initCharts() {
    const chartOptions = {
        layout: {
            background: { type: LightweightCharts.ColorType.Solid, color: '#161b22' },
            textColor: '#c9d1d9',
        },
        grid: {
            vertLines: { color: '#30363d' },
            horzLines: { color: '#30363d' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#30363d',
        },
        timeScale: {
            borderColor: '#30363d',
            barSpacing: 12,
            rightOffset: 5,
        },
    };

    // Main Chart
    const mainContainer = document.getElementById('mainChart');
    mainChart = LightweightCharts.createChart(mainContainer, chartOptions);
    mainSeries = mainChart.addCandlestickSeries({
        upColor: '#3fb950', downColor: '#f85149', borderVisible: false,
        wickUpColor: '#3fb950', wickDownColor: '#f85149'
    });
    
    volumeSeries = mainChart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume_scale'
    });
    
    mainChart.priceScale('volume_scale').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
        visible: false,
    });

    // Overlays - MAs & BB
    ma5Series = mainChart.addLineSeries({ color: '#ffb240', lineWidth: 1, title: 'MA5' });
    ma20Series = mainChart.addLineSeries({ color: '#58a6ff', lineWidth: 2, title: 'MA20' });
    ma60Series = mainChart.addLineSeries({ color: '#8957e5', lineWidth: 1, title: 'MA60' });
    ma120Series = mainChart.addLineSeries({ color: '#ff7b72', lineWidth: 1, title: 'MA120' });
    bbuSeries = mainChart.addLineSeries({ color: 'rgba(88, 166, 255, 0.5)', lineWidth: 1, lineStyle: 2, title: 'BB Up' });
    bblSeries = mainChart.addLineSeries({ color: 'rgba(88, 166, 255, 0.5)', lineWidth: 1, lineStyle: 2, title: 'BB Low' });

    // Overlays - Ichimoku
    ichTenkanSeries = mainChart.addLineSeries({ color: '#e6b422', lineWidth: 1, title: '전환선' });
    ichKijunSeries = mainChart.addLineSeries({ color: '#ff6347', lineWidth: 1, title: '기준선' });
    ichSpanASeries = mainChart.addLineSeries({ color: 'rgba(63, 185, 80, 0.4)', lineWidth: 1, lineStyle: 2, title: '선행A' });
    ichSpanBSeries = mainChart.addLineSeries({ color: 'rgba(248, 81, 73, 0.4)', lineWidth: 1, lineStyle: 2, title: '선행B' });

    // RSI
    rsiChart = LightweightCharts.createChart(document.getElementById('rsiChart'), chartOptions);
    rsiSeries = rsiChart.addLineSeries({ color: '#a371f7', lineWidth: 2, title: 'RSI' });
    rsiSeries.createPriceLine({ price: 70, color: '#f85149', lineWidth: 1, lineStyle: 2 });
    rsiSeries.createPriceLine({ price: 30, color: '#3fb950', lineWidth: 1, lineStyle: 2 });

    // MACD
    macdChart = LightweightCharts.createChart(document.getElementById('macdChart'), chartOptions);
    macdLineSeries = macdChart.addLineSeries({ color: '#58a6ff', lineWidth: 2, title: 'MACD' });
    macdSignalSeries = macdChart.addLineSeries({ color: '#ffb240', lineWidth: 2, title: 'Signal' });
    macdHistSeries = macdChart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: '',
    });

    // Resize handling
    window.addEventListener('resize', () => {
        mainChart.applyOptions({ width: mainContainer.clientWidth });
        rsiChart.applyOptions({ width: document.getElementById('rsiChart').clientWidth });
        macdChart.applyOptions({ width: document.getElementById('macdChart').clientWidth });
    });
}

async function loadSectors() {
    try {
        const res = await fetch(`${API_BASE}/sectors`);
        const data = await res.json();
        const select = document.getElementById('sectorSelect');
        select.innerHTML = '<option value="">-- 업종 선택 --</option>';
        data.sectors.forEach(s => {
            let opt = document.createElement('option');
            opt.value = s; opt.textContent = s;
            select.appendChild(opt);
        });
    } catch(e) { console.error('Error loading sectors', e); }
}

async function loadStocks(sector) {
    if (!sector) return;
    try {
        const res = await fetch(`${API_BASE}/stocks?sector=${encodeURIComponent(sector)}`);
        const data = await res.json();
        renderStockList(data.stocks);
    } catch(e) { console.error('Error loading stocks', e); }
}

async function searchStocksByQuery(query, market = 'KR') {
    try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&market=${encodeURIComponent(market)}`);
        const data = await res.json();
        renderStockList(data.stocks, market);
    } catch(e) { console.error('Error searching stocks', e); }
}

function renderStockList(stocks, market = 'KR') {
    const list = document.getElementById('stockList');
    list.innerHTML = '';
    
    // 미국 주식 직통 입력 옵션 (백엔드 검색 실패 또는 원하는 종목이 안 나올 때)
    if (market === 'US') {
        const query = document.getElementById('searchInput').value.trim().toUpperCase();
        if (query.length > 0) {
            let directLi = document.createElement('li');
            directLi.className = 'stock-item direct-input-item';
            directLi.style.borderBottom = '2px dashed var(--accent)';
            directLi.style.backgroundColor = 'rgba(88, 166, 255, 0.1)';
            directLi.innerHTML = `<span>🔎 티커 직접 입력 분석</span><span class="stock-code" style="font-weight:bold; color:var(--accent);">${query}</span>`;
            directLi.onclick = () => {
                document.querySelectorAll('.stock-item').forEach(i => i.classList.remove('active'));
                directLi.classList.add('active');
                currentTicker = query;
                currentTickerName = query;
                currentMarket = market;
                document.getElementById('currentStockTitle').innerHTML = `🇺🇸 ${query} <span style="font-size:1rem;font-weight:normal;">(${query})</span> - 분석 대기 중...`;
                document.getElementById('currentStockPrice').textContent = '';
            };
            list.appendChild(directLi);
        }
    }

    if (stocks.length === 0) {
        if (market === 'KR') {
             list.innerHTML += '<li style="color:#8b949e; padding:8px; font-size:0.85rem;">검색 결과가 없습니다.</li>';
        }
        return;
    }
    
    stocks.forEach(stock => {
        let li = document.createElement('li');
        li.className = 'stock-item';
        const exchangeLabel = stock.Exchange ? `<span class="stock-exchange" style="font-size:0.7rem; color:#8b949e; margin-left:4px;">${stock.Exchange}</span>` : '';
        li.innerHTML = `<span>${stock.Name}${exchangeLabel}</span><span class="stock-code">${stock.Code}</span>`;
        li.onclick = () => {
            document.querySelectorAll('.stock-item').forEach(i => i.classList.remove('active'));
            li.classList.add('active');
            currentTicker = stock.Code;
            currentTickerName = stock.Name;
            currentMarket = market;
            const marketFlag = market === 'US' ? '🇺🇸 ' : '🇰🇷 ';
            document.getElementById('currentStockTitle').innerHTML = `${marketFlag}${stock.Name} <span style="font-size:1rem;font-weight:normal;">(${stock.Code})</span> - 분석 대기 중...`;
            document.getElementById('currentStockPrice').textContent = '';
        };
        list.appendChild(li);
    });
}

async function analyzeStock(ticker, name = null, market = 'KR') {
    currentTicker = ticker;
    currentMarket = market;
    if (name) currentTickerName = name;
    
    const marketFlag = market === 'US' ? '🇺🇸 ' : '🇰🇷 ';
    document.getElementById('currentStockTitle').innerHTML = `${marketFlag}${currentTickerName || ticker} <span style="font-size:1rem;font-weight:normal;">(${ticker})</span>`;
    const priceEl = document.getElementById('currentStockPrice');
    if (priceEl) priceEl.textContent = '';
    
    document.getElementById('loadingIndicator').classList.remove('hidden');
    
    const capital = document.getElementById('capitalInput').value;
    const aiLevel = document.getElementById('aiLevelSelect').value;
    
    try {
        const res = await fetch(`${API_BASE}/analyze?ticker=${ticker}&capital=${capital}&ai_level=${encodeURIComponent(aiLevel)}&market=${encodeURIComponent(market)}`);
        if (!res.ok) throw new Error('Failed to fetch data');
        const data = await res.json();
        
        renderChartData(data);
        renderStrategyBoard(data);
        
        if (priceEl && data.ohlcv && data.ohlcv.length > 0) {
            const lastCandle = data.ohlcv[data.ohlcv.length - 1];
            const currency = data.currency || (market === 'US' ? 'USD' : 'KRW');
            if (currency === 'USD') {
                priceEl.textContent = '$' + lastCandle.close.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            } else {
                priceEl.textContent = lastCandle.close.toLocaleString() + '원';
            }
        }
        
    } catch (e) {
        alert('분석 오류: ' + e.message);
    } finally {
        document.getElementById('loadingIndicator').classList.add('hidden');
    }
}

function renderChartData(data) {
    // Candles
    mainSeries.setData(data.ohlcv);
    
    // Volume
    const volData = data.ohlcv.map(d => ({
        time: d.time,
        value: d.value,
        color: d.close >= d.open ? 'rgba(63, 185, 80, 0.5)' : 'rgba(248, 81, 73, 0.5)'
    }));
    volumeSeries.setData(volData);
    
    // MA Data
    ma5Series.setData(data.indicators.ma.map(d => d.SMA_5 != null ? {time: d.Date, value: d.SMA_5} : {time: d.Date}));
    ma20Series.setData(data.indicators.ma.map(d => d.SMA_20 != null ? {time: d.Date, value: d.SMA_20} : {time: d.Date}));
    ma60Series.setData(data.indicators.ma.map(d => d.SMA_60 != null ? {time: d.Date, value: d.SMA_60} : {time: d.Date}));
    ma120Series.setData(data.indicators.ma.map(d => d.SMA_120 != null ? {time: d.Date, value: d.SMA_120} : {time: d.Date}));
    
    bbuSeries.setData(data.indicators.bb.map(d => d['BBU_20_2.0'] != null ? {time: d.Date, value: d['BBU_20_2.0']} : {time: d.Date}));
    bblSeries.setData(data.indicators.bb.map(d => d['BBL_20_2.0'] != null ? {time: d.Date, value: d['BBL_20_2.0']} : {time: d.Date}));
    
    // Ichimoku overlay
    if (data.indicators.ichimoku) {
        ichTenkanSeries.setData(data.indicators.ichimoku.map(d => d.ICH_TENKAN != null ? {time: d.Date, value: d.ICH_TENKAN} : {time: d.Date}));
        ichKijunSeries.setData(data.indicators.ichimoku.map(d => d.ICH_KIJUN != null ? {time: d.Date, value: d.ICH_KIJUN} : {time: d.Date}));
        ichSpanASeries.setData(data.indicators.ichimoku.map(d => d.ICH_SPAN_A != null ? {time: d.Date, value: d.ICH_SPAN_A} : {time: d.Date}));
        ichSpanBSeries.setData(data.indicators.ichimoku.map(d => d.ICH_SPAN_B != null ? {time: d.Date, value: d.ICH_SPAN_B} : {time: d.Date}));
    }
    
    // Fibonacci price lines
    if (data.fibonacci_levels) {
        // Clear old price lines by removing them (need to track or just accept they accumulate — we re-init per stock)
        const fibColors = {
            "38.2%": "#e6b422",
            "50.0%": "#58a6ff",
            "61.8%": "#ff7b72",
        };
        for (const [label, price] of Object.entries(data.fibonacci_levels)) {
            if (fibColors[label]) {
                mainSeries.createPriceLine({
                    price: price,
                    color: fibColors[label],
                    lineWidth: 1,
                    lineStyle: 3,
                    title: `Fib ${label}`,
                });
            }
        }
    }
    
    // RSI
    rsiSeries.setData(data.indicators.rsi.map(d => d.RSI_14 != null ? {time: d.Date, value: d.RSI_14} : {time: d.Date}));
    
    // MACD
    macdLineSeries.setData(data.indicators.macd.map(d => d.MACD_12_26_9 != null ? {time: d.Date, value: d.MACD_12_26_9} : {time: d.Date}));
    macdSignalSeries.setData(data.indicators.macd.map(d => d.MACDs_12_26_9 != null ? {time: d.Date, value: d.MACDs_12_26_9} : {time: d.Date}));
    
    const macdHist = data.indicators.macd.map(d => {
        if (d.MACDh_12_26_9 == null) return {time: d.Date};
        return {
            time: d.Date, 
            value: d.MACDh_12_26_9, 
            color: (d.MACDh_12_26_9 >= 0) ? 'rgba(63, 185, 80, 0.8)' : 'rgba(248, 81, 73, 0.8)'
        };
    });
    macdHistSeries.setData(macdHist);
    
    // Markers (Buy/Sell Signals) with strength-based sizing
    const markers = data.signals.map(s => ({
        time: s.time,
        position: s.type === '매수' ? 'belowBar' : 'aboveBar',
        color: s.type === '매수' ? '#3fb950' : '#f85149',
        shape: s.type === '매수' ? 'arrowUp' : 'arrowDown',
        text: `${s.strength} ${s.type}`
    }));
    mainSeries.setMarkers(markers);
    
    // Zoom into recent 100 bars
    const totalBars = data.ohlcv.length;
    if (totalBars > 0) {
        const visibleFrom = Math.max(0, totalBars - 100);
        const visibleTo = totalBars - 1;
        mainChart.timeScale().setVisibleLogicalRange({ from: visibleFrom, to: visibleTo });
        rsiChart.timeScale().setVisibleLogicalRange({ from: visibleFrom, to: visibleTo });
        macdChart.timeScale().setVisibleLogicalRange({ from: visibleFrom, to: visibleTo });
    }
}

function renderStrategyBoard(data) {
    // Market Phase Badge
    const phaseBadge = document.getElementById('marketPhaseBadge');
    if (phaseBadge && data.market_phase) {
        const mp = data.market_phase;
        const phaseColors = { "상승": "#3fb950", "횡보": "#d29922", "하락": "#f85149" };
        const phaseEmoji = { "상승": "🟢", "횡보": "🟡", "하락": "🔴" };
        phaseBadge.innerHTML = `
            <span style="color:${phaseColors[mp.phase] || '#c9d1d9'}; font-weight:700; font-size:1.1rem;">
                ${phaseEmoji[mp.phase] || ''} ${mp.phase} 추세  
                <span style="font-weight:400; font-size:0.85rem; opacity:0.8;">(강도 ${mp.strength}%)</span>
            </span>
        `;
    }
    
    // Signal Score Gauge
    const scoreGauge = document.getElementById('signalScoreGauge');
    if (scoreGauge && data.signals) {
        const recentSignals = data.signals.slice(-5);
        const totalScore = recentSignals.reduce((sum, s) => sum + s.score, 0);
        const maxScore = 15;
        const pct = Math.min(100, Math.max(0, ((totalScore + maxScore) / (2 * maxScore)) * 100));
        const barColor = totalScore >= 3 ? '#3fb950' : totalScore <= -3 ? '#f85149' : '#d29922';
        scoreGauge.innerHTML = `
            <div style="font-size:0.85rem; color:#8b949e; margin-bottom:4px;">종합 신호 점수: <strong style="color:#fff;">${totalScore >= 0 ? '+' : ''}${totalScore.toFixed(1)}</strong></div>
            <div style="width:100%; height:8px; background:#30363d; border-radius:4px; overflow:hidden;">
                <div style="width:${pct}%; height:100%; background:${barColor}; border-radius:4px; transition:width 0.5s;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#8b949e; margin-top:2px;">
                <span>강한 매도</span><span>중립</span><span>강한 매수</span>
            </div>
        `;
    }
    
    // Strategy Status
    const stStatus = document.getElementById('strategyStatus');
    stStatus.textContent = data.current_status;
    stStatus.className = data.current_status.includes('매수') ? 'status-buy' : 
                         data.current_status.includes('매도') ? 'status-sell' : 'status-neutral';
    
    // Detailed Advice (Logic)
    const logicDetailed = document.getElementById('logicAdvice');
    if(logicDetailed && data.detailed_advice) {
        if (typeof marked !== 'undefined') {
            logicDetailed.innerHTML = marked.parse(data.detailed_advice);
        } else {
            let adviceHtml = data.detailed_advice.replace(/\n/g, '<br>');
            adviceHtml = adviceHtml.replace(/\*\*(.*?)\*\*/g, '<strong style="color:#ffffff;">$1</strong>');
            logicDetailed.innerHTML = adviceHtml;
        }
    }
    
    // AI Advice (Gen-AI)
    const aiDetailed = document.getElementById('detailedAdvice');
    if(aiDetailed && data.ai_opinion) {
        if (typeof marked !== 'undefined') {
            aiDetailed.innerHTML = marked.parse(data.ai_opinion);
        } else {
            let adviceHtml = data.ai_opinion.replace(/\n/g, '<br>');
            adviceHtml = adviceHtml.replace(/\*\*(.*?)\*\*/g, '<strong style="color:#ffffff;">$1</strong>');
            aiDetailed.innerHTML = adviceHtml;
        }
    }
    
    // Risk Management
    const rm = data.risk_management;
    document.getElementById('riskInfo').textContent = rm.message;
}
