# Operational Metric Formulas

| Category | Metric | Description | Formula | Custom Metric? |
|----------|--------|-------------|---------|----------------|
| Volume & Throughput | Average Daily Rate | Average number of transactions or events occurring per day over a given period | `Total Events / Number of Days in Period` | Yes |
| Volume & Throughput | Click-Through Rate | Ratio of users who clicked on a result vs. total users who were shown it | `Total Clicks / Total Impressions` | No — client sends as column |
| Volume & Throughput | Contact Rate | Ratio of customers who contacted support vs. total customers served | `Customer Contacts / Total Customers Served` | No — client sends as column |
| Volume & Throughput | Days to Closing | Average number of days between an event being opened (e.g. application, deal) and it being closed/resolved | `AVG(Close Date - Open Date)` | Yes |
| Volume & Throughput | Lift in Average Daily Balance | Percentage change in average daily balance relative to a baseline period (e.g. pre-model vs. post-model) | `(ADB_current - ADB_baseline) / ADB_baseline × 100` | Yes |
| Volume & Throughput | Lift in Revenue | Percentage increase in revenue attributable to the model vs. a baseline or control group | `(Revenue_treatment - Revenue_control) / Revenue_control × 100` | Yes |
| Volume & Throughput | Lift in Settled Sales | Percentage increase in settled/completed sales vs. a baseline period or control group | `(Settled_treatment - Settled_control) / Settled_control × 100` | Yes |
| Volume & Throughput | Points to Double Odds | Scorecard metric expressing how many score points are needed to double the odds of the target outcome (e.g. default, approval) | `log(2) / b` where `b` = log-odds coefficient on score | Yes |
| Volume & Throughput | Score Utilization Percentage | Percentage of eligible decisions where the model score was actually used vs. overridden or bypassed | `Decisions Using Score / Total Eligible Decisions × 100` | No — client sends as column |
| Volume & Throughput | Volume (General) | Total number of inferences/predictions made by the model in a given time period | `COUNT(inference_id) per time_bucket` | No — default Inference Count |
| Volume & Throughput | Volume (LLM) | Total number of LLM inference calls made in a given time period | `COUNT(inference_id) per time_bucket` | No — default Inference Count (GenAI) |
| Volume & Throughput | API Call Volumes | Total number of API requests made to an external or internal service over time, not tied to Arthur inferences | `COUNT(api_request_id) per time_bucket` | Yes |
| Efficiency | Cost | Total or average cost of running the model, derived from token usage × rate for LLMs or compute time for traditional ML | `SUM(prompt_tokens + completion_tokens) × cost_per_token` (LLM) or `SUM(compute_time) × cost_per_unit` | No — embedded in Arthur Agentic Monitoring |
| Efficiency | API Latency | Average time (ms) between an API request being sent to an external service and a response being received | `AVG(response_timestamp - request_timestamp) per time_bucket` | No — default Latency |
| Efficiency | Latency | Average end-to-end model inference latency from request to response | `AVG(inference_end - inference_start) per time_bucket` | No — default Latency |
| Reliability | User Complaints | Total number of user-submitted complaints or negative feedback signals over a time period, sourced from an external system | `COUNT(complaint_id) per time_bucket` | No — client sends as column |
| Reliability | API Error Rates | Ratio of failed API calls to total calls; ratio surfaced at chart layer from error count + total count columns | `COUNT(status != 2xx) / COUNT(total requests) × 100` | No — ratio derived at chart layer |
| Reliability | HTTP Errors | Count of HTTP error responses (4xx/5xx); ratio surfaced at chart layer from error count + total count columns | `COUNT(status_code >= 400) / COUNT(total requests) × 100` | No — ratio derived at chart layer |
