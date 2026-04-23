import pandas as pd
import numpy as np

# ══════════════════════════════════════════════
# Phase 1: 시장 국면 판별 (Market Phase Detection)
# ══════════════════════════════════════════════

def detect_market_phase(df: pd.DataFrame) -> dict:
    """
    현재 종목의 시장 국면을 판별합니다.
    반환: { phase: '상승'|'횡보'|'하락', description: str, strength: 0~100 }
    """
    last = df.iloc[-1]
    
    adx = last.get('ADX_14')
    sma5 = last.get('SMA_5')
    sma20 = last.get('SMA_20')
    sma60 = last.get('SMA_60')
    sma120 = last.get('SMA_120')
    bb_width = last.get('BB_WIDTH')
    
    # ADX 기반 추세 강도
    if adx is None or pd.isna(adx):
        adx = 20  # 기본값
    
    # 정배열/역배열 확인
    all_valid = all(v is not None and not pd.isna(v) for v in [sma5, sma20, sma60])
    is_aligned_up = all_valid and sma5 > sma20 > sma60
    is_aligned_down = all_valid and sma5 < sma20 < sma60
    
    # BB 밴드폭 (좁으면 횡보)
    if bb_width is None or pd.isna(bb_width):
        bb_width = 0.1
    
    if adx >= 25 and is_aligned_up:
        phase = "상승"
        desc = f"ADX {adx:.1f}로 추세 강도가 강하며, 이평선 정배열 상태입니다. 추세 추종 매매가 유효합니다."
        strength = min(100, int(adx * 1.5))
    elif adx >= 25 and is_aligned_down:
        phase = "하락"
        desc = f"ADX {adx:.1f}로 하락 추세가 뚜렷하며, 이평선 역배열 상태입니다. 매매를 관망하거나 짧은 반등만 노리세요."
        strength = min(100, int(adx * 1.5))
    elif adx < 20 or (bb_width < 0.08):
        phase = "횡보"
        desc = f"ADX {adx:.1f}로 추세가 약하며, 볼린저 밴드가 수축({bb_width:.3f}배)되어 있습니다. 박스권 하단 매수/상단 매도 전략이 적합합니다."
        strength = int(adx * 1.0)
    elif sma5 is not None and sma20 is not None and sma5 > sma20:
        phase = "상승"
        desc = f"단기 이평선이 중기 이평선 위에 있어 약한 상승세입니다. 추세 확인 후 진입을 권장합니다."
        strength = int(adx * 1.2)
    else:
        phase = "하락"
        desc = f"단기 이평선이 중기 이평선 아래에 있어 약한 하락세입니다. 보수적 접근이 필요합니다."
        strength = int(adx * 1.0)
    
    return {"phase": phase, "description": desc, "strength": strength}


# ══════════════════════════════════════════════
# Phase 2: 다차원 신호 생성 (Multi-Dimensional Signals)
# ══════════════════════════════════════════════

def generate_signals(df: pd.DataFrame):
    """
    기술적 지표를 교차 검증하여 매수/매도 신호를 생성합니다.
    각 신호에 점수(가중치)를 부여하고 시장 국면에 따라 조절합니다.
    """
    signals = []
    
    if len(df) < 2:
        return signals, "데이터 부족", "데이터가 부족하여 분석할 수 없습니다."
    
    market = detect_market_phase(df)
    phase = market['phase']
    
    recent_period = df.tail(30)
    
    current_status = "관망"
    signal_scores = []  # (날짜, 점수 합, 근거들)
    
    for i in range(1, len(recent_period)):
        prev_row = recent_period.iloc[i-1]
        curr_row = recent_period.iloc[i]
        
        date_str = curr_row['Date']
        close_price = curr_row['Close']
        vol = curr_row['Volume']
        avg_vol = df['Volume'].tail(20).mean()
        is_volume_surge = vol > avg_vol * 1.5 if avg_vol and avg_vol > 0 else False
        
        day_score = 0  # 양수 = 매수, 음수 = 매도
        reasons = []
        
        # ─────────────────────────────────────
        # 1. MA 크로스 (강화된 조건)
        # ─────────────────────────────────────
        sma5_p, sma20_p = prev_row.get('SMA_5'), prev_row.get('SMA_20')
        sma5_c, sma20_c = curr_row.get('SMA_5'), curr_row.get('SMA_20')
        sma60_c = curr_row.get('SMA_60')
        sma120_c = curr_row.get('SMA_120')
        
        if _valid(sma5_p, sma20_p, sma5_c, sma20_c):
            # 골든 크로스
            if sma5_p <= sma20_p and sma5_c > sma20_c:
                is_full_align = _valid(sma60_c, sma120_c) and sma20_c > sma60_c > sma120_c
                if is_full_align and is_volume_surge:
                    day_score += 3
                    reasons.append("🔥 골든크로스 + 완벽 정배열 + 거래량 급증 (강력 매수)")
                elif is_full_align:
                    day_score += 2
                    reasons.append("📈 골든크로스 + 정배열 (매수 유력)")
                elif is_volume_surge:
                    day_score += 1.5
                    reasons.append("📈 골든크로스 + 거래량 급증")
                else:
                    day_score += 0.5
                    reasons.append("⚡ 골든크로스 (단, 정배열/거래량 미동반 — 약한 신호)")
            # 데드 크로스
            elif sma5_p >= sma20_p and sma5_c < sma20_c:
                day_score -= 2
                reasons.append("📉 데드크로스 (5일선 20일선 하향 돌파)")
        
        # ─────────────────────────────────────
        # 2. 스토캐스틱 삼형제
        # ─────────────────────────────────────
        stoch_buy = 0
        stoch_sell = 0
        for suffix in ['5', '10', '20']:
            k_col = f'STOCH_K_{suffix}'
            d_col = f'STOCH_D_{suffix}'
            k_prev, d_prev = prev_row.get(k_col), prev_row.get(d_col)
            k_curr, d_curr = curr_row.get(k_col), curr_row.get(d_col)
            
            if _valid(k_prev, d_prev, k_curr, d_curr):
                if k_prev <= d_prev and k_curr > d_curr and k_curr < 30:
                    stoch_buy += 1
                elif k_prev >= d_prev and k_curr < d_curr and k_curr > 70:
                    stoch_sell += 1
        
        if stoch_buy >= 2:
            day_score += 2
            reasons.append(f"📊 스토캐스틱 삼형제 중 {stoch_buy}개 매수 신호 (과매도 탈출)")
        elif stoch_buy == 1:
            day_score += 0.5
            reasons.append("📊 스토캐스틱 1개 매수 전환")
        
        if stoch_sell >= 2:
            day_score -= 2
            reasons.append(f"📊 스토캐스틱 삼형제 중 {stoch_sell}개 매도 신호 (과매수 이탈)")
        elif stoch_sell == 1:
            day_score -= 0.5
            reasons.append("📊 스토캐스틱 1개 매도 전환")
        
        # ─────────────────────────────────────
        # 3. RSI (기계적 매도 대신 맥락 고려)
        # ─────────────────────────────────────
        rsi_p = prev_row.get('RSI_14')
        rsi_c = curr_row.get('RSI_14')
        
        if _valid(rsi_p, rsi_c):
            if rsi_p < 30 and rsi_c >= 30:
                day_score += 1.5
                reasons.append("💪 RSI 과매도(<30) 탈출 — 반등 가능성")
            elif rsi_c >= 70:
                # 강한 상승세에서는 약한 매도만
                if phase == "상승":
                    day_score -= 0.5
                    reasons.append("⚠️ RSI 과매수(>70)이나 상승 추세 유지 중 — 경계만")
                else:
                    day_score -= 1.5
                    reasons.append("🔻 RSI 과매수(>70) — 매도 고려")
        
        # ─────────────────────────────────────
        # 4. MACD 크로스 + 다이버전스 교차 검증
        # ─────────────────────────────────────
        macd_p = prev_row.get('MACD_12_26_9')
        sig_p = prev_row.get('MACDs_12_26_9')
        macd_c = curr_row.get('MACD_12_26_9')
        sig_c = curr_row.get('MACDs_12_26_9')
        
        if _valid(macd_p, sig_p, macd_c, sig_c):
            if macd_p <= sig_p and macd_c > sig_c:
                day_score += 1.5
                reasons.append("📈 MACD 시그널선 상향 돌파")
            elif macd_p >= sig_p and macd_c < sig_c:
                day_score -= 1.5
                reasons.append("📉 MACD 시그널선 하향 돌파")
        
        # MACD 다이버전스
        div = curr_row.get('MACD_DIVERGENCE', '')
        if div:
            if '상승 다이버전스' == div:
                day_score += 2
                reasons.append("🔮 상승 다이버전스 감지 — 선행적 반전 신호!")
            elif '히든 상승 다이버전스' == div:
                day_score += 1
                reasons.append("🔮 히든 상승 다이버전스 — 기존 상승 추세 지속 가능")
            elif '하락 다이버전스' == div:
                day_score -= 2
                reasons.append("🔮 하락 다이버전스 감지 — 선행적 하락 반전 경고!")
            elif '히든 하락 다이버전스' == div:
                day_score -= 1
                reasons.append("🔮 히든 하락 다이버전스 — 하락 추세 지속 가능")
        
        # ─────────────────────────────────────
        # 5. 볼린저 밴드 + 캔들 패턴 교차 검증
        # ─────────────────────────────────────
        bbl = curr_row.get('BBL_20_2.0')
        bbu = curr_row.get('BBU_20_2.0')
        pattern = curr_row.get('CANDLE_PATTERN', '')
        
        if _valid(bbl) and close_price <= bbl:
            if pattern in ('망치형(Hammer)', '적삼병', '장대양봉'):
                day_score += 2.5
                reasons.append(f"🔥 BB하단 터치 + {pattern} 패턴 (강한 반전 매수)")
            else:
                day_score += 1
                reasons.append("📉 BB하단 접근 (반등 가능, 캔들 확인 필요)")
        
        if _valid(bbu) and close_price >= bbu:
            if pattern in ('역망치형(Inv.Hammer)', '흑삼병', '장대음봉'):
                day_score -= 2.5
                reasons.append(f"🔥 BB상단 터치 + {pattern} 패턴 (강한 매도 신호)")
            else:
                day_score -= 1
                reasons.append("📈 BB상단 접근 (차익 실현 가능)")
        
        # ─────────────────────────────────────
        # 6. 일목균형표 신호
        # ─────────────────────────────────────
        tenkan_p = prev_row.get('ICH_TENKAN')
        kijun_p = prev_row.get('ICH_KIJUN')
        tenkan_c = curr_row.get('ICH_TENKAN')
        kijun_c = curr_row.get('ICH_KIJUN')
        span_a = curr_row.get('ICH_SPAN_A')
        span_b = curr_row.get('ICH_SPAN_B')
        
        if _valid(tenkan_p, kijun_p, tenkan_c, kijun_c):
            if tenkan_p <= kijun_p and tenkan_c > kijun_c:
                day_score += 1.5
                reasons.append("☁️ 일목 전환선이 기준선 상향 돌파 (호전)")
            elif tenkan_p >= kijun_p and tenkan_c < kijun_c:
                day_score -= 1.5
                reasons.append("☁️ 일목 전환선이 기준선 하향 돌파 (역전)")
        
        if _valid(span_a, span_b):
            cloud_top = max(span_a, span_b)
            cloud_bottom = min(span_a, span_b)
            cloud_thickness = abs(span_a - span_b)
            is_thin = cloud_thickness < close_price * 0.01 if close_price > 0 else False
            
            if close_price > cloud_top:
                if prev_row.get('Close') and prev_row['Close'] <= cloud_top:
                    day_score += 2
                    reasons.append("☁️ 일목 구름대 상향 돌파!")
            elif close_price < cloud_bottom:
                if prev_row.get('Close') and prev_row['Close'] >= cloud_bottom:
                    day_score -= 2
                    reasons.append("☁️ 일목 구름대 하향 이탈!")
        
        # ─────────────────────────────────────
        # 7. 캔들 패턴 독립 보너스
        # ─────────────────────────────────────
        if pattern and not any('패턴' in r for r in reasons):
            if pattern in ('망치형(Hammer)', '적삼병', '장대양봉'):
                day_score += 1
                reasons.append(f"🕯️ {pattern} 캔들 패턴 감지 (상승 반전 가중치)")
            elif pattern in ('역망치형(Inv.Hammer)', '흑삼병', '장대음봉'):
                day_score -= 1
                reasons.append(f"🕯️ {pattern} 캔들 패턴 감지 (하락 반전 가중치)")
        
        # ─────────────────────────────────────
        # 8. 거래량 급증 확인 가중치
        # ─────────────────────────────────────
        if is_volume_surge and day_score > 0:
            day_score += 0.5
            reasons.append("📊 거래량 급증 동반 (신뢰도 상승)")
        elif is_volume_surge and day_score < 0:
            day_score -= 0.5
            reasons.append("📊 거래량 급증 동반 매도세 확인")
        
        # ─────────────────────────────────────
        # 시장 국면별 점수 보정
        # ─────────────────────────────────────
        if phase == "상승" and day_score > 0:
            day_score *= 1.2  # 상승장에서 매수 가중
        elif phase == "하락" and day_score > 0:
            day_score *= 0.6  # 하락장에서 매수 감쇄
        elif phase == "하락" and day_score < 0:
            day_score *= 1.2  # 하락장에서 매도 가중
        elif phase == "횡보" and abs(day_score) < 1:
            day_score = 0  # 횡보장에서 약한 신호 무시
        
        # ─────────────────────────────────────
        # 최종 신호 판정
        # ─────────────────────────────────────
        if abs(day_score) >= 1.5 and reasons:
            signal_type = "매수" if day_score > 0 else "매도"
            strength = "강력" if abs(day_score) >= 4 else "보통" if abs(day_score) >= 2.5 else "약한"
            reason_text = " / ".join(reasons[:3])  # 상위 3개 근거
            
            signals.append({
                "time": date_str,
                "type": signal_type,
                "price": float(close_price),
                "score": round(day_score, 1),
                "strength": strength,
                "reason": reason_text,
                "all_reasons": reasons
            })
            
            current_status = f"{strength} {signal_type} 신호 (점수: {day_score:+.1f}): {reasons[0]}"
    
    detailed_advice = generate_detailed_advice(df, current_status, market, signals)
    return signals, current_status, detailed_advice


def _valid(*values):
    """Check that all values are not None and not NaN."""
    for v in values:
        if v is None:
            return False
        try:
            if pd.isna(v):
                return False
        except (TypeError, ValueError):
            pass
    return True


# ══════════════════════════════════════════════
# Phase 5: 상세 조언 생성 (Detailed Advice)
# ══════════════════════════════════════════════

def generate_detailed_advice(df: pd.DataFrame, current_status: str, market: dict, signals: list) -> str:
    """시장 국면, 지표, 캔들 패턴, 다이버전스, 피보나치를 종합한 상세 한글 조언."""
    if len(df) < 2:
        return "데이터가 부족하여 상세 분석을 수행할 수 없습니다."
    
    last = df.iloc[-1]
    phase = market['phase']
    close = last.get('Close')
    
    # ── 시장 국면 ──
    phase_emoji = {"상승": "🟢", "횡보": "🟡", "하락": "🔴"}.get(phase, "⚪")
    phase_text = f"{phase_emoji} **현재 시장 국면:** {phase} 추세 (강도 {market['strength']}%)\n{market['description']}"
    
    # ── 이평선 분석 ──
    sma5 = last.get('SMA_5')
    sma20 = last.get('SMA_20')
    sma60 = last.get('SMA_60')
    sma120 = last.get('SMA_120')
    
    ma_vals = []
    for k, v in [("종가", close), ("MA5", sma5), ("MA20", sma20), ("MA60", sma60), ("MA120", sma120)]:
        if _valid(v):
            ma_vals.append(f"{k}: {v:.2f}")
    ma_vals_str = " / ".join(ma_vals)

    ma_text = f"현재 값 [{ma_vals_str}]\n  "
    
    if _valid(sma5, sma20, sma60) and sma5 > sma20 > sma60:
        ma_text += "이동평균선이 **정배열(5>20>60)** 상태로 상승 추세의 뼈대가 유지되고 있습니다."
    elif _valid(sma5, sma20, sma60) and sma5 < sma20 < sma60:
        ma_text += "이동평균선이 **역배열(5<20<60)** 상태로 하락 추세가 명확합니다."
    elif _valid(sma5, sma20) and sma5 > sma20:
        ma_text += "단기선이 중기선 위에 있어 약한 상승 흐름이지만, 장기 추세 확인이 필요합니다."
    else:
        ma_text += "단기선이 중기선 아래에 있어 단기적으로 약세입니다."
    
    # ── RSI ──
    rsi = last.get('RSI_14')
    if _valid(rsi):
        if rsi >= 70:
            rsi_text = f"RSI {rsi:.1f} — **과매수 구간**. 단, 강한 상승세에서는 70 이상에서도 계속 오를 수 있으므로 스토캐스틱과 교차 확인 필요."
        elif rsi <= 30:
            rsi_text = f"RSI {rsi:.1f} — **과매도 구간**. 기술적 반등 가능성이 높지만 추세 확인이 우선."
        else:
            rsi_text = f"RSI {rsi:.1f} — 중립 구간으로 특별한 과열/침체 없음."
    else:
        rsi_text = "RSI 계산 불가."
    
    # ── 스토캐스틱 삼형제 ──
    stoch_texts = []
    for label, suffix in [("단기", "5"), ("중기", "10"), ("장기", "20")]:
        k = last.get(f'STOCH_K_{suffix}')
        d = last.get(f'STOCH_D_{suffix}')
        if _valid(k, d):
            direction = "상향" if k > d else "하향"
            stoch_texts.append(f"{label}(%K={k:.0f}) {direction}")
    stoch_text = "스토캐스틱 삼형제: " + ", ".join(stoch_texts) if stoch_texts else ""
    
    # ── MACD 다이버전스 ──
    recent_divs = df.tail(10)['MACD_DIVERGENCE']
    div_found = [d for d in recent_divs if d and d is not None]
    div_text = f"최근 감지된 다이버전스: **{div_found[-1]}** — 추세 전환 가능성에 유의하세요." if div_found else ""
    
    # ── 캔들 패턴 ──
    pattern = last.get('CANDLE_PATTERN', '')
    pattern_text = f"최근 캔들 패턴: **{pattern}** 감지" if pattern else ""
    
    # ── 볼린저 밴드 ──
    bbl = last.get('BBL_20_2.0')
    bbu = last.get('BBU_20_2.0')
    if _valid(bbl, bbu, close):
        bb_pos = (close - bbl) / (bbu - bbl) * 100 if (bbu - bbl) > 0 else 50
        bb_text = f"볼린저밴드(상단: {bbu:.2f}, 하단: {bbl:.2f}) 내 위치: 하단 대비 {bb_pos:.0f}% 지점. "
        if close >= bbu:
            bb_text += "주가가 볼린저밴드 **상단(저항)**에 위치. 차익 실현 매물 출회 가능성."
        elif close <= bbl:
            bb_text += "주가가 볼린저밴드 **하단(지지)**에 위치. 기술적 반등 가능성."
    else:
        bb_text = ""
    
    # ── 일목균형표 ──
    span_a = last.get('ICH_SPAN_A')
    span_b = last.get('ICH_SPAN_B')
    if _valid(span_a, span_b, close):
        cloud_top = max(span_a, span_b)
        cloud_bottom = min(span_a, span_b)
        ich_text = f"일목구름대(선행A: {span_a:.2f}, 선행B: {span_b:.2f}, {'양운' if span_a >= span_b else '음운'}): "
        if close > cloud_top:
            ich_text += "주가가 일목 구름대 **위**에 위치 — 상승 신호."
        elif close < cloud_bottom:
            ich_text += "주가가 일목 구름대 **아래**에 위치 — 약세 구간."
        else:
            ich_text += "주가가 일목 구름대 **내부**에 위치 — 방향성 대기."
    else:
        ich_text = ""

    # ── MACD ──
    macd = last.get('MACD_12_26_9')
    macds = last.get('MACDs_12_26_9')
    macd_text = ""
    if _valid(macd, macds):
        macd_text = f"MACD: {macd:.2f}, 시그널: {macds:.2f} — "
        if macd > macds:
            macd_text += "MACD가 시그널선 위에 있음 (상승 우위)."
        else:
            macd_text += "MACD가 시그널선 아래에 있음 (하락 우위)."
    
    # ── 최근 신호 종합 점수 ──
    recent_signals = signals[-5:] if signals else []
    total_score = sum(s['score'] for s in recent_signals) if recent_signals else 0
    
    if total_score >= 5:
        action = "적극 매수 검토 (Strong Buy)"
        action_detail = "다수의 기술적 지표가 동시에 매수를 가리키고 있으며, 시장 국면도 우호적입니다. 분할 매수 진입을 적극 검토하세요."
    elif total_score >= 2:
        action = "매수 우위 (Buy)"
        action_detail = "매수 신호가 우세하지만 아직 결정적이지 않습니다. 리테스트 확인 후 진입하거나 소량 분할 매수로 접근하세요."
    elif total_score <= -5:
        action = "적극 매도/회피 (Strong Sell)"
        action_detail = "다수의 지표가 하락을 경고합니다. 기존 보유분은 손절/익절을 실행하고, 신규 진입은 삼가세요."
    elif total_score <= -2:
        action = "비중 축소 (Sell)"
        action_detail = "매도 신호가 우세합니다. 추가 하락 리스크에 대비하여 비중을 줄이고 현금을 확보하세요."
    else:
        action = "관망 (Hold)"
        action_detail = "뚜렷한 방향성 없이 혼조세입니다. 무리한 매매보다는 추세 전환 확인 후 행동하는 것이 안전합니다."
    
    # ── 조합 ──
    sections = [
        f"🎯 **현재 AI 추천 포지션:** {action} (종합 점수: {total_score:+.1f})",
        "",
        f"📊 **종합 근거 분석**",
        f"• {phase_text}",
        f"• {ma_text}",
        f"• {rsi_text}",
    ]
    
    if stoch_text:
        sections.append(f"• {stoch_text}")
    if macd_text:
        sections.append(f"• {macd_text}")
    if div_text:
        sections.append(f"• {div_text}")
    if pattern_text:
        sections.append(f"• {pattern_text}")
    if bb_text:
        sections.append(f"• {bb_text}")
    if ich_text:
        sections.append(f"• {ich_text}")
    
    sections.append("")
    sections.append(f"💡 **AI의 조언 요약:**")
    sections.append(action_detail)
    
    if recent_signals:
        sections.append("")
        sections.append("📋 **최근 주요 신호:**")
        for s in recent_signals[-3:]:
            emoji = "🟢" if s['type'] == '매수' else "🔴"
            sections.append(f"• {emoji} [{s['time']}] {s['strength']} {s['type']} (점수 {s['score']:+.1f}) — {s['reason'][:80]}")
    
    return "\n".join(sections)
