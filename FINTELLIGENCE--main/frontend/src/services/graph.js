export const getCaseGraph = (api, caseId) => {
  if (!caseId) return Promise.resolve({ nodes: [], links: [] });
  return api(`/graph/${caseId}`);
};

export const reconstructTrail = (api, caseId) => {
  if (!caseId) return Promise.resolve({ trail: [] });
  return api('/graph/reconstruct-trail', {
    method: 'POST',
    body: JSON.stringify({ case_id: caseId }),
  });
};

export const detectCircularFlow = (api, caseId) => {
  if (!caseId) return Promise.resolve([]);
  return api('/detect/circular-flow', {
    method: 'POST',
    body: JSON.stringify({ case_id: caseId }),
  });
};

export const detectLayering = (api, caseId) => {
  if (!caseId) return Promise.resolve([]);
  return api('/detect/layering-chain', {
    method: 'POST',
    body: JSON.stringify({ case_id: caseId }),
  });
};
