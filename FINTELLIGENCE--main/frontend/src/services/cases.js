export const listCases = (api) => api('/cases/');

export const getCaseDetail = (api, caseId) => api(`/cases/${caseId}`);

export const getCaseTransactions = (api, caseId) => api(`/cases/${caseId}/transactions`);

export const createCase = (api, payload) =>
  api('/cases/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

