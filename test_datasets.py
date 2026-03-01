"""
Sample test datasets for benchmarking AETHER.
Add your own labeled test cases here.
"""

# Consistency Test Prompts (no ground truth needed)
CONSISTENCY_PROMPTS = [
    "Nuclear energy is the key to solving climate change",
    "Remote work decreases productivity in software teams",
    "AI will replace most creative jobs by 2030",
    "Universal basic income should be implemented globally",
    "Cryptocurrency is the future of finance",
    "Genetic engineering of humans should be banned",
    "Space exploration is a waste of resources",
    "Social media does more harm than good",
    "Electric vehicles will dominate by 2035",
    "Organic food is healthier than conventional food"
]

# Labeled Test Cases (with ground truth)
# ground_truth should be "POSITIVE" or "NEGATIVE"
LABELED_TEST_CASES = [
    {
        "prompt": "Solar panels typically pay for themselves within 5-7 years",
        "ground_truth": "POSITIVE",
        "source": "NREL 2024 ROI study",
        "category": "energy"
    },
    {
        "prompt": "Working from home reduces carbon emissions from commuting",
        "ground_truth": "POSITIVE",
        "source": "IEA Transport Report 2023",
        "category": "environment"
    },
    {
        "prompt": "Artificial sweeteners are healthier than sugar",
        "ground_truth": "NEGATIVE",
        "source": "Mixed evidence, no clear consensus",
        "category": "health"
    },
    {
        "prompt": "Bitcoin mining consumes more energy than most countries",
        "ground_truth": "POSITIVE",
        "source": "Cambridge Bitcoin Electricity Index",
        "category": "technology"
    },
    {
        "prompt": "Remote work increases employee engagement and satisfaction",
        "ground_truth": "NEGATIVE",
        "source": "Studies show mixed results, depends on role",
        "category": "work"
    },
    {
        "prompt": "Renewable energy is now cheaper than fossil fuels",
        "ground_truth": "POSITIVE",
        "source": "IRENA 2023 Cost Report",
        "category": "energy"
    },
    {
        "prompt": "Social media causes depression in teenagers",
        "ground_truth": "POSITIVE",
        "source": "Multiple meta-analyses confirm correlation",
        "category": "health"
    },
    {
        "prompt": "Self-driving cars will reduce traffic accidents by 90%",
        "ground_truth": "NEGATIVE",
        "source": "Overly optimistic, current data shows 30-50%",
        "category": "technology"
    },
    {
        "prompt": "Plant-based diets reduce risk of heart disease",
        "ground_truth": "POSITIVE",
        "source": "American Heart Association studies",
        "category": "health"
    },
    {
        "prompt": "Homework improves academic performance in elementary school",
        "ground_truth": "NEGATIVE",
        "source": "Research shows minimal benefit under age 12",
        "category": "education"
    }
]

# Real-World Historical Cases (for retroactive validation)
HISTORICAL_CASES = [
    {
        "prompt": "Tesla will become the most valuable car company by 2025",
        "ground_truth": "POSITIVE",
        "date_made": "2020-01-01",
        "outcome_date": "2023-06-01",
        "actual_outcome": "POSITIVE",
        "notes": "Tesla market cap exceeded traditional automakers"
    },
    {
        "prompt": "Cryptocurrency will replace traditional banking by 2025",
        "ground_truth": "NEGATIVE",
        "date_made": "2020-01-01",
        "outcome_date": "2025-12-01",
        "actual_outcome": "NEGATIVE",
        "notes": "Crypto adoption grew but didn't replace banks"
    },
    {
        "prompt": "Remote work will disappear after COVID-19 pandemic ends",
        "ground_truth": "NEGATIVE",
        "date_made": "2021-03-01",
        "outcome_date": "2024-01-01",
        "actual_outcome": "NEGATIVE",
        "notes": "Hybrid/remote remained prevalent"
    }
]

# Domain-Specific Test Sets
TECH_STARTUPS = [
    {
        "prompt": "A social network for pet owners will gain 10M users in 2 years",
        "ground_truth": "NEGATIVE",
        "category": "startup_viability"
    },
    {
        "prompt": "An AI-powered code review tool will save developers 5+ hours per week",
        "ground_truth": "POSITIVE",
        "category": "startup_viability"
    }
]

POLICY_PROPOSALS = [
    {
        "prompt": "Banning plastic bags reduces ocean pollution",
        "ground_truth": "POSITIVE",
        "category": "policy_impact"
    },
    {
        "prompt": "Raising minimum wage always increases unemployment",
        "ground_truth": "NEGATIVE",
        "category": "policy_impact"
    }
]

TECHNICAL_FEASIBILITY = [
    {
        "prompt": "A mobile app can achieve 99.99% uptime on a single server",
        "ground_truth": "NEGATIVE",
        "category": "technical"
    },
    {
        "prompt": "Machine learning can improve spam detection accuracy beyond 95%",
        "ground_truth": "POSITIVE",
        "category": "technical"
    }
]
