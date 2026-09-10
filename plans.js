const planForm = document.querySelector('#plan-form');
const planStatus = document.querySelector('#plan-status');
const saveButton = document.querySelector('#save-plan');
const restoreButton = document.querySelector('#restore-plan');
const apiBase = (window.BLOOM_API_URL || '').replace(/\/$/, '');
let backendReady = false;

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}/api${path}`, { ...options, signal: AbortSignal.timeout(10000) });
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Saved plans are not connected yet. You can still use the calculator.');
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
  return data;
}

async function checkConnection() {
  try {
    const health = await api('/health');
    backendReady = health.service === 'bloom-plans' && health.available === true;
    if (!backendReady) throw new Error('Unavailable');
    planStatus.textContent = 'Ready to save. Plans are stored for 30 days.';
    saveButton.disabled = false;
    restoreButton.disabled = false;
  } catch {
    planStatus.textContent = 'Saving is not available on this site yet. You can still explore the calculator and budget check.';
  }
}

planForm.addEventListener('submit', async event => {
  event.preventDefault();
  if (!backendReady) return;
  saveButton.disabled = true;
  planStatus.textContent = 'Saving your plan…';
  try {
    const data = await api('/plans', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: Number(amount.value), months: Number(term.value), purpose: document.querySelector('#purpose').value })
    });
    document.querySelector('#saved-reference').textContent = data.reference;
    document.querySelector('#saved-result').hidden = false;
    document.querySelector('#plan-reference').value = data.reference;
    planStatus.textContent = 'Your plan is saved. Keep the reference below to open it again.';
  } catch (error) {
    planStatus.textContent = error.name === 'TimeoutError' ? 'The request timed out. Saving could not be confirmed. Please try again.' : error.message;
  } finally { saveButton.disabled = false; }
});

document.querySelector('#restore-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!backendReady) return;
  const status = document.querySelector('#restore-status');
  restoreButton.disabled = true;
  status.textContent = 'Opening your plan…';
  try {
    const reference = document.querySelector('#plan-reference').value.trim().toLowerCase();
    const data = await api(`/plans/${encodeURIComponent(reference)}`);
    amount.value = data.amount;
    term.value = data.months;
    document.querySelector('#purpose').value = data.purpose;
    calculate();
    document.querySelector('#budget-result').textContent = 'A saved plan was opened. Run the budget check again for an updated result.';
    status.textContent = 'Plan opened. Your calculator and purpose have been updated.';
    document.querySelector('#calculator').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  } catch (error) { status.textContent = error.name === 'TimeoutError' ? 'The request timed out. Please try again.' : error.message; }
  finally { restoreButton.disabled = false; }
});

document.querySelector('#budget-form').addEventListener('submit', event => {
  event.preventDefault();
  const income = Number(document.querySelector('#income').value);
  const expenses = Number(document.querySelector('#expenses').value);
  const payment = Number(amount.value) * 0.02 / (1 - Math.pow(1.02, -Number(term.value)));
  const remaining = income - expenses - payment;
  document.querySelector('#budget-result').textContent = remaining >= 0
    ? `With this example repayment, you would have ${money(remaining)} left each month after the expenses you entered. Allow room for irregular costs and savings too.`
    : `With this example repayment, your expenses would exceed your monthly income by ${money(Math.abs(remaining))}. Try a smaller amount or review your budget.`;
});
[amount, term].forEach(input => input.addEventListener('input', () => { document.querySelector('#budget-result').textContent = 'Your loan example changed. Run the budget check again for an updated result.'; }));
document.querySelectorAll('[data-amount]').forEach(link => link.addEventListener('click', () => { document.querySelector('#budget-result').textContent = 'Your loan example changed. Run the budget check again for an updated result.'; }));
checkConnection();
