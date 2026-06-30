def fifo_trace_funds(account_id, transactions):
    """
    Maintains a FIFO queue of incoming funds.
    Each outgoing transaction consumes from 
    the OLDEST available inflow first.
    """
    inflow_queue = []  # ordered list, oldest first
    traced_outflows = []
    
    sorted_txns = sorted(transactions, 
                          key=lambda t: t.date)
    
    for txn in sorted_txns:
        if txn.receiver_account == account_id:
            # It's an inflow
            inflow_queue.append({
                'source_txn_id': txn.id,
                'original_amount': txn.amount,
                'remaining': txn.amount,
                'date': txn.date.isoformat() if txn.date else None
            })
        
        elif txn.sender_account == account_id:
            # It's an outflow
            remaining_to_consume = txn.amount
            consumed_from = []
            
            while remaining_to_consume > 0 and inflow_queue:
                oldest_inflow = inflow_queue[0]
                consume_amount = min(
                    oldest_inflow['remaining'],
                    remaining_to_consume
                )
                
                consumed_from.append({
                    'source_txn_id': oldest_inflow['source_txn_id'],
                    'amount_consumed': consume_amount,
                    'source_date': oldest_inflow['date']
                })
                
                oldest_inflow['remaining'] -= consume_amount
                remaining_to_consume -= consume_amount
                
                if oldest_inflow['remaining'] <= 0:
                    inflow_queue.pop(0)
            
            traced_outflows.append({
                'outflow_txn_id': txn.id,
                'outflow_amount': txn.amount,
                'outflow_date': txn.date.isoformat() if txn.date else None,
                'funded_by': consumed_from,
                'fully_traced': remaining_to_consume == 0
            })
    
    return traced_outflows
