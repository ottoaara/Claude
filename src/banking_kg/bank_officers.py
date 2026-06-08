"""
Static bank officer / board member data for relationship cross-referencing.

Used to surface:
  - Board interlocks: company officer X sits on same external board as bank officer Y
  - Alumni network: company officer X attended same school as bank officer Y

Source: Publicly available proxy statements, SEC filings, and company bios.
All information is from public records.
"""

import re
from typing import List, Dict

BANK_NAME = "Wells Fargo"

BANK_OFFICERS: List[Dict] = [
    {
        "name": "Charles W. Scharf",
        "role": "Chief Executive Officer & President",
        "role_short": "CEO",
        "is_board": True,
        "education": ["Johns Hopkins University", "NYU Stern School of Business"],
        "board_seats": ["Microsoft Corporation"],
    },
    {
        "name": "Steven D. Black",
        "role": "Independent Board Chair",
        "role_short": "Board Chair",
        "is_board": True,
        "education": ["Dartmouth College"],
        "board_seats": ["Chubb Limited", "Vail Resorts"],
    },
    {
        "name": "Mark A. Chancy",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["University of Georgia", "Georgia State University"],
        "board_seats": [],
    },
    {
        "name": "Celeste A. Clark",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["Michigan State University"],
        "board_seats": ["Kellogg Company", "Campbell Soup Company"],
    },
    {
        "name": "Theodore F. Craver Jr.",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["University of California Los Angeles", "Claremont Graduate University"],
        "board_seats": ["BrightSpring Health Services"],
    },
    {
        "name": "Wayne M. Hewett",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["Iowa State University", "Northwestern University Kellogg School of Management"],
        "board_seats": ["Bausch + Lomb", "Diversey Holdings"],
    },
    {
        "name": "Maria R. Morris",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["University of Maryland"],
        "board_seats": ["Boston Scientific", "Leidos Holdings"],
    },
    {
        "name": "Felicia F. Norwood",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["Eastern Illinois University", "Northwestern University Kellogg School of Management"],
        "board_seats": ["Elevance Health"],
    },
    {
        "name": "Richard B. Payne Jr.",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["University of Virginia Darden School of Business"],
        "board_seats": [],
    },
    {
        "name": "Juan A. Pujadas",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["University of Michigan Ross School of Business", "INSEAD"],
        "board_seats": ["Dun & Bradstreet"],
    },
    {
        "name": "Ronald L. Sargent",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["Harvard University", "Harvard Business School"],
        "board_seats": ["Waste Management", "Gap Inc."],
    },
    {
        "name": "Suzanne M. Vautrinot",
        "role": "Independent Director",
        "role_short": "Director",
        "is_board": True,
        "education": ["US Air Force Academy", "Stanford University"],
        "board_seats": ["Parsons Corporation", "Hyatt Hotels Corporation"],
    },
    {
        "name": "Kyle Hranicky",
        "role": "Head of Commercial Banking",
        "role_short": "Commercial Banking",
        "is_board": False,
        "education": ["University of Wisconsin"],
        "board_seats": [],
    },
    {
        "name": "Mike Weinbach",
        "role": "CEO of Consumer Lending",
        "role_short": "Consumer Lending",
        "is_board": False,
        "education": ["Cornell University"],
        "board_seats": [],
    },
    {
        "name": "Ather Williams III",
        "role": "Head of Strategy, Digital & Innovation",
        "role_short": "Chief Strategy Officer",
        "is_board": False,
        "education": ["Harvard University", "Harvard Business School"],
        "board_seats": [],
    },
    {
        "name": "Derek Flowers",
        "role": "Chief Risk Officer",
        "role_short": "CRO",
        "is_board": False,
        "education": ["University of Texas at Austin"],
        "board_seats": [],
    },
    {
        "name": "Michael P. Santomassimo",
        "role": "Chief Financial Officer",
        "role_short": "CFO",
        "is_board": False,
        "education": ["Fordham University", "Columbia Business School"],
        "board_seats": [],
    },
]


def _normalize_board(name: str) -> str:
    """Normalize a board/company name for fuzzy matching."""
    s = name.lower().strip()
    for suffix in [" corporation", " corp.", " corp", " incorporated", " inc.",
                   " inc", " limited", " ltd.", " ltd", " co.", " co",
                   " company", " llc", " lp", " plc", " group"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    return s


def _normalize_school(name: str) -> str:
    """Extract core school name for fuzzy comparison."""
    s = name.lower().strip()
    # Remove degree info (e.g. "Stanford University MBA" → "stanford university")
    s = re.sub(r'\b(mba|ba|bs|phd|ms|ma|jd|md|llb|bsc|mpa|mph)\b.*', '', s)
    # Remove parenthetical info
    s = re.sub(r'\(.*?\)', '', s)
    # Normalize "university of X" → "X university" for partial matching
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def boards_match(a: str, b: str) -> bool:
    """Return True if two board/company names refer to the same organization."""
    na, nb = _normalize_board(a), _normalize_board(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def schools_match(a: str, b: str) -> bool:
    """Return True if two school names refer to the same institution."""
    na, nb = _normalize_school(a), _normalize_school(b)
    if not na or not nb or len(na) < 4 or len(nb) < 4:
        return False
    return na in nb or nb in na


def get_bank_officers_from_db(kg) -> List[Dict]:
    """
    Load bank officers from Neo4j. Falls back to the static BANK_OFFICERS list
    if the database has no WF officer nodes yet.
    """
    import json as _json
    try:
        officers = kg.get_officers(BANK_NAME)
        if officers:
            # Deserialise JSON-string fields if stored that way
            for o in officers:
                for field in ("board_memberships", "education"):
                    val = o.get(field)
                    if isinstance(val, str):
                        try:
                            o[field] = _json.loads(val)
                        except Exception:
                            o[field] = [val] if val else []
            return officers
    except Exception:
        pass
    return BANK_OFFICERS


def find_relationship_connections(company_officers: List[Dict], kg=None) -> Dict:
    """
    Cross-reference company officers against BANK_OFFICERS.
    """
    import json

    bank_officers_list = get_bank_officers_from_db(kg) if kg is not None else BANK_OFFICERS

    board_connections = []
    alumni_connections = []

    # Seen sets to deduplicate
    seen_board = set()
    seen_alumni = set()

    for co in company_officers:
        co_name = co.get("name", "").strip()
        co_role = co.get("role", co.get("role_short", ""))
        if not co_name:
            continue

        # Parse board_memberships — may be stored as JSON string or list
        raw_boards = co.get("board_memberships") or []
        if isinstance(raw_boards, str):
            try:
                raw_boards = json.loads(raw_boards)
            except Exception:
                raw_boards = [raw_boards] if raw_boards else []

        # Parse education — may be stored as JSON string or list
        raw_edu = co.get("education") or []
        if isinstance(raw_edu, str):
            try:
                raw_edu = json.loads(raw_edu)
            except Exception:
                raw_edu = [raw_edu] if raw_edu else []

        for bank_officer in bank_officers_list:
            bk_name = bank_officer["name"]
            bk_role = bank_officer["role"]
            bk_role_short = bank_officer["role_short"]

            # ── Board interlocks ────────────────────────────────────────────
            for co_board in raw_boards:
                if not isinstance(co_board, str) or not co_board.strip():
                    continue
                for bk_board in (bank_officer.get("board_memberships") or bank_officer.get("board_seats") or []):
                    if boards_match(co_board, bk_board):
                        key = (co_name.lower(), bk_name.lower(), _normalize_board(co_board))
                        if key not in seen_board:
                            seen_board.add(key)
                            board_connections.append({
                                "company_officer": co_name,
                                "company_role": co_role,
                                "shared_board": co_board.strip(),
                                "bank_officer": bk_name,
                                "bank_role": bk_role,
                                "bank_role_short": bk_role_short,
                            })

            # ── Alumni network ──────────────────────────────────────────────
            for co_school in raw_edu:
                if not isinstance(co_school, str) or not co_school.strip():
                    continue
                for bk_school in bank_officer.get("education", []):
                    if schools_match(co_school, bk_school):
                        key = (co_name.lower(), bk_name.lower(), _normalize_school(co_school))
                        if key not in seen_alumni:
                            seen_alumni.add(key)
                            alumni_connections.append({
                                "company_officer": co_name,
                                "company_role": co_role,
                                "shared_school": co_school.strip(),
                                "bank_officer": bk_name,
                                "bank_role": bk_role,
                                "bank_role_short": bk_role_short,
                            })

    return {
        "board_connections": board_connections,
        "alumni_connections": alumni_connections,
        "bank_name": BANK_NAME,
    }
