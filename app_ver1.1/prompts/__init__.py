"""
Prompt và template cho hệ thống DB search
"""

# Export từ constants.py
from prompts.constants import (
    FIELDS, 
    VALID_DIEU_KIEN_GIAO_HANG, 
    TRANSACTION_STATUSES,
    FUZZY_SEARCH_FIELDS,
    REGEX_SEARCH_FIELDS,
    EXACT_MATCH_FIELDS
)

# Export từ search_decision.py
from prompts.search_decision import (
    get_mongodb_decision_prompt,
    MONGODB_DECISION_PROMPT,
)

# Export từ mongo_pipeline.py
from prompts.mongo_pipeline import (
    get_mongodb_search_template,
    get_generate_search_query_schema,
    create_custom_search_template,
    MONGODB_SEARCH_TEMPLATE,
    GENERATE_SEARCH_QUERY_SCHEMA
)

__all__ = [
    'FIELDS',
    'VALID_DIEU_KIEN_GIAO_HANG',
    'TRANSACTION_STATUSES',
    'FUZZY_SEARCH_FIELDS',
    'REGEX_SEARCH_FIELDS',
    'EXACT_MATCH_FIELDS',
    'get_mongodb_decision_prompt',
    'get_tool_decision_prompt',
    'MONGODB_DECISION_PROMPT',
    'TOOL_DECISION_PROMPT',
    'get_mongodb_search_template',
    'get_generate_search_query_schema',
    'create_custom_search_template',
    'MONGODB_SEARCH_TEMPLATE',
    'GENERATE_SEARCH_QUERY_SCHEMA'
]
