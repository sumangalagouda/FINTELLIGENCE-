# import networkx as nx
# from app.models.transaction import Transaction


# def build_graph(transactions: list) -> nx.MultiDiGraph:
#     """
#     Build transaction graph from transactions.

#     Uses MultiDiGraph so multiple transactions between
#     the same sender and receiver are preserved.
#     """

#     G = nx.MultiDiGraph()

#     nodes = {}

#     for t in transactions:

#         u = t.sender_account
#         v = t.receiver_account
#         amt = float(t.amount or 0)
#         t_date = t.date

#         # Substitute placeholders for missing accounts so they appear in the graph
#         if not u:
#             u = "SELF"
#         if not v:
#             v = "UNKNOWN"

#         # Initialize sender node
#         if u not in nodes:
#             nodes[u] = {
#                 "total_received": 0.0,
#                 "total_sent": 0.0,
#                 "transaction_count": 0,
#                 "first_seen": t_date,
#                 "last_seen": t_date,
#                 "risk_score": 0.0
#             }

#         # Initialize receiver node
#         if v not in nodes:
#             nodes[v] = {
#                 "total_received": 0.0,
#                 "total_sent": 0.0,
#                 "transaction_count": 0,
#                 "first_seen": t_date,
#                 "last_seen": t_date,
#                 "risk_score": 0.0
#             }

#         # Sender stats
#         nodes[u]["total_sent"] += amt
#         nodes[u]["transaction_count"] += 1

#         if t_date:
#             if nodes[u]["first_seen"] is None or t_date < nodes[u]["first_seen"]:
#                 nodes[u]["first_seen"] = t_date

#             if nodes[u]["last_seen"] is None or t_date > nodes[u]["last_seen"]:
#                 nodes[u]["last_seen"] = t_date

#         # Receiver stats
#         nodes[v]["total_received"] += amt
#         nodes[v]["transaction_count"] += 1

#         if t_date:
#             if nodes[v]["first_seen"] is None or t_date < nodes[v]["first_seen"]:
#                 nodes[v]["first_seen"] = t_date

#             if nodes[v]["last_seen"] is None or t_date > nodes[v]["last_seen"]:
#                 nodes[v]["last_seen"] = t_date

#         # Suspicious transaction flag
#         is_suspicious = amt >= 500000

#         # MultiDiGraph preserves multiple transactions
#         G.add_edge(
#             u,
#             v,
#             txn_id=t.id,
#             amount=amt,
#             weight=amt,
#             date=str(t_date) if t_date else None,
#             description=t.description,
#             type=t.type,
#             is_suspicious=is_suspicious
#         )

#     # Add node attributes
#     for node_id, attrs in nodes.items():

#         if attrs["first_seen"]:
#             attrs["first_seen"] = str(attrs["first_seen"])

#         if attrs["last_seen"]:
#             attrs["last_seen"] = str(attrs["last_seen"])

#         G.add_node(node_id, **attrs)

#     return G


# def build_multi_statement_graph(case_id: str) -> nx.MultiDiGraph:
#     """
#     Build graph from all transactions in a case.
#     """
#     transactions = Transaction.query.filter_by(
#         case_id=case_id,
#         is_failed=False
#     ).all()

#     return build_graph(transactions)


# def graph_to_json(G):
#     """
#     Convert graph to JSON serializable format.
#     """
#     from networkx.readwrite import json_graph

#     return json_graph.node_link_data(G)

import re
import networkx as nx
from app.models.transaction import Transaction


# ============================================================================
# CONFIGURATION
# ============================================================================

SUSPICIOUS_THRESHOLD = 200000


# ============================================================================
# HELPERS
# ============================================================================

def extract_receiver(transaction):
    """
    Extract beneficiary from receiver_account or narration.
    """

    if transaction.receiver_account:
        return transaction.receiver_account.strip().upper()

    if not transaction.description:
        return None

    description = transaction.description.upper()

    patterns = [
        r"UPI/(?:DR|CR)/[^/]+/([^/]+)/",
        r"IMPS/[^/]+/[^/]+/([^/]+)/?",
        r"TO\s+([A-Z ]+)",
    ]

    for pattern in patterns:

        match = re.search(pattern, description)

        if match:
            return match.group(1).strip()

    return None


# ============================================================================
# GRAPH BUILDER
# ============================================================================

def build_graph(transactions: list) -> nx.MultiDiGraph:
    """
    Build transaction graph from transactions.

    MultiDiGraph preserves multiple transfers
    between the same accounts.
    """

    G = nx.MultiDiGraph()
    nodes = {}

    for t in transactions:

        u = t.sender_account or "ACCOUNT_HOLDER"

        v = (
            extract_receiver(t)
            or f"UNKNOWN_{t.id}"
        )

        amt = abs(float(t.amount or 0))
        t_date = t.date

        # ==============================================================
        # INITIALIZE SENDER
        # ==============================================================

        if u not in nodes:

            nodes[u] = {
                "total_received": 0.0,
                "total_sent": 0.0,
                "incoming_count": 0,
                "outgoing_count": 0,
                "transaction_count": 0,
                "first_seen": t_date,
                "last_seen": t_date,
                "risk_score": 0.0
            }

        # ==============================================================
        # INITIALIZE RECEIVER
        # ==============================================================

        if v not in nodes:

            nodes[v] = {
                "total_received": 0.0,
                "total_sent": 0.0,
                "incoming_count": 0,
                "outgoing_count": 0,
                "transaction_count": 0,
                "first_seen": t_date,
                "last_seen": t_date,
                "risk_score": 0.0
            }

        # ==============================================================
        # UPDATE SENDER
        # ==============================================================

        nodes[u]["total_sent"] += amt
        nodes[u]["outgoing_count"] += 1

        # ==============================================================
        # UPDATE RECEIVER
        # ==============================================================

        nodes[v]["total_received"] += amt
        nodes[v]["incoming_count"] += 1

        # ==============================================================
        # TOTAL TRANSACTION COUNT
        # ==============================================================

        nodes[u]["transaction_count"] = (
            nodes[u]["incoming_count"]
            + nodes[u]["outgoing_count"]
        )

        nodes[v]["transaction_count"] = (
            nodes[v]["incoming_count"]
            + nodes[v]["outgoing_count"]
        )

        # ==============================================================
        # FIRST/LAST SEEN
        # ==============================================================

        if t_date:

            if (
                nodes[u]["first_seen"] is None
                or t_date < nodes[u]["first_seen"]
            ):
                nodes[u]["first_seen"] = t_date

            if (
                nodes[u]["last_seen"] is None
                or t_date > nodes[u]["last_seen"]
            ):
                nodes[u]["last_seen"] = t_date

            if (
                nodes[v]["first_seen"] is None
                or t_date < nodes[v]["first_seen"]
            ):
                nodes[v]["first_seen"] = t_date

            if (
                nodes[v]["last_seen"] is None
                or t_date > nodes[v]["last_seen"]
            ):
                nodes[v]["last_seen"] = t_date

        # ==============================================================
        # EDGE ATTRIBUTES
        # ==============================================================

        is_suspicious = (
            amt >= SUSPICIOUS_THRESHOLD
        )

        G.add_edge(
            u,
            v,
            txn_id=t.id,
            amount=amt,
            weight=amt,
            date=(
                t_date.isoformat()
                if t_date
                else None
            ),
            description=t.description,
            type=getattr(t, "type", None),
            is_suspicious=is_suspicious
        )

    # ==================================================================
    # ADD NODE ATTRIBUTES
    # ==================================================================

    for node_id, attrs in nodes.items():

        if attrs["first_seen"]:
            attrs["first_seen"] = (
                attrs["first_seen"].isoformat()
            )

        if attrs["last_seen"]:
            attrs["last_seen"] = (
                attrs["last_seen"].isoformat()
            )

        G.add_node(node_id, **attrs)

    return G


# ============================================================================
# MULTI-STATEMENT GRAPH
# ============================================================================

def build_multi_statement_graph(
    case_id: str
) -> nx.MultiDiGraph:

    transactions = (
        Transaction.query
        .filter_by(
            case_id=case_id,
            is_failed=False
        )
        .all()
    )

    return build_graph(transactions)


# ============================================================================
# JSON SERIALIZATION
# ============================================================================

def graph_to_json(G):

    from networkx.readwrite import json_graph

    return json_graph.node_link_data(G)