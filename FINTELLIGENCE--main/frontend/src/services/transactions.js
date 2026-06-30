export const getStatementTransactions = (api, statementId, options = {}) => {
  if (!statementId) return Promise.resolve({ transactions: [], total: 0, pages: 0, current_page: 1 });

  const params = new URLSearchParams();
  if (options.page) params.set('page', options.page);
  params.set('per_page', options.perPage || 10000);

  const suffix = params.toString() ? `?${params.toString()}` : '';
  return api(`/transactions/${statementId}${suffix}`);
};

