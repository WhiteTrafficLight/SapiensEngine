# Philosopher Data Structure Documentation

This document explains the structure and meaning of philosopher data defined in the `debate_optimized.yaml` file.

## 📁 File Structure

```
philosophers/
├── debate_optimized.yaml     # Philosopher data definitions
├── strategy_rag_weights.yaml # RAG usage weights by strategy
├── debate_strategies.json    # Attack strategy style definitions
└── README.md                 # This document
```

## 🧠 Philosopher Data Structure

Each philosopher is defined with the following structure:

```yaml
philosopher_name:
  name: "Philosopher Name"
  essence: "Core philosophical identity"
  debate_style: "Speaking style in debates"
  personality: "Personality characteristics"
  key_traits: ["Key trait 1", "Key trait 2", "Key trait 3"]
  quote: "Representative quote"
  rag_affinity: 0.0-1.0
  rag_stats: { ... }
  vulnerability_sensitivity: { ... }
  strategy_weights: { ... }
```

## 🎯 Strategy Weights (Attack Strategy Weights)

Weight values for attack strategies each philosopher prefers when attacking opponents. All values sum to 1.0.

**Strategy Definitions**: Detailed information for each strategy can be found in the `debate_strategies.json` file.

| Strategy | Description | Example |
|----------|-------------|---------|
| **Clipping** | Pinpointing specific parts of opponent's argument to expose weaknesses | "Your definition of 'freedom' is ambiguous" |
| **Framing Shift** | Changing the discussion frame to put opponent in disadvantageous position | "This is not an individual issue but a social structural problem" |
| **Reductive Paradox** | Pushing opponent's logic to extremes to reveal contradictions | "By that logic, all actions would be justified" |
| **Conceptual Undermining** | Attacking the validity of concepts used by opponent | "We need to reexamine the very concept of 'justice' you're using" |
| **Ethical Reversal** | Pointing out ethical problems in opponent's argument | "That is a morally unacceptable conclusion" |
| **Temporal Delay** | Pointing out limitations of opponent's argument from temporal perspective | "That's an outdated perspective that doesn't apply today" |
| **Philosophical Reframing** | Reinterpreting from a different philosophical perspective | "From an ontological perspective, it has a completely different meaning" |

### Strategy Preferences by Philosopher:
- **Socrates**: Clipping (0.35) - Exposing logical gaps through questioning
- **Nietzsche**: Framing Shift (0.25) - Overturning existing value frameworks
- **Kant**: Reductive Paradox (0.3) - Pursuing logical consistency
- **Wittgenstein**: Conceptual Undermining (0.5) - Seeking clarity in language and concepts

## 🎯 Vulnerability Sensitivity

Indicates how sensitively each philosopher reacts to different types of vulnerabilities in opponents.

| Vulnerability Type | Description | Philosophers with High Sensitivity |
|--------------------|-------------|----------------------------------|
| **conceptual_clarity** | Ambiguity or lack of clarity in concepts | Socrates(0.9), Wittgenstein(0.9) |
| **logical_leap** | Logical gaps or insufficient evidence | Aristotle(0.7), Beauvoir(0.7) |
| **overgeneralization** | Excessive generalization | Aristotle(0.8), Beauvoir(0.8) |
| **emotional_appeal** | Arguments appealing to emotion | Camus(0.9), Nietzsche(0.8) |
| **lack_of_concrete_evidence** | Lack of concrete evidence or examples | Aristotle(0.9), Marx(0.8) |

### Sensitivity Score Interpretation:
- **0.8-1.0**: Very high sensitivity - Immediate attack when such vulnerabilities are found
- **0.6-0.7**: High sensitivity - Recognized as important attack points
- **0.4-0.5**: Moderate sensitivity - Attack decision depends on situation
- **0.1-0.3**: Low sensitivity - Not much concern

## 🤖 RAG Stats (RAG Usage Determination Stats)

Five characteristics that determine each philosopher's likelihood of using RAG (Retrieval-Augmented Generation).

| Stat | Description | Related Strategies | High Score Philosophers |
|------|-------------|-------------------|-------------------------|
| **data_respect** | Tendency to value external evidence and facts | Clipping, Temporal Delay | Aristotle(0.9), Marx(0.9) |
| **conceptual_precision** | Tendency to demand conceptual accuracy and clarity | Conceptual Undermining, Framing Shift | Socrates(0.9), Kant(0.9), Wittgenstein(0.9) |
| **systematic_logic** | Preference for logical structure and systematic connections | Reductive Paradox, Philosophical Reframing | Hegel(0.9), Kant(0.9) |
| **pragmatic_orientation** | Preference for persuasion based on actual experience/cases | Clipping, Ethical Reversal | Beauvoir(0.9), Confucius(0.8), Marx(0.8) |
| **rhetorical_independence** | Intuitive, informal, and metaphorical tendencies<br/>(Higher values = less RAG usage) | Inversely related to most strategies | Laozi(0.9), Nietzsche(0.9), Camus(0.8) |

### RAG Usage Decision Logic:
```
Old Method (Simple):
RAG Usage Probability = (data_respect + conceptual_precision + systematic_logic + pragmatic_orientation - rhetorical_independence) / 4

New Method (Strategy-weighted):
RAG Score = Σ(strategy_weight[i] × philosopher_rag_stat[i])
```

**RAG Weights by Strategy** (see `strategy_rag_weights.yaml`):
- Each attack strategy has different weights for the 5 RAG stats
- RAG usage is dynamically determined based on philosopher's chosen strategy
- Threshold: 0.3+ for RAG usage, 0.6+ for intensive RAG usage

### RAG Usage Tendencies by Philosopher:
- **High RAG Usage**: Wittgenstein, Kant, Aristotle - Prefer accurate information and systematic arguments
- **Medium RAG Usage**: Plato, Hegel, Marx - Selective usage depending on situation
- **Low RAG Usage**: Nietzsche, Camus, Laozi - Prefer intuition and metaphorical expression

## 📊 Other Attributes

### rag_affinity (RAG Affinity)
- **Range**: 0.0 - 1.0
- **Meaning**: How much the philosopher prefers external information or systematic evidence
- **Usage**: Reference for determining RAG system utilization

### Philosopher Characteristic Summary

| Philosopher | Main Strategy | Main Vulnerability Sensitivity | RAG Tendency |
|-------------|---------------|-------------------------------|--------------|
| **Socrates** | Logical attack through questioning | Conceptual ambiguity | Medium |
| **Plato** | Frame shifting | Lack of concrete evidence | High |
| **Aristotle** | Systematic analysis | Overgeneralization | Very High |
| **Kant** | Pointing out logical contradictions | Conceptual accuracy | Very High |
| **Nietzsche** | Value subversion | Emotional appeals | Low |
| **Hegel** | Dialectical synthesis | Conceptual clarity | High |
| **Marx** | Social frame shifting | Lack of concrete evidence | High |
| **Sartre** | Existential perspective | Emotional appeals | Medium |
| **Camus** | Absurdity acknowledgment | Emotional appeals | Low |
| **Beauvoir** | Concrete experience analysis | Overgeneralization | High |
| **Rousseau** | Naturalness vs. sociality | Emotional appeals | Medium |
| **Confucius** | Practical ethics | Balanced across various | Medium |
| **Laozi** | Paradox and metaphor | Emotional appeals | Very Low |
| **Buddha** | Middle way approach | Overgeneralization | Medium |
| **Wittgenstein** | Conceptual analysis | Conceptual clarity | Very High |

## 🔧 Data Usage

This data is utilized as follows:

1. **Attack Strategy Selection**: Determine appropriate attack methods based on `strategy_weights`
2. **Vulnerability Detection**: Prioritize opponent's weaknesses through `vulnerability_sensitivity`
3. **RAG Usage Decision**: Determine need for external information retrieval by synthesizing `rag_stats`
4. **Speaking Style**: Maintain consistent character through `debate_style` and `personality`

## 📝 Modification Guide

When adding new philosophers or modifying existing data:

1. **Maintain Consistency**: Configure to align with each philosopher's actual philosophical positions
2. **Balance Adjustment**: Adjust so `strategy_weights` sum to 1.0
3. **Relative Comparison**: Set values considering relative differences with other philosophers
4. **Testing**: Verify alignment with expected behavior in actual debates 