export const getCaseGraph = (api, caseId) => {
  if (!caseId) return Promise.resolve({ nodes: [], links: [] });
  return api(`/graph/${caseId}`);
};

