# 🔍 LLM Manager Usage Documentation

## 📊 Overall Summary

- **Total LLM Function Calls**: 20 functions
- **Primary Models**: GPT-4o (participant agents), GPT-4 (moderator), GPT-4-turbo (dialogue management)
- **Token Range**: 300~10,000 max_tokens (actual output: 200~1,500 tokens)
- **Actual Token Usage**: Input 74,600 + Output 37,600 = 112,200 tokens/debate
- **Cost per Debate**: **~$1.20** (optimized to ~$0.86)

---

## 🤖 1. debate_participant_agent.py - Philosopher Agents

### 1.1 Interactive Argument Stage Response Generation

#### `_generate_interactive_argument_response` (Line 995)
- **Purpose**: Generate attack/defense/followup responses in interactive argumentation
- **Model**: GPT-4o
- **Max Tokens**: 10,000
- **Expected Input Tokens**: 2,000-3,000
- **Prompt Content**: 
  - Philosopher style guidelines
  - Situation analysis (attack/defense determination)
  - Recent conversation history
  - Strategic guidelines
- **Cost Impact**: ⭐⭐⭐⭐⭐ (Most expensive call)

### 1.2 Defense Response Generation

#### `_generate_defense_response_with_strategy` (Line 1570)
- **Purpose**: Generate responses using specific defense strategies
- **Model**: GPT-4o
- **Max Tokens**: 1,000
- **Expected Input Tokens**: 1,500-2,000
- **Prompt Content**:
  - Defense strategy information (defense_strategies.json)
  - Attacker information and attack content
  - RAG search results (optional)
  - Philosopher-specific defense styles
- **Cost Impact**: ⭐⭐⭐

### 1.3 Opening Statement Argument Generation

#### `_generate_core_arguments` (Line 1865)
- **Purpose**: Generate core argument structure for opening statements
- **Model**: GPT-4o
- **Max Tokens**: 1,000
- **Expected Input Tokens**: 1,000-1,500
- **Prompt Content**:
  - Debate topic and position
  - Philosopher-specific argumentation styles
  - Requirement for 3-5 key points
- **Cost Impact**: ⭐⭐

#### `_generate_final_opening_argument` (Line 2268)
- **Purpose**: Generate final opening statement presentation
- **Model**: GPT-4o
- **Max Tokens**: 1,300
- **Expected Input Tokens**: 1,200-1,800
- **Prompt Content**:
  - Prepared core arguments
  - RAG enhancement content
  - Philosopher personality reflection
- **Cost Impact**: ⭐⭐⭐

### 1.4 RAG-Related Functions

#### `_generate_rag_queries_for_arguments` (Line 1932)
- **Purpose**: Generate RAG search queries for argument enhancement
- **Model**: GPT-4o
- **Max Tokens**: 1,200
- **Expected Input Tokens**: 800-1,200
- **Prompt Content**:
  - Core argument content
  - Philosopher domain keywords
  - Search query optimization guidelines
- **Cost Impact**: ⭐⭐

### 1.5 Argument Analysis and Strategy Formulation

#### `extract_opponent_key_points` (Line 2741)
- **Purpose**: Extract opponent's key points and analyze vulnerabilities
- **Model**: GPT-4o
- **Max Tokens**: 1,500
- **Expected Input Tokens**: 1,000-1,500
- **Prompt Content**:
  - Complete opponent statements
  - Argument structure analysis requirements
  - JSON format output specification
- **Cost Impact**: ⭐⭐⭐

#### `_extract_arguments_from_response` (Line 3001)
- **Purpose**: Extract argument structure from responses
- **Model**: GPT-4o
- **Max Tokens**: 1,200
- **Expected Input Tokens**: 800-1,200
- **Prompt Content**:
  - Response text analysis
  - Claim-evidence structure identification
  - Argument quality assessment
- **Cost Impact**: ⭐⭐

#### `_score_single_argument` (Line 3159)
- **Purpose**: Calculate vulnerability scores for individual arguments
- **Model**: GPT-4o
- **Max Tokens**: 1,200
- **Expected Input Tokens**: 1,000-1,500
- **Prompt Content**:
  - Argument content and structure
  - Vulnerability analysis criteria
  - Scoring guidelines
- **Cost Impact**: ⭐⭐

#### `_analyze_detailed_vulnerabilities` (Line 3328)
- **Purpose**: Detailed analysis of argument vulnerabilities
- **Model**: GPT-4o
- **Max Tokens**: 300
- **Expected Input Tokens**: 600-800
- **Prompt Content**:
  - Detailed argument content
  - Philosophical perspective vulnerabilities
  - Attack point identification
- **Cost Impact**: ⭐

### 1.6 Attack Strategy Formulation

#### `_select_best_strategy_for_argument` (Line 3553)
- **Purpose**: Select optimal attack strategy for each argument
- **Model**: GPT-4o
- **Max Tokens**: 800
- **Expected Input Tokens**: 700-1,000
- **Prompt Content**:
  - Target argument analysis
  - Available attack strategies
  - Effectiveness prediction
- **Cost Impact**: ⭐⭐

#### `_generate_attack_plan` (Line 3698)
- **Purpose**: Formulate specific attack plans
- **Model**: GPT-4o
- **Max Tokens**: 1,500
- **Expected Input Tokens**: 1,200-1,800
- **Prompt Content**:
  - Selected attack strategy
  - Target argument vulnerabilities
  - Philosopher-specific attack styles
- **Cost Impact**: ⭐⭐⭐

### 1.7 Followup Responses

#### `_generate_followup_response_with_strategy` (Line 4592)
- **Purpose**: Generate followup strategy-based responses
- **Model**: GPT-4o
- **Max Tokens**: 1,000
- **Expected Input Tokens**: 1,500-2,000
- **Prompt Content**:
  - Defender's response analysis
  - Followup strategy information
  - Connection to original attack
- **Cost Impact**: ⭐⭐⭐

---

## 🎯 2. moderator_agent.py - Moderator Agent

### 2.1 Debate Flow Management

#### `_generate_response_for_stage` (Line 305)
- **Purpose**: Basic moderator transition comments
- **Model**: GPT-4
- **Max Tokens**: 300
- **Expected Input Tokens**: 200-400
- **Prompt Content**:
  - Current debate stage
  - Simple transition comment requirements
  - Language matching with debate topic
- **Cost Impact**: ⭐

### 2.2 Debate Opening Introduction

#### `_generate_introduction` - Style-based (Line 448)
- **Purpose**: Debate opening introduction based on moderator style
- **Model**: GPT-4
- **Max Tokens**: 1,500
- **Expected Input Tokens**: 800-1,200
- **Prompt Content**:
  - Moderator style template
  - Debate topic and participant information
  - Pro/con position statements
- **Cost Impact**: ⭐⭐⭐

#### `_generate_introduction` - Basic (Line 501)
- **Purpose**: Basic format debate opening introduction
- **Model**: GPT-4
- **Max Tokens**: 1,500
- **Expected Input Tokens**: 600-800
- **Prompt Content**:
  - Standard moderator role
  - Debate format guidance
  - Participant introductions
- **Cost Impact**: ⭐⭐

### 2.3 Debate Moderation

#### `_moderate_qa_session` (Line 605)
- **Purpose**: Determine need for intervention in QA sessions
- **Model**: GPT-4
- **Max Tokens**: 1,500
- **Expected Input Tokens**: 400-600
- **Prompt Content**:
  - Current message analysis
  - Intervention criteria (hostility, topic deviation, etc.)
  - JSON format response
- **Cost Impact**: ⭐⭐

#### `_check_if_intervention_needed` (Line 903)
- **Purpose**: Determine general moderator intervention necessity
- **Model**: GPT-4
- **Max Tokens**: 300
- **Expected Input Tokens**: 300-500
- **Prompt Content**:
  - Message content review
  - Intervention necessity determination
  - Simple JSON response
- **Cost Impact**: ⭐

### 2.4 Debate Summary and Conclusion

#### `_generate_summary` (Line 720)
- **Purpose**: Generate mid-debate summaries
- **Model**: GPT-4
- **Max Tokens**: 1,500
- **Expected Input Tokens**: 1,000-2,000
- **Prompt Content**:
  - Stage-by-stage speech records
  - Key points from both sides
  - Neutral summary guidelines
- **Cost Impact**: ⭐⭐⭐⭐

#### `_generate_conclusion` (Line 829)
- **Purpose**: Generate debate closing remarks
- **Model**: GPT-4
- **Max Tokens**: 1,500
- **Expected Input Tokens**: 1,000-1,500
- **Prompt Content**:
  - Complete debate records
  - Final conclusions from both sides
  - Balanced closing remarks
- **Cost Impact**: ⭐⭐⭐

---

## 💬 3. debate_dialogue.py - Dialogue Management

### 3.1 Debate Initialization

#### `_generate_stance_statements` (Line 1313)
- **Purpose**: Generate pro/con position statements
- **Model**: GPT-4-turbo
- **Max Tokens**: 1,000
- **Expected Input Tokens**: 800-1,200
- **Prompt Content**:
  - Debate topic
  - Pro/con position requirements
  - Clear and specific statements
- **Cost Impact**: ⭐⭐ (One-time)

---

## 💰 Cost Analysis (Based on Actual Expected Usage)

### API Pricing (2024 Rates)
- **GPT-4o**: Input $0.005/1K tokens, Output $0.015/1K tokens
- **GPT-4**: Input $0.03/1K tokens, Output $0.06/1K tokens  
- **GPT-4-turbo**: Input $0.01/1K tokens, Output $0.03/1K tokens

### Actual Token Consumption by Stage (Per Debate)

| Stage | Function | Input Tokens | Output Tokens | Model | Cost ($) |
|-------|----------|--------------|---------------|-------|----------|
| **Initialization** | stance_statements | 400 | 300 | GPT-4-turbo | 0.013 |
| **Moderator Intro** | introduction | 800 | 400 | GPT-4 | 0.048 |
| **Opening (2 people)** | core_arguments (2x) | 2,000 | 1,000 | GPT-4o | 0.025 |
| | final_opening (2x) | 3,000 | 1,600 | GPT-4o | 0.039 |
| | rag_queries (2x) | 1,600 | 800 | GPT-4o | 0.020 |
| **Interactive Args (4 cycles)** | interactive_argument (12x) | 30,000 | 18,000 | GPT-4o | 0.420 |
| | defense_response (4x) | 8,000 | 4,000 | GPT-4o | 0.100 |
| | followup_response (4x) | 8,000 | 4,000 | GPT-4o | 0.100 |
| **Argument Analysis** | extract_opponent_points (4x) | 4,000 | 2,000 | GPT-4o | 0.050 |
| | score_arguments (8x) | 8,000 | 2,400 | GPT-4o | 0.076 |
| | select_strategy (4x) | 2,800 | 1,600 | GPT-4o | 0.038 |
| **Moderator Summary** | summary (2x) | 4,000 | 1,000 | GPT-4 | 0.180 |
| **Conclusion** | conclusion | 2,000 | 500 | GPT-4 | 0.090 |
| **Subtotal** | - | **74,600** | **37,600** | - | **$1.199** |

### Detailed Analysis

#### 🔥 High-Cost Functions (By Cost)
1. **Interactive Argument Responses** (12x): $0.420 (35%)
2. **Moderator Summaries** (2x): $0.180 (15%)  
3. **Defense Responses** (4x): $0.100 (8.3%)
4. **Followup Responses** (4x): $0.100 (8.3%)
5. **Conclusion Generation**: $0.090 (7.5%)

#### 💡 Low-Cost Functions
- **Argument Analysis**: $0.164 (13.7%)
- **Opening Generation**: $0.084 (7%)
- **Initialization**: $0.061 (5.1%)

### Optimization Strategies

#### 1. Interactive Argument Optimization (35% savings possible)
```python
# Current: max_tokens=10,000, actual output=1,500 tokens
# Improvement: max_tokens=2,000, maintain quality while simplifying responses
# Savings: 20% reduction through input token compression → $0.084 saved
```

#### 2. Moderator Function Streamlining (15% savings possible)  
```python
# Current: Using GPT-4
# Improvement: Switch to GPT-4o (5x cheaper)
# Savings: $0.270 → $0.054 = $0.216 saved
```

#### 3. Argument Analysis Batch Processing (10% savings possible)
```python
# Current: Individual API calls
# Improvement: Analyze multiple arguments in one call
# Savings: 4 API calls → 1 call = $0.041 saved
```

### Post-Optimization Expected Costs

| Item | Current Cost | Post-Optimization | Savings |
|------|--------------|-------------------|---------|
| Interactive Args | $0.420 | $0.336 | $0.084 |
| Moderator | $0.318 | $0.102 | $0.216 |
| Argument Analysis | $0.164 | $0.123 | $0.041 |
| Other | $0.297 | $0.297 | $0.000 |
| **Total** | **$1.199** | **$0.858** | **$0.341** |

**Final Optimization Effect: 28% Cost Reduction**

### Monthly Cost Projections by Usage

| Daily Debates | Monthly Cost (Current) | Monthly Cost (Optimized) | Annual Savings |
|---------------|------------------------|--------------------------|----------------|
| 1 debate | $36 | $26 | $120 |
| 5 debates | $180 | $129 | $612 |
| 10 debates | $360 | $257 | $1,236 |
| 50 debates | $1,800 | $1,287 | $6,156 |

### Real-time Monitoring Recommendations

#### 1. Token Usage Tracking
```python
# Log actual usage after each API call
logger.info(f"Function: {func_name}, Input: {input_tokens}, Output: {output_tokens}, Cost: ${cost:.4f}")
```

#### 2. Daily Usage Limits
```python
# Setting daily budget of $50
daily_budget = 50.0  # Allows approximately 41 debates
current_usage = get_daily_usage()
if current_usage > daily_budget * 0.9:  # Alert at 90%
    send_alert("Daily budget 90% reached")
```

#### 3. Cost Efficiency Metrics
```python
# Track cost vs debate quality
cost_per_quality_score = total_cost / debate_quality_rating
cost_per_participant_satisfaction = total_cost / avg_satisfaction_score
```

---

## 📝 Recommendations

### Development Phase
1. **Add token usage monitoring**
2. **Benchmark response quality vs cost**
3. **Implement caching system**

### Operations Phase  
1. **Set daily usage limits**
2. **Manage per-user quotas**
3. **Build cost alert system**

### Technical Improvements
1. **Prompt optimization** (token efficiency)
2. **Response length limits** (while maintaining quality)
3. **Batch processing** implementation (for analysis functions)

---

*Document generated: 2025-05-31*  
*Version: 1.0* 