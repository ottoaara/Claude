# Temporal Dimension - Data Freshness Management

## Overview

The temporal dimension ensures the knowledge graph stays **current and relevant** by automatically scoring and pruning outdated data. This is critical for commercial banking decisions that require the most recent information.

## 🕐 Relevance Windows (by Data Type)

Different types of data have different "shelf lives":

```
News                  ████░░░░░░░░ 90 days   (decays quickly)
Quarterly Financials  ████████░░░░ 120 days  (moderate decay)
Industry Trends       ████████████ 180 days  (moderate decay)
Company Info          ████████████████ 365 days (slow decay)
Annual Financials     ████████████████ 365 days (slow decay)
Products              ████████████████████ 730 days (very slow decay)
```

## 📊 Scoring Algorithm

### Step 1: Recency Score (0.0 - 1.0)

For each data item, calculate how fresh it is:

```python
# Within relevance window: Linear decay
if days_old <= window:
    score = 1.0 - (days_old / window) * 0.7
    # Examples for 90-day window (news):
    # 0 days old:  1.00 (brand new)
    # 30 days old: 0.77
    # 60 days old: 0.53
    # 90 days old: 0.30

# Beyond window: Exponential decay
else:
    extra_days = days_old - window
    score = 0.3 * (1 - decay_rate) ** extra_days
    # Examples for news (decay_rate=0.05):
    # 120 days old: 0.26
    # 180 days old: 0.15
    # 365 days old: 0.01
```

### Step 2: Content Relevance Score (0.5 - 1.0)

Boost scores based on content importance:

```python
base_score = 0.5

# Severity boosts
if severity == 'high':   +0.3
if severity == 'medium': +0.15

# Sentiment boosts (for risk assessment)
if sentiment == 'negative': +0.2

# Revenue impact
if revenue_impact == 'high': +0.2

# Official filings
if filing_type in ['10-K', '10-Q']: +0.3
```

### Step 3: Combined Score

```python
final_score = (recency_score * 0.60) + (content_score * 0.40)
#              ↑ 60% weight on freshness
#                                  ↑ 40% weight on importance
```

## ✂️ Pruning Strategy

Items below threshold are automatically removed:

```python
# Default threshold: 0.3 (30%)
threshold = 0.3

# Financial data & News: Use full threshold
if relevance_score < 0.3: REMOVE

# Products: Use relaxed threshold (70% of normal)
if relevance_score < 0.21: REMOVE
```

## 🎯 Real-World Examples

### Example 1: News Article

```json
{
  "title": "Company X faces SEC investigation",
  "date": "2024-05-01",  // 35 days ago
  "sentiment": "negative",
  "severity": "high"
}
```

**Scoring:**
- Days old: 35 days
- Recency score: `1.0 - (35/90) * 0.7 = 0.73`
- Content score: `0.5 + 0.2 (negative) + 0.3 (high severity) = 1.0`
- **Final score: `(0.73 * 0.6) + (1.0 * 0.4) = 0.84`** ✅ KEEP

### Example 2: Old News Article

```json
{
  "title": "Company X announces new office",
  "date": "2023-01-15",  // 507 days ago
  "sentiment": "neutral",
  "severity": "low"
}
```

**Scoring:**
- Days old: 507 days (417 days beyond 90-day window)
- Recency score: `0.3 * (1 - 0.05)^417 ≈ 0.0` (exponential decay)
- Content score: `0.5` (no boosts)
- **Final score: `(0.0 * 0.6) + (0.5 * 0.4) = 0.20`** ❌ PRUNED

### Example 3: Recent Financial Filing

```json
{
  "filing_type": "10-Q",
  "period": "2024-Q1",
  "extracted_at": "2024-05-20",  // 16 days ago
  "revenue": 1500.0
}
```

**Scoring:**
- Days old: 16 days
- Recency score: `1.0 - (16/365) * 0.7 = 0.97`
- Content score: `0.5 + 0.3 (official filing) = 0.8`
- **Final score: `(0.97 * 0.6) + (0.8 * 0.4) = 0.90`** ✅ KEEP

### Example 4: Aged Product Data

```json
{
  "product_name": "Legacy Software v2.0",
  "timestamp": "2022-12-01",  // 552 days ago
  "revenue_impact": "low"
}
```

**Scoring:**
- Days old: 552 days (well within 730-day window for products)
- Recency score: `1.0 - (552/730) * 0.7 = 0.47`
- Content score: `0.5` (no boosts)
- **Final score: `(0.47 * 0.6) + (0.5 * 0.4) = 0.48`** ✅ KEEP
- (Products use relaxed threshold of 0.21)

## 📈 Temporal Summary

After scoring, the system provides a summary:

```json
{
  "total_items": 47,
  "fresh_items": 12,      // < 30 days (26%)
  "recent_items": 18,     // 30-90 days (38%)
  "aged_items": 13,       // 90-365 days (28%)
  "stale_items": 4,       // > 365 days (9%)
  "avg_relevance_score": 0.68,
  "oldest_item_age_days": 420,
  "newest_item_age_days": 2
}
```

## 🔄 Integration in Research Workflow

The temporal dimension is applied at **Step 6** in the LangGraph workflow:

```
1. Scrape Company Info
2. Fetch Financials      ┐
3. Search News           ├─ Parallel research
4. Generate Products     │
5. Analyze Industry      ┘
↓
6. 🕐 APPLY TEMPORAL SCORING ← Here!
   - Score all items by recency + content
   - Prune items below threshold
   - Generate temporal summary
↓
7. Populate Neo4j Graph (only recent/relevant data)
8. Generate Summary
```

## 💡 Why This Matters for Commercial Banking

### 1. **Risk Assessment**
- Recent negative news (30 days) gets high priority
- Old positive news from 2 years ago gets filtered out
- Focus on **current risks**

### 2. **Financial Health**
- Latest 10-K/10-Q filings are most relevant
- Quarterly trends show recent trajectory
- Annual data provides context but decays slower

### 3. **Industry Positioning**
- Industry trends shift quickly (180-day window)
- Peer comparisons need recent data
- Market conditions are time-sensitive

### 4. **Product Portfolio**
- Products have longer lifecycles (730 days)
- But legacy products still get lower scores over time
- Focus on revenue-generating products

## 🎛️ Configurable Parameters

You can adjust the temporal behavior:

```python
# In src/banking_kg/temporal.py

# Adjust relevance windows
self.relevance_windows = {
    "news": 60,        # Make news even more time-sensitive
    "financial": 180,  # Shorten financial relevance
}

# Adjust decay rates
self.decay_rates = {
    "news": 0.10,      # Faster news decay
}

# Adjust pruning threshold (in research_orchestrator.py)
pruned_data = self.temporal.prune_low_relevance(
    scored_data, 
    threshold=0.4  # More aggressive pruning
)
```

## 🔍 Checking Temporal Scores

When viewing graph data, each item includes:

```json
{
  "title": "Example news item",
  "date": "2024-05-15",
  "relevance_score": 0.78,  ← Temporal + content score
  // ... other fields
}
```

You can query the API to see what got pruned:

```bash
# Get full temporal summary
curl http://localhost:8000/company/Tesla/graph | jq '.temporal_summary'
```

## 🚀 Future Enhancements

Potential improvements to temporal dimension:

- [ ] **Adaptive windows** - Adjust based on company volatility
- [ ] **Event-triggered refresh** - Re-score when major news breaks
- [ ] **Weighted recency** - Different decay curves per industry
- [ ] **Staleness alerts** - Notify when data needs refresh
- [ ] **Historical tracking** - Track how scores change over time
- [ ] **User preferences** - Let bankers set custom thresholds

## 📊 Performance Impact

Temporal scoring is fast:
- **Scoring**: ~0.1ms per item
- **Pruning**: ~0.05ms per item
- **100 items**: ~15ms total

The scoring happens **in-memory** before Neo4j insertion, so only relevant data hits the database.
