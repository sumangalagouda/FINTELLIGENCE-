import networkx as nx
import pandas as pd

MAX_DEPTH = 10
MAX_LAYERING_DAYS = 7
MIN_AMOUNT_RETENTION = 0.50


def find_layering_chains(graph: nx.MultiDiGraph):

    results = []
    processed_chains = set()

    def get_best_edge(u, v):
        """
        MultiDiGraph may contain multiple transactions between
        the same accounts.

        Prefer the transaction with the largest amount.
        """
        edge_dict = graph[u][v]

        if not edge_dict:
            return None

        return max(
            edge_dict.values(),
            key=lambda x: x.get("weight", 0)
        )

    def calculate_score(chain_length, amount_retention):

        score = 65

        # Longer chains are more suspicious
        score += min((chain_length - 2) * 8, 20)

        # Strong amount preservation
        if amount_retention >= 0.9:
            score += 10
        elif amount_retention >= 0.75:
            score += 5

        return min(100, int(score))

    def dfs(current_node,
            current_path,
            current_amount,
            current_date,
            start_amount):

        # ==========================================================
        # ALERT GENERATION
        # Trigger from A → B → C onwards
        # ==========================================================
        if len(current_path) >= 3:

            chain_key = tuple(current_path)

            if chain_key not in processed_chains:

                processed_chains.add(chain_key)

                chain_str = " → ".join(current_path)

                transactions_involved = []

                for i in range(len(current_path) - 1):

                    u = current_path[i]
                    v = current_path[i + 1]

                    edge_data = get_best_edge(u, v)

                    if edge_data:

                        txn_id = edge_data.get("txn_id")

                        if txn_id:
                            transactions_involved.append(txn_id)

                amount_retention = (
                    current_amount / start_amount
                    if start_amount > 0 else 1.0
                )

                hop_count = len(current_path) - 1

                score = calculate_score(
                    hop_count,
                    amount_retention
                )

                if hop_count >= 4:
                    severity = "critical"
                elif hop_count == 3:
                    severity = "high"
                else:
                    severity = "medium"

                results.append({
                    "detector": "LayeringChain",
                    "triggered": True,
                    "score": score,
                    "reason":
                        f"Potential layering chain detected: "
                        f"{chain_str} "
                        f"({hop_count} hops over "
                        f"{MAX_LAYERING_DAYS} days).",
                    "transactions_involved":
                        transactions_involved,
                    "severity": severity,
                    "metadata": {
                        "chain": current_path,
                        "chain_length": hop_count,
                        "hop_count": hop_count,
                        "amount_retention_pct":
                            round(amount_retention * 100, 2)
                    }
                })

        if len(current_path) >= MAX_DEPTH:
            return

        # ==========================================================
        # EXPLORE NEXT HOPS
        # ==========================================================
        for neighbor in graph.successors(current_node):

            # Prevent cycles
            if neighbor in current_path:
                continue

            edge_data = get_best_edge(
                current_node,
                neighbor
            )

            if not edge_data:
                continue

            next_amount = edge_data.get(
                "weight",
                0.0
            )

            date_str = edge_data.get("date")

            if not date_str:
                continue

            # ======================================================
            # ROBUST DATE PARSING
            # Handles:
            #   2024-04-30
            #   30-04-2024
            #   timestamps
            # ======================================================
            next_date = pd.to_datetime(
                date_str,
                errors="coerce",
                dayfirst=True
            )

            if pd.isna(next_date):
                continue

            next_date = next_date.date()

            # ======================================================
            # TEMPORAL CONSTRAINT
            # Allow up to 7 days between hops
            # ======================================================
            if current_date:

                days_diff = (
                    next_date - current_date
                ).days

                if days_diff < 0:
                    continue

                if days_diff > MAX_LAYERING_DAYS:
                    continue

            # ======================================================
            # AMOUNT RETENTION
            # Allow up to 50% reduction
            # ======================================================
            if current_amount > 0:

                if next_amount < (
                    MIN_AMOUNT_RETENTION
                    * current_amount
                ):
                    continue

            dfs(
                neighbor,
                current_path + [neighbor],
                next_amount,
                next_date,
                start_amount
            )

    # ==============================================================
    # START DFS FROM EVERY EDGE
    # ==============================================================
    for source in graph.nodes:

        for target in graph.successors(source):

            edge_data = get_best_edge(
                source,
                target
            )

            if not edge_data:
                continue

            amount = edge_data.get(
                "weight",
                0.0
            )

            date_str = edge_data.get("date")

            if not date_str:
                continue

            start_date = pd.to_datetime(
                date_str,
                errors="coerce",
                dayfirst=True
            )

            if pd.isna(start_date):
                continue

            dfs(
                target,
                [source, target],
                amount,
                start_date.date(),
                amount
            )

    return results