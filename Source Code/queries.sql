-- Day 2 basic analytics queries and tested result samples
-- Database: bluestock_mf.db

-- Query 1: Top 5 funds by AUM
SELECT scheme_name, fund_house, aum_crore
FROM fact_performance
ORDER BY aum_crore DESC
LIMIT 5;
-- Result sample:
-- scheme_name,fund_house,aum_crore
-- Mirae Asset Emerging Bluechip Fund - Regular - Growth,Mirae Asset MF,49046
-- Kotak Emerging Equity Fund - Regular - Growth,Kotak Mahindra MF,47469
-- Nippon India Small Cap Fund - Regular - Growth,Nippon India MF,43630
-- DSP Top 100 Equity Fund - Regular - Growth,DSP Mutual Fund,41828
-- UTI Mid Cap Fund - Regular - Growth,UTI Mutual Fund,41728

-- Query 2: Average NAV per month
SELECT amfi_code, substr(nav_date, 1, 7) AS month, ROUND(AVG(nav), 4) AS avg_nav
FROM fact_nav
GROUP BY amfi_code, month
ORDER BY amfi_code, month
LIMIT 20;
-- Result sample:
-- amfi_code,month,avg_nav
-- 100016,2022-01,512.5353
-- 100016,2022-02,513.9306
-- 100016,2022-03,522.5782
-- 100016,2022-04,525.6312
-- 100016,2022-05,504.3125
-- 100016,2022-06,465.137
-- 100016,2022-07,436.746
-- 100016,2022-08,421.3311
-- 100016,2022-09,422.1759
-- 100016,2022-10,431.4175
-- 100016,2022-11,463.6936
-- 100016,2022-12,480.9635
-- 100016,2023-01,490.9673
-- 100016,2023-02,493.1681
-- 100016,2023-03,546.0677
-- 100016,2023-04,566.9077
-- 100016,2023-05,566.0106
-- 100016,2023-06,571.042
-- 100016,2023-07,578.758
-- 100016,2023-08,569.4809

-- Query 3: SIP inflow YoY growth
SELECT month, sip_inflow_crore, yoy_growth_pct
FROM fact_sip_inflows
WHERE yoy_growth_pct IS NOT NULL
ORDER BY month;
-- Result sample:
-- month,sip_inflow_crore,yoy_growth_pct
-- 2023-01-01,13856,20.31
-- 2023-02-01,13687,19.66
-- 2023-03-01,14276,15.8
-- 2023-04-01,14749,24.33
-- 2023-05-01,14749,20.05
-- 2023-06-01,14734,20.02
-- 2023-07-01,15245,25.58
-- 2023-08-01,15814,24.58
-- 2023-09-01,16042,23.63
-- 2023-10-01,16928,29.82
-- 2023-11-01,17073,28.31
-- 2023-12-01,17610,29.74
-- 2024-01-01,18838,35.96
-- 2024-02-01,19187,40.18
-- 2024-03-01,20371,42.69
-- 2024-04-01,20371,38.12
-- 2024-05-01,21262,44.16
-- 2024-06-01,21262,44.31
-- 2024-07-01,23332,53.05
-- 2024-08-01,23547,48.9
-- 2024-09-01,24509,52.78
-- 2024-10-01,25323,49.59
-- 2024-11-01,25320,48.3
-- 2024-12-01,26459,50.25
-- 2025-01-01,26400,40.14
-- 2025-02-01,25999,35.5
-- 2025-03-01,25926,27.27
-- 2025-04-01,26632,30.73
-- 2025-05-01,26688,25.52
-- 2025-06-01,27274,28.28
-- 2025-07-01,28464,22.0
-- 2025-08-01,28265,20.04
-- 2025-09-01,29361,19.8
-- 2025-10-01,29529,16.61
-- 2025-11-01,30200,19.27
-- 2025-12-01,31002,17.17

-- Query 4: Transactions by state
SELECT state, COUNT(*) AS transaction_count, SUM(amount_inr) AS total_amount_inr
FROM fact_transactions
GROUP BY state
ORDER BY transaction_count DESC, total_amount_inr DESC;
-- Result sample:
-- state,transaction_count,total_amount_inr
-- Punjab,2965,315780459
-- Madhya Pradesh,2931,308312493
-- Tamil Nadu,2806,315177237
-- Gujarat,2780,298358940
-- West Bengal,2748,297182514
-- Haryana,2736,279634354
-- Telangana,2718,290219284
-- Uttar Pradesh,2695,285368873
-- Delhi,2677,289633404
-- Karnataka,2621,273753570
-- Rajasthan,2577,298645822
-- Maharashtra,2524,269513480

-- Query 5: Funds with expense ratio below 1 percent
SELECT amfi_code, scheme_name, fund_house, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1
ORDER BY expense_ratio_pct ASC;
-- Result sample:
-- amfi_code,scheme_name,fund_house,expense_ratio_pct
-- 118636,Nippon India Gilt Securities Fund - Regular - Growth,Nippon India MF,0.55
-- 100025,HDFC Short Term Debt Fund - Regular - Growth,HDFC Mutual Fund,0.56
-- 120844,Kotak Liquid Fund - Regular - Growth,Kotak Mahindra MF,0.6
-- 119552,SBI Bluechip Fund - Direct Plan - Growth,SBI Mutual Fund,0.66
-- 118633,Nippon India Large Cap Fund - Direct - Growth,Nippon India MF,0.72
-- 119599,SBI Small Cap Fund - Direct Plan - Growth,SBI Mutual Fund,0.72
-- 120507,ICICI Pru Liquid Fund - Regular - Growth,ICICI Prudential MF,0.74
-- 119093,Axis Bluechip Fund - Direct - Growth,Axis Mutual Fund,0.75
-- 119120,SBI Magnum Gilt Fund - Regular Plan - Growth,SBI Mutual Fund,0.77
-- 125498,HDFC Mid-Cap Opportunities Fund - Direct - Growth,HDFC Mutual Fund,0.78
-- 101208,ABSL Liquid Fund - Regular - Growth,Aditya Birla Sun Life MF,0.79
-- 120504,ICICI Pru Bluechip Fund - Direct - Growth,ICICI Prudential MF,0.8
-- 118635,Nippon India ETF Nifty 50 BeES,Nippon India MF,0.89
-- 125497,HDFC Top 100 Fund - Direct Plan - Growth,HDFC Mutual Fund,0.92

-- Query 6: Top categories by net inflow
SELECT category, ROUND(SUM(net_inflow_crore), 2) AS total_net_inflow_crore
FROM fact_category_inflows
GROUP BY category
ORDER BY total_net_inflow_crore DESC
LIMIT 10;
-- Result sample:
-- category,total_net_inflow_crore
-- Liquid,451275.0
-- Sectoral/Thematic,103829.0
-- Flexi Cap,63989.0
-- Large & Mid Cap,57752.0
-- Short Duration,55530.0
-- Mid Cap,55312.0
-- Small Cap,46596.0
-- Hybrid,38868.0
-- Large Cap,25633.0
-- Value/Contra,16980.0

-- Query 7: Best 3 year return funds
SELECT scheme_name, fund_house, return_3yr_pct, sharpe_ratio
FROM fact_performance
ORDER BY return_3yr_pct DESC
LIMIT 10;
-- Result sample:
-- scheme_name,fund_house,return_3yr_pct,sharpe_ratio
-- SBI Small Cap Fund - Regular Plan - Growth,SBI Mutual Fund,23.39,0.94
-- SBI Small Cap Fund - Direct Plan - Growth,SBI Mutual Fund,23.14,0.93
-- ABSL Small Cap Fund - Regular - Growth,Aditya Birla Sun Life MF,22.38,0.9
-- Axis Small Cap Fund - Regular - Growth,Axis Mutual Fund,20.98,0.84
-- Nippon India Small Cap Fund - Regular - Growth,Nippon India MF,20.15,0.81
-- DSP Small Cap Fund - Regular - Growth,DSP Mutual Fund,20.08,0.8
-- Kotak Emerging Equity Fund - Regular - Growth,Kotak Mahindra MF,18.23,0.96
-- ICICI Pru Midcap Fund - Regular - Growth,ICICI Prudential MF,18.08,0.95
-- DSP Midcap Fund - Regular - Growth,DSP Mutual Fund,17.16,0.9
-- HDFC Mid-Cap Opportunities Fund - Regular - Growth,HDFC Mutual Fund,16.58,0.87

-- Query 8: Monthly transaction amount by type
SELECT substr(transaction_date, 1, 7) AS month, transaction_type, SUM(amount_inr) AS total_amount_inr
FROM fact_transactions
GROUP BY month, transaction_type
ORDER BY month, transaction_type
LIMIT 30;
-- Result sample:
-- month,transaction_type,total_amount_inr
-- 2024-01,Lumpsum,125509831
-- 2024-01,Redemption,79503125
-- 2024-01,SIP,12635349
-- 2024-02,Lumpsum,111404051
-- 2024-02,Redemption,69871989
-- 2024-02,SIP,12613376
-- 2024-03,Lumpsum,124810113
-- 2024-03,Redemption,76554972
-- 2024-03,SIP,12088413
-- 2024-04,Lumpsum,127545599
-- 2024-04,Redemption,67445890
-- 2024-04,SIP,13512385
-- 2024-05,Lumpsum,114669898
-- 2024-05,Redemption,77237848
-- 2024-05,SIP,13218606
-- 2024-06,Lumpsum,124985567
-- 2024-06,Redemption,84148612
-- 2024-06,SIP,13131150
-- 2024-07,Lumpsum,117142475
-- 2024-07,Redemption,67075667
-- 2024-07,SIP,13513884
-- 2024-08,Lumpsum,134046496
-- 2024-08,Redemption,81237196
-- 2024-08,SIP,12521433
-- 2024-09,Lumpsum,113775104
-- 2024-09,Redemption,62497934
-- 2024-09,SIP,12288778
-- 2024-10,Lumpsum,127248200
-- 2024-10,Redemption,73935279
-- 2024-10,SIP,12467875

-- Query 9: Top portfolio sectors by market value
SELECT sector, ROUND(SUM(market_value_cr), 2) AS total_market_value_cr
FROM fact_portfolio_holdings
GROUP BY sector
ORDER BY total_market_value_cr DESC
LIMIT 10;
-- Result sample:
-- sector,total_market_value_cr
-- Banking,62840.29
-- IT,38477.11
-- Pharma,34606.1
-- Automobile,34296.97
-- Utilities,25108.63
-- Infrastructure,22433.39
-- FMCG,21151.15
-- Telecom,16051.45
-- Energy,15286.54
-- Diversified,13897.79

-- Query 10: Latest NAV with fund metadata
WITH latest_nav AS (
    SELECT amfi_code, MAX(nav_date) AS latest_date
    FROM fact_nav
    GROUP BY amfi_code
)
SELECT f.amfi_code, f.scheme_name, n.nav_date, n.nav, n.daily_return
FROM latest_nav l
JOIN fact_nav n ON n.amfi_code = l.amfi_code AND n.nav_date = l.latest_date
JOIN dim_fund f ON f.amfi_code = n.amfi_code
ORDER BY f.scheme_name
LIMIT 20;
-- Result sample:
-- amfi_code,scheme_name,nav_date,nav,daily_return
-- 101206,ABSL Frontline Equity Fund - Regular - Growth,2026-05-29,773.2939,-0.008528923797288535
-- 101208,ABSL Liquid Fund - Regular - Growth,2026-05-29,410.1021,0.0009587285424079717
-- 101207,ABSL Small Cap Fund - Regular - Growth,2026-05-29,53.9836,-0.014622695752646186
-- 119093,Axis Bluechip Fund - Direct - Growth,2026-05-29,58.4203,-0.001469927170236418
-- 119092,Axis Bluechip Fund - Regular - Growth,2026-05-29,50.8387,0.0015681917134071632
-- 119094,Axis Midcap Fund - Regular - Growth,2026-05-29,203.8581,0.007607791461895053
-- 119095,Axis Small Cap Fund - Regular - Growth,2026-05-29,56.1319,-0.008898949253035582
-- 149323,DSP Midcap Fund - Regular - Growth,2026-05-29,245.3651,-0.0027779064786387364
-- 149324,DSP Small Cap Fund - Regular - Growth,2026-05-29,279.7511,-0.0033353842514427523
-- 149322,DSP Top 100 Equity Fund - Regular - Growth,2026-05-29,606.2349,0.002064014022137961
-- 125498,HDFC Mid-Cap Opportunities Fund - Direct - Growth,2026-05-29,188.3619,-0.0019017511583249158
-- 100033,HDFC Mid-Cap Opportunities Fund - Regular - Growth,2026-05-29,342.0072,-0.00479811066935798
-- 100025,HDFC Short Term Debt Fund - Regular - Growth,2026-05-29,31.8843,-0.0008085214399202734
-- 125497,HDFC Top 100 Fund - Direct Plan - Growth,2026-05-29,1204.9571,0.0012563098012272622
-- 100016,HDFC Top 100 Fund - Regular Plan - Growth,2026-05-29,583.6113,-0.012410457010226916
-- 120504,ICICI Pru Bluechip Fund - Direct - Growth,2026-05-29,151.1311,-0.0222127475667101
-- 120503,ICICI Pru Bluechip Fund - Regular - Growth,2026-05-29,118.1496,0.012817347652553268
-- 120507,ICICI Pru Liquid Fund - Regular - Growth,2026-05-29,388.5939,0.0005821800880505545
-- 120505,ICICI Pru Midcap Fund - Regular - Growth,2026-05-29,473.764,-0.001219372335258262
-- 120506,ICICI Pru Value Discovery Fund - Regular - Growth,2026-05-29,404.4207,0.005562634966377322
